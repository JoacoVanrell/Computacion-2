# Clase 1 · Ej. 5.3: "la solución correcta" — una imagen con la dependencia ya instalada.
FROM python:3.11-slim
WORKDIR /app
# primero requirements: si solo cambia el código, Docker reusa esta capa (no reinstala)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY con_dependencias.py .
CMD ["python", "con_dependencias.py"]
