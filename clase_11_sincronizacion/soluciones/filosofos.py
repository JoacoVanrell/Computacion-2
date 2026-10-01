#!/usr/bin/env python3
"""Clase 11 · Ej. 7: filósofos comensales — del deadlock a dos soluciones, y la comparación.

    python3 filosofos.py ingenuo          # Parte A con Barrier: se cuelga SIEMPRE (lo detectamos con timeout)
    python3 filosofos.py ingenuo --sin-barrera --corridas 10   # ¿cuántas veces se cuelga sin forzarlo?
    python3 filosofos.py jerarquia        # Parte B
    python3 filosofos.py semaforo         # Parte C
    python3 filosofos.py comparar         # Parte D: tiempos y cuántas veces comió cada uno
"""
import argparse
import random
import threading
import time

NUM = 5


def correr(estrategia, comidas=3, usar_barrera=True, timeout=3.0, duracion=None):
    """Devuelve (se_colgo, segundos, comidas_por_filosofo)."""
    tenedores = [threading.Lock() for _ in range(NUM)]
    barrera = threading.Barrier(NUM, timeout=timeout)     # timeout para poder salir del deadlock
    comedor = threading.Semaphore(NUM - 1)
    comio = [0] * NUM
    hasta = time.perf_counter() + duracion if duracion else None

    def comer(i):
        time.sleep(random.uniform(0.001, 0.01))
        comio[i] += 1                                      # cada filósofo toca SOLO su casillero

    def filosofo(i):
        izq, der = i, (i + 1) % NUM
        for vuelta in range(comidas if not hasta else 10**9):
            if hasta and time.perf_counter() > hasta:
                return
            time.sleep(random.uniform(0.001, 0.01))        # pensar
            if estrategia == "ingenuo":
                with tenedores[izq]:
                    if usar_barrera and vuelta == 0:
                        try:
                            barrera.wait()                 # los 5 tienen el izquierdo...
                        except threading.BrokenBarrierError:
                            return
                    if not tenedores[der].acquire(timeout=timeout):
                        return                             # …y nadie consigue el derecho: DEADLOCK
                    try:
                        comer(i)
                    finally:
                        tenedores[der].release()
            elif estrategia == "jerarquia":
                primero, segundo = sorted((izq, der))      # ordenar ÍNDICES, no Locks
                with tenedores[primero], tenedores[segundo]:
                    comer(i)
            elif estrategia == "semaforo":
                with comedor:                              # como mucho 4 a la mesa
                    with tenedores[izq], tenedores[der]:
                        comer(i)

    hilos = [threading.Thread(target=filosofo, args=(i,), daemon=True) for i in range(NUM)]
    t0 = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout * 3)
    se_colgo = (not hasta) and sum(comio) < NUM * comidas
    return se_colgo, time.perf_counter() - t0, comio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["ingenuo", "jerarquia", "semaforo", "comparar"])
    ap.add_argument("--sin-barrera", action="store_true")
    ap.add_argument("--corridas", type=int, default=1)
    ap.add_argument("--comidas", type=int, default=3)
    a = ap.parse_args()

    if a.modo == "comparar":
        for est in ("jerarquia", "semaforo"):
            t = sum(correr(est, comidas=30)[1] for _ in range(10)) / 10
            _, _, comio = correr(est, duracion=2.0)            # justicia: dejarlos comer 2 s y contar
            print(f"{est:<10} 30 comidas c/u: {t:.3f}s prom · en 2 s comieron {comio} "
                  f"(el que menos comió hizo {min(comio) / max(comio):.0%} del que más)")
        return

    colgadas = 0
    for _ in range(a.corridas):
        colgo, t, comio = correr(a.modo, a.comidas, usar_barrera=not a.sin_barrera)
        colgadas += colgo
        print(f"{'🔒 DEADLOCK' if colgo else '✓ terminó'} en {t:.2f}s — comidas por filósofo: {comio}")
    if a.corridas > 1:
        print(f"Se colgó {colgadas} de {a.corridas} veces")


if __name__ == "__main__":
    main()
