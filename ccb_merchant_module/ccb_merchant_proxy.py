#!/usr/bin/env python
# coding=utf-8
"""
本模块包括建设银行支付退款和查询业务的底层封装，封装类
BnakProxy: 建设银行业务的代理类
    @@环境：银行客户端和验签客户端服务，具体可联系银行开户人员
    @@调用：
        action_obj = BankProxy(order_code=order_code, action="PAY", user=user)
        result_str = action_obj.proxy_bank()
    @@关键参数与返回值：
        1、action = 'PAY'
            功能： 调用建设银行的聚合二维码，返回二维码图像数据
            result_str： 成功， 返回支付二维码图像数据
                         失败， 抛出QRCodeError 信息

        2、action = 'QUERY_PAY'
            功能： 调用建设银行的客户端服务，返回订单的支付结果
            result_str： 成功， 返回银行的支付状态信息，ORDER_STATUS_SUCCESS[0] or ORDER_STATUS_REFUND[0]
                         失败， 抛出OrderPayError 信息，或者其他异常信息

        3、action = 'REFUND'
            功能： 调用建设银行的客户端服务，执行建行支付订单退款
            result_str： 成功， 执行银行退款，返回True
                         失败， 抛出异常信息

        4、action = 'QUERY_REFUND' （支持查询）
            功能： 调用建设银行的客户端服务，返回订单的退款结果
            result_str： 成功， 返回银行的订单状态信息，ORDER_STATUS_SUCCESS[0] or ORDER_STATUS_REFUND[0]
                         失败， 抛出异常信息

open_bank_reply：银行回调函数的实现方法

"""
from django.db import transaction
from django.conf import settings
from importlib import import_module
from utils import *

if not settings.CMMC_ORDER_MODELS_CONF:
    raise ImportError(u"客户端关联订单模块找不到.")
if not settings.CMMC_ORDER_NAME:
    raise Exception(u"请正确配置订单名-CMMC_ORDER_NAME.")

order_module = import_module(settings.CMMC_ORDER_MODELS_CONF)
Order = getattr(order_module, settings.CMMC_ORDER_NAME, None)
if not Order:
    raise Exception(u"订单配置错误")

# 检查Order的字段是否配置正确
if not getattr(Order, settings.CMMC_ORDER_PAY_AMOUNT, None):
    raise Exception(u"订单付款金额字段配置错误")
if not getattr(Order, settings.CMMC_ORDER_PAY_STATUS, None):
    raise Exception(u"订单付款状态字段配置错误")
if not getattr(Order, settings.CMMC_ORDER_PAY_TIME, None):
    raise Exception(u"订单付款时间字段配置错误")
if settings.CMMC_ORDER_CODE_CONF:
    if not getattr(Order, settings.CMMC_ORDER_CODE_CONF, None):
        raise Exception(u"订单号字段配置错误")

import requests
import hashlib
import logging
import json
import urllib
import StringIO
import qrcode
import traceback
import xml.etree.ElementTree as ET
from lxml import etree
import socket
import datetime
logger = logging.getLogger(__name__)


class AuthError(Exception):
    """
        权限错误
    """
    pass


class ActionError(Exception):
    """
        操作错误
    """
    pass


class OrderError(Exception):
    """
        订单错误
    """
    pass


class QRCodeError(Exception):
    """
        生产二维码错误
    """
    pass


class OrderPayError(Exception):
    """
        支付异常
    """
    pass


class TcpProxy(object):
    """
        socket connection to bank tools
    """
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock

    def connect(self, host, port):
        self.sock.connect((host, port))

    def send_data(self, data):
        self.sock.sendall(data)

    def receive_data(self):
        chunks = ""
        chunk = self.sock.recv(2048)
        while chunk:
            chunks += chunk
            chunk = self.sock.recv(2048)
        self.sock.close()
        return chunks


