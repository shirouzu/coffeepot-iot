#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import datetime
import cgi
from http import cookies
import cgitb
import random
import psycopg2
import traceback
import json
from functools import reduce
cgitb.enable()

# 空 1169 & 1179

MAX_DEVICE = 2
MAX_VAL    = 1400
MIN_VAL    = 210
OFF_VAL    = [1310, 1270] #RAW
COEF       = [(1250/650), (1250/600)] # 520/530

VOTE_TIME  = 8 * 60 * 60
CMNT_TIME  = 96 * 60 * 60
UPD_TIME   = 2 * 60 * 60
GRAIN      = 30

SCRIPT_VER = 19

os.environ['PYTHONIOENCODING'] = 'UTF-8'
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

DB_NAME = "coffee-db"

class Obj:
	def __init__(self, **kw): self.__dict__.update(kw)
	def __repr__(self): return "Obj: " + self.__dict__.__repr__()

def get_db():
	return	psycopg2.connect(dbname=DB_NAME)

def raw_to_real(raw_val, idx=0):
	return	max(int((raw_val - OFF_VAL[idx]) * COEF[idx] + 0) //50 * 50, 0)

def real_to_raw(val, idx=0):
	return	int((max(val, 0) // COEF[idx]) + OFF_VAL[idx])

def time_to_dbtime(t):
	return	int(t * 1000)

def dbtime_to_time(t):
	return	int(t // 1000)

def store_vote(db, coffee_id):
	try:
		v = get_vote_start(db)

		cur = db.cursor()
		cur.execute("begin;")

		d = None
		if v:
			cur.execute("select count(id) from vote_tbl where id=%s and date>%s;",
				[coffee_id, time_to_dbtime(v)])
			d = cur.fetchone()[0]

		if not d:
			cur.execute("insert into vote_tbl (date, id, ipaddr) values (%s,%s,%s);",
					(time_to_dbtime(time.time()), coffee_id, os.environ['REMOTE_ADDR']))

		cur.execute("commit;");

	except:
		print(traceback.format_exc())
		cur.execute("abort;");

def get_vote_start(db):
	limit = int(time.time() - VOTE_TIME)
	try:
		cur = db.cursor()
		cur.execute(
			"select date, val from upd_tbl where val>=%s and date>%s order by date desc limit 1;",
			[real_to_raw(MIN_VAL, 0)+50, time_to_dbtime(limit)])
		v = cur.fetchone()
		if v:
			limit = dbtime_to_time(v[0])
			#print("limit=%s val=%s %s" % (time.ctime(limit), v[1], real_to_raw(MIN_VAL, 0)))
			cur.execute("select date from upd_tbl where date>%s order by date limit 1;",
				[v[0],])
			v = cur.fetchone()
			if v:
				#print("limit2=%s" % time.ctime(dbtime_to_time(v[0])))
				return	dbtime_to_time(v[0])

	except:
		print(traceback.format_exc())

	return	limit


def get_vote(db, limit=VOTE_TIME):
	num = 0
	start = time.time() - limit
	try:
		v = get_vote_start(db)
		if v > start:
			start = v

		cur = db.cursor()
		cur.execute("select count(id) from vote_tbl where date>%s;", [time_to_dbtime(start),])
		num = cur.fetchone()[0]

	except:
		print(traceback.format_exc())
		pass

	return	num

def get_upd(db, limit=UPD_TIME):
	try:
		last_date = 0
		last_val = [0] * MAX_DEVICE
		ret = []
		cur = db.cursor()
		start = time.time() - limit
		for idx in range(MAX_DEVICE):
			cur.execute(
				"select date,val from upd_tbl where devidx=%s and date>%s order by date desc;",
				[idx, time_to_dbtime(start)])
			val = []
			for d in cur.fetchall():
				v = [dbtime_to_time(d[0]), raw_to_real(d[1], idx)]
				if not val or val[-1][0] - v[0] >= GRAIN:
					val.append(v)
				if not last_date:
					last_date = dbtime_to_time(d[0])
				if not last_val[idx]:
					last_val[idx] = d[1]

			if not val:
				val.append([0, 0])
			val.reverse()
			ret.append(val)
		return	ret, last_date, last_val

	except:
		print(traceback.format_exc())
		pass

	return	[[[0, 0]] * MAX_DEVICE], last_date, last_val


def store_cmnt(db, name, body):
	try:
		cur = db.cursor()
		cur.execute("begin;");
		cur.execute("insert into cmnt_tbl (date, name, body, ipaddr) values (%s,%s,%s,%s);",
					(time_to_dbtime(time.time()), name, body, os.environ['REMOTE_ADDR']))
		cur.execute("commit;");

	except:
		print(traceback.format_exc())
		cur.execute("abort;");

def get_cmnt(db, limit=CMNT_TIME):
	try:
		cur = db.cursor()
		cur.execute(
			"select date, name, body from cmnt_tbl where date>%s order by date desc limit 10;",
			[time_to_dbtime(time.time() - limit),])

		ret = []
		for d, name, body in cur.fetchall():
			ret.append(time.ctime(d/1000)[11:16] + ": " + name + " " + body)
		return	"<br>".join(ret)

	except:
		print(traceback.format_exc())
		pass

	return	""

def is_windows_phone():
	if "HTTP_USER_AGENT" in os.environ:
		if os.environ["HTTP_USER_AGENT"].find("Windows Phone") >= 0:
			return	True
	return	False


def get_lastdate(db):
	last = 0
	try:
		cur = db.cursor()
		cur.execute(
			"select max(date) from cmnt_tbl union select max(date) from vote_tbl union select max(date) from upd_tbl order by max desc limit 1"
			)
		last = dbtime_to_time(cur.fetchall()[0][0])

	except:
		print(traceback.format_exc())
		pass

	return	last


def cookie_proc():
	ck = cookies.SimpleCookie()
	coffee_id = None

	try:
		ck.load(os.environ["HTTP_COOKIE"])
	except:
		pass

	if "coffeeid" in ck:
		coffee_id = ck["coffeeid"].value
	else:
		ck["coffeeid"] = hex(random.randint(0, 2**128))[2:]

	expires = datetime.datetime.utcnow() + datetime.timedelta(days=30)
	ck["coffeeid"]["expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

	return	ck, coffee_id


def make_data(db):
	vals, last_date, raw_data = get_upd(db)
	for idx in range(MAX_DEVICE):
		targ = vals[idx]
		for i in range(len(targ)):
			if i == 0 or i+1 == len(targ):
				targ[i][0] = time.strftime("%H:%M", time.localtime(targ[i][0]))
			else:
				targ[i][0] = ""

	last_vals = [x[-1][1] for x in vals]

	data = json.dumps({
		"max_dev": MAX_DEVICE,
		"max_val": MAX_VAL,
		"cur_val": last_vals,
		"cmnt": get_cmnt(db),
		"vals": vals,
		"vote": get_vote(db),
		"vote_disp": reduce(lambda x,y: x > y and x or y, last_vals) < MIN_VAL and 1 or 0,
		"date": time.ctime(last_date),
		"elaps": int(time.time() - last_date),
		"last_update": get_lastdate(db),
		"raw_data": raw_data,
		"now": int(time.time()),
		"device_monitor": is_windows_phone() and 1 or 0,
		"notify_msg": "",
		"script_ver": SCRIPT_VER
	})

	return	data

def main():
	ck, coffee_id = cookie_proc()

	print("""Content-Type: text/html\r\n%s\r\n""" % ck.output())

	db = get_db()

	id = None
	try:
		form = cgi.FieldStorage()

		vote = form.getfirst("vote", "")
		if vote and coffee_id:
			store_vote(db, coffee_id)
			print(make_data(db), end="")
			return

		cmnt_name = form.getfirst("cmnt_name", "")
		cmnt_body = form.getfirst("cmnt_body", "")
		if cmnt_name and cmnt_body:
			store_cmnt(db, cmnt_name, cmnt_body)
			print(make_data(db), end="")
			return

		update = form.getfirst("update", "")
		if update:
			if int(update) == get_lastdate(db):
				print(json.dumps({
					'now': int(time.time()),
					'script_ver': SCRIPT_VER
				}))
			else:
				print(make_data(db), end="")

			return

	except:
		print(traceback.format_exc())
		print(".")
		return

	print(HTML_DATA % (make_data(db), json.dumps(os.path.basename(sys.argv[0]))))


###########################################################################################

HTML_DATA='''<html>
<head>
<title>AsahiNet CoffeePot Monitor</title>

<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="keywords" content="Coffee Pot Monitor, AsahiNet, 朝日ネット, コーヒーモニター">
<meta name="viewport" content="width=device-width">
<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
<script type="text/javascript">
	var D = %s; // max_dev, max_val, cur_val, vals, vote, vote_disp, date
	var url = %s;
	var last_update;
	var script_ver;
	var err_cnt = 0;
	var upd_cnt = 0;

	function $(x) {
		return	document.getElementById(x);
	}

	function make_remain_graph(d, idx) {
		var data = google.visualization.arrayToDataTable([
			["Pot", "Remain", { role: "style" } ],
			["ポット" + (idx+1), d.cur_val[idx], "#b87333"]
		]);

		var view = new google.visualization.DataView(data);
		view.setColumns(
			[0, 1, {
				calc: "stringify",
				sourceColumn: 1,
				type: "string",
				role: "annotation"
			}, 2]);

		var opt = {
			title: "ポット" + (idx+1) + "の残量推定 (g)",
			width: 200,
			height: 200,
			bar: {groupWidth: "80%%"},
			legend: { position: "none" },
			chartArea:{ width:"70%%",height:"70%%"},
			vAxis: {
				viewWindowMode: 'explicit',
				viewWindow: {
					max: d.max_val,
					min: 0
				},
			}
		};
		var chart = new google.visualization.ColumnChart($("remain_div" + idx));
		return	{ data: data, opt: opt, view: view, chart: chart };
	}

	function vote_func() {
		var xhr = new XMLHttpRequest();
		xhr.onreadystatechange = function() {
			if (xhr.readyState == 4 && xhr.status == 200) {
				main_func(JSON.parse(xhr.responseText));
			}
		};
		xhr.open("POST", url, false);
		xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
		xhr.send("vote=1");
	}

	function comment_func() {
		var name = $("cmnt_name").value;
		var body = $("cmnt_body").value;
		if (!name || !body) return;
		name = encodeURIComponent(name);
		body = encodeURIComponent(body);

		var xhr = new XMLHttpRequest();
		xhr.onreadystatechange = function() {
			if (xhr.readyState == 4 && xhr.status == 200) {
				main_func(JSON.parse(xhr.responseText));
				$("cmnt_body").value = "";
			}
		};
		xhr.open("POST", url, false);
		xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
		xhr.send("cmnt_name=" + name + "&" + "cmnt_body=" + body);
	}

	function on_err() {
		if (err_cnt++ == 10) {
			reflect_warn(true);
		}
	}

	function update_func() {
		if (upd_cnt > 2000) {
			location.reload(true);
			return;
		}

		var xhr = new XMLHttpRequest();
		xhr.onreadystatechange = function() {
			if (xhr.readyState == 4) {
				upd_cnt++;
				if (xhr.status == 200) {
					err_cnt = 0;
					main_func(JSON.parse(xhr.responseText));
				}
				else {
					on_err();
				}
			}
		};
		xhr.ontimeout = on_err;
		xhr.timeout = 8000;
		xhr.open("POST", url, true);
		xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
		xhr.send("update=" + last_update);
	}

	function make_flow_graph(d, idx) {
		var idx_val = [["残量", "(g)"]].concat(d.vals[idx]);
		var data = google.visualization.arrayToDataTable(
			idx_val
		);

		var view = new google.visualization.DataView(data);
		view.setColumns(
			[0, 1]);

		var opt = {
          title: '残量推移 (g)',
			legend: { position: "none" },
			chartArea:{ width:"70%%",height:"65%%"},
			width: 200,
			height: 150,
			vAxis: {
				viewWindowMode: 'explicit',
				viewWindow: {
					max: d.max_val,
					min: 0
				},
			},
          isStacked: false
		};
		var chart = new google.visualization.SteppedAreaChart($("flow_div" + idx));
		return	{ data: data, opt: opt, view: view, chart: chart };
	}

	function reflect_warn(is_warn) {
		$("warn_div").style = is_warn ? "color:red; margin:5px" : "display:none";
	}

	function reflect_div(node, msg) {
		node.innerHTML = msg;
		node.style = msg ? "color:red; margin:5px" : "display:none";
	}

	function reflect_stat(d) {
		var msg = "";
		for (var i=0; i < d.max_dev; i++) {
			if (d.raw_data[i] < 900 || d.raw_data[i] > 2100) {
				msg += "ポット" + (i+1) + " が異常値です。";
			}
		}
		reflect_div($("stat_div"), msg);
	}

	function is_too_old(elaps) {
		return	(elaps > 600 ? true : false);
	}

	function reflect_data(d) {
		$("vote_div").style = d.vote_disp ? ("padding:3px; display:inline-block; font-weight:bold;" + (d.vote > 0 ? "color:red; border:2px solid red; background-color:#FFDDDD" : "border:1px solid")) : "display:none";
		$("votecnt_div").innerHTML = d.vote;
		$("comment").innerHTML = d.cmnt;
		$("date").innerHTML = d.date;
		$("elaps").innerHTML = d.elaps;
		$("raw_data").innerHTML = d.raw_data;
		reflect_div($("notify_div"), d.notify_msg);

		reflect_warn(is_too_old(new Date().getTime()/1000 - d.last_update));
		reflect_stat(d);
	}

	function main_func(d) {
		if (!d.last_update) {
			var elaps = d.now - last_update;
			$("elaps").innerHTML = elaps;
			if (is_too_old(elaps)) {
				reflect_warn(true);
			}
			return;
		}
		if (d.script_ver > script_ver) {
			location.reload(true);
			return	false;
		}
		var data = [];
		last_update = d.last_update;
		for (var i=0; i < d.max_dev; i++) {
			data[i] = { rdata: make_remain_graph(d, i), fdata: make_flow_graph(d, i) }
		}

		for (var i=0; i < data.length; i++) {
			var	r = data[i].rdata;
			r.chart.draw(r.view, r.opt);
			var f = data[i].fdata;
			f.chart.draw(f.view, f.opt);
		}
		reflect_data(d);
	}

	function start_func(d) {
		script_ver = d.script_ver;
		main_func(d);
		setInterval(update_func, d.device_monitor ? 10000 : 30000);
	}
	google.charts.load('current', {'packages':['corechart']});
	google.charts.setOnLoadCallback(function() { start_func(D); });
</script>
</head>
<body>

<h2 style="padding:0"><a href="" onClick="update_func(); return false;"><img src="/img/asahinet.png"></a> コーヒーポットIoT<br>
<div style="font-size:75%%; position: relative; left: 100px">in 朝日ネット（歌舞伎座タワー）</div></h2>
<hr>
<div id="notify_div" style="display:none"></div>
<div id="stat_div" style="display:none"></div>
<div id="warn_div" style="display:none">このデータは古い情報です</div>

<div id="vote_div" style="display:none">
淹れて欲しい投票 <span id="votecnt_div">0</span>人 &nbsp;&nbsp;<input type="button" value="投票" onClick="vote_func(); return false"></input>
</div>

<table><tr>
	<td><div id="remain_div0"></div></td>
	<td><div id="remain_div1"></div></td></tr>
	</tr><tr>
	<td><div id="flow_div0"></div></td>
	<td><div id="flow_div1"></div></td>
</table>

<div style="font-size:80%%">
<hr>
<div id="comment"></div>
名前: <input type="text" id="cmnt_name" size="8"> コメント: <input type="text" id="cmnt_body"> <input type="button" onClick="comment_func(); return false;" value="書込"></input>
<hr>
Last update Time: <span id="date"></span> (elaps <span id="elaps"></span> sec from last-upload) (<a href="" onClick="update_func(); return false;">refresh</a>)<br>

by H.Shirouzu <span id="raw_data"></span>

</div>
</body>
</html>

'''

main()

