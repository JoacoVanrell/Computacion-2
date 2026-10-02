#!/usr/bin/env python3
"""Clase 18 · Adicionales: scheduler con PRIORIDADES + detector de tareas EGOÍSTAS.

    python3 scheduler_extras.py

- Prioridades: en vez de una deque (FIFO), un heap ordenado por "turno virtual". Cada tarea avanza
  su turno en 1/peso cada vez que corre → una de peso 3 corre ~3 veces más seguido que una de peso 1.
- Egoístas: se mide cuánto tardó cada reanudación; si pasa el umbral, se avisa (como loop.set_debug(True)).
"""
import heapq
import itertools
import time


def trabajo(nombre, pasos, pausa_cpu=0.0):
    for i in range(pasos):
        t0 = time.monotonic()
        while time.monotonic() - t0 < pausa_cpu:
            pass
        yield f"{nombre}{i}"


def scheduler_prioridades(tareas_con_peso, umbral=0.05):
    """tareas_con_peso: lista de (generador, peso)."""
    desempate = itertools.count()
    cola = [(0.0, next(desempate), gen, peso) for gen, peso in tareas_con_peso]
    heapq.heapify(cola)
    orden = []
    while cola:
        turno, _, gen, peso = heapq.heappop(cola)
        t0 = time.monotonic()
        try:
            orden.append(next(gen))
        except StopIteration:
            continue
        dur = time.monotonic() - t0
        if dur > umbral:
            print(f"  ⚠ tarea egoísta: {orden[-1]} tardó {dur * 1000:.0f} ms sin ceder (umbral {umbral * 1000:.0f} ms)")
        heapq.heappush(cola, (turno + 1 / peso, next(desempate), gen, peso))
    return orden


if __name__ == "__main__":
    orden = scheduler_prioridades([(trabajo("A", 6), 3), (trabajo("b", 6), 1)])
    print("Orden (A tiene peso 3, b peso 1):", " ".join(orden))
    print("\nCon una tarea lenta:")
    scheduler_prioridades([(trabajo("rapida", 3), 1), (trabajo("lenta", 2, pausa_cpu=0.1), 1)])
