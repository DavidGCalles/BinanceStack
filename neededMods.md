# Modificaciones necesarias en DB para implementar MACDentry
- Crear tablas:
	- Trading: Tabla de trades ACTIVOS
	- Traded: Tabla de trades FINALIZADOS
## Estructura de trading
- openTime
- symbol
- entry
- exit
- qty
- price
- baseQty

## Estructura de traded
- tabla trading completa
- closeTime
- sellPrice
- baseProfit

# Funcionamiento
Se decide usar un formato completo en traded. Los datos en trading son transitorios y almacenar en esa tabla trades terminados solo va a llevar a problemas.

## Mas cosas
Se están planeando modificaciones grandes en la rama troncal que tendrán que ver con las configuraciones, los timers y el funcionamiento de los servicios. Pero por el momento, este es el menor bloque de funcionalidad antes de pasar a esa reestructuracion. Habilitar este servicio.