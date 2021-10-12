#!/usr/bin/env python3

from datetime import datetime, timedelta
from decimal import Decimal
from dbOPS import DB

tradeOPENED = False

'''La funcion checkRules estaba integrada dentro de una clase monolítica que fue deshechada tras reconstruir el proyecto para funcionar en un cluster de microservicios.
Sin embargo, es extremadamente útil ya que se utiliza para cumplir las reglas que marca el exchange para determinar si un trade es válido.

En este momento, no es funcional ya que dentro del código se pueden observar varios 'self', que refieren a atributos de la clase en la que estaba integrada. '''

def checkRules(self):
	"""Comprueba las reglas de trading. Tras una actualizacion, ya no se utiliza un bucle WHILE que puede
	durar horas dependiendo del par.
	Aun no me gusta la funcion, pero es impresionantemente mas rapida y solo necesita una mejoría de la
	gestion de los bucles if para no tener segmentos de codigo repetidos y manejar alguna excepcion excepcional.
	Las reglas de trading, segun las define la API de Binance, son las siguientes:
		- filtro minNotional: el filtro minNotional se obtiene con (price*quantity)
		- filtro marketLot: este filtro se supera con las siguientes condiciones
			- quantity >= minQty
			- quantity <= maxQty
			- (quantity-minQty) % stepSize == 0
	"""
	act = Decimal(client.get_symbol_ticker(symbol=self.pair)["price"])
	eurP = Decimal(client.get_symbol_ticker(symbol=f"{config.symbol}EUR")["price"])
	invASSET = self.maxINV/eurP ##Precio de inversion minima en moneda ASSET
	startQTY = invASSET/act ##CANTIDAD de moneda BASE
	notionalValue = startQTY*act
	stepCheck = (startQTY-self.data["minQty"])%self.data["stepSize"]
	if stepCheck != 0:
		startQTY = startQTY-stepCheck
		stepCheck = (startQTY-self.data["minQty"])%self.data["stepSize"]
		notionalValue = startQTY*act
		if stepCheck == 0 and notionalValue >= Decimal(sym["minNotional"]):
			'''print("stepCheck PASSED. Reajustado")
			print("minNotional PASSED.")'''
			self.qtys["baseQty"] = f"{startQTY:{self.data['precision']}}"
			self.qtys["eurQty"] = f"{(startQTY*act)*eurP:{self.data['precision']}}"
			self.qtys["assetQty"] = f"{notionalValue:{self.data['precision']}}"
			return True
		else:
			'''msg = [f"stepCheck/notionalValue NOT PASSED"]'''
			return False
	else:
		#print("stepCheck PASSED")
		if notionalValue >= Decimal(sym["minNotional"]):
			#print("minNotional PASSED")
			self.qtys["baseQty"] = f"{startQTY:{self.data['precision']}}"
			self.qtys["eurQty"] = f"{(startQTY*act)*eurP:{self.data['precision']}}"
			self.qtys["assetQty"] = f"{notionalValue:{self.data['precision']}}"
			return True
		else:
			#print("minNotional NOT PASSED")
			self.qtys["baseQty"] = f""
			self.qtys["eurQty"] = f""
			self.qtys["assetQty"] = f""
			#print("Trading Rules Check NOT PASSED. Check de loop.")
			return False

