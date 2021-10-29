#!/usr/bin/env python3

from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
from dbOPS import DB
from TA import Indicators
from sys import argv
import pandas as pd
import pandas_ta as ta

workerTypes = ["test","dbWorker", "dbMiner", "dbCalculator", "MACDentry"]

db = DB()

def test_general():
	print("|TESTING CONTAINER ENVIRONMENT")

def test():
	a = Worker("test", "test")
	a.updateTime = timedelta(minutes=1)
	while True:
		a._internalTick()
class Worker:
	def __init__(self, user, workType):
		#self.API = db.getAPI(user)
		self.work = workType
		#self.client = Client(self.API[0], self.API[1])
		self.updateTime = timedelta(hours=2)
		self.lastCheck = None
	def _internalTick(self):
		now = datetime.now()
		#print(f"lastCheck: {self.lastCheck}")
		#print(f"now: {now}")
		if self.lastCheck == None or now >= self.lastCheck + self.updateTime:
			print(f"internalTick: True | nextCheck: {now+self.updateTime}")
			self.lastCheck = now
			return True
		else:
			#print(f"Tick: False | nextCheck: {self.lastCheck + self.updateTime}")
			return False

class dbWorker(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def startWork(self):
		while True:
			if self._internalTick() == True:
				db.updateSymbols(self.client)
				print(f"Next Check at: {self.lastCheck+self.updateTime}")

class dbMiner(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.pointsNeeded = 54
		self.interval4h = timedelta(hours=4)
		self.interval1d = timedelta(days=1)
	def _checkData(self, symbol, interval):
		"""Comprueba el ultimo registro de "symbol" en la tabla determinada por "interval".
		Si no existe ultimo registro, obtiene todos los determinados en "pointsNeeded" y los carga en la base de datos.
		Si existe, calcula los puntos que tiene que obtener desde la ultima fecha y los pide.
		Esta funcion se encarga de determinar fechas y maximos de almacenamiento, pasando los argumentos concretos a las
		funciones actuadoras de dbOPS.

		Args:
			symbol (STR): Nombre del par.
			interval (STR): cadena equivalente a self.client.KLINE_INTERVAL_nX. Se utiliza para definir la tabla de
				tiempos que usar, el timedelta adecuado para las solicitudes.
		"""
		if interval == "1d":
			deltaInterval = self.interval1d
		elif interval == "4h":
			deltaInterval = self.interval4h
		lastPoint = db.getLastPoint(symbol, interval)
		dateEnd = datetime.now()
		if len(lastPoint) == 0:
			##Si el conteo de la tabla y simbolo concreto da como vacio, intentar obtener los maximos puntos necesarios obteniendo la fecha de inicio (dateStartObj)
			print(f"Tabla {interval}, {symbol}, vacia. Descargando datos completos.")
			dateStartObj = dateEnd-(deltaInterval*self.pointsNeeded)
			db.insertData(self.client, symbol, interval, str(dateStartObj), end = str(dateEnd), limit=self.pointsNeeded)
		else:
			##Si la tabla tiene datos ya, seguir capturando a partir de esa fecha.
			print(f"Tabla {interval}, {symbol}, contiene datos. Comprobando tiempo {lastPoint[0]}")
			if lastPoint[0] < dateEnd-deltaInterval:
				print(f"Tabla {interval}, {symbol}, obteniendo ultimos puntos")
				db.insertData(self.client,symbol, interval, str(lastPoint[0]+deltaInterval), end=str(dateEnd), limit=self.pointsNeeded)
	def startWork(self):
		self.lastCheck = db.getOlderServe(self.work)
		print("Starting Work")
		print(f"lastCheck fetched from DB: {self.lastCheck}")
		while True:
			if self._internalTick() == True:
				pairs = db.servePairs(self.work, limit= 1000)
				for pair in pairs:
					print(f'Checking {pair["symbol"]} in db')
					self._checkData(pair["symbol"], "4h")
					self._checkData(pair["symbol"], "1d")
				self.lastCheck = db.getOlderServe(self.work)

class dbCalculator(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.updateTime = timedelta(minutes=2)
	def _calculate(self, symbol, interval):
		print(f'Calculating data from {symbol} in db at interval {interval}')
		df = db.getDataFrame(symbol, interval)
		#print(df.to_string())
		if df.empty == False:
			try:
				macd = ta.macd(close=df["close"], fast=12, slow=26, signal=9, append=True)
				#print(macd.to_string())
				df["macd"] = macd["MACD_12_26_9"]
				df["sig"] = macd["MACDs_12_26_9"]
				df["histogram"] = macd["MACDh_12_26_9"]
				db.updateData(interval, df)
			except TypeError:
				print("Dataframe Vacio.")
				print(df)
		else:
			print("Dataframe Vacio, saltando")
	def startWork(self):
		self.lastCheck = db.getOlderServe(self.work)
		#print(self.lastCheck)
		while True:
			if self._internalTick() == True:
				pairs = db.servePairs(self.work, limit=100)
				#print(pairs)
				for pair in pairs:
					self._calculate(pair["symbol"], "4h")
					self._calculate(pair["symbol"], "1d")
				self.lastCheck = db.getOlderServe(self.work)

class MACDentry(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.updateTime = timedelta(hours=1)
	def startWork(self):
		self.lastCheck = db.getOlderServe(self.work)
		while True:
			if self._internalTick() == True:
				pairs = db.servePairs(self.work)
				for pair in pairs:
					price = self.client.get_all_tickers(symbol=pair["symbol"])
					print(f'{pair["symbol"]}: price')
				self.lastCheck = db.getOlderServe(self.work)

if __name__ == "__main__":
	#test_general()
	##argv1 = USER/test
	##argv2 = workerType/testType
	try:
		if argv[1] == "test":
			test()
		else:
			if argv[2] in workerTypes:
				if argv[2] == "dbWorker":
					worker = dbWorker(argv[1], argv[2])
				elif argv[2] == "dbMiner":
					worker = dbMiner(argv[1], argv[2])
				elif argv[2] == "dbCalculator":
					worker = dbCalculator(argv[1], argv[2])
				elif argv[2] == "MACDentry":
					worker = MACDentry(argv[1], argv[2])
				try:
					worker.startWork()
				except KeyboardInterrupt:
					print(f"Proceso terminado manualmente.")
			else:
					print("WorkerType No Definido")
	except IndexError:
		print("Test Space")
		test()