#!/usr/bin/env python3
"""Clase 12 · Ej. 6 (OBLIGATORIO): TCP es un flujo, UDP son datagramas. Todo en un solo script.

    python3 tcp_flujo_vs_udp.py

Hace 3 experimentos con un receptor en un thread que anota CADA recv() por separado:
  A) TCP, 3 send() seguidos         → normalmente llega todo en 1 recv: b'HOLACOMOESTAS'
  A2) TCP, con sleep entre send()   → probablemente 3 recv… pero NO está garantizado
  C) UDP, 3 sendto()                → SIEMPRE 3 recvfrom, uno por datagrama
"""
import socket
import threading
import time

MSGS = [b"HOLA", b"COMO", b"ESTAS"]


def receptor_tcp(srv, recibidos):
    conn, _ = srv.accept()
    with conn:
        while True:
            datos = conn.recv(4096)
            if not datos:                    # b"" = el otro lado cerró
                break
            recibidos.append(datos)


def experimento_tcp(pausa):
    srv = socket.create_server(("127.0.0.1", 0))           # puerto 0 = que el SO elija uno libre
    puerto = srv.getsockname()[1]
    recibidos = []
    t = threading.Thread(target=receptor_tcp, args=(srv, recibidos))
    t.start()
    with socket.create_connection(("127.0.0.1", puerto)) as c:
        for m in MSGS:
            c.send(m)
            if pausa:
                time.sleep(pausa)
    t.join()
    srv.close()
    return recibidos


def experimento_udp():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(1)
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for m in MSGS:
        tx.sendto(m, rx.getsockname())                     # sin connect, sin listen, sin accept
    recibidos = []
    try:
        while True:
            datos, _ = rx.recvfrom(4096)
            recibidos.append(datos)
    except socket.timeout:
        pass
    rx.close()
    tx.close()
    return recibidos


if __name__ == "__main__":
    print(f"Mando 3 mensajes: {MSGS}\n")
    r = experimento_tcp(pausa=0)
    print(f"A)  TCP sin pausa     → {len(r)} recv(): {r}")
    r = experimento_tcp(pausa=0.2)
    print(f"A2) TCP con pausa     → {len(r)} recv(): {r}   (¡no confiar en esto!)")
    r = experimento_udp()
    print(f"C)  UDP               → {len(r)} recvfrom(): {r}")
