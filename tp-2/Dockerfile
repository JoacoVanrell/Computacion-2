FROM python:3.11-slim

WORKDIR /app

# Sin buffering en stdout: si no, los print() no aparecen en `docker compose logs`
# hasta que se junta un bloque (es el -u del TP1).
ENV PYTHONUNBUFFERED=1

# Primero las dependencias: si solo cambia el código, esta capa se reusa.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Forma exec (con corchetes): uvicorn queda como PID 1 y recibe directo
# el SIGTERM de `docker compose stop`. Con la forma shell lo recibiría sh.
# --host 0.0.0.0 para que se pueda entrar desde afuera del contenedor.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
