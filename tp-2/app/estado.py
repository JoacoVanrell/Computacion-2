"""Estado en memoria: el dict de tareas y las estadísticas."""
from app.modelos import Tarea

# OJO: con --workers > 1 cada proceso de uvicorn tendría el suyo.
tareas: dict[int, Tarea] = {}
proximo_id = 0


def nuevo_id() -> int:
    global proximo_id
    proximo_id += 1
    return proximo_id
