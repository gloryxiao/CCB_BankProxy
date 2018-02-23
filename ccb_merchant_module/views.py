#!/usr/bin/env python
# coding=utf-8

import json
import traceback
import logging

from django.http import HttpResponse
from utils import auth_check
import ccb_merchant_proxy as agents

logger = logging.getLogger(__name__)


def api_open_bank_reply(request):
    """
        银行回调接口
    """
    dict_resp = auth_check(request, "POST", check_login=False)
    if dict_resp != {}:
        return HttpResponse(json.dumps(dict_resp, ensure_ascii=False), content_type="application/json")
    try:
        agents.open_bank_reply(request)
        return HttpResponse()
    except Exception as ex:
        error_info = traceback.format_exc()
        logger.error(error_info)
        dict_resp = dict(c=-1, m=ex.message)
        return HttpResponse(json.dumps(dict_resp, ensure_ascii=False), content_type="application/json")
