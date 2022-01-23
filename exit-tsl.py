#!/usr/bin/env python3
#! FILENAME.py

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from ssl import SSLError
from sys import argv
from time import sleep

import logging
import ecs_logging

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
		self.logger.info("Start")
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
		#print(f"message type: {msg}")
		price = Decimal(msg['c'])
		#print(f"{msg['s']}: {msg['c']} | {self.streams[msg['s']]['trade']['softLimit']}| {self.streams[msg['s']]['trade']['softSpot']}")
		if self.streams[msg['s']]["trade"]["lastCheck"] == None or self.streams[msg['s']]["trade"]["lastCheck"] <= datetime.now()-self.pingInterval:
			trade = self.streams[msg['s']]["trade"]
			now = datetime.now()
			self.streams[msg['s']]["db"].updateTrade(trade["symbol"],"lastCheck", now)
			self.streams[msg['s']]["logger"].debug("Socket Ping", extra={"symbol":msg['s'], "price":price})
			self.streams[msg['s']]["trade"]["lastCheck"] = now
		if price >= self.streams[msg['s']]["trade"]["softLimit"]:
			self.setLimits(self.streams[msg['s']]["trade"], price)
			#print(f"{now}- AUMENTO. {msg['s']} at {self.streams[msg['s']]['trade']['softLimit']}")
			self.streams[msg['s']]["logger"].warning("Limit Passed", extra={"symbol": msg["s"], "softLimit": self.streams[msg['s']]['trade']['softLimit'], "softStop": self.streams[msg['s']]['trade']['softStop']})
		elif price <= self.streams[msg['s']]["trade"]["softStop"]:
			self.streams[msg['s']]["trade"]["closeTime"] = now
			self.streams[msg['s']]["trade"]["sellPrice"] = price
			self.streams[msg['s']]["trade"]["baseProfit"] = price- self.streams[msg['s']]["trade"]["price"]
			print(f"{now}- CIERRE. {msg['s']} at {self.streams[msg['s']]['trade']['baseProfit']} benefit")
			self.streams[msg['s']]["db"].closeTrade(self.streams[msg['s']]["trade"])
			self.streams[msg['s']]["logger"].warning("Stop Passed", extra={"symbol":msg["s"], "baseProfit": self.streams[msg['s']]["trade"]["baseProfit"]})
			try:
				self.twm.stop_socket(self.streams[msg['s']]["stream"])
			except KeyError:
				self.streams[msg['s']]["logger"].error("Closing socket already closed", extra={"symbol":msg["s"]})
	def startWork(self):
		self.twm = ThreadedWebsocketManager(api_key=self.API[0], api_secret=self.API[1])
		self.twm.start()
		self.logger.debug(f"Getting Open Trades")
		self.trades = self.db.getOpenTrades()
		self.streams = {}
		self.lastCheck = datetime.now()
		for trade in self.trades:
			self.streams[trade["symbol"]] = {}
			self.streams[trade["symbol"]]["trade"] = trade
			#LOGGING
			self.streams[trade["symbol"]]["logger"] = logging.getLogger(f'{trade["symbol"]}-{trade["entryStra"]}-{trade["exitStra"]}')
			self.streams[trade["symbol"]]["logger"].setLevel(logging.DEBUG)
			handler = logging.FileHandler(f'logs/{trade["symbol"]}-{trade["entryStra"]}-{trade["exitStra"]}.json')
			handler.setFormatter(ecs_logging.StdlibFormatter())
			self.streams[trade["symbol"]]["logger"].addHandler(handler)
			#######################################################
			self.logger.info(f"Starting Socket: {trade['symbol']}", extra={"symbol":trade['symbol']})
			self.streams[trade["symbol"]]["db"] = DB()
			self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
		self.logger.debug(f"Giving time to sockets to establish")
		sleep(20)
		self.logger.info(f"Starting unattended monitor")
		while True: 
			if self.lastCheck <= datetime.now()-timedelta(seconds=30): ## Aqui hay que usar self.interval
				#print(f"Tick: {datetime.now()}")
				#newtrades = self.db.getOpenTrades()
				self.lastCheck = datetime.now()
				for trade in self.trades:
					if self.isUnattended(trade["lastCheck"], timedelta(seconds=30)): ##Thresold, ira a configuracion
						self.logger.warning(f"Unattended: {trade['symbol']}", extra={"symbol": trade['symbol'], "lastCheck": trade['lastCheck']})
						try:
							self.twm.stop_socket(self.streams[trade["symbol"]]["stream"])
						except:
							self.logger.error(f"Error closing socket")
						if trade["softLimit"] == None:
							self.setLimits(trade, trade["price"])
						self.streams[trade["symbol"]] = {}
						self.streams[trade["symbol"]]["trade"] = trade
						#LOGGING
						self.streams[trade["symbol"]]["logger"] = logging.getLogger(f'{trade["symbol"]}-{trade["entryStra"]}-{trade["exitStra"]}')
						self.streams[trade["symbol"]]["logger"].setLevel(logging.DEBUG)
						handler = logging.FileHandler(f'logs/{trade["symbol"]}-{trade["entryStra"]}-{trade["exitStra"]}.json')
						handler.setFormatter(ecs_logging.StdlibFormatter())
						self.streams[trade["symbol"]]["logger"].addHandler(handler)
						#######################################################
						self.streams[trade["symbol"]]["db"] = DB()
						self.logger.info(f"Restarting socket: {trade['symbol']}")
						self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
						self.logger.debug(f"Restarted socket: {trade['symbol']}")

if __name__ == "__main__":
	##Instantiate Class
	task = TSLexit(argv[1])
	try:
		##Do Work
		task.startWork()
	except KeyboardInterrupt:
		print("La tarea ha terminado manualmente")