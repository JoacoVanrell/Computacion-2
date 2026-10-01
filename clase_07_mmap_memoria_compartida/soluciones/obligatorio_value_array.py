#!/usr/bin/env python3
"""Clase 7 · Ej. 5 (OBLIGATORIO): Value y Array compartidos.

Parte A — la race condition con Value (4 procesos × N incrementos).
Parte B — la tarea: Array('d', 100) con sin(i*0.01) repartido en 4 procesos,
          + bonus: Value('d') acumulando la suma (con y sin lock).

    python3 obligatorio_value_array.py
"""
import math
from multiprocessing import Array, Process, Value

N = 100_000
TAM = 100
NPROC = 4


# ─────────────── Parte A ───────────────
def incrementar(contador, n, usar_lock):
    for _ in range(n):
        if usar_lock:
            with contador.get_lock():   # Value trae su propio Lock adentro
                contador.value += 1
        else:
            contador.value += 1         # leer → sumar → escribir: NO es atómico


def parte_a(usar_lock):
    contador = Value("i", 0)
    ps = [Process(target=incrementar, args=(contador, N, usar_lock)) for _ in range(NPROC)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    esperado = NPROC * N
    etiqueta = "CON lock" if usar_lock else "SIN lock"
    print(f"[A {etiqueta}] esperado {esperado}, obtenido {contador.value}, "
          f"perdidos {esperado - contador.value}")


# ─────────────── Parte B ───────────────
def calcular_porcion(arr, suma, inicio, fin, usar_lock):
    parcial = 0.0
    for i in range(inicio, fin):
        arr[i] = math.sin(i * 0.01)
        parcial += arr[i]
        if not usar_lock:
            suma.value += arr[i]        # muchos += sin protección → race
    if usar_lock:
        with suma.get_lock():           # mejor: acumulo LOCAL y sumo UNA vez protegido
            suma.value += parcial


def parte_b(usar_lock):
    arr = Array("d", TAM)               # 100 doubles en memoria compartida, inicializados en 0
    suma = Value("d", 0.0)
    chunk = TAM // NPROC
    ps = []
    for k in range(NPROC):
        ini = k * chunk
        fin = TAM if k == NPROC - 1 else (k + 1) * chunk   # el último se lleva el resto
        ps.append(Process(target=calcular_porcion, args=(arr, suma, ini, fin, usar_lock)))
    for p in ps:
        p.start()
    for p in ps:
        p.join()

    errores = sum(1 for i in range(TAM) if arr[i] != math.sin(i * 0.01))
    esperado = sum(math.sin(i * 0.01) for i in range(TAM))
    if not usar_lock:
        print("[B] primeros 20:", [round(arr[i], 4) for i in range(20)])
        print(f"[B] errores en el array: {errores}  (cada proceso escribe SU porción → no hay race)")
    etiqueta = "CON lock" if usar_lock else "SIN lock"
    print(f"[B {etiqueta}] suma esperada {esperado:.6f}, obtenida {suma.value:.6f}")


if __name__ == "__main__":
    parte_a(usar_lock=False)
    parte_a(usar_lock=True)
    parte_b(usar_lock=False)
    parte_b(usar_lock=True)
