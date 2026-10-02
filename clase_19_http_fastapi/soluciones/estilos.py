#!/usr/bin/env python3
"""Clase 19 · Ej. 5: async bien, async mal, def común… y un 4to caso: cálculo pesado.

    python3 estilos.py               # levanta el servidor y mide todo solo (necesita uvicorn + httpx)
    python3 estilos.py servidor      # solo el servidor, en el puerto 8000

Cada medición: 3 pedidos simultáneos al endpoint + un /ping lanzado en el medio
(el /ping mide si el EVENT LOOP sigue atendiendo mientras tanto).
"""
import asyncio
import hashlib
import subprocess
import sys
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor

from fastapi import FastAPI

app = FastAPI()
pool_procesos = None


def hash_iterado(n=1_000_000):
    h = b"x"
    for _ in range(n):
        h = hashlib.sha256(h).digest()
    return h.hex()[:12]


@app.get("/ping")
async def ping():
    return "pong"


@app.get("/async-bien")
async def async_bien():
    await asyncio.sleep(1)                 # cede el control
    return "ok"


@app.get("/async-mal")
async def async_mal():
    time.sleep(1)                          # BLOQUEA el loop
    return "ok"


@app.get("/sync")
def sincronico():
    time.sleep(1)                          # def → threadpool, fuera del loop
    return "ok"


@app.get("/cpu-async-mal")
async def cpu_async_mal():
    return hash_iterado()                  # CPU en el loop: congela todo


@app.get("/cpu-def")
def cpu_def():
    return hash_iterado()                  # threadpool: el loop sigue libre, pero los 3 compiten por el GIL


@app.get("/cpu-procesos")
async def cpu_procesos():
    global pool_procesos
    # spawn (o forkserver), NO fork: este proceso ya tiene threads (el threadpool de FastAPI) y hacer
    # fork con threads puede heredar locks tomados → deadlock (clase 8). Fue lo que me pasó con fork.
    pool_procesos = pool_procesos or ProcessPoolExecutor(3, mp_context=multiprocessing.get_context("spawn"))
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(pool_procesos, hash_iterado)   # otro proceso: sin GIL compartido


async def medir(cliente, ruta):
    t0 = time.perf_counter()
    pedidos = [asyncio.create_task(cliente.get(ruta)) for _ in range(3)]
    await asyncio.sleep(0.1)
    tp = time.perf_counter()
    await cliente.get("/ping")
    t_ping = time.perf_counter() - tp
    await asyncio.gather(*pedidos)
    return time.perf_counter() - t0, t_ping


async def medir_todo():
    import httpx
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=60, trust_env=False) as c:
        for _ in range(50):                         # esperar a que levante
            try:
                await c.get("/ping")
                break
            except httpx.ConnectError:
                await asyncio.sleep(0.1)
        await c.get("/cpu-procesos")                # calentar el pool
        print(f"{'endpoint':<15} {'3 pedidos':>10} {'/ping en el medio':>18}")
        for ruta in ("/async-bien", "/async-mal", "/sync", "/cpu-async-mal", "/cpu-def", "/cpu-procesos"):
            total, t_ping = await medir(c, ruta)
            print(f"{ruta:<15} {total:>9.2f}s {t_ping:>17.2f}s")


if __name__ == "__main__":
    if sys.argv[1:] == ["servidor"]:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
    else:
        p = subprocess.Popen([sys.executable, __file__, "servidor"])
        try:
            asyncio.run(medir_todo())
        finally:
            p.terminate()
