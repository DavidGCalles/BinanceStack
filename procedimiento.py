#!/usr/bin/env python3
#! procedimiento.py

from datetime import datetime, timedelta
from decimal import Decimal
from binance.client import Client
from binance import ThreadedWebsocketManager
from dbOPS import DB
from sys import argv
import pandas as pd
import pandas_ta as ta
from sistema import Worker
from time import sleep

workerTypes = ["MACDentry", "TSL"]
db = DB()

class MACDentry(Worker):
	"""Entrada estandar MACD. Está en construcción y tiene la logica justa para
	no realizar trades totalmente kamikazes. 
	
	Es el esqueleto de lo que pretendo que sea una función mas versatil con la que poder
	llamar a varias MACD diferentes si se requiere.

	Pero eso depende del sistema, también, y por el momento estamos aquí limitados.
	"""
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def _checkDate(self, df):
		"""#! NO ESTA EN USO
		Comprueba que la fecha no es más lejana de self.maxOld

		Args:
			df ([type]): [description]
		"""
		pass
	def startWork(self):
		"""Funcion que ejecuta el loop de entrada y valida los datos de la base de datos.
		"""
		#Obtiene la ultima fecha de comprobación mas antigua
		self.timer.updateLastCheck(db.getOlderServe(self.work))
		while True:
			if self.timer.tick() == True:
				pairs = db.servePairs(self.work, limit=self.batchSize)
				for pair in pairs:
					#Comprobamos si hay trade abierto o no.
					if db.isTradeOpen(pair["symbol"]) == False:
						#Solicitamos el dataframe correspondiente
						df4h = db.getDataFrame(pair["symbol"], "4h")
						if df4h.empty == True:
							#El dataframe puede estar vacio, primera validacion.
							pass
						else:
							try:
								#He recibido errores raros. Por eso el except. A ver si lo pillo.
								last4h = df4h["histogram"].iat[-1]
								prelast4h = df4h["histogram"].iat[-2]
							except:
								print(f"{pair['symbol']}")
								print("ERROR RARO!")
								last4h = None
								print(df4h)
							# Aqui terminan las estructuras de control y empieza el algoritmo propiamente dicho.
							if last4h is not None and prelast4h is not None: 
								if prelast4h < 0:
									if last4h > 0:
										price = Decimal(self.client.get_symbol_ticker(symbol=pair["symbol"])["price"])
										tradeDict = {"pair": pair,
													"symbol": pair["symbol"],
													"price": price,
													"entry": "MACDentry",
													"exit": "TSL"}
										self.openTrade(tradeDict)
					else:
						print(f"{pair['symbol']} TRADE YA ABIERTO!")
						pass
				self.timer.updateLastCheck(db.getOlderServe(self.work))
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()
				'''if df4h.empty == False:
					last4h = df4h["histogram"].iat[-1]
					prelast4h = df4h["histogram"].iat[-2]
					if last4h is not None and prelast4h is not None: 
						if last4h > prelast4h:
							if last4h > 0:
								#print(Decimal(df4h["histogram"].iat[-1]))
								price = Decimal(self.client.get_symbol_ticker(symbol=pair["symbol"])["price"])
								print(f'{pair["symbol"]}: {price}')
								print(df4h["openTime"].iat[-1])
								tradeDict = {"pair": pair,
											"symbol": pair["symbol"],
											"price": price,
											"entry": "MACDentry",
											"exit": "TSL"}
								print(f"Abriendo trade con entrada MACD: {pair['symbol']}")
								self.openTrade(tradeDict)
							else:
								pass
								#print("Ultimo dato menor o igual que 0")
						else:
							pass
							#print("Anterior dato mayor el el actual")
					else:
						pass
						##print("Cant Check histogram, NoneValue")
				else:
					pass
					#print("Dataframe empty")'''
				
class TSLexit(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def setLimits(self, price):
		self.softLimit = price+(price*Decimal("0.07"))
		self.stopLimit = price-(price*Decimal("0.05"))
	def loop(self,msg):
		try:
			price = Decimal(msg["c"])
			print(f"{self.trade['symbol']} -- {self.stopLimit} -- {price} -- {self.softLimit}")
			if price <= self.stopLimit:
				#Vende cagando leches
				print("CERRAMOS!")
				self.trade['sellPrice'] = price
				self.trade['baseProfit'] = (self.trade["qty"]*price)-self.trade["baseQty"]
				self.trade['closeTime'] = datetime.now()
				db.pingTrade(self.trade)
				db.closeTrade(self.trade)
				self.twm.stop()
			elif price >= self.softLimit:
				print("LIMIT UP!")
				self.setLimits(self.softLimit)
				db.pingTrade(self.trade)
			db.pingTrade(self.trade)
		except KeyError:
			pass
	def startWork(self):
		#Pregunta si hay pares desatendidos en trading #! funcion! db? Si, ademas es una metrica importante.
		unattended = db.isTradeUnattended(self.work, timedelta(seconds=30))
		while True:
			if unattended != None:
				self.trade = unattended
				db.pingTrade(self.trade)
				self.setLimits(Decimal(self.trade["price"]))
				self.twm = ThreadedWebsocketManager(api_key=self.API[0], api_secret=self.API[1])
				self.twm.start()
				self.twm.start_symbol_ticker_socket(callback=self.loop, symbol=self.trade["symbol"])
				self.twm.join()
			else:
				print("No trades need TSL monitoring")
				sleep(30)
				unattended = db.isTradeUnattended(self.work, timedelta(seconds=30))

		#Descarga el par que sobrepase el thresold de supervision (7s) y comienza la monitorizacion
		#La monitorizacion 

if __name__ == "__main__":
	##argv1 = USER/test
	##argv2 = workerType/testType
	print(datetime.now())
	try:
		if argv[1] == "test":
			test()
		else:
			if argv[2] in workerTypes:
				if argv[2] == "MACDentry":
					worker = MACDentry(argv[1], argv[2])
				elif argv[2] == "TSL":
					worker = TSLexit(argv[1], argv[2])
				try:
					worker.startWork()
				except KeyboardInterrupt:
					print(f"Proceso terminado manualmente.")
			else:
					print("WorkerType No Definido")
	except IndexError:
		print("Test Space")
		test()