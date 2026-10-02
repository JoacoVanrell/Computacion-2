#!/usr/bin/env python3
"""Clase 17 · Ej. 6: chat multiusuario con selectors, UN solo hilo — con framing correcto, /nick y /lista.

    python3 chat_selectors.py [--puerto 8080]
    nc localhost 8080   (abrí varios)      /nick ana  ·  /lista  ·  /salir  ·  cualquier otra cosa = mensaje

- Sin locks: hay un solo hilo; nadie más toca las estructuras mientras este código corre.
- Framing: buffer de ENTRADA por cliente (un recv puede traer media línea o tres).
- Escritura no bloqueante: buffer de SALIDA por cliente + EVENT_WRITE solo cuando hay algo pendiente
  (difundir ENCOLA; un cliente lento no congela a los demás).
- Protección: si a un cliente se le acumulan más de 1 MB sin leer, se lo desconecta.
"""
import argparse
import selectors
import socket

MAX_PENDIENTE = 1024 * 1024


class Cliente:
    def __init__(self, conn, addr):
        self.conn, self.addr = conn, addr
        self.nick = f"anon{addr[1]}"
        self.entrada = b""
        self.salida = b""


sel = selectors.DefaultSelector()
clientes = {}                                   # conn -> Cliente


def actualizar_interes(c):
    eventos = selectors.EVENT_READ | (selectors.EVENT_WRITE if c.salida else 0)
    sel.modify(c.conn, eventos, data=c)


def encolar(c, texto):
    c.salida += (texto + "\n").encode()
    if len(c.salida) > MAX_PENDIENTE:
        cerrar(c, "no lee lo que le mandamos")
        return
    actualizar_interes(c)


def difundir(texto, excepto=None):
    for c in list(clientes.values()):
        if c is not excepto:
            encolar(c, texto)


def cerrar(c, motivo=""):
    if c.conn not in clientes:
        return
    sel.unregister(c.conn)                      # SIEMPRE antes de close()
    c.conn.close()
    del clientes[c.conn]
    difundir(f"* {c.nick} se fue {('(' + motivo + ')') if motivo else ''}")


def procesar_linea(c, linea):
    if linea.startswith("/nick "):
        viejo, c.nick = c.nick, linea[6:].strip() or c.nick
        difundir(f"* {viejo} ahora es {c.nick}")
    elif linea == "/lista":
        encolar(c, "conectados: " + ", ".join(sorted(x.nick for x in clientes.values())))
    elif linea == "/salir":
        cerrar(c)
    elif linea:
        difundir(f"<{c.nick}> {linea}", excepto=c)


def leer(c):
    try:
        datos = c.conn.recv(4096)
    except ConnectionResetError:
        datos = b""
    if not datos:
        cerrar(c)
        return
    c.entrada += datos
    while b"\n" in c.entrada:                   # todas las líneas COMPLETAS; el resto queda para después
        linea, c.entrada = c.entrada.split(b"\n", 1)
        procesar_linea(c, linea.decode("utf-8", errors="replace").strip())
        if c.conn not in clientes:              # /salir
            return


def escribir(c):
    try:
        n = c.conn.send(c.salida)               # send() y NO sendall(): mandamos lo que entre y volvemos
    except (BlockingIOError, InterruptedError):
        return
    except OSError:
        cerrar(c)
        return
    c.salida = c.salida[n:]
    actualizar_interes(c)                       # si quedó vacío, dejamos de vigilar escritura


def aceptar(srv):
    conn, addr = srv.accept()
    conn.setblocking(False)
    c = Cliente(conn, addr)
    clientes[conn] = c
    sel.register(conn, selectors.EVENT_READ, data=c)
    encolar(c, "bienvenido · /nick <nombre> · /lista · /salir")
    difundir(f"* {c.nick} entró", excepto=c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    puerto = ap.parse_args().puerto
    srv = socket.create_server(("0.0.0.0", puerto))
    srv.setblocking(False)
    sel.register(srv, selectors.EVENT_READ, data=None)
    print(f"chat en :{puerto} con {type(sel).__name__}")
    while True:
        for clave, mascara in sel.select():
            if clave.data is None:
                aceptar(clave.fileobj)
                continue
            c = clave.data
            if mascara & selectors.EVENT_READ:
                leer(c)
            if mascara & selectors.EVENT_WRITE and c.conn in clientes:
                escribir(c)


if __name__ == "__main__":
    main()
