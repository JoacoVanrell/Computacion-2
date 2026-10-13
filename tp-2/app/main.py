"""FastAPI + lifespan: crea la cola, el pool, el cliente httpx y los workers.

Uso (parado en tp-2/):
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Después:
    http://localhost:8000/docs
"""
from fastapi import FastAPI

from app.rutas import router

app = FastAPI(
    title='Plataforma de tareas',
    description='TP2 de Computación II',
)
app.include_router(router)
