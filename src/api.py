"""API REST para consultas de RUC en base de datos SQLite."""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn
import sqlite3


app = FastAPI(
    title="API de Consulta de RUC",
    description="API REST para consultar RUC en base de datos SQLite",
    version="1.0.0",
)


def get_db_path() -> Path:
    """Retorna la ruta de la base de datos SQLite."""
    return Path(__file__).parent.parent / "data" / "ruc.sqlite"


def search_ruc(ruc: str) -> Optional[dict]:
    """
    Busca un RUC exacto en la base de datos.

    Args:
        ruc: RUC a buscar (sin DV)

    Returns:
        Diccionario con los datos si se encuentra, None si no
    """
    db_path = get_db_path()
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT ruc, razon_social, dv, estado FROM ruc WHERE ruc = ? LIMIT 1",
            (ruc,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None
    except Exception:
        return None


def search_razon_social(query: str) -> list:
    """
    Busca por razón social usando LIKE.

    Args:
        query: Texto a buscar en razón social

    Returns:
        Lista de diccionarios con los resultados
    """
    db_path = get_db_path()
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        search_pattern = f"%{query}%"
        cursor.execute(
            "SELECT ruc, razon_social, dv, estado FROM ruc WHERE razon_social LIKE ? LIMIT 100",
            (search_pattern,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
    except Exception:
        return []


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


@app.get("/")
def root():
    """Endpoint raíz con información de la API."""
    return {
        "api": "API de Consulta de RUC",
        "version": "1.0.0",
        "endpoints": {
            "/ruc/{ruc}": "Buscar por RUC exacto",
            "/buscar": "Buscar por RUC o razón social (parámetro 'query')",
        },
    }


@app.get("/ruc/{ruc}")
def get_by_ruc(ruc: str):
    """
    Busca un RUC exacto en la base de datos.

    Args:
        ruc: RUC a buscar (ej: 3634374)

    Returns:
        JSON con los datos del RUC o 404 si no existe
    """
    result = search_ruc(ruc)

    if not result:
        raise HTTPException(status_code=404, detail=f"RUC {ruc} no encontrado")

    return format_response(result)


@app.get("/buscar")
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


@app.get("/health")
def health_check():
    """Endpoint para verificar el estado de la API y la base de datos."""
    db_path = get_db_path()
    db_exists = db_path.exists()

    return {
        "status": "healthy" if db_exists else "warning",
        "database": "connected" if db_exists else "not found",
        "database_path": str(db_path),
    }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Ejecuta el servidor FastAPI.

    Args:
        host: Host donde escuchar (default: 0.0.0.0)
        port: Puerto donde escuchar (default: 8000)
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
