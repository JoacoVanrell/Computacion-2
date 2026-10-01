#!/usr/bin/env python3
"""Bloque 0 · Python avanzado · Ejercicio 4.2: Scheduler de corrutinas con generadores.

Esto es asyncio "en miniatura": cada tarea es un generador que hace un paso
y CEDE el control con `yield`. El scheduler las va despertando en ronda
(round-robin). Nadie es interrumpido a la fuerza: es multitarea COOPERATIVA.

    python3 scheduler.py
"""
from collections import deque


class Scheduler:
    def __init__(self):
        self.listas = deque()          # cola de tareas listas para correr

    def add(self, tarea):
        self.listas.append(tarea)

    def run(self):
        while self.listas:
            tarea = self.listas.popleft()
            try:
                next(tarea)                    # corre hasta el próximo yield
            except StopIteration:
                continue                       # terminó: no la volvemos a encolar
            self.listas.append(tarea)          # sigue viva: al final de la fila


def tarea_a():
    for i in range(3):
        print(f"Tarea A: paso {i}")
        yield


def tarea_b():
    for i in range(5):
        print(f"Tarea B: paso {i}")
        yield


if __name__ == "__main__":
    s = Scheduler()
    s.add(tarea_a())
    s.add(tarea_b())
    s.run()
    # Tarea A: paso 0 / Tarea B: paso 0 / A1 / B1 / A2 / B2 / B3 / B4
