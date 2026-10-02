#!/usr/bin/env python3
"""Clase 18 · Ej. 3, 4 y 5: el puente a async/await y asyncio de verdad, con mediciones.

    python3 asyncio_equivalente.py
"""
import asyncio
import http.server
import threading
import time
import urllib.request


async def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f"  [{nombre}] paso {i}/{pasos}")
        await asyncio.sleep(0)                 # ceder el control (como el yield pelado)


async def dormir_y_devolver(nombre, seg):
    await asyncio.sleep(seg)
    print(f"  terminó {nombre} ({seg}s)")
    return nombre


async def un_segundo():
    await asyncio.sleep(1)


async def main():
    print("── 4.1: el scheduler de la parte A, con asyncio ──")
    await asyncio.gather(tarea("A", 3), tarea("B", 2), tarea("C", 4))

    print("\n── 4.3: orden de terminación vs orden de resultados ──")
    res = await asyncio.gather(dormir_y_devolver("a", 0.3), dormir_y_devolver("b", 0.1), dormir_y_devolver("c", 0.2))
    print(f"  gather devolvió {res}  ← en el orden en que se PASARON, no en el que terminaron")

    t0 = time.perf_counter()
    await asyncio.gather(un_segundo(), un_segundo(), un_segundo())
    t_gather = time.perf_counter() - t0
    t0 = time.perf_counter()
    for f in (un_segundo, un_segundo, un_segundo):
        await f()
    t_for = time.perf_counter() - t0
    print(f"  gather de 3 × 1s: {t_gather:.2f}s · for con await uno por uno: {t_for:.2f}s")


def ej3_puente():
    print("── Ej. 3: una corrutina tiene .send() ──")

    async def f():
        return 99
    c = f()
    print(f"  type(f()) = {type(c).__name__} · hasattr(send) = {hasattr(c, 'send')}")
    try:
        c.send(None)
    except StopIteration as e:
        print(f"  c.send(None) → StopIteration con value = {e.value}  (igual que el return de un generador)")


def ej4_2_crear_no_es_ejecutar():
    print("\n── 4.2: crear no es ejecutar ──")

    async def saludar():
        print("  hola")
    c = saludar()                               # no imprime nada: solo crea el objeto corrutina
    print(f"  saludar() devolvió {type(c).__name__} y no imprimió nada")
    c.close()                                   # (si no, Python avisa: 'coroutine was never awaited')
    asyncio.run(saludar())


def ej5_bloqueo():
    print("\n── 5.1: encontrar el bloqueo (servidor local que tarda 0,5 s por respuesta) ──")

    class Lento(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(0.5)
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Lento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"

    async def bajar_mal():
        return urllib.request.urlopen(url).read()          # BLOQUEANTE: congela el loop

    async def bajar_bien():
        return await asyncio.to_thread(lambda: urllib.request.urlopen(url).read())   # a un thread

    for nombre, fn in (("urllib directo", bajar_mal), ("asyncio.to_thread", bajar_bien)):
        t0 = time.perf_counter()

        async def cinco():
            await asyncio.gather(*(fn() for _ in range(5)))
        asyncio.run(cinco())
        print(f"  5 descargas con {nombre:<18}: {time.perf_counter() - t0:.2f}s")
    srv.shutdown()


if __name__ == "__main__":
    ej3_puente()
    ej4_2_crear_no_es_ejecutar()
    asyncio.run(main())
    t0 = time.perf_counter()
    asyncio.run(un_segundo())
    asyncio.run(un_segundo())
    print(f"\n── 4.1 (3): asyncio.run() dos veces SEGUIDAS funciona ({time.perf_counter() - t0:.1f}s): cada una crea y cierra su loop.")

    async def adentro():
        c = un_segundo()
        try:
            asyncio.run(c)
        except RuntimeError as e:
            c.close()
            print(f"   Pero ADENTRO de una corrutina: RuntimeError: {e}")
    asyncio.run(adentro())
    ej5_bloqueo()
