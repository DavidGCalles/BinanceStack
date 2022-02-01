#!/usr/bin/env python3
#! exit-tsl.py

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
	"""Algoritmo de salida que gestiona la supervisión de diferentes hilos
	capturando precios a la vez según la estrategia "Trailing Stop Loss"

	Args:
		Worker (Worker): Instancia de trabajo con todos los metodos necesarios para controlar los precios
		de los pares asignados en DB y cerrar los trades.
	"""
	def __init__(self, user):
		"""Inicialización. Solo necesita un usuario como argumento.

		Args:
			user (string): nombre del usuario en db
		"""
		super().__init__(user, "TSL")
		self.pingInterval = timedelta(seconds=10) #!Esto deberia estar en configuraciones
		self.logger.info("Start")
	def isUnattended(self, lastCheck, thresold):
		"""Función de conveniencia para comprobar una fecha. Creo que está muy bien hecha
		porque es muy genérica y tiene una función muy clara.
		#! Threesold posiblemente deberia ir a configuracion como variable.

		Args:
			lastCheck (datetime): Ultima comprobación del trade registrada.
			thresold (timedelta): Tiempo maximo sin actualizaciones permitido.

		Returns:
			[boolean]: True = Desatentido /False = No desatendido.
		"""
		if lastCheck != None:
			if lastCheck <= datetime.now()-thresold:
				return True
			else:
				return False
		else:
			return True
	def setLimits(self,trade, price):
		"""Crea dinamicamente los límites superior e inferior de los trades.
		Esta función se utiliza en varios puntos de la tarea.
		#! Los margenes 0.07 y 0.05 deberian ir a configuracion

		Además, reporta a la base de datos una actualizacion en el momento.

		Args:
			trade ([type]): [description]
			price ([type]): [description]
		"""
		trade["softLimit"] = price+(price*Decimal("0.07"))
		trade["softStop"] = price-(price*Decimal("0.05"))
		self.db.updateTrade(trade["symbol"],
						["softLimit","softStop"],
						[trade["softLimit"],trade["softStop"]])
	def handle_socket_message(self,msg):
		"""Realmente, no me gusta esta manera de programar. No me parece
		que lo este haciendo bien.

		Esta función es la que se ejecuta recurrentemente cuando entran datos
		desde los sockets de precios.

		Se captura el precio y se empiezan a hacer comparaciones.
		Si el precio es superior a softLimit, se ejecuta setLimits con el nuevo precio como base. Esto significa que tanto softLimit como softStop se incrementan.
		Si el precio es inferior a softStop, se cierra el trade. Se recogen datos y se envia a la base de datos.

		Args:
			msg (dict): Mensaje de respuesta del socket. 
		"""
		price = Decimal(msg['c'])
		if self.streams[msg['s']]["trade"]["lastCheck"] == None or self.streams[msg['s']]["trade"]["lastCheck"] <= datetime.now()-self.pingInterval:
			trade = self.streams[msg['s']]["trade"]
			now = datetime.now()
			self.streams[msg['s']]["db"].updateTrade(trade["symbol"],"lastCheck", now)
			self.streams[msg['s']]["logger"].debug("Socket Ping", extra={"symbol":msg['s'], "price":price})
			self.streams[msg['s']]["trade"]["lastCheck"] = now
		if price >= self.streams[msg['s']]["trade"]["softLimit"]:
			self.setLimits(self.streams[msg['s']]["trade"], price)
			self.streams[msg['s']]["logger"].warning("Limit Passed", extra={"symbol": msg["s"], "softLimit": self.streams[msg['s']]['trade']['softLimit'], "softStop": self.streams[msg['s']]['trade']['softStop']})
		elif price <= self.streams[msg['s']]["trade"]["softStop"]:
			self.streams[msg['s']]["trade"]["closeTime"] = now
			self.streams[msg['s']]["trade"]["sellPrice"] = price
			self.streams[msg['s']]["trade"]["baseProfit"] = price- self.streams[msg['s']]["trade"]["price"]
			self.streams[msg['s']]["db"].closeTrade(self.streams[msg['s']]["trade"])
			self.streams[msg['s']]["logger"].warning("Stop Passed", extra={"symbol":msg["s"], "baseProfit": self.streams[msg['s']]["trade"]["baseProfit"]})
			try:
				self.twm.stop_socket(self.streams[msg['s']]["stream"])
			except KeyError:
				self.streams[msg['s']]["logger"].error("Closing socket already closed", extra={"symbol":msg["s"]})
	def setupPool(self):
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
			if len(self.streams[trade["symbol"]]["logger"].handlers) > 0:
				pass
			else:
				handler = logging.FileHandler(f'logs/{trade["symbol"]}-{trade["entryStra"]}-{trade["exitStra"]}.json')
				handler.setFormatter(ecs_logging.StdlibFormatter())
				self.streams[trade["symbol"]]["logger"].addHandler(handler)
			#######################################################
			self.logger.info(f"Starting Socket: {trade['symbol']}", extra={"symbol":trade['symbol']})
			self.streams[trade["symbol"]]["db"] = DB()
			self.streams[trade["symbol"]]["stream"] = self.twm.start_symbol_ticker_socket(callback=self.handle_socket_message, symbol=trade["symbol"])
		#self.logger.debug(f"Giving time to sockets to establish")
	def startWork(self):
		"""Otra función que no me gusta nada.

		Esta parte gestiona la existencia y salud de los hilos que comprueban los precios. Se crea un diccionario streams.
		En este diccionario se almacenan entonces el trade, el logger específico y la instancia del conector de base de datos
		que cada hilo va a necesitar.

		Despues de eso los crea y los lanza. Cuando ha pasado un tiempo prudencial, empieza a chequear si alguno no ha iniciado
		o ya se ha caido.
		"""
		self.setupPool()
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
						if len(self.streams[trade["symbol"]]["logger"].handlers) > 0:
							pass
						else:
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