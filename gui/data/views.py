import json
from datetime import datetime
from os import environ
from sqlite3 import OperationalError

import plotly.graph_objects as go
from binance.client import Client
from django.http import HttpResponse
from django.shortcuts import render
from plotly.offline import plot

from dbOPS import DB

api_key = environ.get("TEST_BINANCE_API")
api_sec = environ.get("TEST_BINANCE_SEC")
real_api_key = environ.get("BINANCE_API_KEY")
real_api_sec = environ.get("BINANCE_API_SEC")
client = Client(real_api_key,real_api_sec)
dbName = "/var/www/html/Binance/master/binance.db"

def getTradeable(request):
	shift = request.GET["shift"]
	db = DB(dbName, client, shift)
	tradeable = db.getTRADEABLE(request.GET["sym"])
	return HttpResponse(json.dumps(tradeable))

def putTrading(request):
	shift = request.GET["shift"]
	db = DB(dbName, client, shift)
	symbol = request.GET["sym"]
	evalTS = request.GET["evalTS"]
	evalPrice = request.GET["evalPrice"]
	stop = request.GET["stop"]
	limit = request.GET["limit"]
	assetQty = request.GET["assetQty"]
	baseQty = request.GET["baseQty"]
	try:
		db.tradeSTART(symbol,evalTS, evalPrice, stop, limit, assetQty, baseQty)
		return HttpResponse(str(True))
	except OperationalError:
		####COMPRUEBA LOS PERMISOS DE LA BASE DE DATOS!!!!
		return HttpResponse(str(False))

def putTraded(request):
	shift = request.GET["shift"]
	db = DB(dbName, client, shift)
	symbol = request.GET["sym"]
	endTS = request.GET["endTS"]
	sellPrice = request.GET["sellPrice"]
	try:
		db.tradeEND(symbol,endTS, sellPrice)
		return HttpResponse(str(True))
	except OperationalError:
		####COMPRUEBA LOS PERMISOS DE LA BASE DE DATOS!!!!
		return HttpResponse(str(False))

def getBestShift(request):
	minPerc = request.GET["minPerc"]
	asset = request.GET["asset"]
	db = DB(dbName, client, "ALL")
	bestShift = db.getBestShift(int(minPerc), asset=asset) 
	return HttpResponse(json.dumps(bestShift))
