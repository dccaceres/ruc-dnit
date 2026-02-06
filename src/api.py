"""API REST para consultas de RUC en base de datos SQLite."""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn
import sqlite3
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Consulta de RUC",
    description="API REST para consultar RUC en base de datos SQLite",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@contextmanager
def get_db_connection():
    """Context manager para conexiones a la base de datos SQLite."""
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Base de datos no encontrada: {db_path}")
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Error de base de datos: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_db_path() -> Path:
    """Retorna la ruta de la base de datos SQLite."""
    db_path = os.getenv("DB_PATH", "")
    if db_path:
        return Path(db_path)
    return Path(__file__).parent.parent / "data" / "ruc.sqlite"


def search_ruc(ruc: str) -> Optional[dict]:
    """
    Busca un RUC exacto en la base de datos.

    Args:
        ruc: RUC a buscar (sin DV)

    Returns:
        Diccionario con los datos si se encuentra, None si no
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT ruc, razon_social, dv, estado FROM ruc WHERE ruc = ? LIMIT 1",
                (ruc,),
            )
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None
    except FileNotFoundError:
        logger.error("Base de datos no encontrada")
        return None
    except Exception as e:
        logger.error(f"Error al buscar RUC: {e}")
        return None


def search_razon_social(query: str) -> list:
    """
    Busca por razón social usando LIKE.

    Args:
        query: Texto a buscar en razón social

    Returns:
        Lista de diccionarios con los resultados
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            search_pattern = f"%{query}%"
            cursor.execute(
                "SELECT ruc, razon_social, dv, estado FROM ruc WHERE razon_social LIKE ? LIMIT 100",
                (search_pattern,),
            )
            rows = cursor.fetchall()

            return [dict(row) for row in rows]
    except FileNotFoundError:
        logger.error("Base de datos no encontrada")
        return []
    except Exception as e:
        logger.error(f"Error al buscar razón social: {e}")
        return []


def is_valid_ruc_format(ruc: str) -> bool:
    """
    Valida el formato de un número de RUC.
    
    Args:
        ruc: RUC a validar
        
    Returns:
        True si el formato es válido, False en caso contrario
    """
    # El RUC debe contener solo dígitos y tener una longitud razonable
    return ruc.isdigit() and 1 <= len(ruc) <= 10


def format_response(row: dict) -> dict:
    """
    Formatea la respuesta concatenando RUC con DV.

    Args:
        row: Diccionario con los datos de la fila

    Returns:
        Diccionario formateado
    """
    dv = row.get("dv", "").strip()
    if dv:
        ruc_formatted = f"{row['ruc']}-{dv}"
    else:
        ruc_formatted = row["ruc"]

    return {
        "ruc": ruc_formatted,
        "razon_social": row.get("razon_social", "").strip(),
        "estado": row.get("estado", "").strip(),
    }


@app.get("/", 
         summary="Información de la API",
         description="Endpoint raíz que proporciona información general sobre la API de consulta de RUC.")
def root():
    """Endpoint raíz con información de la API."""
    return {
        "api": "API de Consulta de RUC",
        "version": "1.0.0",
        "description": "API REST para consultar RUC en base de datos SQLite",
        "endpoints": {
            "/ruc/{ruc}": "Buscar por RUC exacto",
            "/buscar": "Buscar por RUC o razón social (parámetro 'query')",
            "/health": "Verificar el estado de la API y la base de datos",
        },
    }


@app.get("/ruc/{ruc}", 
         summary="Buscar por RUC exacto",
         description="Busca un número de RUC exacto en la base de datos y devuelve sus detalles.")
def get_by_ruc(ruc: str):
    """
    Busca un RUC exacto en la base de datos.

    Args:
        ruc: RUC a buscar (ej: 3634374)

    Returns:
        JSON con los datos del RUC o 404 si no existe
    """
    # Validar formato del RUC
    if not is_valid_ruc_format(ruc):
        raise HTTPException(status_code=400, detail=f"Formato de RUC inválido: {ruc}. El RUC debe contener solo dígitos.")
    
    result = search_ruc(ruc)

    if not result:
        raise HTTPException(status_code=404, detail=f"RUC {ruc} no encontrado")

    return format_response(result)


@app.get("/buscar",
         summary="Buscar por RUC o razón social",
         description="Busca por número de RUC exacto o por razón social. Si la consulta es numérica, primero busca como RUC exacto, luego por coincidencias en razón social.")
def search(
    query: str = Query(..., description="RUC o razón social a buscar", min_length=1),
    limit: int = Query(10, description="Cantidad máxima de resultados", ge=1, le=100),
):
    """
    Busca por RUC o razón social.

    Args:
        query: RUC o texto de razón social
        limit: Máximo de resultados a retornar (default: 10, max: 100)

    Returns:
        JSON con los resultados encontrados
    """
    # Si la consulta parece ser un RUC (solo dígitos), validar su formato
    if query.isdigit():
        if not is_valid_ruc_format(query):
            raise HTTPException(status_code=400, detail=f"Formato de RUC inválido: {query}. El RUC debe contener solo dígitos.")
    
    # Intentar buscar como RUC exacto primero
    result = search_ruc(query)

    if result:
        return format_response(result)

    # Si no es RUC exacto, buscar por razón social
    results = search_razon_social(query)

    if not results:
        raise HTTPException(
            status_code=404, detail=f"No se encontraron resultados para '{query}'"
        )

    # Aplicar límite y formatear resultados
    formatted_results = [format_response(row) for row in results[:limit]]

    return {"resultados": formatted_results, "total": len(formatted_results)}


@app.get("/health",
         summary="Verificar estado de la API",
         description="Endpoint para verificar el estado de la API y la conexión a la base de datos.")
def health_check():
    """Endpoint para verificar el estado de la API y la base de datos."""
    db_path = get_db_path()
    db_exists = db_path.exists()

    return {
        "status": "healthy" if db_exists else "warning",
        "database": "connected" if db_exists else "not found",
        "database_path": str(db_path),
    }


def run_server():
    """
    Ejecuta el servidor FastAPI.
    Lee la configuración de variables de entorno o valores por defecto.
    """
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
