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

if __name__ == "__main__":
	db = DB()
	pass
	##Instantiate Class
	##Do Work