#!/usr/bin/env python3
#! procedimiento.py

from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from binance.client import Client
from binance import ThreadedWebsocketManager
from binance import AsyncClient, BinanceSocketManager
from dbOPS import DB
from sys import argv
import pandas as pd
import pandas_ta as ta
from sistema import Worker
from time import sleep
from mariadb import OperationalError
from ssl import SSLError

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
				
class TSLexit(Worker):
	def __init__(self, user, workType):
		super().__init__(user, workType)
	def setLimits(self,trade, price):
		##No sirve para esta version
		trade["softLimit"] = price+(price*Decimal("0.07"))
		trade["stopLimit"] = price-(price*Decimal("0.05"))
	def handle_socket_message(self,msg):
			#print(f"message type: {msg['data']['c']}")
			price = Decimal(msg['c'])
			print(f"{msg['s']}: {msg['c']} | {self.streams[msg['s']]['trade']['softLimit']}| {self.streams[msg['s']]['trade']['stopLimit']}")
			if price >= self.streams[msg['s']]["trade"]["softLimit"]:
				self.setLimits(self.streams[msg['s']]["trade"], price)
			elif price <= self.streams[msg['s']]["trade"]["stopLimit"]:
				print("cerramos!")
				self.streams[msg['s']]["trade"]["closeTime"] = datetime.now()
				self.streams[msg['s']]["trade"]["sellPrice"] = price
				self.streams[msg['s']]["trade"]["baseProfit"] = price- self.streams[msg['s']]["trade"]["price"]
				db.closeTrade(self.streams[msg['s']]["trade"])
				self.twm.stop_socket(self.streams[msg['s']]["stream"])
	'''def handle_socket_message(self,msg):
		#print(f"message type: {msg['data']['c']}")
		price = Decimal(msg['data']['c'])
		print(f"{msg['data']['s']}: {msg['data']['c']} | {self.streams[msg['data']['s']]['trade']['softLimit']}| {self.streams[msg['data']['s']]['trade']['stopLimit']}")
		if price >= self.streams[msg['data']['s']]["trade"]["softLimit"]:
			self.setLimits(self.streams[msg['data']['s']]["trade"], price)
		elif price <= self.streams[msg['data']['s']]["trade"]["stopLimit"]:
			print("cerramos!")
			self.streams[msg['data']['s']]["trade"]["closeTime"] = datetime.now()
			self.streams[msg['data']['s']]["trade"]["sellPrice"] = price
			self.streams[msg['data']['s']]["trade"]["baseProfit"] = price- self.streams[msg['data']['s']]["trade"]["price"]
			db.closeTrade(self.streams[msg['data']['s']]["trade"])
			self.twm.stop_socket(msg["stream"])'''
	def startWork(self):
		self.twm = ThreadedWebsocketManager(api_key=self.API[0], api_secret=self.API[1])
		self.twm.start()
		self.trades = db.getOpenTrades()
		self.reload = False
		self.streams = {}
		streamList = []
		for trade in self.trades:
			self.setLimits(trade, trade["price"])
			self.streams[trade["symbol"]] = {}
			self.streams[trade["symbol"]]["trade"] = trade
			self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
			#streamList.append(trade["symbol"].lower()+"@ticker")
		#self.twm.start_multiplex_socket(callback=self.handle_socket_message, streams=streamList)
		#sleep(10)
		#self.twm.stop_client()
		#sleep(10)
		#print("Reawaking")
		#print(self.twm)
		#twm.join()
		#print("SEGUIMOS!")
		#print(self.trades)
		'''while True:
			if self.reload == True:
				self.twm.stop()
				self.trades = db.getOpenTrades()
				self.streams = {}
				streamList = []
				for trade in self.trades:
					self.setLimits(trade, trade["price"])
					self.streams[trade["symbol"]] = {}
					self.streams[trade["symbol"]]["trade"] = trade
					#self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
					streamList.append(trade["symbol"].lower()+"@ticker")
				self.twm.start()
				self.twm.start_multiplex_socket(callback=self.handle_socket_message, streams=streamList)
			else:
				print("No trades need TSL monitoring")
				sleep(30)
				self.trade = db.isTradeUnattended(self.work, timedelta(seconds=30))

		#Descarga el par que sobrepase el thresold de supervision (7s) y comienza la monitorizacion
		#La monitorizacion'''

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