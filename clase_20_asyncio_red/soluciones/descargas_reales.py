#!/usr/bin/env python3
"""Clase 20 · Ej. 3 (obligatorio): descargas concurrentes con httpx — partes B, C y D.

    python3 descargas_reales.py               # contra un servidor HTTP LOCAL con latencia simulada
    python3 descargas_reales.py --internet    # contra https://example.com (necesita salida a internet)

Por qué un servidor local: así los números no dependen de tu wifi y se puede mostrar
cuántas CONEXIONES TCP abrió cada versión (keep-alive, clase 19). Cada pedido a
/demora/0.3 tarda 0,3 s en responder, como una página "lejana".

Necesita:  pip install httpx requests
"""
import asyncio
import json
import resource
import subprocess
import sys
import time

import httpx

PUERTO = 8765
BASE = f"http://127.0.0.1:{PUERTO}"
LATENCIA = 0.3


# ─────────────────────────── el servidor de prueba (otro proceso) ───────────────────────────
def servidor():
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    conexiones = 0
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"          # keep-alive: una conexión puede llevar varios pedidos

        def setup(self):                       # se llama UNA vez por conexión TCP (no por pedido)
            nonlocal conexiones
            with lock:
                conexiones += 1
            super().setup()

        def do_GET(self):
            nonlocal conexiones
            if self.path.startswith("/demora/"):
                time.sleep(float(self.path.split("/")[2]))
                cuerpo = b"x" * 1256          # ~ lo que pesa example.com
            elif self.path == "/conexiones":   # cuántas conexiones TCP se abrieron (y reinicia)
                with lock:
                    cuerpo, conexiones = json.dumps(conexiones - 1).encode(), 0   # -1: esta misma
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def log_message(self, *a):
            pass

    class Server(ThreadingHTTPServer):
        request_queue_size = 1024              # backlog grande: 200 conexiones de golpe
        daemon_threads = True

    Server(("127.0.0.1", PUERTO), Handler).serve_forever()


# ─────────────────────────── el cliente ───────────────────────────
async def bajar(cliente, url):
    r = await cliente.get(url)
    return url, r.status_code, len(r.content)


async def conexiones_abiertas():
    async with httpx.AsyncClient(trust_env=False) as c:
        return (await c.get(f"{BASE}/conexiones")).json()


async def medir(etiqueta, corrutina, contar=True):
    t0 = time.perf_counter()
    resultado = await corrutina
    dt = time.perf_counter() - t0
    extra = f"   conexiones TCP: {await conexiones_abiertas()}" if contar else ""
    print(f"  {etiqueta:<46} {dt:5.2f}s{extra}")
    return resultado


# Parte B ------------------------------------------------------------------
async def secuencial(urls):
    async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
        return [await bajar(c, u) for u in urls]


async def concurrente(urls, **kw):
    async with httpx.AsyncClient(timeout=10, trust_env=False, **kw) as c:   # UN cliente para todas
        return await asyncio.gather(*(bajar(c, u) for u in urls))


async def un_cliente_por_descarga(urls):
    async def bajar_solo(u):
        async with httpx.AsyncClient(timeout=10, trust_env=False) as c:     # ✗ uno nuevo por pedido
            return await bajar(c, u)
    return await asyncio.gather(*(bajar_solo(u) for u in urls))


async def con_requests(urls):
    import requests                            # sincrónico: bloquea el event loop (clase 19)
    s = requests.Session()
    s.trust_env = False

    async def bajar_mal(u):
        r = s.get(u, timeout=10)               # ← sin await: el loop queda congelado acá
        return u, r.status_code, len(r.content)
    return await asyncio.gather(*(bajar_mal(u) for u in urls))


async def con_requests_en_thread(urls):
    import requests

    async def bajar_en_thread(u):
        r = await asyncio.to_thread(requests.get, u, timeout=10)   # el arreglo si no hay versión async
        return u, r.status_code, len(r.content)
    return await asyncio.gather(*(bajar_en_thread(u) for u in urls))


# Parte C ------------------------------------------------------------------
async def con_semaforo(urls, limite, **kw):
    sem = asyncio.Semaphore(limite)
    async with httpx.AsyncClient(timeout=10, trust_env=False, **kw) as c:
        async def acotada(u):
            async with sem:                    # como mucho `limite` a la vez
                return await bajar(c, u)
        return await asyncio.gather(*(acotada(u) for u in urls))


