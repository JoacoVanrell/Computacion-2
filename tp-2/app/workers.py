"""Bucle del worker: get -> ejecutar con timeout -> task_done."""
# OJO: el orden de los except importa. TimeoutError y CancelledError van
# antes que Exception. CancelledError ni siquiera es un Exception (hereda
# de BaseException), así que el except Exception no la atraparía nunca.
import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime

from app import estado
from app.tareas import ejecutar


async def worker(cola: asyncio.Queue, wid: int, pool: ProcessPoolExecutor):
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

            # El trabajo corre en su PROPIA Task, no en el worker: así el
            # DELETE puede cancelar esa Task y el worker sigue vivo.
            trabajo = asyncio.create_task(ejecutar(tarea, pool))
            estado.en_curso[tarea_id] = trabajo

            # asyncio.timeout: si se pasa del tiempo, cancela el await de
            # adentro (y con él la Task) y lanza TimeoutError.
            async with asyncio.timeout(tarea.timeout):
                tarea.resultado = await trabajo

            tarea.estado = 'completada'
            tarea.terminada = datetime.now()
            print(f'worker {wid}: tarea {tarea_id} completada')

        except TimeoutError:
            # La frenó el sistema, no el usuario: fallida, no cancelada.
            tarea.estado = 'fallida'
            tarea.error = f'Timeout: tardó más de {tarea.timeout} s'
            tarea.terminada = datetime.now()
            print(f'worker {wid}: tarea {tarea_id} fallida por timeout')

        except asyncio.CancelledError:
            if tarea.estado != 'cancelada':
                # No fue un DELETE: me están cancelando a MÍ (se apaga el
                # servidor). Hay que relanzarla siempre (clase 20).
                raise
            # Fue un DELETE: el estado ya lo puso el endpoint. Sigo vivo.
            print(f'worker {wid}: tarea {tarea_id} cancelada en ejecución')

        except Exception as e:
            # La tarea falló, pero el worker sigue vivo para la próxima.
            tarea.estado = 'fallida'
            tarea.error = f'{type(e).__name__}: {e}'
            tarea.terminada = datetime.now()
            print(f'worker {wid}: tarea {tarea_id} fallida ({tarea.error})')

        finally:
            estado.en_curso.pop(tarea_id, None)   # ya no se está ejecutando
            cola.task_done()      # SIEMPRE: bien, con error o con el continue
