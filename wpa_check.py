#!/usr/bin/python3

import os
import sys
import time
import signal
import traceback

TARGS = ["8.8.8.8", "8.8.4.4", "49.212.200.23", "160.16.124.162"]
#TARGS = ["8.8.8.1"]

def log(msg):
	print(time.ctime() + ": " + msg, flush=True)


def ping_test(targs):
	for t in targs:
		v = os.system("ping -c 1 -w 2 %s > /dev/null 2>&1" % t)
		if v == 0:
			return	True

	return	False

def main():
	signal.signal(signal.SIGHUP, signal.SIG_IGN)

	err_cnt = 0
	deep_err = 0

	while True:
		try:
			if ping_test(TARGS):
				err_cnt = 0
				deep_err = 0
				time.sleep(30)
			else:
				err_cnt += 1
				time.sleep(5)

			if err_cnt >= 5:
				log("wlan")
				os.system("sudo /etc/wpa_supplicant/action_wpa.sh wlan0 up")
				err_cnt = 0
				deep_err += 1

			if deep_err >= 10:
				log("reset")
				deep_err = 0
				os.system("sudo /sbin/reboot")

		except:
			traceback.print_exc()
			time.sleep(1)


main()

