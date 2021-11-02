# Proceso de desarrollo
1. Nueva rama.
2. Desarrollo.
	- Realizar los cambios previstos.
3. 1º Fase: deploy-dev.ps1
	- Este entorno contiene una copia de la infraestructura basica y ejecuta solo el servicio en desarrollo para aislar sus errores y comportamiento mas facilmente.
4. 2º Fase: deploy-staging.ps1
	- Este entorno es el más similar a producción. Básicamente es una copia paralela con el servicio nuevo integrado. Esto hará que el push a produccion no sea peligroso.
5. Despliegue:
	- Pull Request a Github
	- Push a DockerHub
	- Reiniciar Produccion

## De estas pautas se desprenden
- Producción apunta a una imagen fija de dockerhub.
- Dev y Staging son imagenes que se construyen en local.
- No se hace push ni pull request hasta que staging demuestre estabilidad en un servicio COMPLETO.