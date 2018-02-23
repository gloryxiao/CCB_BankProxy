^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@
�������н��ף��ۺ϶�ά��֧�����˿��ѯ���ӿڽ����ʵ�֣����뽨�н��ײ����Ͷ�����ƣ�ʵ�ֶ�����Ƶ�������
Author: Sean
Date  : Feb 22, 2018
L     : Python Django
Open Source

^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@^-^:)*_*`_`@_@

@@-@@ ����models����Լ����
    Լ��1������ʹ��order_code��Ϊ������Ķ����룬�������޸�Դ���е�order_code�ֶ�Ϊ�Զ����ֶ��������߶��嶩�������ֶε�
    �Զ������������setting�����ã���django db��ʹ��kwargs�������ơ�
    ex:
    class Order(models.Model):
        order_code = models.CharField(default="", unique=True, max_length=32, verbose_name=u"������")

    Լ��2��ʹ�ý������и����Ķ��������ɹ�����ϸ��Ϣ��μ������̻��ĵ���

@@-@@ setting����

    # ******************************��������(��������)*******************************
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


    # ***************************���пͻ�������****************************
    # ccb_merchant_module customize config (CMMC)
    CMMC_ORDER_CODE_CONF = "order_code"   # �Զ��嶩�������ֶ���
    CMMC_ORDER_MODELS_CONF = "cloud_class_system.apps.order.models"          # �Զ��嶩��ģ������ã���Ӧ��ص�models py�ļ�
    CMMC_ORDER_NAME = "Order"                  # �Զ��嶩�������ֶ���
    CMMC_ORDER_PAY_AMOUNT = "pay_amount"            # �Զ��嶩���������ֶ���
    CMMC_ORDER_PAY_TIME = "pay_time"            # �Զ��嶩������ʱ���ֶ���
    CMMC_ORDER_PAY_STATUS = "pay_status"        # �Զ��嶩������״̬�ֶ���
    CMMC_ORDER_DEL_FLAG = "del_flag"            # �Զ��嶩��ɾ��״̬�ֶ���
    # *********************************************************************

@@-@@ urls��py����

    # CMMC urls ����
    from apps.ccb_merchant_module.urls import urlpatterns as cmmc_urlpatterns
    urlpatterns.extend(cmmc_urlpatterns)
