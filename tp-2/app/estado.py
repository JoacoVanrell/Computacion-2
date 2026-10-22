"""Estado en memoria: el dict de tareas y las estadísticas."""
import asyncio

from app.modelos import Tarea

# OJO: con --workers > 1 cada proceso de uvicorn tendría el suyo.
tareas: dict[int, Tarea] = {}
proximo_id = 0

# Las Task de las tareas que se están ejecutando ahora, por id.
# El DELETE busca acá la Task para cancelarla.
en_curso: dict[int, asyncio.Task] = {}


def nuevo_id() -> int:
    global proximo_id
    proximo_id += 1
    return proximo_id
