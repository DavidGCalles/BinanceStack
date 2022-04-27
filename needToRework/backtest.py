from datetime import datetime, timedelta
from decimal import Decimal
from sys import argv

from binance.client import Client
from workerBase import Worker

from entry_macd import MACDentry

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
	def pickData(self, timePoint, df, interval):
		endItem = (0,"")
		for item in df["openTime"].iteritems():
			if item[1]+interval >= timePoint:
				endItem = item
				break
		#print(f"Since: {timePoint} to {df.loc[0:endItem[0]]}")
		return df.loc[0:endItem[0]]
	def startWork(self):
		entry = MACDentry(self.user)
		symbols = self.db.getSymbols()
		count = 0
		for pair in symbols[:1]:
			print(f'')
			print(f"{count}/{len(symbols)} Starting {pair['symbol']} backtest")
			count += 1
			rawData = self.db.getDataFrame(pair["symbol"], "5m", dataTable="backtest")
			if rawData.shape[0] > 0:
				if self.checkCohesion(rawData, timedelta(minutes=5)):
					print(f'-5m OK |{pair["symbol"]} : {rawData.shape[0]} | {rawData.iloc[0]["openTime"]}| {rawData.iloc[-1]["openTime"]-rawData.iloc[0]["openTime"]}')
					data4h = self.db.getDataFrame(pair["symbol"], "4h", dataTable="backtest")
					data1d = self.db.getDataFrame(pair["symbol"], "1d", dataTable="backtest")
					if data4h.shape[0] > 0 and data1d.shape[0] > 0 and self.checkCohesion(data4h, timedelta(hours=4)) and self.checkCohesion(data1d, timedelta(days=1)):
						print(f'-4h/1d OK| {pair["symbol"]} : {data4h.shape[0]}/{data1d.shape[0]}')
						startTime = datetime.now()
						print(f"-Starting backtest at {startTime}")
						for index, row in rawData.iterrows():
							slice4h = self.pickData(row["openTime"], data4h, timedelta(hours=4))
							slice1d = self.pickData(row["openTime"], data1d, timedelta(hours=24))
							avgPrice = (row["open"]+row["close"]+row["high"]+row["low"])/4
							relevantDict = {"4h": entry.extractRelevant(entry.calculate(slice4h)), 
											"1d": entry.extractRelevant(entry.calculate(slice1d))}
							print(f'{row["openTime"]}: {avgPrice} | {relevantDict}')
							if entry.checkEntry(relevantDict) == True:
								print("--Abriendo Trade!")
								print(row)
								break
						print(f"-Ending backtest. Time Elapsed: {datetime.now()-startTime}")
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