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
				self.logger.info("Starting Task. Updating Symbol Database.")
				self.db.updateSymbols(self.client)
				self.logger.info("Task End.")
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

if __name__ == "__main__":
	##Instantiate Class
	task = dbWorker(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		task.logger.warning("Proceso terminado manualmente.")