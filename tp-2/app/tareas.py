"""Los tres tipos de tarea: descargar, hashear y esperar."""
import asyncio
import hashlib
import time
from concurrent.futures import ProcessPoolExecutor

import httpx

from app import config
from app.modelos import Tarea

# Cuánto esperar como mucho a cada URL. El timeout de la tarea entera va en T7.
TIMEOUT_URL = 10


async def bajar(cliente: httpx.AsyncClient, url: str) -> dict:
    t0 = time.perf_counter()
    r = await cliente.get(url)            # await: mientras espera, el loop atiende a otros
    return {
        'url': url,
        'codigo': r.status_code,
        'bytes': len(r.content),
        'segundos': round(time.perf_counter() - t0, 3),
    }


async def descargar(urls: list[str]) -> list[dict]:
    # UN cliente para todas las URLs: reusa las conexiones (keep-alive, clase 19).
    async with httpx.AsyncClient(timeout=TIMEOUT_URL,
                                 follow_redirects=True) as cliente:
        # gather: todas a la vez, tarda lo que la más lenta (clase 20).
        # return_exceptions=True: una URL rota vuelve como un valor más
        # en la lista, en vez de explotar y perder los resultados de las otras.
        resultados = await asyncio.gather(*(bajar(cliente, u) for u in urls),
                                          return_exceptions=True)
    salida = []
    for url, r in zip(urls, resultados):
        if isinstance(r, Exception):
            salida.append({'url': url, 'error': f'{type(r).__name__}: {r}'})
        else:
            salida.append(r)
    return salida


def calcular_hash(texto: str, iteraciones: int) -> str:
    """CPU-bound puro: ningún await, no le cede el control a nadie.

    Es una función de módulo (def común, no lambda) porque el pool se la
    manda al otro proceso con pickle, y pickle solo sabe mandar funciones
    que se pueden encontrar por su nombre.
    """
    h = texto.encode()
    for _ in range(iteraciones):
        h = hashlib.sha256(h).digest()
    return h.hex()


async def hashear(texto: str, iteraciones: int,
                  pool: ProcessPoolExecutor) -> str:
    if not config.USAR_EXECUTOR:
        # MAL a propósito, solo para la medición 2: calcula dentro del
        # loop y lo congela mientras tanto.
        return calcular_hash(texto, iteraciones)
    # El cálculo corre en otro proceso; el loop solo espera el resultado
    # con await y mientras tanto atiende a los demás.
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool, calcular_hash, texto, iteraciones)


async def esperar(segundos: float) -> str:
    # asyncio.sleep y NO time.sleep: este cede el loop mientras duerme,
    # time.sleep lo congelaría y nadie más sería atendido.
    await asyncio.sleep(segundos)
    return f'Dormí {segundos} s'


async def ejecutar(tarea: Tarea, pool: ProcessPoolExecutor):
    """Elige qué función corre según el tipo. Devuelve el resultado."""
    if tarea.tipo == 'esperar':
        return await esperar(**tarea.parametros)
    if tarea.tipo == 'descargar':
        return await descargar(**tarea.parametros)
    if tarea.tipo == 'hashear':
        return await hashear(**tarea.parametros, pool=pool)
    raise ValueError(f'tipo de tarea desconocido: {tarea.tipo}')
