#!/usr/bin/env python3
"""Clase 13 · Adicional: servidor de comandos por líneas (SMTP en miniatura).

    python3 servidor_comandos.py [--puerto 8080]
    nc localhost 8080        y escribir:   TIME  ·  ECHO hola  ·  HELP  ·  QUIT

Respuestas con código como los protocolos reales:  200 OK ... / 400 error ... / 221 chau
"""
import argparse
import socket
import time


def recibir_lineas(f):
    for linea in f:                               # makefile() ya trae el buffer por líneas
        yield linea.rstrip(b"\r\n").decode("utf-8", errors="replace")


def atender(conn, direccion):
    with conn, conn.makefile("rwb") as f:
        def responder(texto):
            f.write(texto.encode() + b"\r\n")     # \r\n: convención de los protocolos de texto
            f.flush()                             # sin flush queda en el buffer y el cliente no ve nada
        responder("220 bienvenido — HELP para ver comandos")
        for linea in recibir_lineas(f):
            comando, _, arg = linea.partition(" ")
            comando = comando.upper()
            if comando == "TIME":
                responder(f"200 {time.strftime('%Y-%m-%d %H:%M:%S')}")
            elif comando == "ECHO":
                responder(f"200 {arg}")
            elif comando == "HELP":
                responder("200 comandos: TIME, ECHO <texto>, HELP, QUIT")
            elif comando == "QUIT":
                responder("221 chau")
                return
            elif comando == "":
                continue
            else:
                responder(f"400 comando desconocido: {comando}")
    print(f"[{direccion}] desconectado")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    puerto = ap.parse_args().puerto
    with socket.create_server(("0.0.0.0", puerto)) as srv:   # create_server ya pone SO_REUSEADDR
        print(f"Servidor de comandos en 0.0.0.0:{puerto} (secuencial: uno a la vez)")
        while True:
            conn, dire = srv.accept()
            try:
                atender(conn, dire)
            except (ConnectionResetError, BrokenPipeError):
                print(f"[{dire}] cortó de golpe")
