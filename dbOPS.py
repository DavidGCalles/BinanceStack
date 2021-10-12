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

TRADEABLE_ASSETS = ["BTC", "ETH", "BNB"]

def parseKline(kline):
	"""Reconvierte las kline de Binance en el formato utilizado en la base de datos propia para optimizar almacenamiento y acceso"""
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
	return d

def parseDataRow(tupleRow):
	dataRow = {}
	dataRow["openTime"] = tupleRow[0]
	dataRow["symbol"] = tupleRow[1]
	dataRow["open"] = Decimal(tupleRow[2])
	dataRow["high"] = Decimal(tupleRow[3])
	dataRow["low"] = Decimal(tupleRow[4])
	dataRow["close"] = Decimal(tupleRow[5])
	if tupleRow[6] == None:
		dataRow["ema12"] = None
	else:
		dataRow["ema12"] = Decimal(tupleRow[6])
	if tupleRow[7] == None:
		dataRow["ema26"] = None
	else:
		dataRow["ema26"] = Decimal(tupleRow[7])
	if tupleRow[8] == None:
		dataRow["macd"] = None
	else:
		dataRow["macd"] = Decimal(tupleRow[8])
	if tupleRow[9] == None:
		dataRow["sig9"] = None
	else:
		dataRow["sig9"] = Decimal(tupleRow[9])
	if tupleRow[10] == None:
		dataRow["diff"] = None
	else:
		dataRow["diff"] = Decimal(tupleRow[10])
	return dataRow

def sqlToDataframe(sqlCursor):
	data = {
		"openTime": [],
		"symbol": [],
		"open" : [],
		"high" : [],
		"low" : [],
		"close" : [],
		"macd" : [],
		"sig" : [],
		"histogram": []
	}
	for timepoint in sqlCursor:
		try:
			pass
		except:
			pass
	return pd.DataFrame(data)

class DB:
	def __init__(self):
		self.user = f"binance"
		self.password = "binance"
		self.host = "mariadb"
		self.port = 3306
		self.database = "binance"
	def insertData(self, client, symbol, interval, start, end = datetime.now(), limit = 100):
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
		acierto = "0"
		total = "0"
		percent = "0"
		s1 = "0"
		m1 = "0"
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
					"'"+str(precision)+"'",
					"'"+acierto+"'",
					"'"+total+"'",
					"'"+percent+"'",
					"'"+s1+"'",
					"'"+m1+"'",
					"NULL","NULL"]
		querySTR = ",".join(queryARR)
		st = f"INSERT INTO symbols VALUES({querySTR})"
		#print(st)
		cur.execute(st)
		conn.commit()
		conn.close()
	def getLastPoint(self,symbol,intervalData):
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
		return apiKEYS
	def getOlderServe(self, serveType):
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

if __name__ == "__main__":
	db1 = DB()

