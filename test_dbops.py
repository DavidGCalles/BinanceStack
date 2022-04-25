#!/usr/bin/env python3

import dbOPS
import unittest

class Test_dbOps(unittest.TestCase):
	def test_tryConnect(self):
		db = dbOPS.DB()
		self.assertEqual(db.tryConnect(), True)

if __name__ == '__main__':
	unittest.main()