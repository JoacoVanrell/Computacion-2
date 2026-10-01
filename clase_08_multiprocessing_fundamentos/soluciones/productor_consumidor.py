#!/usr/bin/env python3
"""Clase 8 · Ej. 3: productor-consumidor con multiprocessing.Queue (versión con VARIOS consumidores).

    python3 productor_consumidor.py --items 10 --consumidores 3

Detalle clave: con K consumidores hay que mandar K "píldoras venenosas" (None),
una para cada uno. Si mandás una sola, termina un consumidor y los otros se quedan
bloqueados en get() para siempre.
"""
import argparse
import os
import random
import time
from multiprocessing import Process, Queue

FIN = None   # centinela ("poison pill")


def productor(q, n, k_consumidores):
    for i in range(n):
        item = {"id": i, "valor": random.randint(1, 100)}
        q.put(item)                                   # se serializa con pickle
        print(f"[prod] produje {item}")
        time.sleep(0.05)
    for _ in range(k_consumidores):
        q.put(FIN)


def consumidor(q, cid, resultados):
    procesados = 0
    while True:
        item = q.get()                                # BLOQUEA hasta que haya algo
        if item is FIN:
            break
        time.sleep(random.uniform(0.05, 0.2))         # "procesar"
        resultados.put((cid, item["id"], item["valor"] ** 2))
        procesados += 1
    print(f"[cons {cid} PID {os.getpid()}] terminé, procesé {procesados}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--items", type=int, default=10)
    p.add_argument("--consumidores", type=int, default=2)
    a = p.parse_args()

    tareas, resultados = Queue(), Queue()
    prod = Process(target=productor, args=(tareas, a.items, a.consumidores))
    cons = [Process(target=consumidor, args=(tareas, i, resultados)) for i in range(a.consumidores)]
    for pr in [prod, *cons]:
        pr.start()

    # leer los resultados ANTES de join(): un proceso que puso cosas en una Queue
    # no termina hasta que esos datos se vacíen del pipe (si hacés join primero → posible deadlock)
    salida = [resultados.get() for _ in range(a.items)]
    for pr in [prod, *cons]:
        pr.join()

    print(f"\n{len(salida)} resultados; por consumidor:",
          {c: sum(1 for x in salida if x[0] == c) for c in range(a.consumidores)})
