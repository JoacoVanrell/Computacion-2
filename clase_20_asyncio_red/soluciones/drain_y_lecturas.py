#!/usr/bin/env python3
"""Clase 20 · Ej. 2: las cuatro formas de leer + para qué sirve drain() (backpressure).

    python3 drain_y_lecturas.py            # todo
    python3 drain_y_lecturas.py lecturas   # solo 2.2
    python3 drain_y_lecturas.py drain      # solo 2.1 (con y sin drain, cada uno en su proceso)

2.1: un cliente "malo" manda 100 MB a un servidor ECO y NUNCA lee la respuesta.
     - SIN drain(): el servidor sigue leyendo y acumulando el eco en su buffer de escritura → la memoria crece.
     - CON drain(): cuando el buffer pasa el umbral (64 KiB), drain() suspende al handler → deja de leer →
       se llenan los buffers del kernel → TCP frena al cliente (control de flujo de punta a punta).
"""
import asyncio
import socket
import subprocess
import sys
import time

MB = 1024 * 1024


# ─────────────────────────── 2.2 Las formas de leer ───────────────────────────
async def lecturas():
    async def servidor_que_manda(reader, writer):
        writer.write(b"hola\nmundo\n")
        await writer.drain()
        writer.close()                       # cierra enseguida: así se ve qué pasa al llegar al final

    srv = await asyncio.start_server(servidor_que_manda, "127.0.0.1", 0)
    puerto = srv.sockets[0].getsockname()[1]

    async def probar(descripcion, como_leer):
        reader, writer = await asyncio.open_connection("127.0.0.1", puerto)
        await asyncio.sleep(0.05)            # que ya haya llegado todo
        try:
            resultado = await como_leer(reader)
            print(f"  {descripcion:<32} → {resultado!r}")
        except Exception as e:
            print(f"  {descripcion:<32} → {type(e).__name__}: {e}  (partial={e.partial!r})")
        writer.close()
        await writer.wait_closed()

    print("El servidor manda b'hola\\nmundo\\n' y cierra:\n")
    await probar("read(100)", lambda r: r.read(100))
    await probar("readline()", lambda r: r.readline())
    await probar("readexactly(4)", lambda r: r.readexactly(4))
    await probar("readuntil(b'\\n')", lambda r: r.readuntil(b"\n"))
    await probar("readexactly(100)", lambda r: r.readexactly(100))

    async def leer_hasta_el_final(r):
        lecturas = []
        while True:
            d = await r.read(100)
            lecturas.append(d)
            if not d:                        # b'' = el otro lado cerró (igual que recv() en la clase 13)
                return lecturas
    await probar("read() en bucle hasta el final", leer_hasta_el_final)

    async def dos_lineas_y_una_mas(r):
        return [await r.readline() for _ in range(3)]   # la 3ra: b'' (EOF), no excepción
    await probar("readline() × 3", dos_lineas_y_una_mas)

    srv.close()
    await srv.wait_closed()


# ─────────────────────────── 2.1 drain() ───────────────────────────
def rss_mb():
    with open("/proc/self/status") as f:
        for linea in f:
            if linea.startswith("VmRSS"):
                return int(linea.split()[1]) / 1024


async def experimento_drain(con_drain):
    max_buffer = 0

    async def eco(reader, writer):
        nonlocal max_buffer
        try:
            while True:
                datos = await reader.read(64 * 1024)
                if not datos or writer.is_closing():
                    break
                writer.write(datos)
                max_buffer = max(max_buffer, writer.transport.get_write_buffer_size())
                if con_drain:
                    await writer.drain()     # ← la única diferencia
        except ConnectionError:
            pass                             # el cliente cortó con datos sin leer → RST
        writer.transport.abort()             # descartar lo que quedó en el buffer

    srv = await asyncio.start_server(eco, "127.0.0.1", 0)
    puerto = srv.sockets[0].getsockname()[1]
    rss_inicial = rss_mb()

    # el cliente malo es OTRO proceso: un socket bloqueante que manda 100 MB y nunca lee
    t0 = time.perf_counter()
    cliente = await asyncio.create_subprocess_exec(sys.executable, __file__, "_cliente", str(puerto),
                                                   stdout=asyncio.subprocess.PIPE)
    enviados = int((await cliente.stdout.read()).decode() or 0)
    await cliente.wait()
    dt = time.perf_counter() - t0
    rss_final = rss_mb()
    await asyncio.sleep(0.2)
    srv.close()
    etiqueta = "CON drain()" if con_drain else "SIN drain()"
    print(f"  {etiqueta}: el cliente mandó {enviados:3d} MB en {dt:4.1f}s · "
          f"buffer de escritura máx. del servidor: {max_buffer / MB:6.1f} MB · "
          f"memoria del servidor: +{rss_final - rss_inicial:4.0f} MB")


def cliente_malo(puerto):
    s = socket.create_connection(("127.0.0.1", puerto))
    s.settimeout(2)                          # si TCP lo frena más de 2 s seguidos, abandona
    bloque = b"x" * MB
    enviados = 0
    try:
        for _ in range(100):
            s.sendall(bloque)
            enviados += 1
    except socket.timeout:
        pass
    print(enviados)
    s.close()


if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que == "_cliente":
        cliente_malo(int(sys.argv[2]))
        sys.exit()
    if que == "_drain":
        asyncio.run(experimento_drain(sys.argv[2] == "si"))
        sys.exit()
    if que in ("todo", "lecturas"):
        print("=== 2.2 Las formas de leer ===")
        asyncio.run(lecturas())
    if que in ("todo", "drain"):
        print("\n=== 2.1 Cliente que manda 100 MB y nunca lee ===")
        for modo in ("no", "si"):            # cada uno en un proceso limpio, para medir la memoria bien
            subprocess.run([sys.executable, __file__, "_drain", modo])
