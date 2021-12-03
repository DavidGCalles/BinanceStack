#!/usr/bin/env python3
#! procedimiento.py

from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from binance.client import Client
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
	def setLimits(self, price):
		self.softLimit = price+(price*Decimal("0.07"))
		self.stopLimit = price-(price*Decimal("0.05"))
	async def loop(self):
		db.pingTrade(self.trade)
		client = await AsyncClient.create(api_key=self.API[0], api_secret=self.API[1])
		bm = BinanceSocketManager(client)
		# start any sockets here, i.e a trade socket
		ts = bm.symbol_ticker_socket(self.trade["symbol"])
		# then start receiving messages
		count = 0
		self.setLimits(Decimal(self.trade["price"]))
		async with ts as tscm:
			while True:
				res = await tscm.recv()
				count+=1
				print(f'{res["s"]}: {res["c"]} || v {self.stopLimit:.8f} || ^ {self.softLimit:.8f}')
				if count >= 5:
					print(f"DB POLL")
					db.pingTrade(self.trade)
					count = 0
				price = Decimal(res["c"])
				if price <= self.stopLimit:
					#Vende cagando leches
					self.trade['sellPrice'] = price
					self.trade['baseProfit'] = (self.trade["qty"]*price)-self.trade["baseQty"]
					self.trade['closeTime'] = datetime.now()
					db.closeTrade(self.trade)
					print(f'{res["s"]}: {res["c"]} || v {self.stopLimit:.8f} || CERRADO!!')
					break
				elif price >= self.softLimit:
					print(f'{res["s"]}: {res["c"]} || ^ {self.softLimit:.8f} || SOFT LIMIT UP')
					self.setLimits(self.softLimit)
		await client.close_connection()
		'''try:
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
				self.trade = None
				self.twm.stop_socket(self.socketName)
			elif price >= self.softLimit:
				print("LIMIT UP!")
				self.setLimits(self.softLimit)
				db.pingTrade(self.trade)
			db.pingTrade(self.trade)
		except KeyError or TypeError or SSLError:
			print("Error1")
		except OperationalError:
			print("Error2")'''
	def startWork(self):
		#Pregunta si hay pares desatendidos en trading #! funcion! db? Si, ademas es una metrica importante.
		self.trade = db.isTradeUnattended(self.work, timedelta(seconds=30))
		while True:
			if self.trade != None:
				aloop = asyncio.get_event_loop()
				aloop.run_until_complete(self.loop())
				print("Termina la monitorizacion")
				self.trade = None
			else:
				print("No trades need TSL monitoring")
				sleep(30)
				self.trade = db.isTradeUnattended(self.work, timedelta(seconds=30))

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