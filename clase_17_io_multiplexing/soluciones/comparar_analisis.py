#!/usr/bin/env python3
"""Clase 17 · Ej. 3 (OBLIGATORIO): comparar select / poll / epoll… y sacar las conclusiones con números.

    python3 comparar_analisis.py                 # tabla con 3 activos + tabla con la MITAD activos + límite de select
    python3 comparar_analisis.py 10 50 100       # Parte C: con pocas conexiones

Igual que comparar.py del profe, pero además:
  - calcula el factor de crecimiento de cada uno entre la primera y la última cantidad
  - repite con ACTIVOS = n/2 (pregunta 7)
  - encuentra el NÚMERO de fd exacto en el que select() empieza a fallar
"""
import select
import socket
import sys
import time

REPETICIONES = 200


def pares(n):
    lec, esc = [], []
    for _ in range(n):
        a, b = socket.socketpair()
        lec.append(a)
        esc.append(b)
    return lec, esc


def medir(fn):
    t0 = time.perf_counter()
    for _ in range(REPETICIONES):
        fn()
    return (time.perf_counter() - t0) / REPETICIONES * 1e6        # microsegundos por llamada


def una_fila(n, activos):
    lec, esc = pares(n)
    try:
        for w in esc[:activos]:
            w.send(b"x")
        try:
            t_sel = medir(lambda: select.select(lec, [], [], 0))
        except ValueError:
            t_sel = None
        p = select.poll()
        for s in lec:
            p.register(s, select.POLLIN)
        t_poll = medir(lambda: p.poll(0))
        ep = select.epoll()
        for s in lec:
            ep.register(s.fileno(), select.EPOLLIN)
        t_ep = medir(lambda: ep.poll(0))
        ep.close()
        return t_sel, t_poll, t_ep, max(s.fileno() for s in lec)
    finally:
        for s in lec + esc:
            s.close()


def tabla(cantidades, activos_fn, titulo):
    print(f"\n{titulo}")
    print(f"{'conexiones':>10} {'activos':>8} {'fd máx':>7} {'select µs':>10} {'poll µs':>9} {'epoll µs':>9}")
    filas = []
    for n in cantidades:
        a = activos_fn(n)
        s, p, e, fdmax = una_fila(n, a)
        filas.append((n, s, p, e))
        sel = f"{s:10.1f}" if s is not None else f"{'FALLA':>10}"
        print(f"{n:>10} {a:>8} {fdmax:>7} {sel} {p:9.1f} {e:9.1f}")
    (n0, _, p0, e0), (n1, _, p1, e1) = filas[0], filas[-1]
    print(f"  conexiones ×{n1 / n0:.0f} → poll ×{p1 / p0:.0f} · epoll ×{e1 / e0:.1f}")
    return filas


def limite_select():
    """Abre sockets hasta que el fd pase 1023 y prueba select() con UN SOLO socket."""
    abiertos = []
    try:
        while True:
            s = socket.socket()
            abiertos.append(s)
            try:
                select.select([s], [], [], 0)
            except ValueError:
                return s.fileno(), len(abiertos)
    finally:
        for s in abiertos:
            s.close()


if __name__ == "__main__":
    cantidades = [int(x) for x in sys.argv[1:]] or [100, 500, 1000, 2000, 5000]
    tabla(cantidades, lambda n: 3, "A) 3 sockets activos, el resto ociosos (caso real de un servidor)")
    if not sys.argv[1:]:
        tabla(cantidades, lambda n: n // 2, "B) la MITAD de los sockets activos")
        fd, n = limite_select()
        print(f"\nselect() falla con UN solo socket de fd = {fd} (FD_SETSIZE = 1024: fds válidos 0..1023)")
