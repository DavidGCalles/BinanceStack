#!/usr/bin/env python3
#! entry-macd.py

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
		"""Corre las funciones necesarias de python-ta para
		generar el dataframe solicitado.

		#! MUCHAS DE ESTAS CARACTERISTICAS DEBERIAN IR A CONFIG.
		#! - fast, slow, signal

		Args:
			df (pandas.Dataframe): Dataframe con los datos orignales y necesarios para la transformacion.

		Returns:
			df: El mismo dataframe, con los datos añadidos.
		"""
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
				#print(TypeError,err)
				#print(df)
				return df
		else:
			#print("Dataframe Vacio, saltando")
			return df
	def extractRelevant(self,df):
		if df.empty == True:
			return [None, None]
		else:
			try:
				relevant = [df["histogram"].iat[-2], df["histogram"].iat[-1]]
				return relevant
			except:
				return [None,None]
	def checkEntry(self, relevantDict):
		if relevantDict["4h"] != [None, None] and relevantDict["1d"] != [None, None]: 
			if relevantDict["4h"][0] <= 0 and relevantDict["4h"][1] > 0:
				if relevantDict['1d'][0] < relevantDict['1d'][1]:
					return True
				else:
					return False
			else:
				return False
		else:
			return False
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
						df4h = self.calculate(self.db.getDataFrame(pair["symbol"], "4h"))
						df1d = self.calculate(self.db.getDataFrame(pair["symbol"], "1d"))
						relevantDict = {"4h": self.extractRelevant(df4h),
										"1d": self.extractRelevant(df1d)}
						if self.checkEntry(relevantDict) == True:
							print(f"{pair['symbol']} 4h\n{relevantDict['4h'][0]}\n{relevantDict['4h'][1]}\n{pair['symbol']} 1d\n{relevantDict['1d'][0]}\n{relevantDict['1d'][1]}")
							price = Decimal(self.client.get_symbol_ticker(symbol=pair["symbol"])["price"])
							tradeDict = {"pair": pair,
										"symbol": pair["symbol"],
										"price": price,
										"entry": "MACDentry",
										"exit": "TSL"}
							self.openTrade(tradeDict)
							self.logger.debug("Entrada detectada", extra=tradeDict)
					else:
						self.logger.debug("In Monitoring", extra={"symbol": pair["symbol"]})
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
