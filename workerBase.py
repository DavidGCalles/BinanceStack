#!/usr/bin/env python3
#! FILENAME.py

from datetime import datetime, timedelta
from decimal import Decimal
from sys import argv
from time import sleep
from timer import Timer

from binance.client import Client
from dbOPS import DB

class Worker:
	def __init__(self, user, workType):
		self.db = DB()
		self.API = self.db.getAPI(user)
		self.user = user
		self.work = workType
		self.client = Client(self.API[0], self.API[1])
		self.config = self.db.getConfig(user)
		self.requiried = [f"{self.work}_configInterval", f"{self.work}_interval", f"{self.work}_batchSize"]
		self.wide = ["wide_realTrades", "wide_fiat", "wide_maxInv", "wide_maxTrades", "wide_baseCurrency"]
		self._setupWorkConfig()
		self._setupWideConfig()
	def _setupWorkConfig(self):
		#Tantos bloques Try son para aislar cada configuracion. Si los uniese, la ausencia de una caracteristica haria que
		# cada uno de los defaults se sobreescribiese.
		try:
			self.configInterval = Timer(updateTime = timedelta(minutes=int(self.config[self.requiried[0]])))
		except KeyError:
			self.configInterval= Timer(updateTime=timedelta(minutes=2))
			self.db.setConfig(self.user, self.requiried[0], str(2))
		try:
			self.timer = Timer(updateTime = timedelta(minutes=int(self.config[self.requiried[1]])))
		except KeyError:
			self.timer = Timer()
			self.db.setConfig(self.user, self.requiried[1], str(5))
		try:
			self.batchSize = int(self.config[self.requiried[2]])
		except KeyError:
			self.batchSize = 20
			self.db.setConfig(self.user, self.requiried[2], str(20))
	def _setupWideConfig(self):
		try:
			#!MUY IMPORTANTE!
			self.realTrades = bool(self.config[self.wide[0]]) #Variable para determinar paper/real trading.
		except KeyError:
			self.realTrades = False
			self.db.setConfig(self.user, self.wide[0], False)
		try:
			self.fiat = self.config[self.wide[1]] #Variable para determinar la moneda fiat.
		except KeyError:
			self.fiat = "EUR"
			self.db.setConfig(self.user, self.wide[1], "EUR")
		try:
			self.maxInv = int(self.config[self.wide[2]]) #Maxima cantidad (en la FIAT seleccionada) de inversion por trade
		except KeyError:
			self.maxInv = 30
			self.db.setConfig(self.user, self.wide[2], 30)
		try:
			self.maxTrades = int(self.config[self.wide[3]]) #Trades maximos abiertos simultaneamente
		except KeyError:
			self.maxTrades = 10 
			self.db.setConfig(self.user, self.wide[3], 10)
		try:
			self.baseCurrency = self.config[self.wide[4]].split(",") #Pares permitidos para el trading.
		except KeyError:
			self.baseCurrency = ["BTC", "ETH", "BNB"]
			self.db.setConfig(self.user, self.wide[4], str.join(",", self.baseCurrency))
	def _getBaseCurrency(self, symbol):
		"""Metodo de utilidad, exclusivamente utilizado en _checkRules.

		Args:
			symbol ([type]): [description]

		Returns:
			[type]: [description]
		"""
		for base in self.baseCurrency:
			if symbol[len(base)-(len(base)*2):] == base:
				return base
		return None
	def _checkRules(self, pair):
		#! IMPORTANTE. Esta función hace uso de muchas opciones de configuracion WIDE
		# Por todo esto y mucho más, solo se va a crear el esqueleto NO FUNCIONAL y comentado.
		# Falta definir los argumentos de entrada
		#? Estoy a punto de potar. La funcion esta muy bien escrita pero... no hay comentarios y se apoya en estructuras que ya no existen.
		#? Todos los atributos de self provienen de un diccionario de la base de datos, tabla symbol. Sustituidos por el argumento "pair"
		"""Comprueba las reglas de trading.
		Las reglas de trading, segun las define la API de Binance, son las siguientes:
			- filtro minNotional: el filtro minNotional se obtiene con (price*quantity)
			- filtro marketLot: este filtro se supera con las siguientes condiciones
				- quantity >= minQty
				- quantity <= maxQty
				- (quantity-minQty) % stepSize == 0
		"""
		act = Decimal(self.client.get_symbol_ticker(symbol=pair['symbol'])["price"]) # Precio actual del par.
		base = self._getBaseCurrency(pair["symbol"])
		if base != None:
			if base != self.fiat:
				print(f"eurP assign: {base}{self.fiat}")
				eurP = Decimal(self.client.get_symbol_ticker(symbol=f"{base}{self.fiat}")["price"]) #Precio en fiat de la moneda base
			else:
				eurP = act
		else:
			print("No se puede obtener el precio base/fiat y calcular las reglas")
			return [False, {}]
		invBASE = self.maxInv/eurP ##Precio de inversion minima en moneda base
		startQTY = invBASE/act ##CANTIDAD de moneda asset
		notionalValue = startQTY*act
		stepCheck = (startQTY-pair["minQty"])%pair["stepSize"]
		if stepCheck != 0:
			startQTY = startQTY-stepCheck
			stepCheck = (startQTY-pair["minQty"])%pair["stepSize"]
			notionalValue = startQTY*act
			if stepCheck == 0 and notionalValue >= Decimal(pair["minNotional"]):
				'''print("stepCheck PASSED. Reajustado")
				print("minNotional PASSED.")'''
				qtys = {}
				qtys["qty"] = f"{startQTY}"
				qtys["fiatQty"] = f"{(startQTY*act)*eurP}"
				qtys["baseQty"] = f"{notionalValue}"
				return [True, qtys]
			else:
				'''msg = [f"stepCheck/notionalValue NOT PASSED"]'''
				return [False, {}]
	def refreshBasicConfigs(self):
		print("Probing config in DB.")
		self.config = self.db.getConfig(self.user)
		self.configInterval.updateTime = timedelta(minutes=int(self.config[self.requiried[0]]))
		self.timer.updateTime = timedelta(minutes=int(self.config[self.requiried[1]]))
		self.batchSize = int(self.config[self.requiried[2]])
	def openTrade(self, tradeDict):
		"""[summary]

		Args:
			tradeDict ([type]): openTime, symbol, entry, exit, price
		"""
		if self.db.getOpenTradeCount() >= self.maxTrades:
			pass
		else:
			print("OPENING TRADE")
			check = self._checkRules(tradeDict["pair"])
			if check[0] == True:
				tradeDict["qty"] = check[1]["qty"]
				tradeDict["baseQty"] = check[1]["baseQty"]
				if self.realTrades == True:
					print("Opening trade")
					#TODO aqui iria la orden de compra, con una instancia de Binance.client. 
				else:
					print("Opening MOCK trade")
				tradeDict["openTime"] = datetime.now()
				print("Inserting in database.")
				## No funciona correctamente.
				self.db.openTrade(tradeDict)
			else:
				print("El trade no cumple las reglas. Revisa el codigo.")
	def closeTrade(self, tradeDict):
		print("Selling")
		print("Moving from Trading to Traded in DB")


if __name__ == "__main__":
	print("This is a base class, you should not call it from here.")