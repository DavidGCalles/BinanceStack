#!/usr/bin/env python3
#! FILENAME.py

from datetime import datetime, timedelta
from decimal import Decimal
from ssl import SSLError
from sys import argv
from time import sleep

import pandas as pd
import pandas_ta as ta
from workerBase import Worker

class MACDentry(Worker):
	"""Entrada estandar MACD. Está en construcción y tiene la logica justa para
	no realizar trades totalmente kamikazes. 
	
	Es el esqueleto de lo que pretendo que sea una función mas versatil con la que poder
	llamar a varias MACD diferentes si se requiere.

	Pero eso depende del sistema, también, y por el momento estamos aquí limitados.
	"""
	def __init__(self, user):
		super().__init__(user, "MACDentry")
	def _checkDate(self, df):
		"""#! NO ESTA EN USO
		Comprueba que la fecha no es más lejana de self.maxOld

		Args:
			df ([type]): [description]
		"""
		pass
	def calculate(self, df):
		#print(f'Calculating data from {symbol} in db at interval {interval}')
		#print(df.to_string())
		if df.empty == False:
			try:
				macd = ta.macd(close=df["close"], fast=12, slow=26, signal=9, append=True)
				#print(macd.to_string())
				df["macd"] = macd["MACD_12_26_9"]
				df["sig"] = macd["MACDs_12_26_9"]
				df["histogram"] = macd["MACDh_12_26_9"]
				return df
			except TypeError as err:
				print(TypeError,err)
				print(df)
				return df
		else:
			print("Dataframe Vacio, saltando")
			return df
	def startWork(self):
		"""Funcion que ejecuta el loop de entrada y valida los datos de la base de datos.
		"""
		#Obtiene la ultima fecha de comprobación mas antigua
		self.timer.updateLastCheck(self.db.getOlderServe(self.work))
		while True:
			if self.timer.tick() == True:
				pairs = self.db.servePairs(self.work, limit=self.batchSize)
				for pair in pairs:
					#Comprobamos si hay trade abierto o no.
					if self.db.isTradeOpen(pair["symbol"]) == False:
						#Solicitamos el dataframe correspondiente
						df4h = self.db.getDataFrame(pair["symbol"], "4h")
						df4h = self.calculate(df4h)
						if df4h.empty == True:
							#El dataframe puede estar vacio, primera validacion.
							pass
						else:
							try:
								#He recibido errores raros. Por eso el except. A ver si lo pillo.
								last4h = df4h["histogram"].iat[-1]
								prelast4h = df4h["histogram"].iat[-2]
							except Exception as err:
								print(Exception, err)
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
				self.timer.updateLastCheck(self.db.getOlderServe(self.work))
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

if __name__ == "__main__":
	##Instantiate Class
	task = MACDentry(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Tarea finalizada manualmente")