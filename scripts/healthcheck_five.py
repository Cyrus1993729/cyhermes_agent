#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""五类日报投递健康检查包装 (cron 用)"""
import sys
sys.argv = ['healthcheck_daily.py', '--five']
exec(open(r'C:\Users\Administrator\AppData\Local\hermes\scripts\healthcheck_daily.py', encoding='utf-8').read())
