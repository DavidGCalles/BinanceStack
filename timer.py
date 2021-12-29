#!/usr/bin/env python3
#! FILENAME.py

from datetime import datetime, timedelta

from time import sleep

class Timer:
	def __init__(self, updateTime = timedelta(minutes=5)):
		self.updateTime = updateTime
		self.lastCheck = None
	def updateLastCheck(self, newCheck):
		self.lastCheck = newCheck
	def tick(self):
		now = datetime.now()
		#print(f"lastCheck: {self.lastCheck}")
		#print(f"now: {now}")
		if self.lastCheck == None or now >= self.lastCheck + self.updateTime:
			self.lastCheck = now
			print(f"Timer.tick(): True | nextCheck: {self.lastCheck+self.updateTime}")
			return True
		else:
			#print(f"Tick: False | nextCheck: {self.lastCheck + self.updateTime}")
			return False
	def externalTick(self, datetimeToTrack):
		now = datetime.now()
		if datetimeToTrack == None:
			self.lastCheck = now
			print(f"Timer.externalTick(): True | tracked: {datetimeToTrack}")
			return True
		elif now >= datetimeToTrack + self.updateTime:
			self.lastCheck == now
			print(f"Timer.externalTick(): True | tracked: {datetimeToTrack} | triggerHour: {datetimeToTrack+self.updateTime}")
			return True
		else:
			return False

if __name__ == "__main__":
	print("Que haces?!?!")
	pass
	##Instantiate Class
	##Do Work