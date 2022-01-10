#!/usr/bin/env python3
#! FILENAME.py

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from ssl import SSLError
from sys import argv
from time import sleep

import pandas as pd
import pandas_ta as ta
from binance import AsyncClient, BinanceSocketManager, ThreadedWebsocketManager
from binance.client import Client
from dbOPS import DB
from workerBase import Worker

class TSLexit(Worker):
	def __init__(self, user):
		super().__init__(user, "TSL")
		self.pingInterval = timedelta(seconds=10)
	def isUnattended(self, lastCheck, thresold):
		if lastCheck != None:
			if lastCheck <= datetime.now()-thresold:
				return True
			else:
				return False
		else:
			return True
	def setLimits(self,trade, price):
		trade["softLimit"] = price+(price*Decimal("0.07"))
		trade["softStop"] = price-(price*Decimal("0.05"))
		self.db.updateTrade(trade["symbol"],
						["softLimit","softStop"],
						[trade["softLimit"],trade["softStop"]])
	def handle_socket_message(self,msg):
		try:
			#print(f"message type: {msg['data']['c']}")
			price = Decimal(msg['c'])
			#print(f"{msg['s']}: {msg['c']} | {self.streams[msg['s']]['trade']['softLimit']}| {self.streams[msg['s']]['trade']['softSpot']}")
			if self.streams[msg['s']]["trade"]["lastCheck"] == None or self.streams[msg['s']]["trade"]["lastCheck"] <= datetime.now()-self.pingInterval:
				trade = self.streams[msg['s']]["trade"] 
				self.streams[msg['s']]["db"].updateTrade(trade["symbol"],"lastCheck", datetime.now())
				self.streams[msg['s']]["lastCheck"] = datetime.now()
			if price >= self.streams[msg['s']]["trade"]["softLimit"]:
				self.setLimits(self.streams[msg['s']]["trade"], price)
				print(f"AUMENTO. {msg['s']} at {self.streams[msg['s']]['trade']['softLimit']}")
			elif price <= self.streams[msg['s']]["trade"]["softStop"]:
				self.streams[msg['s']]["trade"]["closeTime"] = datetime.now()
				self.streams[msg['s']]["trade"]["sellPrice"] = price
				self.streams[msg['s']]["trade"]["baseProfit"] = price- self.streams[msg['s']]["trade"]["price"]
				print(f"CIERRE. {msg['s']} at {self.streams[msg['s']]['trade']['baseProfit']} benefit")
				self.streams[msg['s']]["db"].closeTrade(self.streams[msg['s']]["trade"])
				self.twm.stop_socket(self.streams[msg['s']]["stream"])
		except SSLError as err:
			print(f"{datetime.now()}, TSLexit.handle_socket_message, Error SSL")
			print(SSLError, err)
	def startWork(self):
		self.twm = ThreadedWebsocketManager(api_key=self.API[0], api_secret=self.API[1])
		self.twm.start()
		print(f"{datetime.now()}- Obteniendo trades abiertos")
		self.trades = self.db.getOpenTrades()
		self.streams = {}
		self.lastCheck = datetime.now()
		for trade in self.trades:
			self.streams[trade["symbol"]] = {}
			self.streams[trade["symbol"]]["trade"] = trade
			print(f"{datetime.now()}- Inicializando Socket: {trade['symbol']}")
			self.streams[trade["symbol"]]["db"] = DB()
			self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
		print(f"{datetime.now()}- Dando tiempo a los sockets a establecerse")
		sleep(20)
		print(f"{datetime.now()}- Comenzando monitoreo de desatendidos.")
		while True:
			if self.lastCheck <= datetime.now()-timedelta(seconds=30): ## Aqui hay que usar self.interval
				#print(f"Tick: {datetime.now()}")
				#newtrades = self.db.getOpenTrades()
				self.lastCheck = datetime.now()
				for trade in self.trades:
					if self.isUnattended(trade["lastCheck"], timedelta(seconds=30)): ##Thresold, ira a configuracion
						print(f"{datetime.now()}- Desatendido: {trade['symbol']} | {trade['lastCheck']}")
						try:
							self.twm.stop_socket(self.streams[trade["symbol"]]["stream"])
						except:
							print(f"{datetime.now()}- Error cerrando el socket")
						if trade["softLimit"] == None:
							self.setLimits(trade, trade["price"])
						self.streams[trade["symbol"]] = {}
						self.streams[trade["symbol"]]["trade"] = trade
						self.streams[trade["symbol"]]["db"] = DB()
						print(f"{datetime.now()}- Reiniciando socket: {trade['symbol']}")
						self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
						print(f"{datetime.now()}- Socket Reiniciado")

if __name__ == "__main__":
	##Instantiate Class
	task = TSLexit(argv[1])
	try:
		##Do Work
		task.startWork()
	except KeyboardInterrupt:
		print("La tarea ha terminado manualmente")