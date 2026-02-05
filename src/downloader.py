"""Módulo principal para descarga y descompresión de archivos ZIP."""

import csv
import os
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup  # type: ignore


class ZipDownloader:
    """Descarga y descomprime archivos ZIP desde una página web."""

    def __init__(self, output_dir: str = "./downloads", overwrite: bool = True):
        """
        Inicializa el descargador.

        Args:
            output_dir: Directorio donde se guardarán los archivos
            overwrite: Si es True, sobrescribe archivos existentes
        """
        self.output_dir = Path(output_dir)
        self.overwrite = overwrite
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_zip_urls(self, url: str) -> List[str]:
        """
        Encuentra todos los enlaces a archivos .zip en una página.

        Args:
            url: URL de la página a analizar

        Returns:
            Lista de URLs completas de archivos .zip
        """
        try:
            response = requests.get(url, timeout=30)
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
                    zip_urls.append(full_url)

            return zip_urls

        except requests.RequestException as e:
            print(f"Error al acceder a {url}: {e}")
            return []

    def download_file(self, url: str) -> Optional[Path]:
        """
        Descarga un archivo desde una URL.

        Args:
            url: URL del archivo a descargar

        Returns:
            Ruta del archivo descargado
        """
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Obtener nombre del archivo de la URL
            # Buscar el patrón [nombre].zip en la URL (ej: ruc0.zip en .../ruc0.zip/...)
            zip_match = re.search(r"([^/]+\.zip)", url, re.IGNORECASE)
            if zip_match:
                filename = zip_match.group(1)
            else:
                # Fallback al método anterior
                filename = Path(urlparse(url).path).name
                if not filename.endswith(".zip"):
                    filename += ".zip"

            if not filename:
                filename = "downloaded_file.zip"

            filepath = self.output_dir / filename

            # Descargar el archivo (siempre sobreescribir)
            print(f"  ⬇️  Descargando: {filename}")
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return filepath

        except requests.RequestException as e:
            print(f"  ❌ Error al descargar {url}: {e}")
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
            print(f"  📦 Descomprimiendo: {zip_path.name}")
            extract_dir = self.output_dir / zip_path.stem
            extract_dir.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # Eliminar el ZIP después de descomprimir
            zip_path.unlink()
            print(f"  ✅ Extraído en: {extract_dir}")
            return True

        except zipfile.BadZipFile as e:
            print(f"  ❌ Error: {zip_path.name} no es un ZIP válido")
            return False
        except Exception as e:
            print(f"  ❌ Error al descomprimir {zip_path.name}: {e}")
            return False

    def process_url(self, url: str) -> dict:
        """
        Procesa una URL: busca, descarga y descomprime archivos ZIP.

        Args:
            url: URL de la página a procesar

        Returns:
            Diccionario con estadísticas del proceso
        """
        print(f"\n🔍 Analizando: {url}")

        zip_urls = self.find_zip_urls(url)

        if not zip_urls:
            print("  ⚠️  No se encontraron archivos .zip")
            return {"found": 0, "downloaded": 0, "extracted": 0}

        print(f"  📋 Archivos encontrados: {len(zip_urls)}")

        stats = {"found": len(zip_urls), "downloaded": 0, "extracted": 0}

        for zip_url in zip_urls:
            zip_path = self.download_file(zip_url)
            if zip_path:
                stats["downloaded"] += 1
                if self.extract_zip(zip_path):
                    stats["extracted"] += 1

        # Unificar archivos .txt y crear base de datos SQLite
        print("\n🔄 Unificando archivos .txt y creando base de datos...")
        self.unify_txt_files()

        return stats

    def unify_txt_files(self, project_root: Optional[Path] = None) -> bool:
        """
        Recorre todas las carpetas en downloads/, busca archivos .txt y los unifica
        en un archivo CSV ruc.csv en el directorio raíz del proyecto, luego crea
        una base de datos SQLite con los datos.

        Args:
            project_root: Ruta del directorio raíz del proyecto (opcional)

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
                print("  ⚠️  No se encontraron archivos .txt en downloads/")
                return False

            print(f"  📋 Archivos .txt encontrados: {len(txt_files)}")

            # Unificar todos los archivos en ruc.csv en la carpeta data
            csv_path = data_dir / "ruc.csv"
            rows = []
            headers = None

            # Leer todos los archivos .txt
            for txt_file in txt_files:
                try:
                    with open(txt_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            # Asumir que cada línea es un registro separado por pipe (|)
                            lines = content.split("\n")
                            for line_idx, line in enumerate(lines):
                                line = line.strip()
                                if line:
                                    # Separar por pipe (|)
                                    parts = [p.strip() for p in line.split("|")]

                                    if len(parts) > 0:
                                        # La primera línea del primer archivo es el header
                                        if line_idx == 0 and headers is None:
                                            headers = parts
                                        else:
                                            rows.append(parts)
                except Exception as e:
                    print(f"  ⚠️  Error al leer {txt_file.name}: {e}")

            if not rows:
                print("  ⚠️  No se encontraron datos válidos en los archivos .txt")
                return False

            # Usar los headers del primer archivo o generar headers por defecto
            if headers is None:
                headers = ["ruc", "razon_social", "dv", "ruc_anterior", "estado"]

            # Escribir el archivo en formato delimitado por pipe (|)
            print(f"  📝 Creando archivo delimitado por pipe: {csv_path}")
            with open(csv_path, "w", encoding="utf-8") as f:
                # Escribir el header
                f.write("|".join(headers) + "\n")
                # Escribir las filas de datos
                for row in rows:
                    f.write("|".join(row) + "\n")

            print(f"  ✅ Archivo creado: {csv_path} con {len(rows)} registros")

            # Verificar que el archivo sea válido
            if not self._validate_pipe_file(csv_path):
                print("  ❌ El archivo no es válido")
                return False

            # Crear la base de datos SQLite
            sqlite_path = data_dir / "ruc.sqlite"
            if self._create_sqlite_db(csv_path, sqlite_path, headers):
                print(f"  ✅ Base de datos SQLite creada: {sqlite_path}")
                return True
            else:
                print("  ❌ Error al crear la base de datos SQLite")
                return False

        except Exception as e:
            print(f"  ❌ Error al unificar archivos: {e}")
            return False

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
                print(
                    f"  ❌ El archivo no es válido: Solo tiene {len(lines)} línea(s). Se requiere al menos header + 1 fila de datos."
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
                        print(f"  🗑️  Eliminando línea {idx}: {motivo}")
                    else:
                        print(f"  🗑️  Eliminando línea {idx}: {motivo}")
                        print(f"     Contenido línea {idx}: {line[:100]}...")

            # Si se encontraron líneas con errores, procesarlas
            if error_lines:
                print(
                    f"  📝 Se eliminarán {len(error_lines)} línea(s) con errores del archivo..."
                )

                # Crear archivo error.csv en el mismo directorio que file_path
                error_path = file_path.parent / "error.csv"

                # Guardar las líneas con error en error.csv
                print(f"  📝 Creando archivo de errores: {error_path}")
                with open(error_path, "w", encoding="utf-8") as f:
                    f.write("numero_linea|contenido_linea|motivo_error\n")
                    for num_linea, contenido, motivo in error_lines:
                        # Escapar pipes en el contenido
                        contenido_escapado = contenido.replace("|", "\\|")
                        f.write(f"{num_linea}|{contenido_escapado}|{motivo}\n")
                print(f"  ✅ Archivo de errores creado: {error_path}")

                # Eliminar líneas en orden inverso para no afectar los índices
                line_indices_to_remove = [idx for idx, _, _ in error_lines]
                for line_idx in sorted(line_indices_to_remove, reverse=True):
                    del lines[line_idx - 1]  # -1 porque lines es 0-indexado

                # Reescribir el archivo original
                with open(file_path, "w", encoding="utf-8") as f:
                    for line in lines:
                        f.write(line + "\n")
                print(
                    f"  ✅ Archivo actualizado: {len(lines)} líneas después de eliminación"
                )

            return True

        except FileNotFoundError:
            print(f"  ❌ El archivo no es válido: No existe el archivo {file_path}")
            return False
        except UnicodeDecodeError:
            print(f"  ❌ El archivo no es válido: No se puede decodificar con UTF-8")
            return False
        except Exception as e:
            print(f"  ❌ El archivo no es válido: {type(e).__name__} - {e}")
            return False

    def _create_sqlite_db(
        self, file_path: Path, sqlite_path: Path, headers: List[str]
    ) -> bool:
        """
        Crea una base de datos SQLite a partir de un archivo delimitado por pipe (|).
        Si el archivo ya existe, lo sobrescribe.

        Args:
            file_path: Ruta del archivo delimitado por pipe
            sqlite_path: Ruta donde se creará la base de datos SQLite
            headers: Lista de encabezados del archivo

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

            # Leer el archivo delimitado por pipe e insertar los datos
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

                insert_count = 0
                for line in lines:
                    # Separar por pipe (|)
                    parts = [p.strip() for p in line.split("|")]

                    # Mapear por posición
                    values = {}
                    for field, idx in field_indices.items():
                        if idx < len(parts):
                            values[field] = parts[idx]
                        else:
                            values[field] = ""

                    # Insertar el registro
                    insert_sql = """
                        INSERT INTO ruc (ruc, razon_social, dv, ruc_anterior, estado)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(
                        insert_sql,
                        (
                            values.get("ruc", ""),
                            values.get("razon_social", ""),
                            values.get("dv", ""),
                            values.get("ruc_anterior", ""),
                            values.get("estado", ""),
                        ),
                    )
                    insert_count += 1

            conn.commit()
            print(
                f"  ✅ Base de datos SQLite creada: {sqlite_path} ({insert_count} registros)"
            )
            conn.close()
            return True

        except Exception as e:
            print(f"  ❌ Error al crear la base de datos SQLite: {e}")
            return False
