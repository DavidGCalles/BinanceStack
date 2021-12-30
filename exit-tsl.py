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
from mariadb import OperationalError
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
			#print(f"message type: {msg['data']['c']}")
			price = Decimal(msg['c'])
			#print(f"{msg['s']}: {msg['c']} | {self.streams[msg['s']]['trade']['softLimit']}| {self.streams[msg['s']]['trade']['softSpot']}")
			try:
				if self.streams[msg['s']]["lastCheck"] == None or self.streams[msg['s']]["lastCheck"] <= datetime.now()-self.pingInterval:
					trade = self.streams[msg['s']]["trade"] 
					self.db.updateTrade(trade["symbol"],"lastCheck", datetime.now())
					self.streams[msg['s']]["lastCheck"] = datetime.now()
			except KeyError:
				print(self.streams[msg['s']])
			if price >= self.streams[msg['s']]["trade"]["softLimit"]:
				self.setLimits(self.streams[msg['s']]["trade"], price)
				print(f"AUMENTO. {msg['s']} at {self.streams[msg['s']]['trade']['softLimit']}")
			elif price <= self.streams[msg['s']]["trade"]["softStop"]:
				self.streams[msg['s']]["trade"]["closeTime"] = datetime.now()
				self.streams[msg['s']]["trade"]["sellPrice"] = price
				self.streams[msg['s']]["trade"]["baseProfit"] = price- self.streams[msg['s']]["trade"]["price"]
				print(f"CIERRE. {msg['s']} at {self.streams[msg['s']]['trade']['baseProfit']} benefit")
				self.db.closeTrade(self.streams[msg['s']]["trade"])
				self.twm.stop_socket(self.streams[msg['s']]["stream"])
	def startWork(self):
		self.twm = ThreadedWebsocketManager(api_key=self.API[0], api_secret=self.API[1])
		self.twm.start()
		self.trades = self.db.getOpenTrades()
		self.streams = {}
		self.lastCheck = datetime.now()
		for trade in self.trades:
			self.streams[trade["symbol"]] = {}
			self.streams[trade["symbol"]]["trade"] = trade
			print(f"Inicializando Socket: {trade['symbol']}")
			self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
			self.streams[trade["symbol"]]["lastCheck"] = None
		sleep(10)
		while True:
			if self.lastCheck <= datetime.now()-timedelta(seconds=30):
				#print(f"Tick: {datetime.now()}")
				newtrades = self.db.getOpenTrades()
				self.lastCheck = datetime.now()
				for trade in newtrades:
					if self.isUnattended(trade["lastCheck"], timedelta(seconds=30)):
						print(f"Desatendidos: {trade}")
						try:
							self.twm.stop_socket(self.streams[trade["symbol"]]["stream"])
						except:
							print("Error cerrando el socket")
						if trade["softLimit"] == None or trade["softStop"] == None:
							self.setLimits(trade, trade["price"])
						self.streams[trade["symbol"]] = {}
						self.streams[trade["symbol"]]["trade"] = trade
						self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
						self.streams[trade["symbol"]]["lastCheck"] = None

if __name__ == "__main__":
	##Instantiate Class
	task = TSLexit(argv[1])
	try:
		##Do Work
		task.startWork()
	except KeyboardInterrupt:
		print("La tarea ha terminado manualmente")