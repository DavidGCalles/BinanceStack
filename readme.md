# EL PROYECTO ESTÁ OFICIALMENTE INUTILIZADO HASTA QUE TERMINE EL REWORK

# Binance Stack
Este repositorio aspira a proporcionar una plataforma flexible de trading algorítmico, completamente extensible y open source, como base de
experimentos para los desarrolladores, como uso para backtesting o como trabajador para modelados mas exigentes de ML.

Está basado en las librerías python-binance (para hacer interfaz con la API de esta) y python-ta, un subconjunto de pandas orientado al analisis tecnico de stocks. La interfaz (aun no disponible) se ejecutará en Django, por lo que podemos decir que esto es un proyecto completo de Python.

Para esto, se ha decidido crear un sistema distribuido de microservicios usando Docker. 

Es un proyecto grande, compuesto de muchas partes móviles. En su estado actual, esta completamente contra recomendado su uso en cualquier entorno
similar a producción por varias razones. La primera de ellas, el almacenamiento de datos sensibles como las claves de API es completa, absolutamente
inseguro. En segundo, aun faltan mecanismos de comprobación y seguridad en cada paso del proceso, por lo que si se activan los trades reales, el programa
podría hacer compras y ventas erroneas, o simplemente comprar y crashear, dejando el trade desatendido.

Dicho esto, si sigues queriendo desplegar una instancia, debajo tienes las instrucciones.

# Configuracion inicial
Binance Stack esta distribuido en diversas capas de funcionamiento. Esto se refleja estructuralmente en la manera de desplegarlo. El primer uso del stack se beneficia de la distribución elegida en el siguiente proceso.

```docker compose -f servers.yml -p dev up -d```

Esto levantará la base de datos central y adminer, con el cual se podrán ejecutar diversas acciones si no se es muy ducho en CLI y SQL. Tras esto, accederemos a [adminer](http://localhost:8070) y nos encontraremos con una pantalla asi:

![Adminer Login Screen](/imgs/adminerLogin.PNG)

Podremos acceder al servidor con las credenciales escritas en la imagen, contraseña "binance", si no hemos modificado nada referente a la configuración de mariadb. Esto nos llevará a la pantalla de administración, donde tendremos que localizar la tabla "users" y añadir un nuevo elemento.

Nuestro usuario y claves de API de binance. Cuidado, no puedo decirlo las suficientes veces. Esto, por el momento, no esta diseñado para ser seguro ni para ser multiusuario, aunque esté dentro del roadmap. Las claves se van a almacenar en texto plano en la base de datos. CUIDADO.

Añadido nuestro usuario, debemos modificar workers.yml y algos.yml con nuestro usuario, para que acceda a las claves correctas de la base de datos.

Tras esta modificacion, podemos lanzar todo el stack en el siguiente orden.

## Secuencia de encendido
- ```docker compose -f visualization.yml -p dev up -d```
- ```docker compose -f prometheus-net.yml -p dev up -d```
- ```docker compose -f elk-net.yml -p dev up -d```
- ```docker compose -f workers.yml -p dev up -d```
- ```docker compose -f algos.yml -p dev up -d```

### Notas
- Los stacks prometheus y elk, no soy explicitamente necesarios para el funcionamiento del sistema. Sin embargo, son herramientas de monitorización invaluables. Aunque un usuario puede prescindir, hasta cierto punto, de estas características, un desarrollador o alguien interesado en el funcionamiento de este sistema va a necesitar desplegar ambos stacks.
- Es recomendable dejar a los workers trabajar durante un tiempo. Esto les permitirá actualizar la base de datos y obtener todos los puntos necesarios para que los algoritmos comiencen a funcionar correctamente. Sobre todo al principio, el sistema debe solicitar mucha información a Binance.

# Organizacion del sistema

![Diagrama de servicios](/imgs/generalStructure.svg "Diagrama de servicios").