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
		for pair in symbols[:100]:
			rawData = self.db.getDataFrame(pair["symbol"], "5m", dataTable="backtest")
			if rawData.shape[0] > 0:
				print(f'')
				print(f'--5m OK |{pair["symbol"]} : {rawData.shape[0]} | {rawData.iloc[0]["openTime"]}| {rawData.iloc[-1]["openTime"]}')
				data4h = self.db.getDataFrame(pair["symbol"], "4h", dataTable="backtest")
				data1d = self.db.getDataFrame(pair["symbol"], "1d", dataTable="backtest")
				if data4h.shape[0] > 0 and data1d.shape[0] > 0:
					print(f'--4h/1d OK| {pair["symbol"]} : {data4h.shape[0]}/{data1d.shape[0]}')
				
					
			

if __name__ == "__main__":
	##Instantiate Class
	task = BackTest(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Tarea finalizada manualmente")