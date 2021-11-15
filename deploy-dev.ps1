docker compose -f dev.yml -p dev down
docker compose -f sta.yml -p sta down
Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData
Copy-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\code_dbData\ \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\dev_dbData -force
docker compose -f dev.yml -p dev up -d --build