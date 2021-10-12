Remove-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\devenv_dbDataDEV
Copy-Item -r \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\code_dbData\ \\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes\devenv_dbDataDEV -force
docker compose -f dev.yml -p devENV up -d --build