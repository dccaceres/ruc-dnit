# Zip Downloader + API RUC - Project Overview

## Project Description
This is a Python project that downloads and decompresses `.zip` files from a webpage (specifically DNIT - Dirección Nacional de Identificación Tributaria in Paraguay) and provides a REST API to query RUC (Registro Único de Contribuyentes) numbers. The project consists of two main components:
1. A downloader that scrapes ZIP files from a webpage, extracts them, and processes the contained TXT files into a unified CSV and SQLite database
2. A FastAPI-based REST API for querying RUC information

## Architecture & Components
- **Main Module** (`src/main.py`): CLI entry point that handles arguments, configuration loading, and orchestrates the download process
- **Downloader** (`src/downloader.py`): Core functionality for scraping ZIP files, downloading, extracting, and processing TXT files into CSV and SQLite
- **API** (`src/api.py`): FastAPI implementation for RUC queries with endpoints for exact RUC lookup and fuzzy search
- **Configuration**: Supports INI files, environment variables, and CLI arguments
- **Data Processing**: Converts pipe-delimited TXT files to validated CSV and SQLite database

## Key Features
- Web scraping for ZIP file links on a target page
- Automated download and extraction of ZIP files
- Unification of multiple TXT files into a single validated CSV
- Automatic SQLite database creation with RUC data
- Error validation and logging of problematic records
- REST API with endpoints for RUC lookup and search
- Support for multiple configuration methods (INI, env vars, CLI args)

## Dependencies
- `requests>=2.31.0` - Web requests and downloads
- `beautifulsoup4>=4.12.0` - HTML parsing for link extraction
- `python-dotenv>=1.0.0` - Environment variable management
- `fastapi>=0.109.0` - Web framework for the REST API
- `uvicorn>=0.27.0` - ASGI server for running the API

## Building and Running

### Setup
```bash
pip install -r requirements.txt
```

### Download and Process Data
```bash
# Basic usage
python -m src.main https://example.com

# With custom output directory
python -m src.main https://example.com -o ./my_files

# Using config file (defaults to config.ini)
python -m src.main

# Using environment variables
python -m src.main --env
```

### Run the API Server
```bash
# Using the installed script
ruc-api

# Or directly with Python
python -m src.api
```

The API runs by default on `http://localhost:8000` and provides:
- `/` - API info
- `/ruc/{ruc}` - Exact RUC lookup
- `/buscar?query={text}` - Search by RUC or business name
- `/health` - Health check endpoint
- `/docs` - Interactive API documentation (Swagger UI)
- `/redoc` - Alternative API documentation (ReDoc)

### Configuration Options
The project supports three configuration methods (in order of precedence):
1. Command-line arguments
2. Environment variables (when using `--env`)
3. INI configuration file

Configuration files:
- `config.ini` - Main configuration with URL, output directory, and overwrite settings
- `api.ini` - API server configuration (host, port)
- `.env` - Environment variables (copy from `.env.example`)

## Development Conventions
- The project follows standard Python conventions
- Configuration is flexible and supports multiple methods
- Error handling is implemented throughout the download and processing pipeline
- Data validation occurs during CSV creation with error logging
- SQLite database is recreated on each run (overwritten)
- ZIP files are deleted after extraction to save space

## Project Structure
```
zip-downloader/
├── src/
│   ├── __init__.py
│   ├── downloader.py    # Core download/extract/unify logic
│   ├── api.py           # FastAPI REST API implementation
│   └── main.py          # CLI interface
├── data/
│   ├── ruc.csv          # Unified and validated CSV file
│   ├── ruc.sqlite       # SQLite database with RUC data
│   └── error.csv        # Log of invalid records removed during validation
├── downloads/           # Directory for downloaded ZIP files and extracted content
├── config.ini           # Default configuration file
├── api.ini              # API server configuration
├── .env.example         # Template for environment variables
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project metadata and scripts
└── README.md
```

## Data Processing Flow
1. Scrape webpage for ZIP file links
2. Download each ZIP file
3. Extract ZIP contents to individual directories
4. Process all TXT files in extracted directories
5. Unify TXT content into a single pipe-delimited CSV
6. Validate CSV format and remove problematic records
7. Create SQLite database from validated CSV
8. Log any removed records to error.csv

## API Endpoints
- `GET /` - API information
- `GET /ruc/{ruc}` - Exact RUC lookup (returns formatted RUC with verification digit)
- `GET /buscar?query={text}[&limit=N]` - Search by RUC or business name (with optional limit)
- `GET /health` - Health check for API and database connection
- `GET /docs` - Interactive API documentation
- `GET /redoc` - Alternative API documentation

## Author & License
- Author: Daniel Cáceres
- Email: dccaceres@gmail.com
- License: MIT

## AGENTS
- Answer always in Spanish