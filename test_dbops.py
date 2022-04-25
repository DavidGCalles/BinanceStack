#!/usr/bin/env python3

import dbOPS
import unittest

class Test_dbClass(unittest.TestCase):
	def test_tryConnect(self):
		db = dbOPS.DB()
		self.assertEqual(db.tryConnect(), True)

class Test_symbolClass(unittest.TestCase):
	def test_parseRaw(self):
		inst = dbOPS.Symbol()
		self.assertEqual(inst.tryConnect(), True)

if __name__ == '__main__':
	unittest.main()