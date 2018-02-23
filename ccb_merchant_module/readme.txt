^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@
建设银行交易（聚合二维码支付，退款，查询）接口解耦合实现，分离建行交易操作和订单设计，实现订单设计的自由性
Author: Sean
Date  : Feb 22, 2018
L     : Python Django
Open Source

^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@

@@-@@ 订单models表项约定：
    约定1：建议使用order_code作为订单表的订单码，否则请修改源码中的order_code字段为自定义字段名，或者定义订单代码字段的
    自定义变量，并在setting中配置，在django db中使用kwargs参数定制。
    ex:
    class Order(models.Model):
        order_code = models.CharField(default="", unique=True, max_length=32, verbose_name=u"订单号")

    约定2：使用建设银行给定的订单码生成规则，详细信息请参见建行商户文档。

@@-@@ setting配置

    # ******************************建行设置(生产环境)*******************************
    BANK_PUBLIC_KEY = "xxxxxxxx"
    BANK_MERCHANT_ID = "xxxxxxxx"
    BANK_POS_ID = "xxxxxxxx"
    BANK_BRANCH_ID = "xxxxxxxx"
    BANK_USER_ID = "xxxxxxxx-001"
    BANK_USER_PASSWORD = "xxxxxxxx"
    PREFIX_ORDER_CODE = BANK_MERCHANT_ID
    BANK_PROXY_URL = "192.168.100.25:xxxxxxxx"
    BANK_TOOLS_HOST = "192.168.100.25"
    BANK_TOOLS_PORT = xxxxxxxx
    BANK_VERIFY_PORT = xxxxxxxx
    # *********************************************************************


    # ***************************建行客户端设置****************************
    # ccb_merchant_module customize config (CMMC)
    CMMC_ORDER_CODE_CONF = "order_code"   # 自定义订单代码字段名
    CMMC_ORDER_MODELS_CONF = "cloud_class_system.apps.order.models"          # 自定义订单模块的配置，对应相关的models py文件
    CMMC_ORDER_NAME = "Order"                  # 自定义订单名称字段名
    CMMC_ORDER_PAY_AMOUNT = "pay_amount"            # 自定义订单付款金额字段名
    CMMC_ORDER_PAY_TIME = "pay_time"            # 自定义订单付款时间字段名
    CMMC_ORDER_PAY_STATUS = "pay_status"        # 自定义订单付款状态字段名
    CMMC_ORDER_DEL_FLAG = "del_flag"            # 自定义订单删除状态字段名
    # *********************************************************************

@@-@@ urls。py配置

    # CMMC urls 设置
    from apps.ccb_merchant_module.urls import urlpatterns as cmmc_urlpatterns
    urlpatterns.extend(cmmc_urlpatterns)
