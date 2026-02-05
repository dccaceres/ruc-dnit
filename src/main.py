"""Interfaz de línea de comandos para ZipDownloader."""

import argparse
import configparser
from pathlib import Path

from dotenv import load_dotenv

from .downloader import ZipDownloader


def load_config(config_file: str = "config.ini") -> configparser.ConfigParser:
    """Carga configuración desde archivo .ini."""
    config = configparser.ConfigParser()
    config_path = Path(config_file)

    if config_path.exists():
        config.read(config_path)
        return config
    return None


def cli():
    """Punto de entrada CLI para zip-downloader."""
    parser = argparse.ArgumentParser(
        description="Descarga y descomprime archivos .zip desde una página web"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="URL de la página a procesar (opcional si se usa --config)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./downloads",
        help="Directorio de salida (default: ./downloads)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="No sobrescribir archivos existentes",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.ini",
        help="Archivo de configuración (default: config.ini)",
    )
    parser.add_argument(
        "--env", action="store_true", help="Usar variables de entorno desde .env"
    )

    args = parser.parse_args()

    # Cargar variables de entorno si se solicita
    if args.env:
        load_dotenv()
        url = args.url or os.getenv("ZIP_DOWNLOAD_URL")
        output_dir = args.output or os.getenv("ZIP_OUTPUT_DIR", "./downloads")
        overwrite = not args.no_overwrite
    else:
        # Cargar configuración desde archivo
        config = load_config(args.config)
        if config and "DEFAULT" in config:
            url = args.url or config.get("DEFAULT", "url", fallback=None)
            output_dir = args.output or config.get(
                "DEFAULT", "output_dir", fallback="./downloads"
            )
            overwrite_str = config.get("DEFAULT", "overwrite", fallback="true")
            overwrite = overwrite_str.lower() == "true" and not args.no_overwrite
        else:
            url = args.url
            output_dir = args.output
            overwrite = not args.no_overwrite

    if not url:
        parser.error(
            "Se requiere una URL. Proporciona:\n"
            "  - Como argumento: python -m src.main https://example.com\n"
            "  - En config.ini: url = https://example.com\n"
            "  - En .env: ZIP_DOWNLOAD_URL=https://example.com (con --env)"
        )

    # Crear descargador y procesar
    downloader = ZipDownloader(output_dir=output_dir, overwrite=overwrite)
    stats = downloader.process_url(url)

    # Mostrar resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN")
    print("=" * 50)
    print(f"Archivos encontrados:  {stats['found']}")
    print(f"Archivos descargados:  {stats['downloaded']}")
    print(f"Archivos extraídos:    {stats['extracted']}")
    print("=" * 50)


if __name__ == "__main__":
    import os

    cli()