class BankProxy(object):
    """
        银行系统代理
    """
    Version = "0.0.1"
    Action = ["REFUND", "QUERY_PAY", "QUERY_REFUND", "PAY"]
    Prompt = "Bank proxy module"

    def __init__(self, order_code=None, action=None, user=None):
        if not user:
            raise AuthError(u"需要用户权限")
        self.user = user
        if action not in self.Action:
            raise ActionError(u"动作命令错误")
        self.action = action
        if not order_code:
            raise OrderError(u"订单号错误")
        try:
            if settings.CMMC_ORDER_CODE_CONF:
                self.order = Order.objects.get(**{settings.CMMC_ORDER_CODE_CONF: order_code,
                                                  settings.CMMC_ORDER_DEL_FLAG: FLAG_NO})
            else:
                self.order = Order.objects.get(del_flag=FLAG_NO, order_code=order_code)
        except:
            raise OrderError(u"订单号错误")
        self.merchant_id = settings.BANK_MERCHANT_ID
        self.pos_id = settings.BANK_POS_ID
        self.user_id = settings.BANK_USER_ID
        self.branch_id = settings.BANK_BRANCH_ID
        self.user_password = settings.BANK_USER_PASSWORD
        self.public_key = settings.BANK_PUBLIC_KEY
        self.cash_code = '01'
        self.proxy_url = settings.BANK_PROXY_URL

    @staticmethod
    def proxy_connection(url, method="POST", content_type=None, data=None):
        """
            静态函数，请求建行url地址并返回结果
            :param url : 建行url地址
            :param method: 请求动作
            :param content_type: "text/xml", 传送xml
            :param data: 传送内容，
        """
        headers = {"Content_type": content_type} if content_type else None
        try:
            if method != "POST":
                re = requests.get(url, params=data)
            else:
                if headers:
                    re = requests.post(url, data=data, headers=headers)
                else:
                    re = requests.post(url, data=data)
            if re.status_code == requests.codes.ok:
                # fixme 可能返回的结果编码不一致
                return re.text
            else:
                raise re.raise_for_status()
        except:
            raise

    def pay_qrcode(self):
        """
            生成集合二维码，否则抛出异常
        """
        def md5_generate(byte_str):
            """
                md5 hash
                :param byte_str: string in byte
            """
            if not isinstance(byte_str, str):
                raise Exception(u"请输入byte类型的字符串")
            md5_obj = hashlib.md5()
            md5_obj.update(byte_str)
            return md5_obj.hexdigest()

        def qrcode_generate(qrcode_url_str):
            """
                生成聚合二维码数据
            """
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qrcode_url_str)
            qr.make(fit=True)
            img = qr.make_image()
            string_io = StringIO.StringIO()
            img.save(string_io, "PNG")
            return string_io.getvalue()

        raw_str_list = ["MERCHANTID=" + self.merchant_id, "POSID=" + self.pos_id, "BRANCHID=" + self.branch_id,
                        "ORDERID=" + getattr(self.order, settings.CMMC_ORDER_CODE_CONF),
                        "PAYMENT=" + getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT),
                        "CURCODE=" + self.cash_code, "TXCODE=" + "530550", "REMARK1=" + "", "REMARK2=" + "",
                        "RETURNTYPE=" + str(3), "TIMEOUT=" + "", "PUB=" + self.public_key[-30:]]
        raw_str = "&".join(raw_str_list).encode("UTF-8")
        mac_hash = md5_generate(raw_str)
        query_params = {"CCB_IBSVersion": "V6",
                        "MERCHANTID": self.merchant_id, "POSID": self.pos_id, "BRANCHID": self.branch_id,
                        "ORDERID": getattr(self.order, settings.CMMC_ORDER_CODE_CONF),
                        "PAYMENT": getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT), "CURCODE": self.cash_code,
                        "REMARK1": "", "REMARK2": "", "TXCODE": "530550", "RETURNTYPE": 3, "TIMEOUT": "",
                        "MAC": mac_hash}
        qrcode_url = "https://ibsbjstar.ccb.com.cn/CCBIS/ccbMain"
        response_1 = self.proxy_connection(qrcode_url, method="POST", data=query_params)
        response_json_1 = json.loads(response_1)
        if response_json_1["SUCCESS"] == "true":
            if response_json_1.get("ERRCODE", ""):
                raise QRCodeError(u"{0}: {1}".format(response_json_1['ERRCODE']), response_json_1.get("ERRMSG"))
            response_2 = self.proxy_connection(response_json_1['PAYURL'], method="GET")
            response_json_2 = json.loads(response_2)
            if response_json_2["SUCCESS"] == "true":
                if response_json_2.get("ERRCODE", ""):
                    raise QRCodeError(u"{0}: {1}".format(response_json_2['ERRCODE']), response_json_2.get("ERRMSG"))
                qrcode_str = urllib.unquote(response_json_2['QRURL'])
                # 生成付款吗
                return qrcode_generate(qrcode_str)
            else:
                raise QRCodeError(u"二维码生成错误")
        else:
            raise QRCodeError(u"二维码生成错误")

    @staticmethod
    def xml_generate(encoding='utf-8', xml_declaration=None, standalone=None, data={}):
        """
        create xml use data info, the data is a dict that contains all info about the xml file,
        without the declaration. This is a simple complition about two level xml.
        :params @ encoding: encoding type
                @ xml_declaration: xml header if use
                @ standalone: [None | True | False]  if standalone use
                @ data: two level data info to create xml
        :return @ xml_string: the string reprents xml using encoding encoded.
        """
        data_keys = data.keys()
        if len(data_keys) != 1:
            raise Exception(u"数据信息错误")
        root_key = data_keys[0]
        root = ET.Element(root_key)
        root_info = data[root_key]
        for key, value in root_info.items():
            node = ET.SubElement(root, key)
            if isinstance(value, dict):
                for key1, value1 in value.items():
                    node1 = ET.SubElement(node, key1)
                    node1.text = unicode(value1)
            else:
                node.text = unicode(value)
        xml_string = ET.tostring(root, encoding="utf-8")
        xml_tree = etree.fromstring(xml_string).getroottree()
        return etree.tostring(xml_tree, xml_declaration=xml_declaration, encoding=encoding, standalone=standalone)

    @staticmethod
    def xml_parse_return_code(xml_string):
        """
            xml解析函数，判断xml返回结果是否正确。
            lxml etree decode xml string using the xml declaration encoding format
            ：return [T|F]
        """
        root = etree.fromstring(xml_string).getroottree()
        return_code = root.find("RETURN_CODE").text
        return_msg = root.find("RETURN_MSG").text
        return return_code, return_msg

    def bank_proxy_connection(self, sn=1):
        """
            银行连接操作
        """

        def create_xml(request_sn=sn):
            """生成有顺序的xml格式"""
            tx_root = etree.Element("TX")
            etree.SubElement(tx_root, "REQUEST_SN").text = str(request_sn)
            etree.SubElement(tx_root, "CUST_ID").text = self.merchant_id
            etree.SubElement(tx_root, "USER_ID").text = self.user_id
            etree.SubElement(tx_root, "PASSWORD").text = self.user_password
            etree.SubElement(tx_root, "TX_CODE").text = "5W1001"
            etree.SubElement(tx_root, "LANGUAGE").text = "CN"
            tx_info = etree.SubElement(tx_root, "TX_INFO")
            etree.SubElement(tx_info, "REM1").text = ""
            etree.SubElement(tx_info, "REM2").text = ""
            return etree.tostring(tx_root, xml_declaration=True, encoding="GB2312", standalone=True)

        try:
            # fixme the dict key is arbitrary to output
            # connection_xml = self.xml_generate(encoding="GB2312", xml_declaration=True, standalone=True, data=data)
            connection_xml = create_xml(sn)
            sock_connect = TcpProxy()
            sock_connect.connect(settings.BANK_TOOLS_HOST, settings.BANK_TOOLS_PORT)
            sock_connect.send_data(connection_xml)
            connection_resp = sock_connect.receive_data()
            # connection_resp = self.proxy_connection(self.proxy_url, method="POST", content_type="text/xml",
            #                                         data=connection_xml)
            resp_code, resp_msg = self.xml_parse_return_code(connection_resp)
            if resp_code != "000000":
                raise Exception(u"{0}".format(resp_msg))
            else:
                return True
        except Exception as ex:
            error_info = traceback.format_exc()
            logger.error(u"[{0}: fatal error-{1}-[trace infos -{2}]]".format(self.Prompt, ex.message, error_info))
            raise ex

    def bank_query_pay(self):
        sn = self.order.id
        data = {"TX": {"REQUEST_SN": sn, "CUST_ID": self.merchant_id, "USER_ID": self.user_id,
                       "PASSWORD": self.user_password, "TX_CODE": "5W1002", "LANGUAGE": "CN",
                       "TX_INFO": {"START": "", "STARTHOUR": "", "STARTMIN": "",
                                   "END": "", "ENDHOUR": "", "ENDMIN": "",
                                   "KIND": "0", "ORDER": getattr(self.order, settings.CMMC_ORDER_CODE_CONF),
                                   "ACCOUNT": "", "DEXCEL": "1", "MONEY": "",
                                   "NORDERBY": "2", "PAGE": "", "POS_CODE": self.pos_id,
                                   "STATUS": "3"}
                       }
                }
        if self.bank_proxy_connection(sn):
            xml_query_pay = self.xml_generate(encoding="GB2312", xml_declaration=True, standalone=True, data=data)
            # resp_query = self.proxy_connection(self.proxy_url, "POST", "text/xml", xml_query_pay)
            socket_connect = TcpProxy()
            socket_connect.connect(settings.BANK_TOOLS_HOST, settings.BANK_TOOLS_PORT)
            socket_connect.send_data(xml_query_pay)
            resp_query = socket_connect.receive_data()
            resp_code, resp_msg = self.xml_parse_return_code(resp_query)
            if resp_code != "000000":
                raise OrderPayError(u"{0}".format(resp_msg))
            else:
                root = etree.fromstring(resp_query).getroottree()
                query_order = root.xpath("//ORDER")[0].text
                query_amount = root.xpath("//PAYMENT_MONEY")[0].text
                query_status = root.xpath("//ORDER_STATUS")[0].text
                if query_order != getattr(self.order, settings.CMMC_ORDER_CODE_CONF) or \
                        float(query_amount) != getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT):
                    raise Exception(u"账单号/支付金额不匹配")
                else:
                    return query_status
        else:
            raise Exception(u"bank connection error")

    def bank_query_refund(self):
        sn = self.order.id
        data = {"TX": {"REQUEST_SN": sn, "CUST_ID": self.merchant_id, "USER_ID": self.user_id,
                       "PASSWORD": self.user_password, "TX_CODE": "5W1003", "LANGUAGE": "CN",
                       "TX_INFO": {"START": "", "STARTHOUR": "", "STARTMIN": "",
                                   "END": "", "ENDHOUR": "", "ENDMIN": "",
                                   "KIND": "0", "ORDER": getattr(self.order, settings.CMMC_ORDER_CODE_CONF),
                                   "ACCOUNT": "", "DEXCEL": "1", "MONEY": "",
                                   "NORDERBY": "2", "PAGE": "", "POS_CODE": self.pos_id,
                                   "STATUS": "3"}
                       }
                }
        if self.bank_proxy_connection(sn):
            xml_query_refund = self.xml_generate(encoding="GB2312", xml_declaration=True, standalone=True, data=data)
            # resp_query = self.proxy_connection(self.proxy_url, "POST", "text/xml", xml_query_refund)
            socket_connect = TcpProxy()
            socket_connect.connect(settings.BANK_TOOLS_HOST, settings.BANK_TOOLS_PORT)
            socket_connect.send_data(xml_query_refund)
            resp_query = socket_connect.receive_data()
            resp_code, resp_msg = self.xml_parse_return_code(resp_query)
            if resp_code != "000000":
                raise Exception(u"{0}".format(resp_msg))
            else:
                root = etree.fromstring(resp_query).getroottree()
                query_order = root.xpath("//ORDER")[0].text
                query_status = root.xpath("//ORDER_STATUS")[0].text
                query_refund_amount = root.xpath("//REFUNDEMENT_AMOUNT")[0].text
                if query_order != getattr(self.order, settings.CMMC_ORDER_CODE_CONF) or \
                        float(query_refund_amount) != getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT):
                    raise Exception(u"账单号/退款支付金额不匹配")
                else:
                    return query_status
        else:
            raise Exception(u"bank connection error")

    def bank_refund(self):
        def create_xml_refund(request_sn, money, order_code):
            """生成有顺序的xml格式"""
            tx_root = etree.Element("TX")
            etree.SubElement(tx_root, "REQUEST_SN").text = str(request_sn)
            etree.SubElement(tx_root, "CUST_ID").text = self.merchant_id
            etree.SubElement(tx_root, "USER_ID").text = self.user_id
            etree.SubElement(tx_root, "PASSWORD").text = self.user_password
            etree.SubElement(tx_root, "TX_CODE").text = "5W1004"
            etree.SubElement(tx_root, "LANGUAGE").text = "CN"
            tx_info = etree.SubElement(tx_root, "TX_INFO")
            etree.SubElement(tx_info, "MONEY").text = str(money)
            etree.SubElement(tx_info, "ORDER").text = order_code
            etree.SubElement(tx_info, "SIGN_INFO").text = ""
            etree.SubElement(tx_info, "SIGNCERT").text = ""
            return etree.tostring(tx_root, xml_declaration=True, encoding="GB2312", standalone=True)

        sn = self.order.id

        if self.bank_proxy_connection(sn):
            # xml_refund = self.xml_generate(encoding="GB2312", xml_declaration=True, standalone=True, data=data)
            # resp_query = self.proxy_connection(self.proxy_url, "POST", "text/xml", xml_refund)
            xml_refund = create_xml_refund(sn, getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT),
                                           getattr(self.order, settings.CMMC_ORDER_CODE_CONF))
            socket_connect = TcpProxy()
            socket_connect.connect(settings.BANK_TOOLS_HOST, settings.BANK_TOOLS_PORT)
            socket_connect.send_data(xml_refund)
            resp_query = socket_connect.receive_data()
            resp_code, resp_msg = self.xml_parse_return_code(resp_query)
            if resp_code != "000000":
                raise Exception(u"{0}".format(resp_msg))
            else:
                root = etree.fromstring(resp_query).getroottree()
                query_order = root.xpath("//ORDER_NUM")[0].text
                query_refund_amount = root.xpath("//AMOUNT")[0].text
                if query_order != getattr(self.order, settings.CMMC_ORDER_CODE_CONF) or \
                        float(query_refund_amount) != getattr(self.order, settings.CMMC_ORDER_PAY_AMOUNT):
                    raise Exception(u"账单号/退款支付金额不匹配")
                else:
                    return True
        else:
            raise Exception(u"bank connection error")

    def proxy_bank(self):
        if self.action == self.Action[0]:
            return self.bank_refund()
        elif self.action == self.Action[1]:
            return self.bank_query_pay()
        elif self.action == self.Action[2]:
            return self.bank_query_refund()
        else:
            return self.pay_qrcode()


