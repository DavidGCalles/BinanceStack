from workerBase import Worker

class BackTest(Worker):
	def __init__(self, user):
		super().__init__(user, "backTest")
	def startWork(self):
		entries = {}
		symbols = self.db.getSymbols()
		for pair in symbols:
			rawData = self.db.getDataFrame(pair["symbol"], "4h")
			

if __name__ == "__main__":
	##Instantiate Class
	task = BackTest(argv[1])
	##Do Work
	try:
		task.startWork()
	except KeyboardInterrupt:
		print("Tarea finalizada manualmente")