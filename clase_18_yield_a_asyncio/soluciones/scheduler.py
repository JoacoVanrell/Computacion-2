#!/usr/bin/env python3
"""Clase 18 · Ej. 2 (OBLIGATORIO): un event loop cooperativo con generadores, desde cero.

    python3 scheduler.py            # corre las partes A, B, C y D con explicación
"""
import heapq
import itertools
import time
from collections import deque


# ═══════════════════ Parte A: intercalado ═══════════════════
def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f"  [{nombre}] paso {i}/{pasos}")
        yield                                   # cedo el control


def scheduler(tareas):
    """Round-robin. Devuelve cuántas veces reanudó tareas (llamadas a next)."""
    pendientes = deque(tareas)
    reanudaciones = 0
    while pendientes:
        t = pendientes.popleft()
        reanudaciones += 1
        try:
            next(t)                             # corre hasta su próximo yield
        except StopIteration:
            continue                            # terminó → no vuelve a la cola
        pendientes.append(t)
    return reanudaciones


def sin_yield(nombre):
    """OJO: sin yield NO es un generador; llamarla la ejecuta entera y devuelve None."""
    print(f"  [{nombre}] soy una función común")


# ═══════════════════ Parte B: la egoísta ═══════════════════
def tarea_egoista(nombre, segundos):
    print(f"  [{nombre}] me pongo a calcular {segundos}s sin ceder…")
    t0 = time.monotonic()
    while time.monotonic() - t0 < segundos:     # ocupada: nunca hace yield adentro
        pass
    print(f"  [{nombre}] listo")
    yield


def tarea_con_hora(nombre, pasos, inicio):
    for i in range(pasos):
        print(f"  [{nombre}] paso {i + 1} a los {time.monotonic() - inicio:.2f}s")
        yield


# ═══════════════════ Parte C/D: tiempo + yield from ═══════════════════
def dormir(segundos):
    """No duerme: CEDE el control diciendo 'no me despiertes antes de este instante'."""
    yield time.monotonic() + segundos


def tarea_lenta(nombre, veces, espera):
    for i in range(veces):
        yield from dormir(espera)               # delega: el yield de dormir() sube hasta el scheduler
        print(f"  [{nombre}] desperté ({i + 1}/{veces})")


def tarea_rota(nombre, espera):
    dormir(espera)                              # sin yield from: crea el generador… y lo tira
    print(f"  [{nombre}] 'dormí'… pero no se suspendió nada")
    yield


def scheduler_con_tiempo(tareas):
    """Cola de prioridad por hora de despertar (heap). Si nadie está listo, el SCHEDULER duerme
    hasta el próximo despertar (en asyncio real esto es select/epoll con timeout)."""
    contador = itertools.count()                # desempate para el heap
    cola = [(0.0, next(contador), t) for t in tareas]
    heapq.heapify(cola)
    while cola:
        cuando, _, t = heapq.heappop(cola)
        espera = cuando - time.monotonic()
        if espera > 0:
            time.sleep(espera)                  # el loop está ocioso: puede dormir (no es una tarea)
        try:
            proximo = next(t)
        except StopIteration:
            continue
        heapq.heappush(cola, (proximo or 0.0, next(contador), t))


if __name__ == "__main__":
    print("── Parte A ──")
    n = scheduler([tarea("A", 3), tarea("B", 2), tarea("C", 4)])
    print(f"  next() llamados: {n}  (= 3+2+4 pasos + 3 llamadas finales que dan StopIteration)")
    print("  Tarea sin yield:")
    r = sin_yield("X")
    print(f"  devolvió {r!r}: se ejecutó al LLAMARLA, no es una tarea → scheduler([r]) daría TypeError")

    print("\n── Parte B: una tarea egoísta en el medio ──")
    t0 = time.monotonic()
    scheduler([tarea_con_hora("A", 3, t0), tarea_egoista("EGO", 1.5), tarea_con_hora("B", 3, t0)])
    print("  → mientras EGO calculaba, A y B estuvieron 1,5 s congeladas: nadie puede sacarle el control.")

    print("\n── Parte C: tres tareas que esperan 0,15 s (3 veces cada una) ──")
    t0 = time.monotonic()
    scheduler_con_tiempo([tarea_lenta(x, 3, 0.15) for x in "ABC"])
    total = time.monotonic() - t0
    print(f"  total {total:.2f}s · secuencial serían 9 × 0,15 = 1,35s → las esperas se SOLAPAN")

    print("\n── Parte D: olvidarse el yield from ──")
    t0 = time.monotonic()
    scheduler_con_tiempo([tarea_rota("R", 1.0)])
    print(f"  tardó {time.monotonic() - t0:.2f}s en vez de 1 s, y no hubo ningún error")
