#!/usr/bin/env python3
"""Clase 10 · Ej. 2 y 3: el GIL en acción. Threads SÍ ayudan con I/O, NO con CPU.

    python3 gil_io_vs_cpu.py
"""
import sys
import threading
import time
from multiprocessing import Pool


def io_bound(_=None):
    time.sleep(0.5)                  # esperar (red/disco): el thread SUELTA el GIL mientras espera


def cpu_bound(_=None):
    total = 0
    for i in range(6_000_000):       # bytecode Python puro: NECESITA el GIL todo el tiempo
        total += i
    return total


def con_threads(f, n):
    hs = [threading.Thread(target=f) for _ in range(n)]
    t0 = time.perf_counter()
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    return time.perf_counter() - t0


def secuencial(f, n):
    t0 = time.perf_counter()
    for _ in range(n):
        f()
    return time.perf_counter() - t0


def con_procesos(f, n):
    t0 = time.perf_counter()
    with Pool(n) as p:
        p.map(f, range(n))
    return time.perf_counter() - t0


if __name__ == "__main__":
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"Python {sys.version.split()[0]} — GIL {'ACTIVO' if gil else 'DESACTIVADO (free-threaded)'}\n")
    N = 4
    for nombre, f in (("I/O-bound", io_bound), ("CPU-bound", cpu_bound)):
        s, t = secuencial(f, N), con_threads(f, N)
        linea = f"{nombre}: secuencial {s:.2f}s · {N} threads {t:.2f}s ({s / t:.1f}x)"
        if f is cpu_bound:
            p = con_procesos(f, N)
            linea += f" · {N} procesos {p:.2f}s ({s / p:.1f}x)"
        print(linea)
