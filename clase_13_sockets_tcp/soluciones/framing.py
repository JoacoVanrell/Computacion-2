#!/usr/bin/env python3
"""Clase 13 · Ej. 3 (OBLIGATORIO): framing por delimitador y por longitud, con las pruebas extremas.

    python3 framing.py test                     # corre TODAS las pruebas de la consigna
    python3 framing.py servidor-lineas  [--puerto 8080]   # probar a mano con: nc localhost 8080
    python3 framing.py servidor-longitud [--puerto 8081]

Los dos servidores responden el mensaje en MAYÚSCULAS, usando el mismo framing que recibieron.
"""
import argparse
import socket
import struct
import threading
import time

MAX_MENSAJE = 10 * 1024 * 1024          # 10 MB: tope para que un cliente no nos haga reservar 5 GB


# ───────────────────── Estrategia 1: delimitador \n ─────────────────────
def recibir_lineas(sock):
    """Generador de líneas completas. El buffer SOBREVIVE entre recv():
    un recv puede traer media línea (la guardamos) o tres y media (entregamos las 3)."""
    buffer = b""
    while True:
        pedazo = sock.recv(4096)
        if not pedazo:                               # el otro cerró
            return                                   # (lo que quedó sin \n se descarta)
        buffer += pedazo
        while b"\n" in buffer:                       # WHILE: puede haber varias líneas
            linea, buffer = buffer.split(b"\n", 1)
            yield linea
        if len(buffer) > MAX_MENSAJE:
            raise ValueError("línea demasiado larga")


def atender_lineas(conn):
    with conn:
        for linea in recibir_lineas(conn):
            # decodificamos la línea COMPLETA (nunca un pedazo: un carácter UTF-8 puede quedar partido)
            texto = linea.decode("utf-8", errors="strict")
            conn.sendall(texto.upper().encode("utf-8") + b"\n")


# ───────────────────── Estrategia 2: prefijo de longitud ─────────────────────
def recibir_exacto(sock, n):
    """Lee EXACTAMENTE n bytes (recv(n) puede devolver menos → hay que insistir)."""
    partes, faltan = [], n
    while faltan:
        pedazo = sock.recv(min(faltan, 65536))
        if not pedazo:
            return None                              # cerraron en el medio
        partes.append(pedazo)
        faltan -= len(pedazo)
    return b"".join(partes)                          # join al final: más eficiente que += en bucle


def enviar_mensaje(sock, payload: bytes):
    sock.sendall(struct.pack("!I", len(payload)) + payload)   # !I = 4 bytes, sin signo, orden de RED


def recibir_mensaje(sock):
    cabecera = recibir_exacto(sock, 4)
    if cabecera is None:
        return None
    (largo,) = struct.unpack("!I", cabecera)
    if largo > MAX_MENSAJE:
        raise ValueError(f"mensaje de {largo} bytes: supera el máximo")
    return recibir_exacto(sock, largo) if largo else b""      # 0 bytes es un mensaje válido (vacío)


def atender_longitud(conn):
    with conn:
        while (msg := recibir_mensaje(conn)) is not None:
            enviar_mensaje(conn, msg.decode("utf-8").upper().encode("utf-8"))


# ───────────────────── servidor genérico ─────────────────────
def servir(atender, puerto, una_vez=False):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # ANTES del bind
    srv.bind(("127.0.0.1", puerto))
    srv.listen(16)
    def bucle():
        while True:
            conn, _ = srv.accept()
            try:
                atender(conn)
            except (ConnectionResetError, BrokenPipeError, ValueError, UnicodeDecodeError) as e:
                print(f"  [srv] cliente descartado: {e!r}")
            if una_vez:
                break
    return srv, bucle


# ───────────────────── pruebas de la consigna ─────────────────────
def test():
    ok = True

    def check(nombre, obtenido, esperado):
        nonlocal ok
        bien = obtenido == esperado
        ok &= bien
        print(f"  {'✓' if bien else '✗'} {nombre}: {obtenido!r}")

    srv_l, bucle_l = servir(atender_lineas, 0)
    threading.Thread(target=bucle_l, daemon=True).start()
    p_l = srv_l.getsockname()[1]
    print("DELIMITADOR \\n")
    with socket.create_connection(("127.0.0.1", p_l)) as c:            # (4) todo en un sendall
        c.sendall(b"uno\ndos\ntres\n")
        c.shutdown(socket.SHUT_WR)
        check("3 mensajes en 1 sendall", list(recibir_lineas(c)), [b"UNO", b"DOS", b"TRES"])
    with socket.create_connection(("127.0.0.1", p_l)) as c:            # (5) byte por byte
        for b in b"hola\n":
            c.sendall(bytes([b]))
            time.sleep(0.05)
        c.shutdown(socket.SHUT_WR)
        check("byte por byte", list(recibir_lineas(c)), [b"HOLA"])
    with socket.create_connection(("127.0.0.1", p_l)) as c:            # (7) \n adentro del mensaje
        c.sendall("línea\ncon enter\n".encode())
        c.shutdown(socket.SHUT_WR)
        check("mensaje con \\n adentro (se PARTE en 2)", list(recibir_lineas(c)),
              ["LÍNEA".encode(), b"CON ENTER"])

    srv_n, bucle_n = servir(atender_longitud, 0)
    threading.Thread(target=bucle_n, daemon=True).start()
    p_n = srv_n.getsockname()[1]
    print("PREFIJO DE LONGITUD")
    with socket.create_connection(("127.0.0.1", p_n)) as c:
        datos = b"".join(struct.pack("!I", len(m)) + m for m in (b"uno", b"dos", b"tres"))
        c.sendall(datos)                                                # todo junto
        check("3 mensajes en 1 sendall", [recibir_mensaje(c) for _ in range(3)], [b"UNO", b"DOS", b"TRES"])
        for b in struct.pack("!I", 4) + b"hola":                        # byte por byte (¡cabecera incluida!)
            c.sendall(bytes([b]))
            time.sleep(0.02)
        check("byte por byte", recibir_mensaje(c), b"HOLA")
        enviar_mensaje(c, "línea\ncon enter".encode())
        check("mensaje con \\n adentro (llega ENTERO)", recibir_mensaje(c), "LÍNEA\nCON ENTER".encode())
        enviar_mensaje(c, b"")
        check("mensaje de 0 bytes", recibir_mensaje(c), b"")
    with socket.create_connection(("127.0.0.1", p_n)) as c:
        c.sendall(struct.pack("!I", 2**32 - 1))   # "voy a mandar 4 GB" (lo máximo que entra en 4 bytes)
        c.shutdown(socket.SHUT_WR)
        check("cabecera gigante → el servidor corta la conexión", c.recv(10), b"")
    print("\nTODO OK ✓" if ok else "\nHAY FALLAS ✗")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["test", "servidor-lineas", "servidor-longitud"])
    ap.add_argument("--puerto", type=int)
    a = ap.parse_args()
    if a.modo == "test":
        test()
    else:
        atender = atender_lineas if a.modo == "servidor-lineas" else atender_longitud
        puerto = a.puerto or (8080 if a.modo == "servidor-lineas" else 8081)
        print(f"{a.modo} en 127.0.0.1:{puerto}")
        servir(atender, puerto)[1]()
