"""Pruebas unitarias para el módulo downloader."""

import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import requests
from downloader import ZipDownloader


class TestZipDownloader(unittest.TestCase):
    """Pruebas para la clase ZipDownloader."""

    def setUp(self):
        """Configuración inicial para las pruebas."""
        self.temp_dir = tempfile.mkdtemp()
        # Usar un directorio de logs temporal para las pruebas
        self.logs_dir = os.path.join(self.temp_dir, "logs")
        self.downloader = ZipDownloader(
            output_dir=self.temp_dir,
            log_dir=self.logs_dir,
            log_level=logging.WARNING  # Menos verboso para pruebas
        )

    def tearDown(self):
        """Limpieza después de las pruebas."""
        # Cerrar handlers de logging para liberar archivos
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
            logging.root.removeHandler(handler)
        
        # Eliminar archivos y directorios creados durante las pruebas
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except (PermissionError, FileNotFoundError):
                    # Ignorar errores si el archivo está en uso o ya fue eliminado
                    pass
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except (OSError, FileNotFoundError):
                    # Ignorar errores si el directorio no está vacío o ya fue eliminado
                    pass
        
        try:
            os.rmdir(self.temp_dir)
        except (OSError, FileNotFoundError):
            # Ignorar errores si el directorio no está vacío o ya fue eliminado
            pass

    def test_initialization(self):
        """Prueba la inicialización del ZipDownloader."""
        self.assertEqual(self.downloader.output_dir, Path(self.temp_dir))
        self.assertTrue(self.downloader.overwrite)
        self.assertTrue(self.downloader.output_dir.exists())

    def test_is_valid_url(self):
        """Prueba la validación de URLs."""
        # URLs válidas
        self.assertTrue(self.downloader._is_valid_url("https://example.com/file.zip"))
        self.assertTrue(self.downloader._is_valid_url("http://example.com/file.zip"))
        
        # URLs inválidas
        self.assertFalse(self.downloader._is_valid_url("example.com"))
        self.assertFalse(self.downloader._is_valid_url(""))
        self.assertFalse(self.downloader._is_valid_url("ftp://example.com"))

    def test_get_filename_from_url(self):
        """Prueba la extracción de nombres de archivo desde URLs."""
        # URL con nombre de archivo claro
        filename = self.downloader._get_filename_from_url("https://example.com/files/data.zip")
        self.assertEqual(filename, "data.zip")
        
        # URL sin extensión
        filename = self.downloader._get_filename_from_url("https://example.com/files/data")
        self.assertEqual(filename, "data.zip")
        
        # URL compleja
        filename = self.downloader._get_filename_from_url("https://example.com/path/to/ruc0.zip/download")
        self.assertEqual(filename, "ruc0.zip")

    @patch('requests.get')
    def test_find_zip_urls_success(self, mock_get):
        """Prueba la búsqueda de URLs de ZIP en una página."""
        # Configurar mock
        mock_response = Mock()
        mock_response.text = '''
            <html>
                <body>
                    <a href="file1.zip">Download 1</a>
                    <a href="path/to/file2.zip">Download 2</a>
                    <a href="notazip.txt">Not a ZIP</a>
                </body>
            </html>
        '''
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Ejecutar método
        urls = self.downloader.find_zip_urls("https://example.com")
        
        # Verificar resultados
        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com/file1.zip", urls)
        self.assertIn("https://example.com/path/to/file2.zip", urls)

    @patch('requests.get')
    def test_find_zip_urls_invalid_url(self, mock_get):
        """Prueba el manejo de URLs inválidas."""
        # Prueba con URL inválida
        urls = self.downloader.find_zip_urls("invalid-url")
        self.assertEqual(len(urls), 0)

    @patch('requests.get')
    def test_find_zip_urls_request_error(self, mock_get):
        """Prueba el manejo de errores en solicitudes HTTP."""
        # Configurar mock para lanzar excepción
        mock_get.side_effect = requests.RequestException("Request failed")
        
        # Ejecutar método
        urls = self.downloader.find_zip_urls("https://example.com")
        
        # Verificar resultados
        self.assertEqual(len(urls), 0)

    @patch('requests.get')
    def test_download_file_success(self, mock_get):
        """Prueba la descarga exitosa de un archivo."""
        # Configurar mock
        mock_response = Mock()
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2', b'']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Ejecutar método
        file_path = self.downloader.download_file("https://example.com/file.zip")
        
        # Verificar resultados
        self.assertIsNotNone(file_path)
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.name, "file.zip")
        self.assertEqual(file_path.read_bytes(), b'chunk1chunk2')

    @patch('requests.get')
    def test_download_file_invalid_url(self, mock_get):
        """Prueba el manejo de URLs inválidas en descargas."""
        # Prueba con URL inválida
        file_path = self.downloader.download_file("invalid-url")
        self.assertIsNone(file_path)

    @patch('requests.get')
    def test_download_file_request_error(self, mock_get):
        """Prueba el manejo de errores en descargas."""
        # Configurar mock para lanzar excepción
        mock_get.side_effect = requests.RequestException("Download failed")
        
        # Ejecutar método
        file_path = self.downloader.download_file("https://example.com/file.zip")
        
        # Verificar resultados
        self.assertIsNone(file_path)

    def test_write_batch_to_csv(self):
        """Prueba la escritura por lotes al CSV."""
        # Crear archivo CSV temporal
        csv_path = Path(self.temp_dir) / "test.csv"
        
        # Datos de prueba
        batch = [
            ["ruc1", "empresa1", "dv1", "anterior1", "activo"],
            ["ruc2", "empresa2", "dv2", "anterior2", "inactivo"]
        ]
        
        # Ejecutar método
        self.downloader._write_batch_to_csv(csv_path, batch)
        
        # Verificar resultados
        self.assertTrue(csv_path.exists())
        content = csv_path.read_text()
        expected = "ruc1|empresa1|dv1|anterior1|activo\nruc2|empresa2|dv2|anterior2|inactivo\n"
        self.assertEqual(content, expected)

    def test_extract_zip_success(self):
        """Prueba la extracción exitosa de un archivo ZIP."""
        import zipfile
        
        # Crear un archivo ZIP de prueba
        zip_path = Path(self.temp_dir) / "test.zip"
        extract_dir = Path(self.temp_dir) / "test"
        
        # Crear contenido para el ZIP
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr("file1.txt", "contenido del archivo 1")
            zipf.writestr("file2.txt", "contenido del archivo 2")
        
        # Ejecutar método
        result = self.downloader.extract_zip(zip_path)
        
        # Verificar resultados
        self.assertTrue(result)
        self.assertFalse(zip_path.exists())  # Archivo ZIP eliminado
        self.assertTrue(extract_dir.exists())
        self.assertTrue((extract_dir / "file1.txt").exists())
        self.assertTrue((extract_dir / "file2.txt").exists())

    def test_extract_zip_invalid_file(self):
        """Prueba el manejo de archivos ZIP inválidos."""
        # Crear un archivo que no es ZIP
        zip_path = Path(self.temp_dir) / "test.txt"
        zip_path.write_text("esto no es un zip")
        
        # Ejecutar método
        result = self.downloader.extract_zip(zip_path)
        
        # Verificar resultados
        self.assertFalse(result)
        self.assertTrue(zip_path.exists())  # Archivo no eliminado

    def test_logging_setup(self):
        """Prueba que los archivos de log se creen correctamente."""
        # Verificar que el directorio de logs existe
        logs_path = Path(self.logs_dir)
        self.assertTrue(logs_path.exists())
        self.assertTrue(logs_path.is_dir())
        
        # Verificar que se creó al menos un archivo de log
        log_files = list(logs_path.glob("zip_downloader_*.log"))
        self.assertGreater(len(log_files), 0, "Debería existir al menos un archivo de log")
        
        # Verificar que el nombre del log sigue el formato esperado
        for log_file in log_files:
            self.assertTrue("zip_downloader_" in log_file.name)
            self.assertTrue(".log" in log_file.name)
            # Verificar que contiene fecha y hora en el nombre
            name_parts = log_file.name.replace("zip_downloader_", "").replace(".log", "")
            self.assertEqual(len(name_parts), 15)  # Formato: YYYYMMDD_HHMMSS

    def test_unify_txt_files_existing_output(self):
        """Prueba el manejo cuando el archivo de salida ya existe."""
        import zipfile
        
        # Crear directorio data
        data_dir = Path(self.temp_dir) / "data"
        data_dir.mkdir(exist_ok=True)
        
        # Crear un archivo CSV existente
        csv_path = data_dir / "ruc.csv"
        csv_path.write_text("ruc|razon_social|dv|ruc_anterior|estado\n123|empresa|1|0|activo\n")
        
        # Crear un archivo TXT de prueba
        txt_dir = Path(self.temp_dir) / "downloads"
        txt_dir.mkdir(exist_ok=True)
        txt_file = txt_dir / "test.txt"
        txt_file.write_text("ruc|razon_social|dv|ruc_anterior|estado\n456|otra empresa|2||inactivo\n")
        
        # Ejecutar método
        result = self.downloader.unify_txt_files(project_root=Path(self.temp_dir))
        
        # Verificar resultados
        self.assertTrue(result)
        self.assertTrue(csv_path.exists())
        
        # Verificar que el contenido sea el esperado (debería tener solo los nuevos datos)
        content = csv_path.read_text()
        lines = content.strip().split('\n')
        self.assertEqual(len(lines), 2)  # Header + 1 fila de datos
        self.assertIn("ruc|razon_social|dv|ruc_anterior|estado", lines[0])
        self.assertIn("456|otra empresa|2||inactivo", content)


if __name__ == '__main__':
    unittest.main()