#!/usr/bin/env python3
"""Clase 11 · Adicional: rate limiter thread-safe (token bucket): máximo N operaciones por segundo.

Hay un "balde" con hasta N fichas que se rellena a N fichas/s. Cada operación gasta una.
Si no hay fichas, el thread espera (Condition con timeout) hasta que se regenere una.
"""
import threading
import time


class RateLimiter:
    def __init__(self, por_segundo):
        self.capacidad = por_segundo
        self.tasa = por_segundo
        self.fichas = float(por_segundo)
        self.ultimo = time.monotonic()           # monotonic: no salta si cambia la hora del sistema
        self.cond = threading.Condition()

    def _rellenar(self):
        ahora = time.monotonic()
        self.fichas = min(self.capacidad, self.fichas + (ahora - self.ultimo) * self.tasa)
        self.ultimo = ahora

    def adquirir(self):
        with self.cond:
            while True:
                self._rellenar()
                if self.fichas >= 1:
                    self.fichas -= 1
                    return
                faltante = (1 - self.fichas) / self.tasa
                self.cond.wait(timeout=faltante)   # dormir justo lo necesario (suelta el lock)


if __name__ == "__main__":
    limiter = RateLimiter(por_segundo=5)
    hechas = []
    lock = threading.Lock()

    def worker():
        for _ in range(5):
            limiter.adquirir()
            with lock:
                hechas.append(time.monotonic())

    t0 = time.monotonic()
    hs = [threading.Thread(target=worker) for _ in range(4)]     # 4 hilos × 5 = 20 operaciones
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    dur = time.monotonic() - t0
    print(f"20 operaciones a máx 5/s (con ráfaga inicial de 5): {dur:.2f}s  (esperado ≈ 3.0s)")
    ventana_peor = max(sum(1 for x in hechas if t <= x < t + 1) for t in hechas)
    print(f"Máximo de operaciones en cualquier ventana de 1 s: {ventana_peor}  (≤ 10 = ráfaga + tasa)")
