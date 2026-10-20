"""FastAPI + lifespan: crea la cola, el pool, el cliente httpx y los workers.

Uso (parado en tp-2/):
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Después:
    http://localhost:8000/docs
"""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config
from app.rutas import router
from app.workers import worker


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # --- al arrancar, antes de atender el primer pedido ---
    app.state.cola = asyncio.Queue(maxsize=config.MAXSIZE_COLA)
    # El pool se crea UNA vez: crear procesos es caro, así se reusan.
    app.state.pool = ProcessPoolExecutor(max_workers=config.PROCESOS)
    app.state.workers = [
        asyncio.create_task(worker(app.state.cola, i, app.state.pool))
        for i in range(config.WORKERS)
    ]
    print(f'{config.WORKERS} workers esperando tareas '
          f'(cola de {config.MAXSIZE_COLA} lugares, '
          f'{config.PROCESOS} procesos para hashear, '
          f'executor {"SÍ" if config.USAR_EXECUTOR else "NO"})')

    yield                                  # acá el servidor atiende

    # --- al apagar ---
    # Por ahora como en cola.py: cancelarlos. El apagado ordenado
    # con centinela va en T8.
    for w in app.state.workers:
        w.cancel()
    await asyncio.gather(*app.state.workers, return_exceptions=True)
    app.state.pool.shutdown()


app = FastAPI(
    title='Plataforma de tareas',
    description='TP2 de Computación II',
    lifespan=ciclo_de_vida,
)
app.include_router(router)
