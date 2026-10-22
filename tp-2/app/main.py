"""FastAPI + lifespan: crea la cola, el pool, el cliente httpx y los workers.

Uso (parado en tp-2/):
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Después:
    http://localhost:8000/docs
"""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI

from app import config, estado, persistencia
from app.rutas import router
from app.workers import CENTINELA, worker


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # --- al arrancar, antes de atender el primer pedido ---
    persistencia.avisar_volcado_previo()
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

    # --- al apagar (SIGTERM o SIGINT) ---
    # Cuando llegamos acá, uvicorn ya recibió la señal y dejó de aceptar
    # conexiones: no entran tareas nuevas.
    await apagar(app)


async def apagar(app: FastAPI):
    print('Apagando: espero a las tareas en curso...')
    ahora = datetime.now()

    # 1. Las pendientes no se van a ejecutar: el worker las va a saltear.
    for tarea in estado.tareas.values():
        if tarea.estado == 'pendiente':
            tarea.estado = 'cancelada'
            tarea.error = 'El servidor se apagó antes de ejecutarla'
            tarea.terminada = ahora

    try:
        # Todo con LÍMITE: el put también, por si la cola está llena.
        async with asyncio.timeout(config.LIMITE_APAGADO):
            # 2. Un centinela POR worker (clase 21): cada uno termina lo
            #    que tiene entre manos, saca su centinela y se retira solo.
            for _ in app.state.workers:
                await app.state.cola.put(CENTINELA)
            # 3. Esperar a que se retiren.
            await asyncio.gather(*app.state.workers)
        print('Todos los workers se retiraron solos')
    except TimeoutError:
        print(f'Pasaron {config.LIMITE_APAGADO} s: cancelo lo que queda')
        for w in app.state.workers:
            w.cancel()
        await asyncio.gather(*app.state.workers, return_exceptions=True)
        for tarea in estado.tareas.values():
            if tarea.estado == 'ejecutando':
                tarea.estado = 'cancelada'
                tarea.error = 'Cortada por el apagado del servidor'
                tarea.terminada = datetime.now()

    # 4. Volcar el estado. to_thread: escribir a disco bloquea.
    archivo = await asyncio.to_thread(persistencia.volcar)
    print(f'Estado guardado en {archivo}')

    # 5. Cerrar el pool sin esperar a hashes que ya nadie va a usar.
    app.state.pool.shutdown(wait=False, cancel_futures=True)


app = FastAPI(
    title='Plataforma de tareas',
    description='TP2 de Computación II',
    lifespan=ciclo_de_vida,
)
app.include_router(router)
