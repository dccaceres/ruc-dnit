# Guía de Despliegue en Producción

Este documento detalla los pasos para desplegar la API de Consulta de RUC en un entorno de producción utilizando Docker.

## Prerrequisitos

- Docker instalado
- Docker Compose instalado
- Acceso a internet (para descargar la imagen base de Python y los datos de la DNIT)

## Estructura de Contenedores

El despliegue utiliza dos servicios definidos en `docker-compose.yml`:

1.  **api**: Servidor web FastAPI corriendo con Gunicorn + Uvicorn workers.
    -   Puerto: 8000
    -   Volumen: `./data` (persistencia de la base de datos SQLite)
    -   Reinicio automático (`restart: unless-stopped`)

2.  **downloader**: Servicio "batch" que descarga y actualiza los datos.
    -   Ejecuta el script de descarga una vez y termina.
    -   Comparte el volumen `./data` con la API.

## Pasos para el Despliegue

### 1. Preparación

Asegúrate de tener el código fuente en el servidor:

```bash
git clone <repositorio>
cd ruc-dnit
```

### 2. Configuración (Opcional)

Si necesitas cambiar la URL de descarga u otros parámetros, puedes editar el archivo `.env` o modificar las variables de entorno en `docker-compose.yml`.

### 3. Ejecución Inicial (Descarga de Datos)

Antes de iniciar la API, es recomendable descargar y procesar los datos para generar la base de datos SQLite.

```bash
docker-compose run --rm downloader
```

Este comando descargará los ZIPs, procesará los TXT y generará `data/ruc.sqlite`.
*Nota: Este proceso puede tardar varios minutos dependiendo de la velocidad de descarga y procesamiento.*

### 4. Iniciar la API

Una vez generada la base de datos, inicia el servicio de la API en segundo plano:

```bash
docker-compose up -d api --build
```

La API estará disponible en `http://localhost:8000`.

### 5. Verificación

Puedes verificar que la API está funcionando correctamente:

```bash
curl http://localhost:8000/health
```

O revisando los logs:

```bash
docker-compose logs -f api
```

## Actualización de Datos

Para actualizar los datos periódicamente (por ejemplo, diariamente o semanalmente), puedes configurar un **cron job** en el servidor host que ejecute el downloader:

```bash
# Ejemplo: Actualizar todos los días a las 3:00 AM
0 3 * * * cd /ruta/al/proyecto && /usr/local/bin/docker-compose run --rm downloader
```

Como ambos servicios comparten el volumen `./data`, la API verá los cambios automáticamente en la siguiente consulta (o se puede reiniciar la API si se prefiere forzar reconexión, aunque SQLite maneja esto bien).

## Notas de Seguridad

-   El `Dockerfile` crea un usuario no privilegiado (`appuser`) para ejecutar la aplicación.
-   En un entorno expuesto a internet, se recomienda utilizar un proxy inverso (como Nginx, Caddy o Traefik) delante del contenedor de la API para manejar HTTPS/SSL.