class DojiSeeker:
	"""Clase que engloba los métodos para detectar tendencias según la teoria de las velas japonesas."""
	def currentTrend(self):
		#explain = f"---Identificando tendencia a 5 dias---" 
		#print(explain)
		firstClose = self.kline[0]["close"]
		lastClose = self.kline[-1]["close"]
		#print(f"firstClose: {firstClose}\nlastClose: {lastClose}")
		if firstClose > lastClose:
		#	print(f"Tendencia bajista confirmada")
			self.trend = "BEAR"
		else:
		#	print(f"Tendencia alcista confirmada")
			self.trend = "BULL"
		#print("-"*len(explain))
	def _shootingStar(self):
		relevantDoji = self.kline[-1]
		#print(relevantDoji)
		bodySize = 0
		wickSize = 0
		if relevantDoji["open"] > relevantDoji["close"]:
			bodySize = relevantDoji["open"]-relevantDoji["close"]
			wickSize = relevantDoji["high"]-relevantDoji["open"]
		else:
			bodySize = relevantDoji["close"]-relevantDoji["open"]
			wickSize = relevantDoji["high"]-relevantDoji["close"]
		#print(f"bodySize: {bodySize}\nwickSize: {wickSize}")
		if wickSize >= bodySize*2:
			print(f"{self.symbol}: Shooting Star identified")
		else:
			#print("Shooting Star missed")
			pass
	def _hammer(self):
		relevantDoji = self.kline[-1]
		#print(relevantDoji)
		bodySize = 0
		TOPwickSize = 0
		BOTwickSize = 0
		if relevantDoji["open"] > relevantDoji["close"]:
			bodySize = relevantDoji["open"]-relevantDoji["close"]
			TOPwickSize = relevantDoji["high"]-relevantDoji["open"]
			BOTwickSize = relevantDoji["close"]-relevantDoji["low"]
		else:
			bodySize = relevantDoji["close"]-relevantDoji["open"]
			TOPwickSize = relevantDoji["high"]-relevantDoji["close"]
			BOTwickSize = relevantDoji["open"]-relevantDoji["low"]
		#print(f"bodySize: {bodySize}\nTOPwickSize: {TOPwickSize}\nBOTwickSize: {BOTwickSize}")
		if TOPwickSize >= bodySize*2 and BOTwickSize <= bodySize:
			print(f"{self.symbol}: Inverted Hammer identified")
		elif BOTwickSize >= bodySize*2 and TOPwickSize <= bodySize:
			print(f"{self.symbol}: Hammer identified")
		else:
			#print("Hammer missed")
			pass
	def _piercing(self):
		d1 = self.kline[-1]
		d2 = self.kline[-2]
		if d2["open"] > d2["close"] and d1["close"] > d1["open"]:
			if d1["open"] <= d2["low"]:
				halfd2 = d2["close"] + ((d2["open"]-d2["close"])/2)
				if d1["close"] >= halfd2:
					print(f"{self.symbol}: Piercing identified")
				else:
					#print("Piercing Missed | Not above 50%")
					pass
			else:
				#print("Piercing Missed | d1 open above d2 low")
				pass
		else:
			#print("Piercing Missed | d2 not bearish or d1 not bullish")
			pass
	def searchReverseBull(self):
		self._shootingStar()
	def searchReverseBear(self):
		self._hammer()
		self._piercing()
	def __init__(self, symbol, kline, opMode):
		self.symbol = symbol
		self.kline = parseKline(kline)
		self.trend = None
		self.currentTrend()
		self.searchReverseBear()
		self.searchReverseBull()
		print(self.trend)

class Indicators:
	"""Clase que engloba los indicadores de analisis técnico que se vayan desarrollando"""
	def setAbsolutes(self):
		""" Obtiene datos sueltos.
		"""
		

		pass
	def setSMA(self, period):
		"""SIMPLE MOVING AVERAGE

		Args:
			period (int): periodos de los que obtener el sma
		"""
		#print(f"Getting SMA{period} for interval {interval}")
		
		smaColumn = []
		if len(self.data) > 0:
			for ind,val in enumerate(self.data):
				if ind < period:
					smaColumn.append(None)
				else:
					avg = 0
					values = self.data[ind-period:ind]
					for value in values:
						avg = avg + value["close"]
					avg = avg/len(values)
					smaColumn.append(avg)
		self.sma[period] = smaColumn
	def setEMA(self, period):
		self.setSMA(period)
		ema = []
		#
		multiplier = Decimal(2/(period+1))
		for ind,val in enumerate(self.sma[period]):
			if val == None:
				ema.append(None)
			else:
				if self.sma[period][ind-1] == None:
					ema.append(None)
				else:
					if ind == 0:
						ema.append(None)
					else:
						ema.append(Decimal((self.data[ind]["close"] * multiplier)+self.sma[period][ind-1]*(1-multiplier)))
		self.ema[period] = ema
	def setMACD(self, period1, period2, signal):
		self.setEMA(period1)
		self.setEMA(period2)
		macd = []
		for ind,val in enumerate(self.data):
			if self.ema[period1][ind] == None or self.ema[period2][ind] == None:
				macdPoint = None
			else:
				macdPoint = self.ema[period1][ind]-self.ema[period2][ind]
			macd.append(macdPoint)
		self.macd[f"{period1} {period2}"] = macd
	def __init__(self, data):
		"""Se inicializan las variables que mantendrán todos los valores.

		Se ejecuta por defecto:
			self.setMACD()

		Args:
			data (LIST): [description]
		
		Attributes:
			open(Decimal): Precio de apertura de la serie.
			close(Decimal): Precio de cierre de la serie.
			high (Decimal): Precio más alto de la serie.
			low (Decimal): Precio más bajo de la serie.
			sma (LIST): Lista de diccionarios cuyas claves son los periodos correspondients de SMA solicitados. 
		"""
		self.data = data
		self.open = 0
		self.close = 0
		self.high = 0
		self.low = 0
		self.sma = {}
		self.ema = {}
		self.macd = {}
		self.setMACD(12, 26, 0)

