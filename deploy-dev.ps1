#Esta instrucción apaga todo el stack. Puede ser comentada para despliegue rapido en según que situaciones.
docker compose -f dev.yml -p dev down

#Replica el volumen de la base de datos.
#Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData
#Copy-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\code_dbData\ \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData -force

#Replica el repositorio actual en el volumen usado en desarrollo.
Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_code\_data\code\
Copy-Item -r C:\Users\David\GitHub\BinanceProject\code \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_code\_data

#Despliegue simple/despliegue con escalado estandar
#docker compose -f dev.yml -p dev up -d
docker compose -f dev.yml -p dev up -d --scale tslexit=10