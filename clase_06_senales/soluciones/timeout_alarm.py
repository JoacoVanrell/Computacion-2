#!/usr/bin/env python3
"""Clase 6 · Ej. 4: timeout con SIGALRM como context manager.

    with timeout(2):
        operacion_lenta()       # si tarda más de 2 s → TimeoutError

Solo funciona en el hilo principal y en Unix (SIGALRM no existe en Windows).
"""
import signal
import time
from contextlib import contextmanager


@contextmanager
def timeout(segundos):
    def handler(sig, frame):
        raise TimeoutError(f"se pasó de {segundos}s")
    anterior = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, segundos)       # admite decimales (alarm() solo enteros)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)          # cancelar SIEMPRE, aunque haya terminado antes
        signal.signal(signal.SIGALRM, anterior)


if __name__ == "__main__":
    with timeout(1):
        time.sleep(0.2)
    print("rápida: OK")
    try:
        with timeout(0.5):
            time.sleep(3)
    except TimeoutError as e:
        print("lenta: TimeoutError →", e)
