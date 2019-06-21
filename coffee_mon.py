#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import signal
import json
import hmac
from functools import reduce
from urllib.request import urlopen
from urllib.parse   import urlencode
from hx711 import HX711, GpioCleanup
import traceback

#INIT_PARAM_1 = [450, 470]
#INIT_PARAM_2 = [8518041, 8568916]

INIT_PARAM_1 = [450, 450]
INIT_PARAM_2 = [8500000, 8530000]

MAX_DEV = 2
MAX_GRACE = 30
MAX_PERIOD = 60
OFF_VAL = [0, 0]

UPD_URL = "https://ipmsg.org/cgi-bin/coffee-upd.cgi"
COFFEE_MON_PSK = "coffee_mon.psk"

class GravMon:
	def __init__(self, target_list):
		self.hxs = [HX711(x[0], x[1]) for x in target_list]

	def init(self, ref_unit, tare=None):
		[x.set_reading_format("LSB", "MSB") for x in self.hxs]
		[x.set_reference_unit(v) for x,v in zip(self.hxs, ref_unit)]
		[x.reset() for x in self.hxs]

		if tare:
			[x.tare2(v) for x,v in zip(self.hxs, tare)]
		else:
			[x.tare() for x in self.hxs]

	def reset(self):
		[x.power_down() for x in self.hxs]
		[x.power_up() for x in self.hxs]

	def get_val(self, val):
		return	[x.get_weight(val) for x in self.hxs]

def upload(url, v):
	try:
		r = urlopen(url, data=urlencode(v).encode("utf-8"), timeout=10)
		return	r.read().decode("utf-8")
	except:
		traceback.print_exc()
		pass



def need_upd(val, last_upd, lru, diff):
	max_diff = 0
	for i in range(len(lru)):
		L = lru[i]
		for x,y in zip(val, L):
			max_diff = max(abs(x - y), max_diff)

	if diff >= MAX_PERIOD:
		return	True

	if max_diff < MAX_GRACE:
		for x,y in zip(val, last_upd):
			if abs(x-y) >= MAX_GRACE:
				print("abs=%s" % abs(x-y))
				return	True

	return	False

def get_medians(vals):
	inv = tuple(zip(*vals))
	return	[x for x in map(lambda x: sorted(x)[len(x)//2], inv)]

def get_psk():
	psk_path = os.path.join(os.path.dirname(sys.argv[0]), COFFEE_MON_PSK)
	return	open(psk_path, "rb").read().strip()

def get_hmac(v, psk):
	hm = hmac.new(psk, v)
	return	hm.hexdigest()

def main():
	signal.signal(signal.SIGHUP, signal.SIG_IGN)
	gm = GravMon([[4,14], [17,18]])

#	gm.init([450, 470])
	gm.init(INIT_PARAM_1, INIT_PARAM_2)

	start = 0.0
	max_lru = 8
	last_upd = [0.0 * MAX_DEV]
	lru = [[0.0] * MAX_DEV] * max_lru
	lru_idx = 0

	psk = get_psk()

	while True:
		try:
			val = gm.get_val(5)
			print("%10.1f %10.1f" % (val[0], val[1]))

			cur = time.time()
			lru[lru_idx % max_lru] = val
			lru_idx += 1

			if lru_idx >= max_lru and need_upd(val, last_upd, lru, cur - start):
				med = get_medians(lru)
				start = cur
				data = [int(x[0] + x[1]) for x in zip(med, OFF_VAL)]
				vals = json.dumps({ "data": data, "seed": int(time.time()) })
				upd_data = { "val": vals, "hmac": get_hmac(vals.encode(), psk) }
				upload(UPD_URL, upd_data)
				last_upd = med
				print("upd %s" % upd_data)

			gm.reset()
			time.sleep(1)

		except (KeyboardInterrupt, SystemExit):
			GpioCleanup()
			break

		except:
			traceback.print_exc()
			time.sleep(1)

main()

