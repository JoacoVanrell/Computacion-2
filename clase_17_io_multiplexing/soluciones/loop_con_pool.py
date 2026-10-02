#!/usr/bin/env python3
"""Clase 17 · Ej. 7: el costo del hilo único… y cómo resolverlo SIN abandonar el event loop.

    python3 loop_con_pool.py demo        # mide: trabajo pesado en el loop vs mandado a un pool

Regla de oro: NADA que tarde puede correr en el hilo del loop. Lo pesado va a un pool de PROCESOS
(es CPU-bound) y, cuando termina, el resultado vuelve al loop. ¿Cómo se entera el loop, que está
dormido en select()? Con un socketpair (el "self-pipe" de la clase 6): el callback del Future escribe
1 byte en un extremo, y ese extremo está registrado en el selector → el loop se despierta.
(Esto es, a mano, lo que asyncio hace con run_in_executor.)
"""
import hashlib
import queue
import selectors
import socket
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor


def trabajo_pesado(datos):
    h = datos
    for _ in range(3_000_000):          # ~1-2 s de CPU
        h = hashlib.sha256(h).digest()
    return h.hex()[:16]


def servidor(puerto_q, con_pool):
    sel = selectors.DefaultSelector()
    srv = socket.create_server(("127.0.0.1", 0))
    srv.setblocking(False)
    sel.register(srv, selectors.EVENT_READ, "aceptar")
    despertador_r, despertador_w = socket.socketpair()
    despertador_r.setblocking(False)
    sel.register(despertador_r, selectors.EVENT_READ, "despertar")
    terminados = queue.Queue()                 # (conn, resultado) que vienen del pool
    pool = ProcessPoolExecutor(2) if con_pool else None
    puerto_q.put(srv.getsockname()[1])

    def cuando_termina(conn, fut):             # corre en un hilo interno del pool, NO en el loop
        terminados.put((conn, fut.result()))
        despertador_w.send(b"!")               # despertá al loop

    while True:
        for clave, _ in sel.select():
            if clave.data == "aceptar":
                conn, _ = srv.accept()
                conn.setblocking(False)
                sel.register(conn, selectors.EVENT_READ, "cliente")
            elif clave.data == "despertar":
                despertador_r.recv(1024)
                while not terminados.empty():
                    conn, res = terminados.get()
                    conn.sendall(res.encode())    # respuesta corta: no hace falta buffer de salida
            else:
                conn = clave.fileobj
                datos = conn.recv(100)
                if not datos:
                    sel.unregister(conn)
                    conn.close()
                elif datos.strip() == b"PING":
                    conn.sendall(b"PONG")          # respuesta instantánea
                elif pool:
                    fut = pool.submit(trabajo_pesado, datos)
                    fut.add_done_callback(lambda f, c=conn: cuando_termina(c, f))
                else:
                    conn.sendall(trabajo_pesado(datos).encode())   # ← congela el loop


def demo():
    for con_pool in (False, True):
        q = queue.Queue()
        threading.Thread(target=servidor, args=(q, con_pool), daemon=True).start()
        puerto = q.get()
        pesado = socket.create_connection(("127.0.0.1", puerto))
        rapido = socket.create_connection(("127.0.0.1", puerto))
        time.sleep(0.2)
        t0 = time.perf_counter()
        pesado.sendall(b"calcula")
        time.sleep(0.05)                          # el pesado llega primero
        rapido.sendall(b"PING")
        rapido.recv(10)
        t_ping = time.perf_counter() - t0
        pesado.recv(100)
        t_pesado = time.perf_counter() - t0
        print(f"{'con pool' if con_pool else 'sin pool':<9} PING respondido a los {t_ping:.2f}s · "
              f"cálculo pesado a los {t_pesado:.2f}s")


if __name__ == "__main__":
    demo()
