# Zip Downloader + API RUC

Descarga y descomprime automáticamente archivos `.zip` desde una página web y proporciona una API REST para consultar RUCs.

## 🚀 Características

- 🔍 Busca enlaces a archivos `.zip` en cualquier página web
- ⬇️ Descarga múltiples archivos automáticamente
- 📦 Descomprime y unifica archivos `.txt` en CSV
- 🗃️ Crea base de datos SQLite con los datos
- 🔧 Validación automática de CSV con eliminación de errores
- 🌐 API REST para consulta de RUCs
- 📊 Búsqueda por RUC exacto o razón social

## 📦 Instalación

```bash
# Clonar o copiar el proyecto
cd zip-downloader

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
  "ruc": "3634374-9",
  "razon_social": "DANIEL CACERES",
  "estado": "ACTIVO"
}
```

##### `GET /buscar?query={texto}`
Busca por RUC o razón social

```bash
# Buscar por parte de la razón social
curl "http://localhost:8000/buscar?query=DANIEL"

# Buscar por RUC
curl "http://localhost:8000/buscar?query=3634374"

# Limitar resultados
curl "http://localhost:8000/buscar?query=DANIEL&limit=5"
```

**Respuesta**:
```json
{
  "resultados": [
    {
      "ruc": "3634374-9",
      "razon_social": "DANIEL CACERES",
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

#### Documentación Interactiva

La API incluye documentación automática de Swagger/OpenAPI:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

## 📂 Estructura del proyecto

```
zip-downloader/
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
