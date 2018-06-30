#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import psycopg2
import cgi
import cgitb
cgitb.enable()

os.environ['PYTHONIOENCODING'] = 'UTF-8'
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

DB_NAME = "coffee-db"

class Obj:
	def __init__(self, **kw): self.__dict__.update(kw)
	def __repr__(self): return "Obj: " + self.__dict__.__repr__()


def func():
	print("""\r\n\r\n""")

	try:
		form = cgi.FieldStorage()
		val = [int(x) for x in form["val"].value.split(",")]

		conn = psycopg2.connect(dbname=DB_NAME)
		cur = conn.cursor()
		t = int(time.time()*1000)

		cur.execute("begin;")
		for i, v in enumerate(val):
			cur.execute(
				"insert into upd_tbl (date, val, devidx, ipaddr) values (%s,%s,%s,%s);",
					(t, v, i, os.environ['REMOTE_ADDR']))
		cur.execute("commit;");

	except:
		traceback.print_exc()
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

