docker compose -f dev.yml -p dev down
#Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData
#Copy-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\code_dbData\ \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData -force
Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_code\_data\code\
Copy-Item -r C:\Users\David\GitHub\BinanceProject\code \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_code\_data
docker compose -f dev.yml -p dev up -d
#docker compose -f dev.yml -p dev up -d --scale tslexit=10