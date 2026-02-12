# DNIT RUC Zip Downloader + API RUC

Descarga y descomprime automáticamente archivos `.zip` desde la página web configurable (DNIT) y proporciona una API REST para consultar RUCs.

## 🚀 Características

- 🔍 Busca enlaces a archivos `.zip` en la página web
- ⬇️ Descarga múltiples archivos automáticamente
- 📦 Descomprime y unifica archivos `.txt` en CSV
- 🔧 Validación automática de CSV con eliminación de errores
- 🗃️ Crea base de datos SQLite con los datos
- 🌐 API REST para consulta de RUCs
- 📊 Búsqueda por RUC exacto o razón social

## 📦 Instalación

```bash
# Clonar o copiar el proyecto
cd ruc-dnit

# Instalar dependencias
pip install -r requirements.txt
```

## 🎯 Uso

### 1. Descargar y Procesar Datos

#### Opción 1: Línea de comandos (CLI)

```bash
# Básico
python -m src.main https://example.com

# Con directorio de salida personalizado
python -m src.main https://example.com -o ./mis_archivos

# Sin sobrescribir archivos existentes
python -m src.main https://example.com --no-overwrite
```

#### Opción 2: Archivo de configuración

1. Edita `config.ini`:
```ini
[DEFAULT]
url = https://example.com
output_dir = ./downloads
overwrite = true
```

2. Ejecuta:
```bash
python -m src.main
```

#### Opción 3: Variables de entorno

1. Crea un archivo `.env`:
```bash
cp .env.example .env
```

2. Edita `.env`:
```env
ZIP_DOWNLOAD_URL=https://example.com
ZIP_OUTPUT_DIR=./downloads
```

3. Ejecuta:
```bash
python -m src.main --env
```

### 2. API REST para Consulta de RUC

#### Iniciar el servidor

```bash
# Usando el script instalado
ruc-api

# O directamente con Python
python -m src.api
```

Por defecto, la API corre en `http://localhost:8000`

#### Endpoints

##### `GET /`
Información de la API

```bash
curl http://localhost:8000/
```

##### `GET /ruc/{ruc}`
Busca un RUC exacto

```bash
curl http://localhost:8000/ruc/3634374
```

**Respuesta**:
```json
{
  "ruc": "1234567-8",
  "razon_social": "JUAN PEREZ",
  "estado": "ACTIVO"
}
```

##### `GET /buscar?query={texto}`
Busca por RUC o razón social

```bash
# Buscar por parte de la razón social
curl "http://localhost:8000/buscar?query=JUAN"

# Buscar por RUC
curl "http://localhost:8000/buscar?query=1234567"

# Limitar resultados
curl "http://localhost:8000/buscar?query=JUAN&limit=5"
```

**Respuesta**:
```json
{
  "resultados": [
    {
      "ruc": "1234567-8",
      "razon_social": "JUAN PEREZ",
      "estado": "ACTIVO"
    }
  ],
  "total": 1
}
```

##### `GET /health`
Verifica el estado de la API y la base de datos

```bash
curl http://localhost:8000/health
```

**Respuesta**:
```json
{
  "status": "healthy",
  "database": "connected",
  "database_path": "C:\\dev\\python\\ruc-dnit\\data\\ruc.sqlite"
}
```

#### Característica: Determinación de Tipo de Persona

La API incluye una funcionalidad para determinar si un RUC corresponde a persona física o jurídica:

- **Persona Jurídica**: RUCs que empiezan con "800", "801", "802" y tienen mayor o igual a 8 dígitos
- **Persona Física**: RUCs que NO empiezan con "800", "801", "802" y tienen entre 6-8 dígitos
- **Desconocido**: Formatos no válidos o que no cumplen los criterios
**Obs.: Si se puede mejorar la logica bienvenido sea un PR**

Esta información se incluye automáticamente en todas las respuestas de la API.

#### Documentación Interactiva

La API incluye documentación automática de Swagger/OpenAPI:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🐳 Despliegue en Producción

Para desplegar la aplicación en un entorno de producción utilizando Docker, consulta la guía detallada en [DEPLOY.md](./DEPLOY.md).

## 📋 Proceso de Validación

El proceso de validación del CSV incluye:

1. **Detección de líneas con errores** (columnas incorrectas)
2. **Creación de archivo `error.csv`** con las líneas problemáticas
3. **Eliminación automática** de líneas con "CANCELADO" y columnas incorrectas
4. **Generación de archivo limpio** para SQLite

**Archivo de errores** (`data/error.csv`):
- `numero_linea`: posición original de la línea
- `contenido_linea`: contenido de la línea eliminada
- `motivo_error`: descripción del problema

## 📝 Registros y Diagnóstico

El sistema genera archivos de log detallados para diagnóstico y seguimiento:

- **Ubicación**: `logs/zip_downloader_YYYYMMDD_HHMMSS.log`
- **Formato**: `timestamp - nombre - nivel - mensaje`
- **Niveles**: DEBUG, INFO, WARNING, ERROR

**Ejemplo de contenido de log**:
```
2026-02-12 11:13:48,894 - downloader - INFO - ZipDownloader inicializado con output_dir=./downloads
2026-02-12 11:13:48,894 - downloader - INFO - Encontrados 2 archivos ZIP en https://example.com
2026-02-12 11:13:48,898 - downloader - INFO - Descargando: archivo1.zip
2026-02-12 11:13:48,901 - downloader - INFO - Descarga completada: archivo1.zip (123.45 KB)
```

**Configuración de logging** (opcional):
```python
from downloader import ZipDownloader
import logging

downloader = ZipDownloader(
    log_dir="./mis_logs",      # Directorio personalizado
    log_level=logging.DEBUG    # Nivel detallado
)
```

**Niveles disponibles**:
- `logging.DEBUG`: Información detallada (desarrollo)
- `logging.INFO`: Operaciones normales (recomendado)
- `logging.WARNING`: Solo advertencias y errores
- `logging.ERROR`: Solo errores críticos

## 📂 Estructura del proyecto

```
zip-downloader/
├── logs/                # Archivos de log con timestamp
│   ├── zip_downloader_YYYYMMDD_HHMMSS.log
│   └── ...
├── src/
│   ├── __init__.py
│   ├── downloader.py    # Lógica de descarga/descompresión/unificación
│   ├── api.py           # API REST FastAPI
│   └── main.py          # Interfaz CLI
├── data/
│   ├── ruc.csv          # CSV unificado y validado
│   ├── ruc.sqlite       # Base de datos SQLite
│   └── error.csv        # Líneas eliminadas por errores
├── config.ini           # Configuración por archivo
├── api.ini              # Configuración de la API
├── .env.example         # Plantilla variables de entorno
├── requirements.txt     # Dependencias
├── pyproject.toml       # Metadata del proyecto
└── README.md
```

## 🔧 Dependencias

- `requests>=2.31.0` - Descarga de archivos
- `beautifulsoup4>=4.12.0` - Parsing HTML
- `python-dotenv>=1.0.0` - Variables de entorno
- `fastapi>=0.109.0` - API REST
- `uvicorn>=0.27.0` - Servidor ASGI

## ⚠️ Notas

- Los archivos `.zip` se eliminan después de descomprimirse
- La base de datos SQLite se sobrescribe en cada ejecución
- El RUC se retorna concatenado con el dígito verificador: `{ruc}-{dv}`
- La API soporta hasta 100 resultados por búsqueda

## 👤 Autor

- **Daniel Cáceres**
- Correo: dccaceres@gmail.com

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**.

