#!/usr/bin/env python3

from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
from dbOPS import DB
from TA import Indicators
from sys import argv

workerTypes = ["dbWorker", "dbMiner", "dbCalculator"]

db = DB()

def test_general():
	print("|TESTING CONTAINER ENVIRONMENT")

class Worker:
	def __init__(self, user, workType):
		self.API = db.getAPI(user)
		self.work = workType
		self.client = Client(self.API[0], self.API[1])
		self.updateTime = timedelta(hours=2)
		self.lastCheck = None
	def _internalTick(self):
		now = datetime.now()
		print(f"lastCheck: {self.lastCheck}")
		print(f"now: {now}")
		print(f"nextCheck: {self.lastCheck + self.updateTime}")
		if self.lastCheck == None or now >= self.lastCheck + self.updateTime:
			print(f"Próxima comprobación: {now+self.updateTime}")
			self.lastCheck = now
			return True
		else:
			return False

class dbWorker(Worker):
	"""[summary]

	Args:
		Worker ([type]): [description]
	"""
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def startWork(self):
		while True:
			if self._internalTick() == True:
				db.updateSymbols(self.client)
				print(f"Next Check at: {self.lastCheck+self.updateTime}")

class dbMiner(Worker):
	"""
	Args:
		Worker ([type]): [description]
	"""
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
		while True:
			if self._internalTick() == True:
				pairs = db.servePairs(self.work, limit= 50)
				for pair in pairs:
					print(f'Checking {pair["symbol"]} in db')
					self._checkData(pair["symbol"], "4h")
					self._checkData(pair["symbol"], "1d")
				self.lastCheck = db.getOlderServe(self.work)

class dbCalculator(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
		self.updateTime = timedelta(minutes=2)
	def startWork(self):
		self.lastCheck = db.getOlderServe(self.work)
		#print(self.lastCheck)
		while True:
			if self._internalTick() == True:
				pairs = db.servePairs(self.work)
				#print(pairs)
				for pair in pairs:
					print(f'Calculating data from {pair["symbol"]} in db')
					data4h = db.getFullData(pair["symbol"], "4h")
					calcs = Indicators(data4h)
					db.updateData(pair["symbol"], "4h", data4h, "ema12", calcs.ema[12])
					db.updateData(pair["symbol"], "4h", data4h, "ema26", calcs.ema[26])
					db.updateData(pair["symbol"], "4h", data4h, "macd", calcs.macd["12 26"])
				self.lastCheck = db.getOlderServe(self.work)
if __name__ == "__main__":
	#test_general()
	##argv1 = USER
	##argv2 = workerType
	try:
		if argv[2] in workerTypes:
			if argv[2] == "dbWorker":
				worker = dbWorker(argv[1], argv[2])
			elif argv[2] == "dbMiner":
				worker = dbMiner(argv[1], argv[2])
			elif argv[2] == "dbCalculator":
				worker = dbCalculator(argv[1], argv[2])
			try:
				worker.startWork()
			except KeyboardInterrupt:
				print(f"Proceso terminado manualmente.")
		else:
			print("WorkerType No Definido")
	except IndexError:
		print("Test Space")
		test_general()