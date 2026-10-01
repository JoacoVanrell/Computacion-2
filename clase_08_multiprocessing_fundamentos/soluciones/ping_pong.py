#!/usr/bin/env python3
"""Clase 8 · Ej. 4: ping-pong padre ↔ hijo con multiprocessing.Pipe (bidireccional)."""
from multiprocessing import Pipe, Process

RONDAS = 5


def hijo(conn):
    for _ in range(RONDAS):
        msg = conn.recv()                      # bloquea hasta que el padre mande
        print(f"   hijo  recibió {msg!r}")
        conn.send(f"pong {msg.split()[1]}")
    conn.close()


if __name__ == "__main__":
    lado_padre, lado_hijo = Pipe()             # duplex=True por defecto: los dos extremos mandan y reciben
    p = Process(target=hijo, args=(lado_hijo,))
    p.start()
    lado_hijo.close()                          # el padre no usa ese extremo (mismo principio que os.pipe)
    for i in range(1, RONDAS + 1):
        lado_padre.send(f"ping {i}")
        print(f"padre recibió {lado_padre.recv()!r}")
    p.join()
