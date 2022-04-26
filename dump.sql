CREATE TABLE IF NOT EXISTS `binance`.`users` (
  `name` VARCHAR(255) NOT NULL ,
  `key` VARCHAR(255) NOT NULL ,
  `secret` VARCHAR(255) NOT NULL ,
  `mail` VARCHAR(255) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `symbols` (
  `symbol` VARCHAR(50) PRIMARY KEY NOT NULL ,
  `minNotional` DECIMAL(40,8) NOT NULL DEFAULT '0' ,
  `minQty` DECIMAL(40,8) NOT NULL DEFAULT '0' ,
  `stepSize` DECIMAL(40,8) NOT NULL DEFAULT '0' ,
  `precisionAsset` INT(2) NOT NULL DEFAULT '0' ,
  `acierto` INT(5) NOT NULL DEFAULT '0' ,
  `total` INT(5) NOT NULL DEFAULT '0' ,
  `percent` INT(3) NOT NULL DEFAULT '0' ,
  `1S` BOOLEAN NULL DEFAULT NULL ,
  `1M` BOOLEAN NULL DEFAULT NULL ,
  `dbMiner` DATETIME NULL DEFAULT NULL ,
  `dbCalculator` DATETIME NULL DEFAULT NULL,
  `MACDentry` DATETIME NULL DEFAULT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `backtest_data_4h` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `backtest_data_1d` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `backtest_data_5m` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `data_4h` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `data_1d` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `data_5m` (
  `openTime` DATETIME NOT NULL ,
  `symbol` VARCHAR(50) NOT NULL ,
  `open` DECIMAL(40,8) NOT NULL ,
  `high` DECIMAL(40,8) NOT NULL ,
  `low` DECIMAL(40,8) NOT NULL ,
  `close` DECIMAL(40,8) NOT NULL ) ENGINE = InnoDB;
CREATE TABLE IF NOT EXISTS `trading` (
  `openTime` datetime NOT NULL,
  `symbol` varchar(50) NOT NULL,
  `entryStra` varchar(50) NOT NULL,
  `exitStra` varchar(50) NOT NULL,
  `qty` decimal(40,8) NOT NULL,
  `price` decimal(40,8) NOT NULL,
  `baseQty` decimal(40,8) NOT NULL,
  `softLimit` decimal(40,8) NULL DEFAULT NULL,
  `softStop` decimal(40,8) NULL DEFAULT NULL,
  `lastCheck` datetime NULL DEFAULT NULL) ENGINE='InnoDB';
CREATE TABLE IF NOT EXISTS `traded` (
  `openTime` datetime NOT NULL,
  `symbol` varchar(50) NOT NULL,
  `entryStra` varchar(50) NOT NULL,
  `exitStra` varchar(50) NOT NULL,
  `qty` decimal(40,8) NOT NULL,
  `price` decimal(40,8) NOT NULL,
  `baseQty` decimal(40,8) NOT NULL,
  `closeTime` datetime NOT NULL,
  `sellPrice` decimal(40,8) NOT NULL,
  `baseProfit` decimal(40,8) NOT NULL) ENGINE='InnoDB';
CREATE TABLE IF NOT EXISTS `config` (
  `user` varchar(50) NOT NULL,
  `keyName` VARCHAR(50) NOT NULL,
  `value` VARCHAR(50) NOT NULL) ENGINE = 'InnoDB';