"""Bucle del worker: get -> ejecutar con timeout -> task_done."""
import asyncio
from datetime import datetime

from app import estado
from app.tareas import ejecutar


async def worker(cola: asyncio.Queue, wid: int):
    """Bucle infinito: saca ids de la cola hasta que lo cancelen.

    Por la cola viaja solo el id; la tarea vive en estado.tareas.
    """
    while True:
        tarea_id = await cola.get()
        tarea = estado.tareas[tarea_id]
        try:
            if tarea.estado == 'cancelada':
                # La cancelaron mientras esperaba en la fila: pasa de largo.
                print(f'worker {wid}: tarea {tarea_id} cancelada, la salteo')
                continue

            tarea.estado = 'ejecutando'
            tarea.iniciada = datetime.now()
            print(f'worker {wid}: ejecuto la tarea {tarea_id} ({tarea.tipo})')

            tarea.resultado = await ejecutar(tarea)     # TODO (T7): timeout

            tarea.estado = 'completada'
            tarea.terminada = datetime.now()
            print(f'worker {wid}: tarea {tarea_id} completada')

        except Exception as e:
            # La tarea falló, pero el worker sigue vivo para la próxima.
            tarea.estado = 'fallida'
            tarea.error = f'{type(e).__name__}: {e}'
            tarea.terminada = datetime.now()
            print(f'worker {wid}: tarea {tarea_id} fallida ({tarea.error})')

        finally:
            cola.task_done()      # SIEMPRE: bien, con error o con el continue
