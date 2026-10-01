#!/usr/bin/env python3
"""Servidor eco con pool de threads acotado."""
import socket
from concurrent.futures import ThreadPoolExecutor

MAX_WORKERS = 20

def atender(conn, direccion):
    with conn:
        while True:
            datos = conn.recv(4096)
            if not datos:
                break
            conn.sendall(datos)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', 8080))
    servidor.listen(128)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        while True:
            conn, direccion = servidor.accept()
            pool.submit(atender, conn, direccion)