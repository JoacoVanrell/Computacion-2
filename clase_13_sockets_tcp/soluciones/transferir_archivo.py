#!/usr/bin/env python3
"""Clase 13 · Adicional: transferencia de archivos con framing por longitud (+ verificación md5).

    python3 transferir_archivo.py recibir --puerto 9000 --destino recibidos/
    python3 transferir_archivo.py enviar archivo.iso --host localhost --puerto 9000
    python3 transferir_archivo.py demo        # prueba sola con un archivo de 120 MB

Protocolo:  [2 B largo nombre][nombre utf-8][8 B tamaño][contenido...][16 B md5]
El tamaño va en 8 bytes ('!Q') porque 4 bytes ('!I') solo llegan a 4 GB.
El archivo se manda/recibe DE A PEDAZOS: nunca está entero en memoria (sirve para archivos enormes).
"""
import argparse
import hashlib
import os
import socket
import struct
import threading
import time

BLOQUE = 1024 * 1024


def recibir_exacto(sock, n):
    partes = []
    while n:
        p = sock.recv(min(n, BLOQUE))
        if not p:
            raise ConnectionError("se cortó la transferencia")
        partes.append(p)
        n -= len(p)
    return b"".join(partes)


def enviar(ruta, host, puerto):
    nombre = os.path.basename(ruta).encode()
    tam = os.path.getsize(ruta)
    md5 = hashlib.md5()
    with socket.create_connection((host, puerto)) as s, open(ruta, "rb") as f:
        s.sendall(struct.pack("!H", len(nombre)) + nombre + struct.pack("!Q", tam))
        while bloque := f.read(BLOQUE):
            md5.update(bloque)
            s.sendall(bloque)
        s.sendall(md5.digest())
        respuesta = s.recv(100).decode()
    print(f"[enviar] {ruta} ({tam / 1e6:.1f} MB) md5={md5.hexdigest()} → servidor: {respuesta}")
    return respuesta.startswith("OK")


def recibir_uno(conn, destino):
    with conn:
        (largo,) = struct.unpack("!H", recibir_exacto(conn, 2))
        nombre = os.path.basename(recibir_exacto(conn, largo).decode())   # basename: que no nos escriban ../../etc
        (tam,) = struct.unpack("!Q", recibir_exacto(conn, 8))
        ruta = os.path.join(destino, nombre)
        md5 = hashlib.md5()
        with open(ruta, "wb") as f:
            faltan = tam
            while faltan:
                bloque = conn.recv(min(faltan, BLOQUE))
                if not bloque:
                    raise ConnectionError("se cortó la transferencia")
                md5.update(bloque)
                f.write(bloque)
                faltan -= len(bloque)
        ok = recibir_exacto(conn, 16) == md5.digest()
        conn.sendall(b"OK md5 coincide" if ok else b"ERROR md5 distinto")
        print(f"[recibir] {ruta} ({tam / 1e6:.1f} MB) md5 {'✓' if ok else '✗'} {md5.hexdigest()}")


def servidor(puerto, destino, una_vez=False, listo=None):
    os.makedirs(destino, exist_ok=True)
    with socket.create_server(("0.0.0.0", puerto)) as srv:
        if listo:
            listo.set()
        while True:
            conn, _ = srv.accept()
            try:
                recibir_uno(conn, destino)
            except (ConnectionError, struct.error) as e:
                print(f"[recibir] falló: {e}")
            if una_vez:
                return


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["enviar", "recibir", "demo"])
    ap.add_argument("archivo", nargs="?")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--puerto", type=int, default=9000)
    ap.add_argument("--destino", default="recibidos")
    a = ap.parse_args()
    if a.modo == "recibir":
        servidor(a.puerto, a.destino)
    elif a.modo == "enviar":
        enviar(a.archivo, a.host, a.puerto)
    else:
        origen = "/tmp/archivo_prueba.bin"
        with open(origen, "wb") as f:
            f.write(os.urandom(120 * 1024 * 1024))
        listo = threading.Event()
        t = threading.Thread(target=servidor, args=(a.puerto, "/tmp/recibidos", True, listo))
        t.start()
        listo.wait()
        t0 = time.perf_counter()
        enviar(origen, "127.0.0.1", a.puerto)
        t.join()
        print(f"120 MB en {time.perf_counter() - t0:.2f}s")
