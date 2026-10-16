"""Los tres tipos de tarea: descargar, hashear y esperar."""
import asyncio

from app.modelos import Tarea


async def esperar(segundos: float) -> str:
    # asyncio.sleep y NO time.sleep: este cede el loop mientras duerme,
    # time.sleep lo congelaría y nadie más sería atendido.
    await asyncio.sleep(segundos)
    return f'Dormí {segundos} s'


async def ejecutar(tarea: Tarea):
    """Elige qué función corre según el tipo. Devuelve el resultado."""
    if tarea.tipo == 'esperar':
        return await esperar(**tarea.parametros)
    # TODO: descargar (T5) y hashear (T6)
    raise NotImplementedError(f'el tipo {tarea.tipo} todavía no está hecho')
