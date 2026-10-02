#!/usr/bin/env python3
"""Clase 19 · Ej. 3 (OBLIGATORIO): API de tareas con FastAPI — el esqueleto del TP2, extendido.

    pip install fastapi uvicorn httpx
    python3 api.py                       → http://localhost:8000/docs
    python3 probar_api.py                → corre todas las pruebas de la consigna y muestra códigos/mensajes

Sobre el api.py del profe agrega:
  - PATCH /tareas/{id}   (Parte C.8) con un modelo de campos OPCIONALES
  - GET /estadisticas    (Parte C.9) cantidad de tareas por estado
  - límite de 10 pendientes en POST (Parte C.10) → 503 + Retry-After (justificación en el README)
  - middleware que mide cada pedido y lo devuelve en el header X-Tiempo (adicional)
  - un print en el endpoint para comprobar que la validación ocurre ANTES (Parte B.7)
"""
import asyncio
import os
import threading
import time
from collections import Counter
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

MAX_PENDIENTES = 10
Estado = Literal["pendiente", "ejecutando", "completada"]

app = FastAPI(title="Tareas", description="Clase 19 · esqueleto del TP2")

# Estado en memoria. OJO: con --workers > 1 cada proceso tiene SU diccionario (ver README, ej. 4).
tareas: dict[int, dict] = {}
proximo_id = 0


class TareaNueva(BaseModel):
    tipo: Literal["descargar", "hashear", "esperar"]
    prioridad: int = Field(default=1, ge=1, le=5, description="1 = más baja, 5 = más alta")


class Tarea(TareaNueva):
    id: int
    estado: Estado = "pendiente"


class CambioTarea(BaseModel):
    """PATCH: todo opcional. Solo se cambia lo que venga en el cuerpo."""
    estado: Estado | None = None
    prioridad: int | None = Field(default=None, ge=1, le=5)


@app.middleware("http")
async def medir_tiempo(request: Request, call_next):
    """Corre ANTES y DESPUÉS de cada endpoint (envuelve a todos, incluso a los que fallan con 422)."""
    t0 = time.perf_counter()
    respuesta = await call_next(request)          # acá se ejecuta la validación + el endpoint
    respuesta.headers["X-Tiempo"] = f"{(time.perf_counter() - t0) * 1000:.2f}ms"
    return respuesta


@app.get("/")
async def raiz():
    return {"servicio": "tareas", "docs": "/docs"}


@app.get("/tareas", response_model=list[Tarea])
async def listar(estado: Estado | None = Query(default=None), limite: int = Query(default=10, ge=1, le=100)):
    items = list(tareas.values())
    if estado:
        items = [t for t in items if t["estado"] == estado]
    return items[:limite]


@app.post("/tareas", response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva, response: Response):
    global proximo_id
    pendientes = sum(1 for t in tareas.values() if t["estado"] == "pendiente")
    if pendientes >= MAX_PENDIENTES:
        # 503: el servidor no puede aceptar más trabajo AHORA (no es culpa del pedido); Retry-After dice cuándo volver
        raise HTTPException(status_code=503, detail=f"Hay {pendientes} tareas pendientes (máximo {MAX_PENDIENTES})",
                            headers={"Retry-After": "5"})
    proximo_id += 1
    tarea = {"id": proximo_id, **nueva.model_dump(), "estado": "pendiente"}
    tareas[proximo_id] = tarea
    response.headers["Location"] = f"/tareas/{proximo_id}"     # dónde quedó el recurso creado
    return tarea


@app.get("/tareas/{tarea_id}", response_model=Tarea)
async def obtener(tarea_id: int):
    print(f"[obtener] me llamaron con tarea_id={tarea_id!r} de tipo {type(tarea_id).__name__}")
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="No existe esa tarea")
    return tareas[tarea_id]


@app.patch("/tareas/{tarea_id}", response_model=Tarea)
async def modificar(tarea_id: int, cambio: CambioTarea):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="No existe esa tarea")
    datos = cambio.model_dump(exclude_unset=True)       # SOLO los campos que mandó el cliente
    if not datos:
        raise HTTPException(status_code=422, detail="No mandaste ningún campo para cambiar")
    tareas[tarea_id].update(datos)
    return tareas[tarea_id]


@app.delete("/tareas/{tarea_id}", status_code=204)
async def borrar(tarea_id: int):
    if tarea_id not in tareas:
        raise HTTPException(status_code=404, detail="No existe esa tarea")
    del tareas[tarea_id]


@app.get("/estadisticas")
async def estadisticas():
    por_estado = Counter(t["estado"] for t in tareas.values())
    return {"total": len(tareas),
            "por_estado": {e: por_estado.get(e, 0) for e in ("pendiente", "ejecutando", "completada")},
            "pid": os.getpid()}


@app.get("/quien-soy")
async def quien_soy():
    loop = asyncio.get_running_loop()
    return {"pid": os.getpid(), "thread": threading.current_thread().name,
            "loop": type(loop).__name__, "id_del_loop": id(loop)}


@app.get("/quien-soy-sync")
def quien_soy_sync():
    try:
        asyncio.get_running_loop()
        estado = "HAY loop"
    except RuntimeError:
        estado = "NO hay loop corriendo acá"
    return {"thread": threading.current_thread().name, "loop": estado}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
