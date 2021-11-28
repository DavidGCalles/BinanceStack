#!/usr/bin/env python3

import sqlite3
from binance.client import Client
from datetime import datetime
from decimal import Decimal
import mariadb
import dateparser
import socket
from requests import exceptions as Rexceptions
from urllib3 import exceptions as Uexceptions
import pandas as pd
import numpy as np

"""Lista de assets con los que se va a hacer trading. Esto limita la cantidad de pares almacenados desde el exchange a aquellos
que tengan estas monedas como base (segundo componente)
"""
TRADEABLE_ASSETS = ["BTC", "ETH", "BNB"]

def parseKline(kline):
	"""Trata los klines de la API de binance para obtener los datos necesarios y almacenarlos
	en base de datos o utilizarlos. Función de conveniencia.
	Convierte los datos de STR al tipo necesario para trabajar con ellos.

	Args:
		kline (list): punto de datos de la API de binance. Es una lista que sigue este
		https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data orden

	Returns:
		[dict]: Diccionario con los datos necesarios para el bot y la BBDD.
	"""
	newKline = []
	for candle in kline:
		newCandle = {
			"openTime": datetime.fromtimestamp(candle[0]/1000),
			"open": Decimal(candle[1]),
			"high": Decimal(candle[2]),
			"low": Decimal(candle[3]),
			"close": Decimal(candle[4])
		}
		newKline.append(newCandle)
	return newKline

def parseSymbol(symbol):
	#! Esta función hay que modificarla cada vez que modifiquemos la tabla symbols. Hay que mejorarla. 
	#TODO: Recibir una lista de Keys de la base de datos y conformar dinamicamente el diccionario.
	"""Recibe una tupla con los datos de trading de un simbolo y los convierte en un diccionario para trabajar mejor.

	Args:
		symbol (tuple): tupla con la información ya almacenada de BBDD.

	Returns:
		[dict]: Diccionario con los mismos datos organizados por key.
	"""
	d = {}
	d["symbol"] = symbol[0]
	d["minNotional"] = symbol[1]
	d["minQty"] = symbol[2]
	d["stepSize"] = symbol[3]
	d["precision"] = symbol[4]
	d["acierto"] = symbol[5]
	d["total"] = symbol[6]
	d["percent"] = symbol[7]
	d["1S"] = symbol[8]
	d["1M"] = symbol[9]
	d["dbMiner"] = symbol[10]
	d["dbCalculator"] = symbol[11]
	d["MACDentry"] = symbol[12]
	return d

def parseData(responseTuple):
	fieldNames = ["openTime", "symbol", "open", "high", "low", "close", "macd", "sig", "histogram"]
	d = {}
	for ind, val in enumerate(fieldNames):
		d[val] = fieldNames[ind]
	return d

def parseSQLtoDict(fieldNames, responseTuple):
	"""Esta funcion va a sustituir a parseSymbol y parseData
	De hecho, las vamos a reconstruir a su semejanza. Es hasta elegante."""
	d = {}
	for ind, val in enumerate(fieldNames):
		d[val] = responseTuple[ind]
	return d

