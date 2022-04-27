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
from binance.client import Client


"""Lista de assets con los que se va a hacer trading. Esto limita la cantidad de pares almacenados desde el exchange a aquellos
que tengan estas monedas como base (segundo componente)

Esta variable ya es parte de config.wide. Se crea el issue #68
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

def parseSQLtoDict(fieldNames, responseTuple):
	"""Convierte una respuesta SQL(tupla) en un diccionario
	con los parametros determinados en fieldNames.

	Args:
		fieldNames (list): nombres de los campos (habitualmente coinciden
			con los de las tablas de la respuesta)
		responseTuple (tuple): respuesta en bruto de la base de datos.

	Returns:
		dict: diccionario en el que cada fieldName es asignado como Key y el valor
			correspondiente de SQL
	"""
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
	#! Metodos basicos de DB (se heredaran y utilizaran en clases derivadas tal cual)
	def tryConnect(self):
		"""Función de conexión a db de conveniencia. Devuelve un bool en función de una conexion correcta o no.
		El cursor y la conexion se almacenan en la propia instancia.

		Returns:
			bool: Depende de la conexion correcta o no.
		"""
		try:
			self.conn = mariadb.connect(
				user=self.user,
				password=self.password,
				host=self.host,
				port=self.port,
				database=self.database
				)
			self.conn.autocommit = False
			#print(f"Conexion correcta a: {self.host}")
			self.cur = self.conn.cursor()
			return True
		except mariadb.Error as e:
			print(f"Error conectando a mariadb: {e}")
			return False
	#! Metodos de administración y limpieza.
	def getSymbols(self):
		"""Obtiene una lista de pares limpia de la base de datos.
		Requiere tratamiento porque la base de datos devuelve tuplas.
		El tratamiento convierte las tuplas en diccionarios de mas facil utilización.

		Returns:
			[List]: Lista con todos los simbolos en formato diccionario y sus
			reglas de trading.
		"""
		if self.tryConnect():
			self.cur.execute("SELECT * FROM symbols")
			clean = []
			#Itera sobre la lista obtenida de la base de datos y convierte las tuplas de un solo elemento en cadenas.
			for i in self.cur:
				sym = Symbol()
				sym.parseSQL(i)
				clean.append(sym)
			self.conn.close()
			return clean
		else:
			print("Imposible acceder a db")
			return []
	#! Metodos antiguos
	def insertData(self, client, symbol, interval, start, end = datetime.now(), dataTable = "", limit = 100):
		"""Metodo para insertar datos desde la API de binance a las tablas data_4h y data_1d.
		Recibe una fecha de entrada y salida para saber los datos requeridos. También implementa
		un mecanismo de bufer circular, donde "limit" es el numero de puntos de datos relacionados
		que se almacenarán en total, eliminando los mas antiguos según entran nuevos (FIFO).

		#! Se desactiva el bufer circular para comenzar a tratar los datos de otro modo.

		Args:
			client (binance.Client): Instancia de cliente de binance para hacer las peticiones a la api.
			symbol (string): Par de monedas requerido.
			interval (string): Cadena que, en este momento solo puede ser  "4h","1d" o "5m". Esta muy enlazado a las tablas de la BBDD
			start (datetime.datetime): Fecha de comienzo 
			end (datetime.datetime, optional): Fecha de final. Defaults to datetime.now().
			dataTable(string): Tabla de datos actuales o datos backtest. Defaults to ""
			limit (int, optional): Limite de puntos de datos en los que el bufer actua. Defaults to 100.
		"""
		cur = self.tryConnect()
		if dataTable == "backtest":
			dataTable = "backtest_"
		try:
			kline = parseKline(client.get_historical_klines(symbol, interval, start_str= f"{start}", end_str= f"{end}"))
		except (Rexceptions.ConnectionError, Uexceptions.ConnectionError,
			Uexceptions.ReadTimeoutError, Rexceptions.ReadTimeout):
			kline = []
			print(f"--> Connection reset, skipping")
			self.conn.close()
		if len(kline) > 0:
			for candle in kline:
				query = f"INSERT INTO `{dataTable}data_{interval}` (`openTime`, `symbol`, `open`, `high`, `low`, `close`) VALUES ('{candle['openTime']}', '{symbol}', '{candle['open']}', '{candle['high']}', '{candle['low']}', '{candle['close']}');"
				#print(query)
				cur.execute(query)
				self.conn.commit()
		##OPERACION DE LIMPIEZA
		'''query = f"SELECT COUNT(*) FROM data_{interval} WHERE symbol = '{symbol}'"
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
			conn.commit()'''
		self.conn.close()

	def getLastPoint(self,symbol,intervalData, dataTable = ""):
		"""Obtiene el punto mas reciente de las tablas de datos, del symbolo requerido.
		Esta función se usa para determinar los rangos de datos solicitados a la API de
		binance.

		Args:
			symbol (string): Cadena del par necesario.
			intervalData (string): "4h" o "1D", referentes a las tablas de datos almacenados.
			dataTable (string): Para utilizar como fuente las tablas de datos actuales y backtest intercambiablemente.


		Returns:
			[list]: Lista de dos puntos que contiene la entrada solicitada. Punto mas reciente, y punto mas alejado en el tiempo
			#? Una lista de un solo punto parece un poco absurda. Quizá habría que factorizar esta funcion de algun modo.
		"""
		cur = self.tryConnect()
		if dataTable == "backtest":
			dataTable = "backtest_"
		last = []
		orders = ["DESC","ASC"]
		for order in orders:
			query = f"SELECT * FROM {dataTable}data_{intervalData} WHERE symbol = '{symbol}' ORDER BY openTime {order} LIMIT 1"
			cur.execute(query)
			for point in cur:
				try:
					last.append(point[0])
				except IndexError:
					last.append(point)
		self.conn.close()
		return last
	def getDataFrame(self, symbol,intervalData, dataTable = ""):
		"""Obtiene un pandas dataframe del simbolo e intervalo solicitados.

		Args:
			symbol (string): Cadena del par necesario.
			intervalData (string): "4h" o "1D", referentes a las tablas de datos almacenados.

		Returns:
			[pandas.Dataframe]: Dataframe con todos los datos del simbolo requerido. 
		"""
		if dataTable == "backtest":
			dataTable = "backtest_"
		cur = self.tryConnect()
		query = f"SELECT * FROM {dataTable}data_{intervalData} WHERE symbol = '{symbol}' ORDER BY openTime ASC"
		pdQuery = pd.read_sql_query(query, self.conn)
		df = pd.DataFrame(pdQuery, columns=["openTime","symbol","open","high","low","close"])
		self.conn.close()
		return df
	
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
			for sym in delisted:
				st = f"DELETE FROM symbols WHERE symbol='{sym}'"
				#print(st)
				cur.execute(st)
				conn.commit()
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
				#print(ex)
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
	def getConfig(self, user):
		"""Obtiene las configuraciones de un usuario.

		Args:
			user (string): nombre del usuario

		Returns:
			[dict]: Contiene un diccionario con claves/valores de
				las configuraciones guardadas en el servidor.
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
		st = f"SELECT * FROM config WHERE user='{user}'"
		cur.execute(st)
		configDict = {}
		for configSet in cur:
			configDict[configSet[1]] = configSet[2]
		conn.close()
		return configDict
	def setConfig(self, user, key, val):
		"""Escribe valores de configuracion de manera individual.
		Recibe usuario, clave y valor, por lo que la funcion solo crea
		el query y lo ejecuta.

		Args:
			user (string): usuario
			key (string): nombre de la caracteristica
			val (string): valor de la característica.
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
		query = f"INSERT INTO config (user, keyName, value) VALUES ('{user}','{key}','{val}')"
		cur.execute(query)
		conn.commit()
		conn.close()
	def getOpenTrades(self):
		"""Obtiene toda la tabla de trades abiertos.

		Returns:
			[list]: Compuesta de diccionarios las claves de "fieldNames"
		"""
		cur = self.tryConnect()
		query = f"SELECT * FROM trading"
		try:
			cur.execute(query)
			fieldNames = ["openTime", "symbol","entryStra","exitStra","qty","price","baseQty","softLimit","softStop","lastCheck"]
			parsed = []
			for point in cur:
				try:
					parsed.append(parseSQLtoDict(fieldNames, point))
				except:
					parsed.append([])
			self.conn.close()
			return parsed
		except mariadb.InterfaceError as err:
			## DO SOME LOGGING HERE!
			print(f"{datetime.now()}, db.getOpenTrades, Imposible obtener trades")
			print(mariadb.InterfaceError, err)
			self.conn.close()
			return []
		except mariadb.ProgrammingError as err:
			print(f"{datetime.now()}, db.getOpenTrades, Imposible obtener trades")
			print(mariadb.ProgrammingError, err)
			self.conn.close()
			return[]
	def getOpenTradeCount(self):
		"""Devuelve el numero de trades en la tabla trading

		Returns:
			[int]: Numero de trades abiertos.
		"""
		cur = self.tryConnect()
		query = f"SELECT COUNT(*) FROM trading"
		cur.execute(query)
		for point in cur:
			try:
				self.conn.close()
				return int(point[0])
			except:
				self.conn.close()
				return 0
	def openTrade(self, tradeDict):
		"""Inserta un trade en la tabla de trading.

		Args:
			tradeDict (dict): Datos necesarios para que la peticion sql pueda procesarse.
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
		query = f"INSERT INTO trading (openTime, symbol, entryStra, exitStra, qty, price, baseQty, lastCheck) VALUES ('{tradeDict['openTime']}','{tradeDict['symbol']}','{tradeDict['entry']}','{tradeDict['exit']}','{tradeDict['qty']}','{tradeDict['price']}','{tradeDict['baseQty']}','{datetime.now()}')"
		cur.execute(query)
		conn.commit()
		conn.close()
	def isTradeOpen(self, symbol):
		"""Comprueba si hay un trade abierto con el simbolo entregado

		Args:
			symbol (string): Simbolo que se busca en la base de datos

		Returns:
			[bool]: True = Existente en la base de datos / False = No existe.
		"""
		cur = self.tryConnect()
		query = f"SELECT COUNT(*) FROM trading WHERE symbol = '{symbol}'"
		cur.execute(query)
		for point in cur:
			try:
				self.conn.close()
				return bool(point[0])
			except:
				self.conn.close()
				return False
	def updateTrade(self, symbol, key, value):
		"""Actualiza los trades, pudiendo hacerlo de uno en uno
		o varios a la vez, proporcionando dos listas en vez de dos
		argumentos unicos.

		Args:
			symbol (string): Par que se va a actualizar
			key (string|list): campo/s que se van a actualizar
			value (string|list): valor/es que se van a actualizar
		"""
		cur = self.tryConnect()
		if type(key) == list:
			query = f"UPDATE trading SET"
			for ind, k in enumerate(key):
				if ind == 0:
					bit = f" {k} = '{value[ind]}'"
				else:
					bit = f", {k} = '{value[ind]}'"
				query += bit
			query += f" WHERE symbol = '{symbol}'"
			#print(query)
		else:
			query = f"UPDATE trading SET {key} = '{value}' WHERE symbol = '{symbol}'"
		try:
			cur.execute(query)
			self.conn.commit()
			self.conn.close()
		except mariadb.OperationalError as err:
			print(f"{datetime.now()}, Imposible actualizar el trade {symbol}")
			print(mariadb.OperationalError, err)
			self.conn.close()
		except mariadb.InterfaceError as err:
			print(f"{datetime.now()}, Imposible actualizar el trade {symbol}")
			print(mariadb.InterfaceError, err)
			self.conn.close()
	def closeTrade(self, trade):
		"""Cierra un trade. Esto significa moverlo de la tabla trading a traded, añadiendo datos por el camino.

		Args:
			trade (dict): debe tener todos los datos necesarios para terminar el sql.
		"""
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
			query = f"DELETE FROM trading WHERE symbol = '{trade['symbol']}'"
			cur.execute(query)
			self.conn.commit()
			self.conn.close()
			print("Eliminando ABIERTO")

