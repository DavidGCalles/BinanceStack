#!/usr/bin/env python3
#! FILENAME.py

from datetime import datetime, timedelta
from sys import argv
from binance.client import Client

from workerBase import Worker

class dbWorker(Worker):
	def __init__(self, user):
		super().__init__(user, "dbWorker")
		self.logger.info("Symbol Updater started")
	def startWork(self):
		while True:
			if self.timer.tick() == True:
				print("Starting Task. Updating Symbol Database.")
				self.db.updateSymbols(self.client)
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

if __name__ == "__main__":
	##Instantiate Class
	task = dbWorker(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Proceso terminado manualmente.")