@transaction.atomic
def open_bank_reply(request):
    """
        建设银行回调接口，银行通知订单是否已经支付
    """
    logger.debug(u"debug in bank verify: request GET is {}".format(request.GET))
    logger.debug(u"debug in bank verify: request POST is {}".format(request.POST))
    pos_id = request.POST.get("POSID", "") if not request.GET.get("POSID", "") else request.GET.get("POSID", "")
    branch_id = request.POST.get("BRANCHID", "") if not request.GET.get("BRANCHID", "") else request.GET.get("BRANCHID", "")
    order_id = request.POST.get("ORDERID", "") if not request.GET.get("ORDERID", "") else request.GET.get("ORDERID", "")
    payment = request.POST.get("PAYMENT", "") if not request.GET.get("PAYMENT", "") else request.GET.get("PAYMENT", "")
    curcode = request.POST.get("CURCODE", "") if not request.GET.get("CURCODE", "") else request.GET.get("CURCODE", "")
    remark_1 = request.POST.get("REMARK1", "") if not request.GET.get("REMARK1", "") else request.GET.get("REMARK1", "")
    remark_2 = request.POST.get("REMARK2", "") if not request.GET.get("REMARK2", "") else request.GET.get("REMARK2", "")
    acc_type = request.POST.get("ACC_TYPE", "") if not request.GET.get("ACC_TYPE", "") else request.GET.get("ACC_TYPE", "")
    success = request.POST.get("SUCCESS", "") if not request.GET.get("SUCCESS", "") else request.GET.get("SUCCESS", "")
    sign = request.POST.get("SIGN", "") if not request.GET.get("SIGN", "") else request.GET.get("SIGN", "")

    raw_str_verfy = "POSID=" + pos_id + "&BRANCHID=" + branch_id + "&ORDERID=" + order_id + "&PAYMENT=" + payment + \
    "&CURCODE=" + curcode + "&REMARK1=" + remark_1 + "&REMARK2=" + remark_2 + "&ACC_TYPE=" + acc_type + "&SUCCESS=" \
                    + success + "&SIGN=" + sign
    # mind the EOF is \n
    raw_str_verfy += "\n"
    # todo something to verify the request bank reply
    # here yes
    boolean = bank_verify_sign(raw_str_verfy)
    if boolean:
        order_obj = Order.objects.filter(**{settings.CMMC_ORDER_DEL_FLAG: FLAG_NO,
                                            settings.CMMC_ORDER_CODE_CONF: order_id,
                                            settings.CMMC_ORDER_PAY_STATUS: ORDER_CHOICE_0[0]}).first()
        if not order_obj:
            return
        setattr(order_obj, settings.CMMC_ORDER_PAY_STATUS, ORDER_CHOICE_2[0])
        setattr(order_obj, settings.CMMC_ORDER_PAY_TIME, datetime.datetime.now())
        order_obj.save()
        logger.debug(u"[in api bank open reply]: order pay has been ensured .")
    else:
        return


def bank_verify_sign(raw_str):
    """
        建设银行验签
    """
    logger.debug(u"bank_verify_sign string is {}".format(raw_str))
    socket_connect = TcpProxy()
    socket_connect.connect(settings.BANK_TOOLS_HOST, settings.BANK_VERIFY_PORT)
    socket_connect.send_data(raw_str)
    resp = socket_connect.receive_data()
    logger.debug(u"bank verify result is {}".format(resp))
    result = resp[0]
    if result.lower() == "n":
        return False
    elif result.lower() == "y":
        return True
    else:
        return False