# Parte D ------------------------------------------------------------------
async def fallos():
    urls = [f"{BASE}/demora/{LATENCIA}"] * 4 + ["http://127.0.0.1:1/nadie-escucha"] + [f"{BASE}/demora/1.0"]
    terminadas = []

    async with httpx.AsyncClient(timeout=10, trust_env=False) as c:
        async def anotada(u):
            r = await bajar(c, u)
            terminadas.append(u)
            return r

        print("\n  D.10) gather normal con una URL inválida:")
        t0 = time.perf_counter()
        try:
            await asyncio.gather(*(anotada(u) for u in urls))
        except httpx.ConnectError as e:
            print(f"     → gather lanzó {type(e).__name__} a los {time.perf_counter() - t0:.2f}s; "
                  f"terminadas hasta ahí: {len(terminadas)} de 5 buenas — los resultados de las demás se PIERDEN")
        await asyncio.sleep(1.2)
        print(f"     → pero las otras NO se cancelaron: 1,2 s después ya terminaron {len(terminadas)} de 5")

        print("  D.11) gather(..., return_exceptions=True):")
        resultados = await asyncio.gather(*(bajar(c, u) for u in urls), return_exceptions=True)
        for r in resultados:
            if isinstance(r, Exception):
                print(f"     ✗ {type(r).__name__}: {r}")
            else:
                print(f"     ✓ {r[1]}  {r[2]} bytes  {r[0]}")


async def main(internet):
    if internet:
        urls = ["https://example.com"] * 10
    else:
        urls = [f"{BASE}/demora/{LATENCIA}"] * 10
    contar = not internet

    print(f"10 descargas de {urls[0]}\n")
    print("Parte B")
    await medir("secuencial (un AsyncClient)", secuencial(urls), contar)
    res = await medir("gather (un AsyncClient reutilizado)", concurrente(urls), contar)
    await medir("gather con un AsyncClient POR descarga", un_cliente_por_descarga(urls), contar)
    await medir("gather con requests adentro de la corrutina", con_requests(urls), contar)
    await medir("gather con requests vía asyncio.to_thread", con_requests_en_thread(urls), contar)
    print(f"  (ejemplo de resultado: {res[0][1]}  {res[0][2]} bytes)")

    print("\nParte C")
    await medir("Semaphore(3)", con_semaforo(urls, 3), contar)
    if internet:
        return

    # 200 URLs con `ulimit -n 64`: cada variante en su propio proceso, para que los sockets que
    # quedan colgados de la que falla no contaminen a la siguiente.
    print("  200 URLs, ulimit -n 64:")
    for variante in ("sin", "con"):
        r = subprocess.run([sys.executable, __file__, "c200", variante], capture_output=True, text=True)
        print(r.stdout, end="")
        print(f"{'':54}conexiones TCP: {await conexiones_abiertas()}")

    print("\nParte D")
    await fallos()


async def doscientas(variante):
    muchas = [f"{BASE}/demora/{LATENCIA}"] * 200
    sin_tope = dict(limits=httpx.Limits(max_connections=None))    # httpx por defecto ya acota a 100
    _, duro = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, duro))       # = `ulimit -n 64`
    try:
        if variante == "sin":
            await medir("   sin semáforo (y sin el tope de httpx)", concurrente(muchas, **sin_tope), False)
        else:
            await medir("   con Semaphore(20)", con_semaforo(muchas, 20, **sin_tope), False)
    except Exception as e:
        raiz = e
        while raiz.__cause__ or raiz.__context__:                # httpx envuelve el error original
            raiz = raiz.__cause__ or raiz.__context__
        print(f"     ✗ {type(e).__name__}: {e}\n       causa real → {type(raiz).__name__}: {raiz}")


if __name__ == "__main__":
    if sys.argv[1:] == ["servidor"]:
        servidor()
    elif sys.argv[1:2] == ["c200"]:
        asyncio.run(doscientas(sys.argv[2]))
    elif "--internet" in sys.argv:
        asyncio.run(main(internet=True))
    else:
        srv = subprocess.Popen([sys.executable, __file__, "servidor"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(0.6)
            asyncio.run(main(internet=False))
        finally:
            srv.terminate()
