#!/usr/bin/env python3
"""Clase 9 · Ej. 7: pipeline de 3 etapas… y la respuesta a "¿cómo escalarías la etapa lenta?".

    python3 pipeline_escalado.py --lentos 1     # la etapa 2 (lenta) con 1 proceso → cuello de botella
    python3 pipeline_escalado.py --lentos 4     # la misma etapa con 4 procesos → mucho más rápido

    q1 ─► [×2] ─► q2 ─► [+10 LENTA] ×K ─► q3 ─► [formatear] ─► q4 ─► main

Con K procesos en una etapa, el centinela se complica:
  - la etapa anterior manda K Nones (uno por cada proceso de la etapa lenta)
  - la etapa siguiente tiene que esperar K Nones antes de terminar.
"""
import argparse
import time
from multiprocessing import Process, Queue

FIN = None


def etapa(entrada, salida, funcion, finales_que_espero=1, finales_que_mando=1):
    vistos = 0
    while True:
        item = entrada.get()
        if item is FIN:
            vistos += 1
            if vistos == finales_que_espero:     # recién cuando TODOS los de antes terminaron
                for _ in range(finales_que_mando):
                    salida.put(FIN)
                return
            continue
        salida.put(funcion(item))


def por2(x):
    time.sleep(0.02)
    return x * 2


def mas10_lenta(x):
    time.sleep(0.2)                               # 10 veces más lenta que las otras
    return x + 10


def formatear(x):
    time.sleep(0.02)
    return f"resultado_{x:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", type=int, default=20)
    ap.add_argument("--lentos", type=int, default=1, help="procesos en la etapa lenta")
    a = ap.parse_args()
    k = a.lentos
    q1, q2, q3, q4 = Queue(), Queue(), Queue(), Queue()

    procesos = [Process(target=etapa, args=(q1, q2, por2, 1, k))]                    # manda K FIN
    procesos += [Process(target=etapa, args=(q2, q3, mas10_lenta, 1, 1)) for _ in range(k)]
    procesos += [Process(target=etapa, args=(q3, q4, formatear, k, 1))]              # espera K FIN
    t0 = time.perf_counter()
    for p in procesos:
        p.start()
    for i in range(a.items):
        q1.put(i)
    q1.put(FIN)

    resultados = []
    while (r := q4.get()) is not FIN:
        resultados.append(r)
    for p in procesos:
        p.join()
    dur = time.perf_counter() - t0
    print(f"{len(resultados)} resultados con {k} proceso(s) en la etapa lenta: {dur:.2f}s")
    print("   (ojo: con K>1 el ORDEN de salida ya no está garantizado)", sorted(resultados)[:3], "...")


if __name__ == "__main__":
    main()