class DB:
	"""Clase que engloba las conexiones, variables y funciones relacionadas con la base de datos.
	"""
	def __init__(self):
		"""Inicialización. No requiere ningun argumento porque los datos son hardcoded.
		"""
		self.user = f"binance"
		self.password = "binance"
		self.host = "mariadb"
		self.port = 3306
		self.database = "binance"
	def tryConnect(self):
		try:
			self.conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
				print(f"Error connecting to MariaDB Platform: {e}")
		return self.conn.cursor()
	def insertData(self, client, symbol, interval, start, end = datetime.now(), limit = 100):
		#! Determina las cuestiones horarias (UTC) del funcionamiento y explicalas!!!!
		"""Metodo para insertar datos desde la API de binance a las tablas data_4h y data_1d.
		Recibe una fecha de entrada y salida para saber los datos requeridos. También implementa
		un mecanismo de bufer circular, donde "limit" es el numero de puntos de datos relacionados
		que se almacenarán en total, eliminando los mas antiguos según entran nuevos (FIFO).

		Args:
			client (binance.Client): Instancia de cliente de binance para hacer las peticiones a la api.
			symbol (string): Par de monedas requerido.
			interval (string): Cadena que, en este momento solo puede ser  "4h" o "1d". Esta muy enlazado a las tablas de la BBDD
			start (datetime.datetime): Fecha de comienzo 
			end (datetime.datetime, optional): Fecha de final. Defaults to datetime.now().
			limit (int, optional): Limite de puntos de datos en los que el bufer actua. Defaults to 100.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
				print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		try:
			kline = parseKline(client.get_historical_klines(symbol, interval, start_str= f"{start}", end_str= f"{end}"))
		except (Rexceptions.ConnectionError, Uexceptions.ConnectionError,
			Uexceptions.ReadTimeoutError, Rexceptions.ReadTimeout):
			kline = []
			print(f"--> Connection reset, skipping")
		if len(kline) > 0:
			for candle in kline:
				query = f"INSERT INTO `data_{interval}` (`openTime`, `symbol`, `open`, `high`, `low`, `close`, `macd`, `sig`, `histogram`) VALUES ('{candle['openTime']}', '{symbol}', '{candle['open']}', '{candle['high']}', '{candle['low']}', '{candle['close']}', NULL, NULL, NULL);"
				#print(query)
				cur.execute(query)
				conn.commit()
		##OPERACION DE LIMPIEZA
		query = f"SELECT COUNT(*) FROM data_{interval} WHERE symbol = '{symbol}'"
		cur.execute(query)
		count = 0
		for point in cur:
			try:
				count = point[0]
			except:
				count = 0
		if count > limit:
			toErase = count-limit
			query = f"DELETE FROM data_{interval} WHERE symbol = '{symbol}' ORDER BY openTime ASC LIMIT {toErase}"
			cur.execute(query)
			conn.commit()
		conn.close()
	def _insertSymbol(self, data):
		"""Funcion para insertar los simbolos y sus datos en la tabla Symbols.

		He tenido que prescindir de actualizar el valor "precision" porque me daba errores SQL que no
		podia solucionar.
		#? Trabajar en esto. Algun dia tendremos que saber porque sucede o necesitaremos ese valor. SEGURO.

		Args:
			data (dict): Diccionario directo desde la API de binance. Esta funcion es llamada por cada par
			en los datos resultantes del exchange. 
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		minNotional = "-"
		minQty = "-"
		stepSize = "-"
		precision = "-"
		for filt in data["filters"]:
			if filt["filterType"] == "MIN_NOTIONAL":
				minNotional = filt["minNotional"]
			elif filt["filterType"] == "LOT_SIZE":
				minQty = filt["minQty"]
				stepSize = filt["stepSize"]
		try:
			precision = data["baseAssetPrecision"]
		except KeyError:
			pass
		queryARR = ["'"+data["symbol"]+"'",
					"'"+minNotional+"'",
					"'"+minQty+"'",
					"'"+stepSize+"'",
					str(precision)]
		querySTR = ",".join(queryARR)
		#st = f"INSERT INTO symbols (symbol, minNotional, minQty, stepSize, precision) VALUES ({querySTR});"
		st = f"INSERT INTO symbols (symbol, minNotional, minQty, stepSize) VALUES ('{data['symbol']}','{minNotional}','{minQty}','{stepSize}')"
		#print(st)
		cur.execute(st)
		conn.commit()
		conn.close()
	def getLastPoint(self,symbol,intervalData):
		"""Obtiene el punto mas reciente de las tablas de datos, del symbolo requerido.
		Esta función se usa para determinar los rangos de datos solicitados a la API de
		binance.

		Args:
			symbol (string): Cadena del par necesario.
			intervalData (string): "4h" o "1D", referentes a las tablas de datos almacenados.

		Returns:
			[list]: Lista de un solo punto que contiene la entrada solicitada. 
			#? Una lista de un solo punto parece un poco absurda. Quizá habría que factorizar esta funcion de algun modo.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
				print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		##Obtenemos la entrada mas reciente del simbolo en la tabla de 4h
		query = f"SELECT * FROM data_{intervalData} WHERE symbol = '{symbol}' ORDER BY openTime DESC LIMIT 1"
		cur.execute(query)
		last = []
		for point in cur:
			try:
				last.append(point[0])
			except IndexError:
				last.append(point)
		conn.close()
		return last
	def getDataFrame(self, symbol,intervalData):
		"""Obtiene un pandas dataframe del simbolo e intervalo solicitados.

		Args:
			symbol (string): Cadena del par necesario.
			intervalData (string): "4h" o "1D", referentes a las tablas de datos almacenados.

		Returns:
			[pandas.Dataframe]: Dataframe con todos los datos del simbolo requerido. 
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"SELECT * FROM data_{intervalData} WHERE symbol = '{symbol}' ORDER BY openTime ASC"
		pdQuery = pd.read_sql_query(query, conn)
		df = pd.DataFrame(pdQuery, columns=["openTime","symbol","open","high","low","close", "macd", "sig", "histogram"])
		conn.close()
		return df
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas.
		El tratamiento convierte las tuplas en diccionarios de mas facil utilización.

		Returns:
			[List]: Lista con todos los simbolos en formato diccionario y sus
			reglas de trading.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		cur.execute("SELECT * FROM symbols")
		clean = []
		#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
		for i in cur:
			d = parseSymbol(i)
			clean.append(d)
		conn.close()
		return clean
	def updateSymbols(self, client):
		"""Funcion basica para la base de datos. Esta funcion actualiza la tabla symbols con simbolos nuevos
		o elimina los que ya estan fuera de lista.

		Args:
			client (binance.Client): Cliente binance para solicitar los pares del exchange.
		"""
		symDict = self.getSymbols()
		exchDict = client.get_exchange_info()["symbols"]
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		#######DELISTED LOOP######
		delisted = []
		for sym in symDict:
			inList = False
			for ex in exchDict:
				if sym["symbol"] == ex["symbol"]:
					inList = True
			if inList == False:
				delisted.append(sym["symbol"])
				if len(delisted) > 0:
					st = f"DELETE FROM symbols WHERE symbol='{sym['symbol']}'"
					cur.execute(st)
		print(f"Delisted: {delisted}")
		#############################
		#######NEWLISTED LOOP########
		newlisted = []
		for ex in exchDict:
			inList = False
			for sym in symDict:
				if ex["symbol"] == sym["symbol"]:
					inList = True
			if inList == False and ex["symbol"][-3:] in TRADEABLE_ASSETS:
				newlisted.append(ex["symbol"])
				self._insertSymbol(ex)
		print(f"New Listed: {newlisted}")
		#############################
		#########UPDATE TRENDS#######
		''' Se obtienen las tendencias de 4 periodos en intervalos de 1S y 1M'''
		'''symDict = self.getSymbols()
		for sym in symDict:
			kline1S = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1WEEK, "4 weeks ago"))
			if len(kline1S) > 0:
				trend = kline1S[-1]["close"]- kline1S[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1S = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()
			kline1M = parseKline(client.get_historical_klines(sym['symbol'], Client.KLINE_INTERVAL_1MONTH, "4 months ago"))
			if len(kline1M) > 0:
				trend = kline1M[-1]["close"]- kline1M[0]["close"]
				if trend > 0:
					trendString = "BULL"
				else:
					trendString = "BEAR"
				query = f"UPDATE symbols SET 1M = '{trendString}' WHERE symbol = '{sym['symbol']}'"
				cur.execute(query)
				conn.commit()'''
		#############################
		########UPDATE PERCENTS######
		'''symDict = self.getSymbols()
		for sym in symDict:
			trades = self.getPairHistoric("scalper", pair= sym["symbol"])
			if len(trades)>0:
				aciertos = 0
				total = 0
				for trade in trades:
					total = total + 1
					if Decimal(trade["sellPrice"]) > Decimal(trade["evalPrice"]):
						aciertos = aciertos + 1
				perc = (aciertos/total)*100
				st = f"UPDATE symbols SET acierto = '{aciertos}', total = '{total}', percent = '{perc}' WHERE symbol = '{sym['symbol']}' "
				cur.execute(st)
				conn.commit()'''
		#################################
		conn.close()
	def updateData(self, intervalData, dataframe):
		"""Actualiza las tablas de "data" con datos proporcionados en un pandas dataframe.

		Args:
			intervalData (string): "4h" o "1D"
			dataframe (pandas.Dataframe): Dataframe que contiene los datos precalculados restantes en la base de datos.
			Estos datos son MACD, signal, histogram.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
				print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		for index, row in dataframe.iterrows():
			queryStart = f"UPDATE data_{intervalData} SET "
			macdBIT = ""
			sigBIT = ""
			histogramBIT = ""
			##
			macd = row["macd"]
			sig = row["sig"]
			histogram = row["histogram"]
			##
			if np.isnan(macd):
				macdBIT = f"macd = NULL, "
			else:
				macdBIT = f"macd = '{macd}',"
			##
			if np.isnan(sig):
				sigBIT = f"sig = NULL, "
			else:
				sigBIT = f"sig = '{sig}',"
			##
			if np.isnan(histogram):
				histogramBIT = f"histogram = NULL "
			else:
				histogramBIT = f"histogram = '{histogram}' "
			endQuery = f"WHERE symbol = '{row['symbol']}' AND openTime = '{row['openTime']}'"
			cur.execute(queryStart+macdBIT+sigBIT+histogramBIT+endQuery)
		conn.commit()
		conn.close()
	def getAPI(self, user):
		"""Obtiene la clave de api y secreto de un usuario desde la tabla users.
		Además, incluye las configuraciones relacionadas con ese usuario.
		#! Atencion, altamente inseguro. Simplemente queria que funcionase.

		Args:
			user (string): Nombre del usuario.

		Returns:
			[list]: Lista compuesta de [API_KEY, API_SECRET, CONFIG] en cadenas.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		st = f"SELECT * FROM users WHERE name='{user}'"
		cur.execute(st)
		apiKEYS=[]
		for idAPI in cur:
			apiKEYS.append(idAPI[1])
			apiKEYS.append(idAPI[2])
		conn.close()
		return apiKEYS
	def getOlderServe(self, serveType):
		"""Recupera la fecha más antigua de servicio de un par en la tabla symbols.
		Para más información sobre como funcionan los timers de servicio, referirse
		a documentacion exterior.

		Args:
			serveType (string): Tipo de servicio del que consultamos el timer.

		Returns:
			datetime.Datetime: Fecha más antigua de servicio.
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"SELECT * FROM symbols ORDER BY {serveType} ASC LIMIT 1"
		cur.execute(query)
		for point in cur:
			try:
				sym = parseSymbol(point)
				conn.close()
				return sym[serveType]
			except IndexError:
				conn.close()
				return None
	def servePairs(self, serveType, order = "ASC", limit = 20):
		"""Sirve pares desde base de datos. Maneja que pares servir por las columnas
		de servicio. Los actualiza en la base de datos para mantener los timers.


		Args:
			serveType (string): Cadena que indica el servicio.
			order (str, optional): Coger los X primeros o los X ultimos. Defaults to "ASC".
			limit (int, optional): Cantidad de simbolos servidos. Defaults to 20.

		Returns:
			list: Lista de diccionarios de simbolos. 
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"SELECT * FROM symbols ORDER BY {serveType} {order} LIMIT {limit}"
		cur.execute(query)
		toServe = []
		for pair in cur:
			toServe.append(parseSymbol(pair))
		for i in toServe:
			#print(i[0])
			query = f"UPDATE symbols SET {serveType} = '{datetime.now()}' WHERE symbol = '{i['symbol']}'"
			cur.execute(query)
		conn.commit()
		conn.close()
		return toServe
	def serveData(self, symbol, interval="FULL"):
		"""[summary]

		Args:
			symbol ([type]): [description]
			interval (str, optional): [description]. Defaults to "FULL".
		"""
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"SELECT * FROM symbols ORDER BY {serveType} {order} LIMIT {limit}"
		cur.execute(query)
		conn.close()
	def getConfig(self, user):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		st = f"SELECT * FROM config WHERE user='{user}'"
		cur.execute(st)
		configDict = {}
		for configSet in cur:
			configDict[configSet[1]] = configSet[2]
		return configDict
	def setConfig(self, user, key, val):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"INSERT INTO config (user, keyName, value) VALUES ('{user}','{key}','{val}')"
		cur.execute(query)
		conn.commit()
		conn.close()
	def getOpenTradeCount(self):
		cur = self.tryConnect()
		query = f"SELECT COUNT(*) FROM trading"
		cur.execute(query)
		for point in cur:
			try:
				return int(point[0])
			except:
				return 0
			finally:
				self.conn.close()
	def openTrade(self, tradeDict):
		try:
			conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
		except mariadb.Error as e:
			print(f"Error connecting to MariaDB Platform: {e}")
		cur = conn.cursor()
		query = f"INSERT INTO trading (openTime, symbol, entryStra, exitStra, qty, price, baseQty) VALUES ('{tradeDict['openTime']}','{tradeDict['symbol']}','{tradeDict['entry']}','{tradeDict['exit']}','{tradeDict['qty']}','{tradeDict['price']}','{tradeDict['baseQty']}')"
		cur.execute(query)
		conn.commit()
		conn.close()
	def isTradeOpen(self, symbol):
		cur = self.tryConnect()
		query = f"SELECT COUNT(*) FROM trading WHERE symbol = '{symbol}'"
		cur.execute(query)
		for point in cur:
			try:
				return bool(point[0])
			except:
				return False
			finally:
				self.conn.close()
	def isTradeUnattended(self, exitType, thresold):
		cur = self.tryConnect()
		now = datetime.now()
		query = f"SELECT * FROM trading WHERE lastCheck IS NULL AND exitStra = '{exitType}' ORDER BY openTime LIMIT 1"
		cur.execute(query)
		for trade in cur:
			fieldNames = ["openTime", "symbol", "entryStra", "exitStra", "qty", "price", "baseQty", "lastCheck"]
			self.conn.close()
			return parseSQLtoDict(fieldNames, trade)
		query = f"SELECT * FROM trading WHERE exitStra = '{exitType}' ORDER BY lastCheck LIMIT 1"
		cur.execute(query)
		for trade in cur:
			fieldNames = ["openTime", "symbol", "entryStra", "exitStra", "qty", "price", "baseQty", "lastCheck"]
			tradeDict = parseSQLtoDict(fieldNames, trade)
			if tradeDict["lastCheck"]+thresold < datetime.now():
				self.conn.close()
				return tradeDict
			else:
				self.conn.close()
				return None
		self.conn.close()
	def pingTrade(self, trade):
		cur = self.tryConnect()
		query = f"UPDATE trading SET lastCheck = '{datetime.now()}' WHERE symbol = '{trade['symbol']}'"
		cur.execute(query)
		self.conn.commit()
		self.conn.close()
	def closeTrade(self, trade):
		cur = self.tryConnect()
		query = f"SELECT COUNT(*) FROM traded WHERE openTime = '{trade['openTime']}' AND symbol = '{trade['symbol']}' AND qty = '{trade['qty']}'"
		#print(query)
		cur.execute(query)
		isClosed = False
		for point in cur:
			try:
				isClosed =  bool(point[0])
			except:
				isClosed = False
		if isClosed == False:
			query = f"INSERT INTO traded (`openTime`, `symbol`, `entryStra`, `exitStra`, `qty`, `price`, `baseQty`, `closeTime`, `sellPrice`,`baseProfit`) VALUES ('{trade['openTime']}', '{trade['symbol']}', '{trade['entryStra']}', '{trade['exitStra']}','{trade['qty']}', '{trade['price']}', '{trade['baseQty']}', '{trade['closeTime']}', '{trade['sellPrice']}', '{trade['baseProfit']}');"
			print(query)
			cur.execute(query)
			self.conn.commit()
			print("Insertando CIERRE")
			query = f"DELETE FROM trading WHERE symbol = '{trade['symbol']}'"
			cur.execute(query)
			self.conn.commit()
			self.conn.close()
			print("Eliminando ABIERTO")
		else:
			pass

if __name__ == "__main__":
	db1 = DB()

