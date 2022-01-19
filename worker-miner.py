#!/usr/bin/env python3
#! FILENAME.py

from datetime import datetime, timedelta
from decimal import Decimal
from sys import argv

from binance.client import Client
from workerBase import Worker

class dbMiner(Worker):
	def __init__(self, user):
		super().__init__(user, "dbMiner")
		self.logger.info(f"Start {self.work}")
		self.pointsNeeded = 54
		self.interval4h = timedelta(hours=4)
		self.interval1d = timedelta(days=1)
	def _checkData(self, symbol, interval):
		"""Comprueba el ultimo registro de "symbol" en la tabla determinada por "interval".
		Si no existe ultimo registro, obtiene todos los determinados en "pointsNeeded" y los carga en la base de datos.
		Si existe, calcula los puntos que tiene que obtener desde la ultima fecha y los pide.
		Esta funcion se encarga de determinar fechas y maximos de almacenamiento, pasando los argumentos concretos a las
		funciones actuadoras de dbOPS.

		Args:
			symbol (STR): Nombre del par.
			interval (STR): cadena equivalente a self.client.KLINE_INTERVAL_nX. Se utiliza para definir la tabla de
				tiempos que usar, el timedelta adecuado para las solicitudes.
		"""
		self.logger.debug(f"Comprobando datos locales.", extra={"symbol": symbol, "interval": interval})
		if interval == "1d":
			deltaInterval = self.interval1d
		elif interval == "4h":
			deltaInterval = self.interval4h
		lastPoint = self.db.getLastPoint(symbol, interval)
		dateEnd = datetime.now()
		if len(lastPoint) == 0:
			##Si el conteo de la tabla y simbolo concreto da como vacio, intentar obtener los maximos puntos necesarios obteniendo la fecha de inicio (dateStartObj)
			dateStartObj = dateEnd-(deltaInterval*self.pointsNeeded)
			self.logger.warning("No hay datos locales. Solicitando.", extra={"symbol": symbol, "interval": interval, "startPoint": str(dateStartObj)})
			self.db.insertData(self.client, symbol, interval, str(dateStartObj), end = str(dateEnd), limit=self.pointsNeeded)
		else:
			##Si la tabla tiene datos ya, seguir capturando a partir de esa fecha.
			#print(f"------> {interval}, contiene datos. Comprobando tiempo {lastPoint[0]}")
			if lastPoint[0] < dateEnd-deltaInterval:
				self.logger.info("Hay datos locales. Actualizando.", extra={"symbol": symbol, "interval": interval, "startPoint": str(lastPoint[0]+deltaInterval)})
				#print(f"---------> {interval}, obteniendo ultimos puntos")
				self.db.insertData(self.client,symbol, interval, str(lastPoint[0]+deltaInterval), end=str(dateEnd), limit=self.pointsNeeded)
			else:
				self.logger.debug("Datos locales actualizados.", extra={"symbol": symbol, "interval": interval})
				#print(f"---------> {interval}, tabla actualizada.")
	def startWork(self):
		self.timer.updateLastCheck(self.db.getOlderServe(self.work))
		while True:
			if self.timer.tick() == True:
				self.logger.info("Start Mining", extra={"batchSize": self.batchSize})
				#print(f"Timer.lastCheck fetched from DB: {self.timer.lastCheck}")
				pairs = self.db.servePairs(self.work, limit= self.batchSize)
				for pair in pairs:
					#print(f"Checking {pair['symbol']}:")
					#print(f'---> Checking in db')
					self._checkData(pair["symbol"], "4h")
					self._checkData(pair["symbol"], "1d")
				self.timer.updateLastCheck(self.db.getOlderServe(self.work))
				self.logger.info("End Mining")
			if self.configInterval.tick() == True:
				self.refreshBasicConfigs()

if __name__ == "__main__":
	##Instantiate Class
	task = dbMiner(argv[1])
	try:
		##Do Work
		task.startWork()
	except:
		task.logger.warning("Tarea terminada manualmente")