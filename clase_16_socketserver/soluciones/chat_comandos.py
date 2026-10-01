#!/usr/bin/env python3
"""Clase 16 · Ej. 4: un servidor "de verdad" con socketserver — NICK, BROADCAST, WHO, timeout.

    python3 chat_comandos.py [--puerto 8080] [--timeout 30]
    nc localhost 8080      (abrí 2 o 3)
        NICK ana
        BROADCAST hola a todos
        WHO
        QUIT

Dónde vive cada dato:
  - el apodo de UN cliente → en el HANDLER (self.nick): hay un handler por conexión y muere con ella.
  - la lista de conectados (para BROADCAST/WHO) → en el SERVIDOR, que es uno solo y lo ven todos los
    threads → protegida con un Lock.
"""
import argparse
import socket
import socketserver
import threading


class ServidorChat(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.lock = threading.Lock()
        self.clientes = {}                      # handler -> nick

    def difundir(self, texto, excepto=None):
        """Manda a todos. Copia la lista con el lock tomado y escribe FUERA del lock:
        si un cliente lento nos bloquea el sendall, no frena a todo el chat."""
        with self.lock:
            destinos = [h for h in self.clientes if h is not excepto]
        for h in destinos:
            try:
                h.enviar(texto)
            except OSError:                     # se desconectó justo mientras le escribíamos
                self.sacar(h)

    def sacar(self, handler):
        with self.lock:
            return self.clientes.pop(handler, None)


class Chat(socketserver.StreamRequestHandler):
    timeout = 30                                # StreamRequestHandler aplica settimeout() al socket

    def setup(self):
        super().setup()                         # ¡imprescindible! crea rfile/wfile
        self.nick = f"anon{self.client_address[1]}"
        self.escribir = threading.Lock()        # dos threads podrían escribirle a ESTE cliente a la vez
        with self.server.lock:
            self.server.clientes[self] = self.nick

    def enviar(self, texto):
        with self.escribir:
            self.wfile.write((texto + "\n").encode())
            self.wfile.flush()

    def handle(self):
        self.enviar("bienvenido · comandos: NICK <n>, BROADCAST <txt>, WHO, QUIT")
        try:
            for linea in self.rfile:
                cmd, _, arg = linea.decode(errors="replace").strip().partition(" ")
                cmd = cmd.upper()
                if cmd == "NICK" and arg:
                    viejo, self.nick = self.nick, arg
                    with self.server.lock:
                        self.server.clientes[self] = arg
                    self.server.difundir(f"* {viejo} ahora es {arg}")
                elif cmd == "BROADCAST" and arg:
                    self.server.difundir(f"<{self.nick}> {arg}", excepto=self)
                    self.enviar("ok")
                elif cmd == "WHO":
                    with self.server.lock:
                        nombres = sorted(self.server.clientes.values())
                    self.enviar("conectados: " + ", ".join(nombres))
                elif cmd == "QUIT":
                    self.enviar("chau")
                    return
                else:
                    self.enviar("? comando desconocido")
        except TimeoutError:
            self.enviar("desconectado por inactividad")

    def finish(self):
        if self.server.sacar(self):
            self.server.difundir(f"* {self.nick} se fue")
        try:
            super().finish()
        except OSError:
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    ap.add_argument("--timeout", type=float, default=30)
    a = ap.parse_args()
    Chat.timeout = a.timeout
    with ServidorChat(("0.0.0.0", a.puerto), Chat) as srv:
        print(f"chat en :{a.puerto} (timeout de inactividad {a.timeout}s)")
        srv.serve_forever()
