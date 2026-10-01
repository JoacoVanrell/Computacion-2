#!/usr/bin/env python3
"""Clase 15 · Ej. 4: connect() en UDP — no conecta, pero filtra remitentes y habilita errores ICMP.

    python3 udp_connect_icmp.py
"""
import socket
import time


def puerto_libre():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]               # al cerrar, ese puerto queda sin nadie


vacio = puerto_libre()

# 1) CON connect: el ICMP "port unreachable" llega a nuestro socket
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2)
s.connect(("127.0.0.1", vacio))
s.send(b"hola")
t0 = time.perf_counter()
try:
    s.recv(4096)
except ConnectionRefusedError:
    print(f"CON connect: ConnectionRefusedError en {time.perf_counter() - t0:.3f}s  ← avisó el ICMP")
except TimeoutError:
    print("CON connect: timeout")
s.close()

# 2) SIN connect: el kernel no sabe a qué socket darle el ICMP → lo descarta
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2)
s.sendto(b"hola", ("127.0.0.1", vacio))
t0 = time.perf_counter()
try:
    s.recvfrom(4096)
except ConnectionRefusedError:
    print("SIN connect: ConnectionRefusedError")
except TimeoutError:
    print(f"SIN connect: timeout después de {time.perf_counter() - t0:.1f}s  ← esperamos para nada")
s.close()

# 3) connect() filtra: un tercero nos manda algo y el kernel lo tira
rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("127.0.0.1", 0))
amigo = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
amigo.bind(("127.0.0.1", 0))
extrano = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.connect(amigo.getsockname())                 # solo acepto datagramas de "amigo"
extrano.sendto(b"soy un extrano", rx.getsockname())
amigo.sendto(b"soy el amigo", rx.getsockname())
rx.settimeout(1)
recibidos = []
try:
    while True:
        recibidos.append(rx.recv(100))
except TimeoutError:
    pass
print(f"Filtro: llegaron {recibidos}  ← el del extraño lo descartó el kernel")
