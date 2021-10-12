from datetime import datetime, timedelta
from os import environ
from decimal import Decimal

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
assets = ["ETH", "BNB", "BTC"]

def index(request):
	return render(request, "index.html")

def Trading(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADINGdict()
	d = {"syms": a}
	return render(request, "trading.html", d)

def Traded(request):
	db = DB(dbName,client, request.GET["shift"])
	a = db.getTRADEDdict()
	assets = [{"name": "ETH", "good": 0, "bad": 0, "percGood": 0, "benefit": 0},
				{"name": "BNB", "good": 0, "bad": 0, "percGood": 0, "benefit": 0},
				{"name": "BTC", "good": 0, "bad": 0, "percGood": 0, "benefit": 0}]
	general = {"good": 0, "bad":0,"percGood":0, "duration": timedelta(seconds= 0)}
	for item in a:
		evalPrice = Decimal(item["evalPrice"])
		endPrice = Decimal(item["sell"])
		if endPrice > evalPrice:
			item["tradeEND"] = True
			general["good"] = general["good"] +1
		else:
			item["tradeEND"] = False
			general["bad"] = general["bad"] +1
		item["duration"] = item["endTS"]-item["evalTS"]
		general["duration"] = general["duration"] + item["duration"]

	totTrades = general["good"]+general["bad"]
	try:
		general["percGood"] = f"{(general['good']/totTrades)*100:.2f}"
		general["duration"] = general["duration"]/totTrades
	except ZeroDivisionError:
		general["percGood"] = 0
		general["duration"] = 0

	for asset in assets:
		Lass = len(asset["name"])
		for item in a:
			if item["symbol"][Lass-Lass*2:] == asset["name"]:
				if item["tradeEND"] == True:
					asset["good"] = asset["good"] + 1
				else:
					asset["bad"] = asset["bad"] + 1
				soldAT = Decimal(item["sell"])*Decimal(item["baseQty"])
				ben = soldAT-Decimal(item["assetQty"])
				asset["benefit"] = asset["benefit"] + ben
		totTrades = asset["good"]+asset["bad"]
		try:
			asset["percGood"] = (asset["good"]/totTrades)*100
		except ZeroDivisionError:
			asset["percGood"] = 0
		asset["percGood"] = f"{asset['percGood']:.2f}"
		asset["benefit"] = f"{asset['benefit']:.8f}"

	d = {"syms": a, "assets": assets, "general": general}
	return render(request, "traded.html", d)

def Efectivity(request):
	db = DB(dbName,client, request.GET["shift"])
	##Efectividad por dia/asset
	graphs = []
	data = db.getEFperDay(asset=request.GET["asset"])
	colors = ["orange",]*len(data["day"])
	for i in range(len(data["day"])):
		if Decimal(data["perc"][i]) <= Decimal("100") and Decimal(data["perc"][i]) >= Decimal("65"):
			colors[i] = "green"
	graph = go.Figure(data=[go.Scatter(x=data["day"], y=data["co"], hovertext=data["text"], mode="markers",marker_color=colors)])
	graph.update_layout(title="Efectividad general diaria "+request.GET["asset"])
	graphDIV = plot(graph, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
				"autosizable": True})
	graphs.append(graphDIV)
	d = {"graphs": graphs}
	return render(request, "efectivity.html", d)

def Stats(request):
	db = DB(dbName,client, request.GET["shift"])
	#####Grafico GENERAL
	percs = db.getPercentage()
	bestShift = db.getBestShift(66)
	colors = ["orange",]*24
	for i in bestShift["hour"]:
		colors[int(i)] = "green"
	perTradeStart = go.Figure(data=[
		go.Bar(name="Porcentaje", x=percs["hour"], y=percs["perc"], hovertext=percs["totals"], marker_color=colors)])
	perTradeStart.update_layout(barmode="group",title="Efectividad general")
	startTSdiv = plot(perTradeStart, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})
	###Graficos de asset
	assets = ["ETH","BNB","BTC"]
	graphs = []
	for asset in assets:
		percs = db.getPercentage(asset=asset)
		bestShift = db.getBestShift(66, asset=asset)
		colors = ["orange",]*24
		for i in bestShift["hour"]:
			colors[int(i)] = "green"
		TradeStart = go.Figure(data=[
		go.Bar(name="Porcentaje", x=percs["hour"], y=percs["perc"], hovertext=percs["totals"], marker_color=colors)])
		TradeStart.update_layout(barmode="group",title=f"Efectividad {asset}")
		TSdiv = plot(TradeStart, output_type="div",
				include_plotlyjs=False,
				config={"displayModeBar": False,
						"autosizable": True})
		graphs.append(TSdiv)
	####
	###VARIABLES PARA EL GRAFCO POR PARES
	'''parList = []
	winList = []
	losList = []
	for item in a:
		try:
			ind = parList.index(item["symbol"])
		except ValueError:
			parList.append(item["symbol"])
			winList.append(0)
			losList.append(0)
			ind = parList.index(item["symbol"])
		if item["tradeEND"] == True:
			winList[ind] = winList[ind] + 1
		else:
			losList[ind] = losList[ind] + 1
	###Grafico de trades por pares.
	perPair = go.Figure(data=[
		go.Bar(name="Ganados", x=winList, y=parList, orientation= "h"),
		go.Bar(name="Perdidos", x=losList, y=parList, orientation="h")])
	perPair.update_layout(barmode="group",title="Resultados agrupados por Pares",
						height=3000)
	perPairdiv = plot(perPair, output_type="div",
			include_plotlyjs=False,
			config={"displayModeBar": False,
					"autosizable": True})'''
	###############################
	d = {"perStartTS": startTSdiv, "graphs": graphs}
	return render(request, "stats.html", d)

def Graph(request):
	sym = request.GET["sym"]
	evalTS = request.GET["evalTS"]
	endTS = request.GET["endTS"]
	evalPrice = request.GET["evalPrice"]
	stopPrice = request.GET["stopPrice"]
	limitPrice = request.GET["limitPrice"]
	kline = client.get_historical_klines(sym, Client.KLINE_INTERVAL_5MINUTE, evalTS, endTS)
	df = {"Date":[],
		"Open": [],
		"High": [],
		"Low": [],
		"Close": []}
	for line in kline:
		df["Date"].append(datetime.fromtimestamp(line[0]/1000))
		df["Open"].append(line[1])
		df["High"].append(line[2])
		df["Low"].append(line[3])
		df["Close"].append(line[4])
	fig = go.Figure(data=[
		go.Candlestick(x=df['Date'],
				open=df['Open'],
				high=df['High'],
				low=df['Low'],
				close=df['Close'])])
	fig.update_layout(
		autosize=True,
		width=800,
		height=1200)
	div = plot(fig, output_type="div",
				include_plotlyjs=False,
				config={"displayModeBar": False,
						"autosizable": True})
	#db = DB(dbName,client, request.GET["shift"])
	#syms = db.getTRADINGdict()
	#symDATA = None
	#for i in syms:
	#	if i["symbol"] == sym:
	#		symDATA = i
	d = {"sym": sym, "graph": div, "evalTS": evalTS, "endTS": endTS}
	return render(request, "graphView.html", d)
