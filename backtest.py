from datetime import datetime, timedelta
from decimal import Decimal
from sys import argv

from binance.client import Client
from workerBase import Worker

class BackTest(Worker):
	def __init__(self, user):
		super().__init__(user, "backTest")
	def checkCohesion(self, dataFrame, timeFrame):
		for index, row in dataFrame.iterrows():
			try:
				nextRow = dataFrame.iloc[index+1]
				if (nextRow["openTime"]-row["openTime"]) == timeFrame:
					pass
				else:
					self.logger.critical("No hay cohesion en el dataframe.",
										extra={"symbol": row["symbol"], "timeFrame": str(timeFrame), "deltaRows": str(nextRow['openTime']-row['openTime'])})
					return False
			except IndexError:
				self.logger.info("Ultima linea de datos. Dataframe Coherente.", extra={"symbol": row["symbol"]})
				return True
	def startWork(self):
		entries = {}
		symbols = self.db.getSymbols()
		for pair in symbols[:10]:
			rawData = self.db.getDataFrame(pair["symbol"], "5m", dataTable="backtest")
			if rawData.shape[0] > 0:
				print(f'')
				if self.checkCohesion(rawData, timedelta(minutes=5)):
					print(f'--5m OK |{pair["symbol"]} : {rawData.shape[0]} | {rawData.iloc[0]["openTime"]}| {rawData.iloc[-1]["openTime"]-rawData.iloc[0]["openTime"]}')
					data4h = self.db.getDataFrame(pair["symbol"], "4h", dataTable="backtest")
					data1d = self.db.getDataFrame(pair["symbol"], "1d", dataTable="backtest")
					if data4h.shape[0] > 0 and data1d.shape[0] > 0 and self.checkCohesion(data4h, timedelta(hours=4)) and self.checkCohesion(data1d, timedelta(days=1)):
						print(f'--4h/1d OK| {pair["symbol"]} : {data4h.shape[0]}/{data1d.shape[0]}')
				else:
					print("No hay cohesion en 5m")

if __name__ == "__main__":
	##Instantiate Class
	task = BackTest(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Tarea finalizada manualmente")