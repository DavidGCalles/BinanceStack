from datetime import datetime, timedelta
from decimal import Decimal
from sys import argv

from binance.client import Client
from workerBase import Worker

class BackTest(Worker):
	def __init__(self, user):
		super().__init__(user, "backTest")
	def startWork(self):
		entries = {}
		symbols = self.db.getSymbols()
		for pair in symbols[:10]:
			rawData = self.db.getDataFrame(pair["symbol"], "5m", dataTable="backtest")
			print(f'{pair["symbol"]} : {rawData.size} | {rawData.iloc[0]["openTime"]}| {rawData.iloc[-1]["openTime"]}')
			#print(rawData.head())
			

if __name__ == "__main__":
	##Instantiate Class
	task = BackTest(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Tarea finalizada manualmente")