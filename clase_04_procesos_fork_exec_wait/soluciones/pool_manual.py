#!/usr/bin/env python3
"""Clase 4 · Adicional: pool manual de workers usando SOLO fork/wait.

Hay una lista de tareas y como máximo N hijos vivos a la vez. Cada vez que un hijo
termina (wait), el padre lanza otro con la próxima tarea, hasta agotar la lista.
Cada hijo "devuelve" su resultado con el código de salida (0-255).

    python3 pool_manual.py --workers 3
"""
import argparse
import os
import random
import time


def tarea(n):
    """Trabajo de ejemplo: duerme un rato y devuelve n² % 256 (cabe en un código de salida)."""
    time.sleep(random.uniform(0.2, 0.8))
    return (n * n) % 256


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--tareas", type=int, default=10)
    args = p.parse_args()

    pendientes = list(range(args.tareas))
    vivos = {}                                    # pid -> tarea
    resultados = {}
    inicio = time.time()

    while pendientes or vivos:
        # lanzar hijos mientras haya lugar y tareas
        while pendientes and len(vivos) < args.workers:
            n = pendientes.pop(0)
            pid = os.fork()
            if pid == 0:
                random.seed(os.getpid())          # si no, todos los hijos heredan la misma semilla
                os._exit(tarea(n))
            vivos[pid] = n
            print(f"[padre] lancé tarea {n} en PID {pid}  (vivos: {len(vivos)})")
        # esperar a que termine CUALQUIERA
        pid, status = os.wait()
        n = vivos.pop(pid)
        resultados[n] = os.WEXITSTATUS(status)
        print(f"[padre] PID {pid} terminó tarea {n} → {resultados[n]}")

    print(f"\nResultados: {dict(sorted(resultados.items()))}")
    print(f"Tiempo: {time.time() - inicio:.2f}s con {args.workers} workers")
    assert all(resultados[n] == (n * n) % 256 for n in resultados)


if __name__ == "__main__":
    main()
