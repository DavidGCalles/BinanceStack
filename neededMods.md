# Modificaciones necesarias en DB para implementar MACDentry
- Crear tablas:
	- Trading: Tabla de trades ACTIVOS
	- Traded: Tabla de trades FINALIZADOS
## Estructura de trading
- id
- openTime
- symbol
- entry
- exit
- qty
- price
- baseQty

## Estructura de traded
- id(heredado de trading)
- closeTime
- sellPrice
- baseProfit

# Funcionamiento
Para optimizar las consultas y el almacenamiento, las tablas van a estar relacionadas por el numero de id, pudiendo obtener los datos relacionados entre apertura y cierre del trade facilmente.

## Mas cosas
Se están planeando modificaciones grandes en la rama troncal que tendrán que ver con las configuraciones, los timers y el funcionamiento de los servicios. Pero por el momento, este es el menor bloque de funcionalidad antes de pasar a esa reestructuracion. Habilitar este servicio.