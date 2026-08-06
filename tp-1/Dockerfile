FROM python:3.11-slim

WORKDIR /app

# procps trae ps/top: no los usamos en el código (está prohibido),
# pero sirven para comparar a mano si mi monitor dice la verdad.
RUN apt-get update && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.json .
COPY src/ ./src/

# -u = sin buffering en stdout. Importante con multiprocessing:
# si no, los prints de los hijos quedan atrapados y no ves nada.
CMD ["python", "-u", "src/main.py"]