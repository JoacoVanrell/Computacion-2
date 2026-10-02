#!/usr/bin/env python3
"""Clase 20 · Adicionales: el chat de la clase 17 (y los comandos de la 16) con asyncio,
con apagado ordenado DE VERDAD ante SIGTERM/SIGINT.

    python3 chat_async.py              # servidor en el puerto 9020  →  nc localhost 9020
    python3 chat_async.py --test       # levanta el servidor, conecta 3 clientes, chatea y le manda SIGTERM

Comandos:  /nick NOMBRE · /quien · /cuantos · /salir   (cualquier otra línea se reenvía a todos)

⚠️ Lo que descubrí probando eco_async.py: desde Python 3.12, salir del `async with servidor:`
espera a que TODAS las conexiones terminen. Con un `nc` abierto, el SIGTERM imprime "Cerrando"
pero el proceso NO termina. Para el TP2 hace falta cerrar los clientes a mano (acá) o
`servidor.close_clients()` (Python 3.13).
"""
import asyncio
import signal
import sys

PUERTO = 9020
GRACIA = 2.0                           # segundos para que los clientes se despidan antes de cortarlos

clientes = {}                          # writer → nick      (sin Lock: ver comentario en difundir)
tareas = set()                         # las tasks de cada cliente, para poder cancelarlas al cerrar


async def difundir(texto, menos=None):
    # Recorro una COPIA: mientras espero el drain() de uno, otro cliente puede entrar o salir
    # (es un await en el medio de la "sección crítica" → la regla de la clase).
    for w in list(clientes):
        if w is menos or w.is_closing():
            continue
        w.write(texto.encode())
        try:
            async with asyncio.timeout(1):   # un cliente lento no frena a todos para siempre
                await w.drain()
        except (TimeoutError, ConnectionError):
            w.close()


async def atender(reader, writer):
    tareas.add(asyncio.current_task())
    nick = "anon{}".format(writer.get_extra_info("peername")[1])
    clientes[writer] = nick
    writer.write(f"Bienvenido, {nick}. Comandos: /nick /quien /cuantos /salir\n".encode())
    await difundir(f"* {nick} entró\n", menos=writer)
    try:
        while True:
            try:
                async with asyncio.timeout(300):          # siempre timeout: 5 min sin hablar → afuera
                    linea = await reader.readline()
            except TimeoutError:
                writer.write(b"* timeout por inactividad\n")
                break
            if not linea:
                break
            texto = linea.decode(errors="replace").strip()
            if texto.startswith("/nick "):
                viejo, clientes[writer] = clientes[writer], texto[6:].strip()[:20] or clientes[writer]
                await difundir(f"* {viejo} ahora es {clientes[writer]}\n")
            elif texto == "/quien":
                writer.write(("* conectados: " + ", ".join(clientes.values()) + "\n").encode())
            elif texto == "/cuantos":
                writer.write(f"* {len(clientes)} conectados\n".encode())
            elif texto == "/salir":
                break
            elif texto:
                await difundir(f"[{clientes[writer]}] {texto}\n", menos=writer)
            await writer.drain()
    except asyncio.CancelledError:
        writer.write(b"* el servidor se cierra\n")
        raise                                             # SIEMPRE relanzarla
    except ConnectionError:
        pass
    finally:
        nick = clientes.pop(writer, nick)
        tareas.discard(asyncio.current_task())
        writer.close()
        await difundir(f"* {nick} salió\n")


async def main():
    srv = await asyncio.start_server(atender, "0.0.0.0", PUERTO, reuse_address=True)
    print(f"chat en el puerto {PUERTO} (un hilo, una Task por cliente)", flush=True)

    cerrar = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, cerrar.set)           # se ejecuta ENTRE tareas: momento seguro

    await cerrar.wait()
    print(f"cerrando: no acepto más conexiones; {len(tareas)} clientes tienen {GRACIA}s", flush=True)
    srv.close()                                           # 1) dejar de aceptar
    await difundir(f"* el servidor se cierra en {GRACIA:.0f} s\n")
    _, pendientes = await asyncio.wait(tareas, timeout=GRACIA) if tareas else (None, set())
    for t in pendientes:                                  # 2) a los que siguen, cancelarlos
        t.cancel()
    await asyncio.gather(*pendientes, return_exceptions=True)
    await srv.wait_closed()                               # 3) ahora sí termina enseguida
    print(f"listo: {len(pendientes)} clientes cortados después de la gracia", flush=True)


async def prueba():
    import time
    srv = await asyncio.create_subprocess_exec(sys.executable, "-u", __file__, stdout=asyncio.subprocess.PIPE)
    print("servidor:", (await srv.stdout.readline()).decode().strip())

    async def cliente(nick):
        r, w = await asyncio.open_connection("127.0.0.1", PUERTO)
        await r.readline()                                # bienvenida
        w.write(f"/nick {nick}\n".encode())
        await w.drain()
        return r, w

    (ra, wa), (rb, wb), (rc, wc) = [await cliente(n) for n in ("ana", "beto", "caro")]
    await asyncio.sleep(0.2)
    wa.write(b"hola a todos\n/quien\n")
    await wa.drain()
    await asyncio.sleep(0.3)

    async def lo_que_llego(r):
        datos = b""
        try:
            while True:
                async with asyncio.timeout(0.2):
                    linea = await r.readline()
                if not linea:
                    break
                datos += linea
        except TimeoutError:
            pass
        return datos.decode()

    print("--- lo que vio beto ---\n" + await lo_que_llego(rb), end="")
    print("--- lo que vio ana ---\n" + await lo_que_llego(ra), end="")
    wc.close()                                            # caro se va: el resto se entera
    await asyncio.sleep(0.2)
    print("--- beto, después de que caro cerró ---\n" + await lo_que_llego(rb), end="")

    t0 = time.perf_counter()
    srv.send_signal(signal.SIGTERM)                       # ana y beto siguen conectados
    print("--- SIGTERM con 2 clientes conectados ---")
    print("ana recibe:\n" + await lo_que_llego(ra), end="")
    while (linea := await srv.stdout.readline()):
        print("servidor:", linea.decode().strip())
    await srv.wait()
    print(f"el proceso terminó solo en {time.perf_counter() - t0:.1f}s (rc={srv.returncode}) "
          "aunque ana y beto nunca cerraron")


if __name__ == "__main__":
    asyncio.run(prueba() if "--test" in sys.argv else main())