class Symbol(DB):
	def __init__(self):
		super().__init__()
		self.requiriedData = {"symbol": "",
							"minNotional":"",
							"minQty": "",
							"stepSize": ""}
	def _checkRequiried(self):
		for key in self.requiriedData:
			if self.requiriedData[key] is not "":
				pass
			else:
				return False
		return True
	def parseRaw(self, rawData):
		self.requiriedData["symbol"] = rawData["symbol"]
		for filt in rawData["filters"]:
			if filt["filterType"] == "MIN_NOTIONAL":
				self.requiriedData["minNotional"] = Decimal(filt["minNotional"])
			elif filt["filterType"] == "LOT_SIZE":
				self.requiriedData["minQty"] = Decimal(filt["minQty"])
				self.requiriedData["stepSize"] = Decimal(filt["stepSize"])
		return self._checkRequiried()
	def parseSQL(self, sqlData):
		self.requiriedData["symbol"] = sqlData[0]
		self.requiriedData["minNotional"] = Decimal(sqlData[1])
		self.requiriedData["minQty"] = Decimal(sqlData[2])
		self.requiriedData["stepSize"] = Decimal(sqlData[3])
		return self._checkRequiried()
	def insertSymbol(self):
		if self.tryConnect():
			st = f"INSERT INTO symbols (symbol, minNotional, minQty, stepSize) VALUES ('{self.requiriedData['symbol']}','{self.requiriedData['minNotional']}','{self.requiriedData['minQty']}','{self.requiriedData['stepSize']}')"
			#print(st)
			try:
				self.cur.execute(st)
				self.conn.commit()
				self.conn.close()
				#print(f"Registro insertado: {self.requiriedData['symbol']}")
				return True
			except mariadb.Error as e:
				print(f"Error: {e}")
				print(f"Imposible insertar el registro: {self.requiriedData['symbol']}")
				self.conn.close()
				return False
		else:
			print(f"Imposible insertar el registro: {self.requiriedData['symbol']}")
			return False
	def deleteSymbol(self):
		if self.tryConnect():
			st = f"DELETE FROM symbols WHERE symbol='{self.requiriedData['symbol']}'"
			#print(st)
			try:
				self.cur.execute(st)
				self.conn.commit()
				#print(self.cur.rowcount) #! Este atributo del cursor nos puede servir para afinar la respuesta de la db a la operación.
				self.conn.close()
				return True
			except mariadb.Error as e:
				print(f"Error: {e}")
				self.conn.close()
				print(f"Imposible borrar el registro: {self.requiriedData['symbol']}")
				return False
			#print(f"Registro borrado: {self.requiriedData['symbol']}")
		else:
			print(f"Imposible borrar el registro: {self.requiriedData['symbol']}")
			return False

class User(DB):
	def __init__(self, userName, pwd = ""):
		super().__init__()
		self.userName = userName
		self.apiKeys = []
	def stage1(self):
		self.getAPIkeys()
		self.client = Client(self.apiKeys[0],self.apiKeys[1])
	def getAPIkeys(self):
		if self.tryConnect():
			st = f"SELECT * FROM users WHERE name='{self.userName}'"
			self.cur.execute(st)
			self.apiKeys=[]
			for idAPI in self.cur:
				self.apiKeys.append(idAPI[1])
				self.apiKeys.append(idAPI[2])
			self.conn.close()
			#print("Credenciales obtenidas de DB")
			return True
		else:
			print("Imposible obtener credenciales")
			return False

if __name__ == "__main__":
	db1 = DB()

