#!/usr/bin/env python3
#! sistema.py

from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
from dbOPS import DB
from sys import argv
import pandas as pd
import pandas_ta as ta

workerTypes = ["dbWorker", "dbMiner", "dbCalculator"]
realTrades = False
db = DB()

#! Esqueletos de funciones para esta rama.
#! Se van a escribir fuera porque seran metodos de una superclase que aun no existe
def openTrade(tradeDict):
	"""[summary]

	Args:
		tradeDict ([type]): openTime, symbol, entry, exit, qty, price, baseQty
	"""
	#TODO Aqui iria una comprobacion de los trades maximos, definidos en la configuracion WIDE
	#TODO realTrades, hay que factorizarlo. Va a ser un bool en WIDE configuracion. En cuanto se implemente WIDE, al menos.
	if realTrades == True:
		print("Opening trade")
		#TODO aqui iria la orden de compra, con una instancia de Binance.client. 
	else:
		print("Opening MOCK trade")
	tradeDict["openTime"] = datetime.now()
	tradeDict["qty"] = 20 #! Hardcoded porque si. Tengo que transferir bastantes funciones desde LEGACY para determinar esto.
	## Faltan cosas por definir.
	print("Inserting in database.")
	## No funciona correctamente.
	db.openTrade(tradeDict)
def closeTrade(tradeDict):
	print("Selling")
	print("Moving from Trading to Traded in DB")
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

class Timer:
	def __init__(self, updateTime = timedelta(minutes=5)):
		self.updateTime = updateTime
		self.lastCheck = None
	def updateLastCheck(self, newCheck):
		self.lastCheck = newCheck
	def tick(self):
		now = datetime.now()
		#print(f"lastCheck: {self.lastCheck}")
		#print(f"now: {now}")
		if self.lastCheck == None or now >= self.lastCheck + self.updateTime:
			self.lastCheck = now
			print(f"Timer.tick(): True | nextCheck: {self.lastCheck+self.updateTime}")
			return True
		else:
			#print(f"Tick: False | nextCheck: {self.lastCheck + self.updateTime}")
			return False
	def externalTick(self, datetimeToTrack):
		now = datetime.now()
		if datetimeToTrack == None:
			self.lastCheck = now
			print(f"Timer.externalTick(): True | tracked: {datetimeToTrack}")
			return True
		elif now >= datetimeToTrack + self.updateTime:
			self.lastCheck == now
			print(f"Timer.externalTick(): True | tracked: {datetimeToTrack} | triggerHour: {datetimeToTrack+self.updateTime}")
			return True
		else:
			return False


class Worker:
	def __init__(self, user, workType):
		self.API = db.getAPI(user)
		self.user = user
		self.work = workType
		self.client = Client(self.API[0], self.API[1])
		self.config = db.getConfig(user)
		self.requiried = [f"{self.work}_configInterval", f"{self.work}_interval", f"{self.work}_batchSize"]
		#Tantos bloques Try son para aislar cada configuracion. Si los uniese, la ausencia de una caracteristica haria que
		# cada uno de los defaults se sobreescribiese.
		try:
			self.configInterval = Timer(updateTime = timedelta(minutes=int(self.config[self.requiried[0]])))
		except KeyError:
			self.configInterval= Timer(updateTime=timedelta(minutes=2))
			db.setConfig(self.user, self.requiried[0], str(2))
		try:
			self.timer = Timer(updateTime = timedelta(minutes=int(self.config[self.requiried[1]])))
		except KeyError:
			self.timer = Timer()
			db.setConfig(self.user, self.requiried[1], str(5))
		try:
			self.batchSize = int(self.config[self.requiried[2]])
		except KeyError:
			self.batchSize = 20
			db.setConfig(self.user, self.requiried[2], str(20))
	def refreshBasicConfigs(self):
		print("Probing config in DB.")
		self.config = db.getConfig(self.user)
		self.configInterval.updateTime = timedelta(minutes=int(self.config[self.requiried[0]]))
		self.timer.updateTime = timedelta(minutes=int(self.config[self.requiried[1]]))
		self.batchSize = int(self.config[self.requiried[2]])

class dbWorker(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def startWork(self):
		while True:
			if self.timer.tick() == True:
				print("Starting Task. Updating Symbol Database.")
				db.updateSymbols(self.client)
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

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
		print(f"Comprobando datos de: {symbol}")
		if interval == "1d":
			deltaInterval = self.interval1d
		elif interval == "4h":
			deltaInterval = self.interval4h
		lastPoint = db.getLastPoint(symbol, interval)
		dateEnd = datetime.now()
		if len(lastPoint) == 0:
			##Si el conteo de la tabla y simbolo concreto da como vacio, intentar obtener los maximos puntos necesarios obteniendo la fecha de inicio (dateStartObj)
			dateStartObj = dateEnd-(deltaInterval*self.pointsNeeded)
			db.insertData(self.client, symbol, interval, str(dateStartObj), end = str(dateEnd), limit=self.pointsNeeded)
			print(f"------> {interval}, vacia. Descargando datos completos desde {dateStartObj}")
		else:
			##Si la tabla tiene datos ya, seguir capturando a partir de esa fecha.
			print(f"------> {interval}, contiene datos. Comprobando tiempo {lastPoint[0]}")
			if lastPoint[0] < dateEnd-deltaInterval:
				print(f"---------> {interval}, obteniendo ultimos puntos")
				db.insertData(self.client,symbol, interval, str(lastPoint[0]+deltaInterval), end=str(dateEnd), limit=self.pointsNeeded)
			else:
				print(f"---------> {interval}, tabla actualizada.")
	def startWork(self):
		self.timer.updateLastCheck(db.getOlderServe(self.work))
		while True:
			if self.timer.tick() == True:
				print("Starting Task, Mining Data.")
				print(f"Timer.lastCheck fetched from DB: {self.timer.lastCheck}")
				pairs = db.servePairs(self.work, limit= self.batchSize)
				for pair in pairs:
					print(f"Checking {pair['symbol']}:")
					print(f'---> Checking in db')
					self._checkData(pair["symbol"], "4h")
					self._checkData(pair["symbol"], "1d")
				self.timer.updateLastCheck(db.getOlderServe(self.work))
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

class dbCalculator(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
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
		self.timer.updateLastCheck(db.getOlderServe(self.work))
		#print(self.lastCheck)
		while True:
			if self.timer.tick() == True:
				pairs = db.servePairs(self.work, limit=self.batchSize)
				#print(pairs)
				for pair in pairs:
					self._calculate(pair["symbol"], "4h")
					self._calculate(pair["symbol"], "1d")
				self.timer.updateLastCheck(db.getOlderServe(self.work))
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

if __name__ == "__main__":
	##argv1 = USER/test
	##argv2 = workerType/testType
	print(datetime.now())
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
				try:
					worker.startWork()
				except KeyboardInterrupt:
					print(f"Proceso terminado manualmente.")
			else:
					print("WorkerType No Definido")
	except IndexError:
		print("Test Space")
		test()