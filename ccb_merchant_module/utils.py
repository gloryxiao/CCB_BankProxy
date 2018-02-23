#!/usr/bin/env python
# coding=utf-8

# 状态标志
FLAG_YES = 1
FLAG_NO = 0

# 订单标志
ORDER_CHOICE_0 = (0, u"未支付")
ORDER_CHOICE_1 = (1, u"已取消")
ORDER_CHOICE_2 = (2, u"已支付")
ORDER_CHOICE_3 = (3, u"申请退款")
ORDER_CHOICE_4 = (4, u"退款已拒绝")
ORDER_CHOICE_5 = (5, u"退款中")
ORDER_CHOICE_6 = (6, u"已退款")

ORDER_CHOICES = (ORDER_CHOICE_0, ORDER_CHOICE_1, ORDER_CHOICE_2, ORDER_CHOICE_3, ORDER_CHOICE_4, ORDER_CHOICE_5,
                 ORDER_CHOICE_6)
REFUND_CHOICES = (ORDER_CHOICE_3, ORDER_CHOICE_4, ORDER_CHOICE_5, ORDER_CHOICE_6)

# 建行相关信息记录
# 流水查询状态 支付&退款
ORDER_STATUS_FAIL = (0, u"失败")
ORDER_STATUS_SUCCESS = (1, u"成功")
ORDER_STATUS_WAIT = (2, u"待银行确认")
ORDER_STATUS_REFUND_PART = (3, u"已部分退款")
ORDER_STATUS_REFUND = (4, u"已全额退款")
ORDER_STATUS_WAIT_1 = (5, u"待银行确认")


import logging
from err_code import *
from django.conf import settings

logger = logging.getLogger(__name__)

# 是否检查登录
IS_CHECK_LOGIN = True


def auth_check(request, method="POST", role=None, check_login=True):
    dict_resp = {}

    log_request(request)
    if not IS_CHECK_LOGIN:
        return dict_resp

    if check_login:
        if not request.user.is_authenticated():
            dict_resp = {'c': ERR_USER_NOTLOGGED[0], 'm': ERR_USER_NOTLOGGED[1]}
            return dict_resp

        if role:
            if role not in get_user_role(request.user):
                dict_resp = {'c': ERR_USER_AUTH[0], 'm': ERR_USER_AUTH[1]}
                return dict_resp

    if request.method != method.upper():
        dict_resp = {'c': ERR_REQUESTWAY[0], 'm': ERR_REQUESTWAY[1]}
        return dict_resp

    return dict_resp


def log_request(request):
    # self.start_time = time.time()
    remote_addr = request.META.get('REMOTE_ADDR')
    if remote_addr in getattr(settings, 'INTERNAL_IPS', []):
        remote_addr = request.META.get('HTTP_X_FORWARDED_FOR') or remote_addr
    if hasattr(request, 'user'):
        user_account = getattr(request.user, 'username', '-')
    else:
        user_account = 'nobody-user'
    if 'POST' == str(request.method):
        logger.info('[POST] %s %s %s :' % (remote_addr, user_account, request.get_full_path()))
        # info(request.POST)
    if 'GET' == str(request.method):
        logger.info('[GET] %s %s %s :' % (remote_addr, user_account, request.get_full_path()))
        # info(request.GET)


def get_user_role(user):
    user_role_list = list()
    user_role_list.append(user.type)
    return user_role_list
