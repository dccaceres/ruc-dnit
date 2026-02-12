"""Módulo principal para descarga y descompresión de archivos ZIP."""

import csv
import logging
import os
import re
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup  # type: ignore


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """
    Configura el sistema de logging con archivo rotativo por fecha/hora.

    Args:
        log_dir: Directorio donde se guardarán los logs
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Logger configurado
    """
    # Crear directorio de logs si no existe
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Generar nombre de archivo con fecha y hora
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = log_path / f"zip_downloader_{timestamp}.log"

    # Cerrar handlers existentes para evitar ResourceWarning
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)

    # Configurar logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configurado: {log_filename}")
    logger.info(f"Nivel de logging: {logging.getLevelName(log_level)}")
    
    return logger


# Configurar logging al importar el módulo
logger = setup_logging()


class ZipDownloader:
    """Descarga y descomprime archivos ZIP desde una página web."""

    def __init__(self, output_dir: str = "./downloads", overwrite: bool = True, 
                 request_timeout: int = 30, download_timeout: int = 60,
                 log_dir: str = "logs", log_level: int = logging.INFO):
        """
        Inicializa el descargador.

        Args:
            output_dir: Directorio donde se guardarán los archivos
            overwrite: Si es True, sobrescribe archivos existentes
            request_timeout: Timeout para solicitudes HTTP (segundos)
            download_timeout: Timeout para descargas de archivos (segundos)
            log_dir: Directorio para archivos de log
            log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR)
        """
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.request_timeout = request_timeout
        self.download_timeout = download_timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Reconfigurar logging si se especifican parámetros diferentes
        global logger
        logger = setup_logging(log_dir, log_level)
        
        logger.info(f"ZipDownloader inicializado con output_dir={self.output_dir}")
        logger.info(f"Parámetros: overwrite={overwrite}, request_timeout={request_timeout}s, download_timeout={download_timeout}s")

    def _is_valid_url(self, url: str) -> bool:
        """
        Valida que una URL sea válida para HTTP/HTTPS.

        Args:
            url: URL a validar

        Returns:
            True si la URL es válida (solo http/https)
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc, result.scheme.lower() in ['http', 'https']])
        except ValueError:
            return False

    def find_zip_urls(self, url: str) -> List[str]:
        """
        Encuentra todos los enlaces a archivos .zip en una página.

        Args:
            url: URL de la página a analizar

        Returns:
            Lista de URLs completas de archivos .zip
        """
        if not self._is_valid_url(url):
            logger.error(f"URL inválida: {url}")
            return []

        try:
            logger.debug(f"Analizando página: {url}")
            response = requests.get(url, timeout=self.request_timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            zip_urls = []

            for link in soup.find_all("a", href=True):
                href = link["href"]
                href_lower = href.lower()
                # Buscar enlaces que terminen con .zip o contengan .zip/
                if href_lower.endswith(".zip") or ".zip/" in href_lower:
                    # Convertir URLs relativas a absolutas
                    full_url = urljoin(url, href)
                    if self._is_valid_url(full_url):
                        zip_urls.append(full_url)

            logger.info(f"Encontrados {len(zip_urls)} archivos ZIP en {url}")
            return zip_urls

        except requests.RequestException as e:
            logger.error(f"Error al acceder a {url}: {e}")
            return []

    def _get_filename_from_url(self, url: str) -> str:
        """
        Extrae el nombre de archivo de una URL.

        Args:
            url: URL del archivo

        Returns:
            Nombre del archivo con extensión .zip
        """
        # Buscar el patrón [nombre].zip en la URL (ej: ruc0.zip en .../ruc0.zip/...)
        zip_match = re.search(r"([^/]+\.zip)", url, re.IGNORECASE)
        if zip_match:
            return zip_match.group(1)
        
        # Fallback al método anterior
        filename = Path(urlparse(url).path).name
        if not filename.endswith(".zip"):
            filename += ".zip"
        
        return filename if filename else "downloaded_file.zip"

    def download_file(self, url: str, chunk_size: int = 8192) -> Optional[Path]:
        """
        Descarga un archivo desde una URL.

        Args:
            url: URL del archivo a descargar
            chunk_size: Tamaño de los chunks para descarga en bytes

        Returns:
            Ruta del archivo descargado
        """
        if not self._is_valid_url(url):
            logger.error(f"URL inválida para descarga: {url}")
            return None

        try:
            logger.debug(f"Iniciando descarga de: {url}")
            response = requests.get(url, stream=True, timeout=self.download_timeout)
            response.raise_for_status()

            filename = self._get_filename_from_url(url)
            filepath = self.output_dir / filename

            # Descargar el archivo (siempre sobreescribir)
            logger.info(f"Descargando: {filename}")
            
            # Crear directorio si no existe
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)

            file_size = filepath.stat().st_size
            logger.info(f"Descarga completada: {filename} ({file_size / 1024:.2f} KB)")
            return filepath

        except requests.RequestException as e:
            logger.error(f"Error al descargar {url}: {e}")
            return None
        except IOError as e:
            logger.error(f"Error de I/O al guardar {url}: {e}")
            return None

    def extract_zip(self, zip_path: Path) -> bool:
        """
        Descomprime un archivo ZIP en el directorio de salida.

        Args:
            zip_path: Ruta del archivo ZIP

        Returns:
            True si la extracción fue exitosa
        """
        try:
            logger.info(f"Descomprimiendo: {zip_path.name}")
            extract_dir = self.output_dir / zip_path.stem
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Eliminar el ZIP después de descomprimir
            zip_path.unlink()
            logger.info(f"Extraído en: {extract_dir}")
            return True

        except zipfile.BadZipFile as e:
            logger.error(f"Error: {zip_path.name} no es un ZIP válido")
            return False
        except Exception as e:
            logger.error(f"Error al descomprimir {zip_path.name}: {e}")
            return False

    def process_url(self, url: str) -> dict:
        """
        Procesa una URL: busca, descarga y descomprime archivos ZIP.

        Args:
            url: URL de la página a procesar

        Returns:
            Diccionario con estadísticas del proceso
        """
        logger.info(f"Analizando: {url}")

        zip_urls = self.find_zip_urls(url)

        if not zip_urls:
            logger.warning("No se encontraron archivos .zip")
            return {"found": 0, "downloaded": 0, "extracted": 0}

        logger.info(f"Archivos encontrados: {len(zip_urls)}")

        stats = {"found": len(zip_urls), "downloaded": 0, "extracted": 0}

        for zip_url in zip_urls:
            zip_path = self.download_file(zip_url)
            if zip_path:
                stats["downloaded"] += 1
                if self.extract_zip(zip_path):
                    stats["extracted"] += 1

        # Unificar archivos .txt y crear base de datos SQLite
        logger.info("Unificando archivos .txt y creando base de datos...")
        self.unify_txt_files()

        logger.info(f"Proceso completado. Estadísticas: {stats}")
        return stats

    def unify_txt_files(self, project_root: Optional[Path] = None, batch_size: int = 1000) -> bool:
        """
        Recorre todas las carpetas en downloads/, busca archivos .txt y los unifica
        en un archivo CSV ruc.csv en el directorio raíz del proyecto, luego crea
        una base de datos SQLite con los datos.

        Args:
            project_root: Ruta del directorio raíz del proyecto (opcional)
            batch_size: Número de líneas a procesar por lote (para archivos grandes)

        Returns:
            True si el proceso fue exitoso
        """
        try:
            # Determinar el directorio raíz del proyecto (donde está src/)
            if project_root is None:
                project_root = Path(__file__).parent.parent
            else:
                project_root = Path(project_root)

            # Crear carpeta data en el directorio raíz
            data_dir = project_root / "data"
            data_dir.mkdir(parents=True, exist_ok=True)

            # Buscar todos los archivos .txt en downloads/
            txt_files = list(self.output_dir.glob("**/*.txt"))

            if not txt_files:
                logger.warning("No se encontraron archivos .txt en downloads/")
                return False

            logger.info(f"Archivos .txt encontrados: {len(txt_files)}")

            # Unificar todos los archivos en ruc.csv en la carpeta data
            csv_path = data_dir / "ruc.csv"
            temp_csv_path = data_dir / "ruc_temp.csv"
            headers = None
            total_rows = 0

            # Procesar archivos .txt por lotes para optimizar memoria
            logger.info(f"Procesando archivos .txt con batch_size={batch_size}")
            
            # Primero, determinar los headers
            for txt_file in txt_files:
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        first_line = f.readline().strip()
                        if first_line and headers is None:
                            headers = [p.strip() for p in first_line.split("|")]
                            if headers:
                                break
                except Exception as e:
                    logger.warning(f"Error al leer headers de {txt_file.name}: {e}")
                    continue

            # Usar headers por defecto si no se encontraron
            if headers is None:
                headers = ["ruc", "razon_social", "dv", "ruc_anterior", "estado"]
                logger.info("Usando headers por defecto")

            # Escribir el header al archivo temporal
            with open(temp_csv_path, "w", encoding="utf-8") as f:
                f.write("|".join(headers) + "\n")

            # Procesar cada archivo .txt línea por línea
            for txt_file in txt_files:
                try:
                    logger.debug(f"Procesando archivo: {txt_file.name}")
                    with open(txt_file, "r", encoding="utf-8") as f:
                        # Saltar header si es el primer archivo
                        first_line_skipped = False
                        batch = []
                        
                        for line_idx, line in enumerate(f):
                            line = line.strip()
                            if line:
                                # Saltar la primera línea (header) de cada archivo
                                if line_idx == 0:
                                    first_line_skipped = True
                                    continue
                                
                                # Separar por pipe (|)
                                parts = [p.strip() for p in line.split("|")]
                                if len(parts) > 0:
                                    batch.append(parts)
                                    
                                    # Escribir por lotes para optimizar I/O
                                    if len(batch) >= batch_size:
                                        self._write_batch_to_csv(temp_csv_path, batch)
                                        total_rows += len(batch)
                                        batch = []
                                        logger.debug(f"Procesadas {total_rows} líneas...")
                        
                        # Escribir el último batch
                        if batch:
                            self._write_batch_to_csv(temp_csv_path, batch)
                            total_rows += len(batch)
                            batch = []
                            
                except Exception as e:
                    logger.warning(f"Error al procesar {txt_file.name}: {e}")
                    continue

            if total_rows == 0:
                logger.warning("No se encontraron datos válidos en los archivos .txt")
                temp_csv_path.unlink()  # Limpiar archivo temporal
                return False

            logger.info(f"Archivo temporal creado: {temp_csv_path} con {total_rows} registros")

            # Eliminar archivo final si existe antes de renombrar
            if csv_path.exists():
                logger.debug(f"Eliminando archivo existente: {csv_path}")
                csv_path.unlink()

            # Renombrar archivo temporal al final
            temp_csv_path.rename(csv_path)
            logger.info(f"Archivo final creado: {csv_path}")

            # Verificar que el archivo sea válido
            if not self._validate_pipe_file(csv_path):
                logger.error("El archivo no es válido")
                return False

            # Crear la base de datos SQLite
            sqlite_path = data_dir / "ruc.sqlite"
            if self._create_sqlite_db(csv_path, sqlite_path, headers):
                logger.info(f"Base de datos SQLite creada: {sqlite_path}")
                return True
            else:
                logger.error("Error al crear la base de datos SQLite")
                return False

        except Exception as e:
            logger.error(f"Error al unificar archivos: {e}")
            # Limpiar archivo temporal si existe
            if 'temp_csv_path' in locals() and temp_csv_path.exists():
                try:
                    temp_csv_path.unlink()
                    logger.debug(f"Archivo temporal eliminado por error: {temp_csv_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Error al limpiar archivo temporal {temp_csv_path}: {cleanup_error}")
            return False

    def _write_batch_to_csv(self, csv_path: Path, batch: List[List[str]]) -> None:
        """
        Escribe un lote de datos al archivo CSV.

        Args:
            csv_path: Ruta del archivo CSV
            batch: Lista de filas a escribir
        """
        try:
            with open(csv_path, "a", encoding="utf-8") as f:
                for row in batch:
                    f.write("|".join(row) + "\n")
        except Exception as e:
            logger.error(f"Error al escribir batch al CSV: {e}")
            raise

    def _validate_pipe_file(self, file_path: Path) -> bool:
        """
        Valida que el archivo delimitado por pipe (|) sea válido.
        Si encuentra líneas con errores, las elimina del archivo original y
        las guarda en error.csv para su revisión.

        Args:
            file_path: Ruta del archivo delimitado por pipe

        Returns:
            True si el archivo es válido (o se corrigieron los errores)
        """
        try:
            # Leer todo el archivo
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            # Verificar que hay al menos header + 1 fila de datos
            if len(lines) < 2:
                logger.error(
                    f"El archivo no es válido: Solo tiene {len(lines)} línea(s). Se requiere al menos header + 1 fila de datos."
                )
                return False

            # Verificar que todas las filas tengan el mismo número de columnas
            header_line = lines[0]
            num_cols = len(header_line.split("|"))
            error_lines = []  # Tuplas: (numero_linea, contenido_linea, motivo_error)

            for idx, line in enumerate(lines[1:], start=2):
                line_cols = len(line.split("|"))
                if line_cols != num_cols:
                    # Determinar el motivo del error
                    motivo = (
                        f"Tiene {line_cols} columna(s) pero se esperaban {num_cols}"
                    )
                    if "CANCELADO" in line.upper():
                        motivo += " (contiene CANCELADO)"

                    error_lines.append((idx, line, motivo))

                    # Mostrar mensaje de eliminación
                    if "CANCELADO" in line.upper():
                        logger.info(f"Eliminando línea {idx}: {motivo}")
                    else:
                        logger.info(f"Eliminando línea {idx}: {motivo}")
                        logger.debug(f"Contenido línea {idx}: {line[:100]}...")

            # Si se encontraron líneas con errores, procesarlas
            if error_lines:
                logger.info(
                    f"Se eliminarán {len(error_lines)} línea(s) con errores del archivo..."
                )

                # Crear archivo error.csv en el mismo directorio que file_path
                error_path = file_path.parent / "error.csv"

                # Guardar las líneas con error en error.csv
                logger.info(f"Creando archivo de errores: {error_path}")
                with open(error_path, "w", encoding="utf-8") as f:
                    f.write("numero_linea|contenido_linea|motivo_error\n")
                    for num_linea, contenido, motivo in error_lines:
                        # Escapar pipes en el contenido
                        contenido_escapado = contenido.replace("|", "\\|")
                        f.write(f"{num_linea}|{contenido_escapado}|{motivo}\n")
                logger.info(f"Archivo de errores creado: {error_path}")

                # Eliminar líneas en orden inverso para no afectar los índices
                line_indices_to_remove = [idx for idx, _, _ in error_lines]
                for line_idx in sorted(line_indices_to_remove, reverse=True):
                    del lines[line_idx - 1]  # -1 porque lines es 0-indexado

                # Reescribir el archivo original
                with open(file_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        f.write(line + "\n")
                logger.info(
                    f"Archivo actualizado: {len(lines)} líneas después de eliminación"
                )

            return True

        except FileNotFoundError:
            logger.error(f"El archivo no es válido: No existe el archivo {file_path}")
            return False
        except UnicodeDecodeError:
            logger.error(f"El archivo no es válido: No se puede decodificar con UTF-8")
            return False
        except Exception as e:
            logger.error(f"El archivo no es válido: {type(e).__name__} - {e}")
            return False

    def _create_sqlite_db(
        self, file_path: Path, sqlite_path: Path, headers: List[str], batch_size: int = 1000
    ) -> bool:
        """
        Crea una base de datos SQLite a partir de un archivo delimitado por pipe (|).
        Si el archivo ya existe, lo sobrescribe.

        Args:
            file_path: Ruta del archivo delimitado por pipe
            sqlite_path: Ruta donde se creará la base de datos SQLite
            headers: Lista de encabezados del archivo
            batch_size: Número de registros a insertar por transacción

        Returns:
            True si la base de datos se creó exitosamente
        """
        try:
            # Campos esperados en la tabla y sus índices (0-based)
            # El archivo no tiene header, por lo que asumimos el orden:
            # 0: ruc, 1: razon_social, 2: dv, 3: ruc_anterior, 4: estado
            field_indices = {
                "ruc": 0,
                "razon_social": 1,
                "dv": 2,
                "ruc_anterior": 3,
                "estado": 4,
            }

            # Eliminar la base de datos si ya existe
            if sqlite_path.exists():
                sqlite_path.unlink()

            # Crear la base de datos
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()

            # Crear la tabla ruc
            create_table_sql = """
                CREATE TABLE ruc (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ruc TEXT,
                    razon_social TEXT,
                    dv TEXT,
                    ruc_anterior TEXT,
                    estado TEXT
                )
            """
            cursor.execute(create_table_sql)

            # Leer el archivo delimitado por pipe e insertar los datos por lotes
            insert_sql = """
                INSERT INTO ruc (ruc, razon_social, dv, ruc_anterior, estado)
                VALUES (?, ?, ?, ?, ?)
            """
            
            batch = []
            insert_count = 0
            
            with open(file_path, "r", encoding="utf-8") as f:
                # Saltar header
                header = f.readline()
                
                for line_idx, line in enumerate(f):
                    line = line.strip()
                    if line:
                        # Separar por pipe (|)
                        parts = [p.strip() for p in line.split("|")]
                        
                        # Mapear por posición
                        values = []
                        for field in ["ruc", "razon_social", "dv", "ruc_anterior", "estado"]:
                            idx = field_indices[field]
                            values.append(parts[idx] if idx < len(parts) else "")
                        
                        batch.append(tuple(values))
                        
                        # Insertar por lotes para optimizar rendimiento
                        if len(batch) >= batch_size:
                            cursor.executemany(insert_sql, batch)
                            insert_count += len(batch)
                            batch = []
                            
                            # Commit periódico para evitar transacciones demasiado grandes
                            if insert_count % (batch_size * 10) == 0:
                                conn.commit()
                                logger.debug(f"Insertados {insert_count} registros...")
                
                # Insertar el último batch
                if batch:
                    cursor.executemany(insert_sql, batch)
                    insert_count += len(batch)
                    batch = []

            # Commit final
            conn.commit()
            logger.info(
                f"Base de datos SQLite creada: {sqlite_path} ({insert_count} registros)"
            )
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error al crear la base de datos SQLite: {e}")
            if 'conn' in locals():
                try:
                    conn.rollback()
                    conn.close()
                except Exception as cleanup_error:
                    logger.warning(f"Error al cerrar conexión SQLite: {cleanup_error}")
            return False
