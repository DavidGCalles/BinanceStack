<# STAGING Y PRODUCCION son el mismo entorno, PERO staging no efectua los trades. Hasta que prod sea viable, staging sera el mas estable. #>
docker compose -f prod.yml -p sta down
Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\sta_dbData
Copy-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\code_dbData\ \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\sta_dbData -force
docker compose -f prod.yml -p sta up -d --build