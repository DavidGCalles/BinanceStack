#!/usr/bin/env python3

import dbOPS
import unittest

class Test_dbClass(unittest.TestCase):
	def test_tryConnect(self):
		db = dbOPS.DB()
		self.assertEqual(db.tryConnect(), True)

class Test_symbolClass(unittest.TestCase):
	def test_parseRaw(self):
		mockInput = {'symbol': 'ETHBTC', 'status': 'TRADING', 'baseAsset': 'ETH', 'baseAssetPrecision': 8, 'quoteAsset': 'BTC',
					'quotePrecision': 8, 'quoteAssetPrecision': 8, 'baseCommissionPrecision': 8, 'quoteCommissionPrecision': 8,
					'orderTypes': ['LIMIT', 'LIMIT_MAKER', 'MARKET', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'],
					'icebergAllowed': True, 'ocoAllowed': True, 'quoteOrderQtyMarketAllowed': True, 'allowTrailingStop': True, 'isSpotTradingAllowed': True, 'isMarginTradingAllowed': True,
					'filters': [{'filterType': 'PRICE_FILTER', 'minPrice': '0.00000100', 'maxPrice': '922327.00000000', 'tickSize': '0.00000100'}, 
								{'filterType': 'PERCENT_PRICE', 'multiplierUp': '5', 'multiplierDown': '0.2', 'avgPriceMins': 5},
								{'filterType': 'LOT_SIZE', 'minQty': '0.00010000', 'maxQty': '100000.00000000', 'stepSize': '0.00010000'},
								{'filterType': 'MIN_NOTIONAL', 'minNotional': '0.00010000', 'applyToMarket': True, 'avgPriceMins': 5},
								{'filterType': 'ICEBERG_PARTS', 'limit': 10},
								{'filterType': 'MARKET_LOT_SIZE', 'minQty': '0.00000000', 'maxQty': '1351.84169735', 'stepSize': '0.00000000'},
								{'filterType': 'TRAILING_DELTA', 'minTrailingAboveDelta': 10, 'maxTrailingAboveDelta': 2000, 'minTrailingBelowDelta': 10, 'maxTrailingBelowDelta': 2000},
								{'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': 200}, {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': 5}],
					'permissions': ['SPOT', 'MARGIN']}
		inst = dbOPS.Symbol()
		self.assertEqual(inst.parseRaw(mockInput), True)
	def test_parseSQL(self):
		mockInput = ("ETHBTC", "0.00002", "0.4232", "0.00670")
		inst = dbOPS.Symbol()
		self.assertEqual(inst.parseSQL(mockInput), True)

class Test_userClass(unittest.TestCase):
	def test_getAPIKeys(self):
		user = dbOPS.User("david")
		self.assertEqual(user.getAPIkeys(), True)
		self.assertEqual(len(user.apiKeys), 2)

'''class Test_devSpace(unittest.TestCase):
	def test_binanceClientDEV(self):
		user = dbOPS.User("david")
		user.stage1()
		for symbol in user.client.get_exchange_info()["symbols"]:
			print(symbol)
			input()'''

if __name__ == '__main__':
	unittest.main()