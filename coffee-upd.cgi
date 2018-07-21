#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
import psycopg2
import hmac
import cgi
import cgitb
import traceback
cgitb.enable()

os.environ['PYTHONIOENCODING'] = 'UTF-8'
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

DB_NAME = "coffee-db"

COFFEE_MON_PSK = "coffee_mon.psk"

class Obj:
	def __init__(self, **kw): self.__dict__.update(kw)
	def __repr__(self): return "Obj: " + self.__dict__.__repr__()

def get_psk():
	psk_path = os.path.join(os.path.dirname(sys.argv[0]), COFFEE_MON_PSK)
	return	open(psk_path, "rb").read().strip()

def check_hmac(v, hm):
	return	hmac.new(get_psk(), v).hexdigest() == hm

def func():
	print("""\r\n\r\n""")

	try:
		form = cgi.FieldStorage()
		vals = form["val"].value
		hm = form["hmac"].value
		if not check_hmac(vals.encode(), hm):
			raise

		val = json.loads(vals)
		data = val["data"]
		seed = val["seed"]
		if int(seed) + 60 < time.time(): # 本来は DB に単調増加値として比較＆記録する
			raise

		conn = psycopg2.connect(dbname=DB_NAME)
		cur = conn.cursor()
		t = int(time.time()*1000)

		cur.execute("begin;")
		for i, v in enumerate(data):
			cur.execute(
				"insert into upd_tbl (date, val, devidx, ipaddr) values (%s,%s,%s,%s);",
					(t, v, i, os.environ['REMOTE_ADDR']))
		cur.execute("commit;");

	except:
		print(traceback.format_exc())
		print(".")
		return

	HTML='''
		<html>
		<head></head>
		<body>
		OK(%s)
		</body>
		<html>
	''' % str(cur)

	print(HTML)



func()

