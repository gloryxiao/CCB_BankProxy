#!/usr/bin/env python
# coding=utf-8

from django.conf.urls import url
from views import *

urlpatterns = [
    url("^api/open/bank_reply$", api_open_bank_reply),
]
