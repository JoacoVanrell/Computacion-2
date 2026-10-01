FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY *.py ./
# -u = sin buffer: los print aparecen al instante en "docker compose logs"
CMD ["python", "-u", "worker.py"]
