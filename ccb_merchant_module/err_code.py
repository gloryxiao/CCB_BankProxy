#!/usr/bin/env python
# coding=utf-8


ERR_SUCCESS = [0, u'完成']
ERR_SUCCESS_FRESH = [1, u'完成，刷新数据']
ERR_PART_SUCCESS = [2, u'部分完成']
ERR_WAIT_QUERY = [3, u"等待重新连接请求"]
ERR_LOGIN_FAIL = [40003, u'用户名或密码错误']
ERR_USER_NOTLOGGED = [40004, u'用户未登录']
ERR_USER_AUTH = [40005, u'用户权限不够']
ERR_REQUESTWAY = [40006, u'请求方式错误']
ERR_ACTION_NOT_SUPPORT = [40006, u'不支持的ACTION']
ERR_USER_INFO = [40007, u'用户信息错误']
ERR_USER_FLAG = [40007, u'用户标识错误']
ERR_USER_INFO_INCOMPLETE = [40007, u'用户信息不完整']
ERR_FILE_FORMAT_NOT_SUPPORTED = [40008, u'文件格式不支持']
ERR_INTERNAL_ERROR = [40009, u'服务器内部错误']
ERR_USER_ALREADY_EXIST = [40010, u'用户已经存在']
ERR_USER_NOT_EXIST = [40012, u'用户不存在']
ERR_REQUEST_PARAMETER_ERROR = [40014, u"请求参数不正确"]
ERR_DATA_WRITE_ERR = [40015, u"写入文件错误"]
ERR_USER_TYPE_ERR = [40016, u'用户类型不正确']

ERR_DELETE_COURSE_ERROR = [40020, u"删除课程错误，课程对应有订单信息，请查看订单信息"]
