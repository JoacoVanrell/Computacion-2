#!/usr/bin/env python3
"""Clase 8 · Ej. 5: cuánto cuesta crear 100 procesos con fork, forkserver y spawn.

    python3 fork_vs_spawn.py --n 100
"""
import argparse
import multiprocessing as mp
import time


def nada():
    pass


def medir(metodo, n):
    ctx = mp.get_context(metodo)       # contexto: no cambia el método global del programa
    t0 = time.perf_counter()
    ps = [ctx.Process(target=nada) for _ in range(n)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    return time.perf_counter() - t0


if __name__ == "__main__":             # imprescindible: spawn RE-IMPORTA este archivo en cada hijo
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    n = ap.parse_args().n
    base = None
    for metodo in ("fork", "forkserver", "spawn"):
        t = medir(metodo, n)
        base = base or t
        print(f"{metodo:<11} {t:7.3f} s   ({t / n * 1000:6.2f} ms por proceso, {t / base:4.1f}× fork)")
