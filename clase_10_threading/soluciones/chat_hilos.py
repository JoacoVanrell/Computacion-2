#!/usr/bin/env python3
"""Clase 10 · Adicional: chat multi-hilo. N "usuarios" mandan mensajes a una Queue central
y un único thread "display" los muestra. Nadie toca print() salvo el display → no se mezclan líneas.
"""
import queue
import random
import threading
import time

FIN = object()                         # centinela único (nadie va a mandar este objeto por error)


def usuario(nombre, buzon, n):
    for i in range(n):
        time.sleep(random.uniform(0.05, 0.3))
        buzon.put((time.strftime("%H:%M:%S"), nombre, f"mensaje {i + 1}"))
    buzon.put(FIN)


def display(buzon, n_usuarios):
    terminados = 0
    while terminados < n_usuarios:
        msg = buzon.get()
        if msg is FIN:
            terminados += 1
            continue
        hora, quien, texto = msg
        print(f"[{hora}] {quien:>6}: {texto}")


if __name__ == "__main__":
    buzon = queue.Queue()              # thread-safe: los locks están adentro
    nombres = ["ana", "beto", "caro"]
    pantalla = threading.Thread(target=display, args=(buzon, len(nombres)))
    usuarios = [threading.Thread(target=usuario, args=(n, buzon, 3)) for n in nombres]
    pantalla.start()
    for u in usuarios:
        u.start()
    for u in usuarios:
        u.join()
    pantalla.join()
    print("chat cerrado")
