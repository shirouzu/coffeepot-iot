#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
from functools import reduce
from urllib.request import urlopen
from urllib.parse   import urlencode
from hx711 import HX711, GpioCleanup
import traceback

MAX_DEV = 2
MAX_GRACE = 30
MAX_PERIOD = 60
OFF_VAL = [0, 20]

UPD_URL = "https://ipmsg.org/cgi-bin/coffee-upd.cgi"

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
		r = urlopen(url, data=urlencode(v).encode("utf-8"))
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

	if max_diff < MAX_GRACE:
		if diff >= MAX_PERIOD:
			print("period")
			return	True
		for x,y in zip(val, last_upd):
			if abs(x-y) >= MAX_GRACE:
				print("abs=%s" % abs(x-y))
				return	True

	return	False


def main():
	gm = GravMon([[2,3], [4,14]])

#	gm.init([450, 470], [8514653, 8567927])
	gm.init([450, 470], [8518041, 8568916])
#	gm.init([450, 470])

	start = 0.0
	max_lru = 5
	last_upd = [0.0 * MAX_DEV]
	lru = [[0.0] * MAX_DEV] * max_lru
	lru_idx = 0

	while True:
		try:
			val = gm.get_val(5)
			print("%10.1f %10.1f" % (val[0], val[1]))

			cur = time.time()
			if need_upd(val, last_upd, lru, cur - start):
				start = cur
				sval = [str(int(x[0] + x[1])) for x in zip(val, OFF_VAL)]
				upload(UPD_URL, { "val": ",".join(sval) })
				last_upd = val

			lru[lru_idx] = val
			lru_idx = (lru_idx + 1) % max_lru

			gm.reset()
			time.sleep(1)

		except (KeyboardInterrupt, SystemExit):
			GpioCleanup()
			break

main()

