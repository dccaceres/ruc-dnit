# Usar una imagen base oficial de Python ligera
FROM python:3.9-slim

# Establecer variables de entorno para evitar archivos .pyc y buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY src/ ./src/
COPY config.ini .
COPY api.ini .

# Crear directorios para datos y descargas (se montarán como volúmenes)
RUN mkdir -p data downloads

# Exponer el puerto de la API
EXPOSE 8000

# Usuario no privilegiado para seguridad
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Comando por defecto (se puede sobrescribir en docker-compose)
# Ejecuta la API con Gunicorn usando Uvicorn workers
CMD ["gunicorn", "src.api:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
