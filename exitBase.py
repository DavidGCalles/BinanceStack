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
from sistema import Worker

###LISTA DE COSAS QUE VAN EN EL EXITBASE
#- ISUNATTENDED entera. Será de base para cualquier metodo.
#-- la variable thresold va a configuracion. Es el margen en segundos por el cual se considera desatendido.
#- self.pingInterval a configuracion. Es utilizado para limitar el ping que hacen los sockets.
#- self.twm Pasa a init. 
#- self.streams

if __name__ == "__main__":
	db = DB()
	pass
	##Instantiate Class
	task = None
	try:
		##Do Work
		task.startWork()
	except KeyboardInterrupt:
		print("La tarea ha terminado manualmente")