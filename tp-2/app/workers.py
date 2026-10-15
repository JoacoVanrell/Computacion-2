"""Bucle del worker: get -> ejecutar con timeout -> task_done."""
import asyncio

from app import estado


async def worker(cola: asyncio.Queue, wid: int):
    """Bucle infinito: saca ids de la cola hasta que lo cancelen.

    Por la cola viaja solo el id; la tarea vive en estado.tareas.
    """
    while True:
        tarea_id = await cola.get()
        try:
            tarea = estado.tareas[tarea_id]
            if tarea.estado == 'cancelada':
                # La cancelaron mientras esperaba en la fila: pasa de largo.
                print(f'worker {wid}: tarea {tarea_id} cancelada, la salteo')
                continue
            print(f'worker {wid}: tomé la tarea {tarea_id} ({tarea.tipo})')
            # TODO (T3 2/2): estados reales y ejecutar la tarea
        finally:
            cola.task_done()      # SIEMPRE, también con el continue
