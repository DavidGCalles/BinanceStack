import mariadb
"""Este script se utiliza para crear el scheme de la base de datos de binance.
Lo he pasado muy mal al perder la base de datos. Recrearla a mano una segunda vez... NO. """
host = "192.168.1.200"
port = 3306
user = "binance"
password = "binance"
database = "binance"

try:
	conn = mariadb.connect(
				user=user,
				password=password,
				host=host,
				port=port,
				database=database
				)
except mariadb.Error as e:
	print(f"Error connecting to MariaDB Platform: {e}")
cur = conn.cursor()

def createUserTable():
	"""La tabla de usuarios se utiliza para guardar claves de API y correo de los usuarios.
	"""
	query = f"CREATE TABLE IF NOT EXISTS `users` ( `name` VARCHAR(255) NOT NULL , `key` VARCHAR(255) NOT NULL , `secret` VARCHAR(255) NOT NULL , `mail` VARCHAR(255) NOT NULL ) ENGINE = InnoDB;"
	cur.execute(query)
	print("Tabla de usuarios creada")

def createSymbolTable():
	"""La tabla de simbolos es el núcleo principal del sistema. Contiene:
		- Todos los pares del exchange TRADEABLES (dbOPS decidirá cuales son en base a un array)
		- Características necesarias en las reglas de trading (marcadas por binance)
		- Estadisticas básicas (aciertos, total, porcentaje)
		- Campos de monitorización, utilizados para determinar por los servicios cuando esos pares fueron inspeccionados por ultima vez.
	"""
	query = f"CREATE TABLE IF NOT EXISTS `symbols` ( `symbol` VARCHAR(50) NOT NULL , `minNotional` DECIMAL(40,8) NOT NULL , `minQty` DECIMAL(40,8) NOT NULL , `stepSize` DECIMAL(40,8) NOT NULL , `precision` INT(2) NOT NULL , `acierto` INT(5) NOT NULL DEFAULT '0' , `total` INT(5) NOT NULL DEFAULT '0' , `percent` INT(3) NOT NULL DEFAULT '0' , `1S` BOOLEAN NULL DEFAULT NULL , `1M` BOOLEAN NULL DEFAULT NULL , `dbMiner` DATETIME NULL DEFAULT NULL , `scalper` DATETIME NULL DEFAULT NULL ) ENGINE = InnoDB;"
	cur.execute(query)
	print("Tabla de simbolos creada")

def createDataTables():
	"""Crea las tablas que contendrán los datos de las velas necesarias y los calculos MACD.
	"""
	query = f"CREATE TABLE IF NOT EXISTS `data_4h` ( `openTime` DATETIME NOT NULL , `symbol` VARCHAR(50) NOT NULL , `open` DECIMAL(40,8) NOT NULL , `high` DECIMAL(40,8) NOT NULL , `low` DECIMAL(40,8) NOT NULL , `close` DECIMAL(40,8) NOT NULL , `ema12` DECIMAL(40,8) NULL , `ema26` DECIMAL(40,8) NULL , `macd` DECIMAL(40,8) NULL , `sig9` DECIMAL(40,8) NULL , `diff` DECIMAL(40,8) NULL ) ENGINE = InnoDB;"
	cur.execute(query)
	print("Tabla de 4h creada")
	query = f"CREATE TABLE IF NOT EXISTS `data_1d` ( `openTime` DATETIME NOT NULL , `symbol` VARCHAR(50) NOT NULL , `open` DECIMAL(40,8) NOT NULL , `high` DECIMAL(40,8) NOT NULL , `low` DECIMAL(40,8) NOT NULL , `close` DECIMAL(40,8) NOT NULL , `ema12` DECIMAL(40,8) NULL , `ema26` DECIMAL(40,8) NULL , `macd` DECIMAL(40,8) NULL , `sig9` DECIMAL(40,8) NULL , `diff` DECIMAL(40,8) NULL ) ENGINE = InnoDB;"
	cur.execute(query)
	print("Tabla de 1d creada")

if __name__== "__main__":
	createUserTable()
	createSymbolTable()
	createDataTables()
	conn.close()