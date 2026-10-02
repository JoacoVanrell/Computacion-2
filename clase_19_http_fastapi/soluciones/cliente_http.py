#!/usr/bin/env python3
"""Clase 19 · Adicional: cliente HTTP a mano (sin requests/httpx) + keep-alive.

    python3 cliente_http.py http://example.com/
    python3 cliente_http.py --keepalive        # dos pedidos por la MISMA conexión contra un servidor local

Framing de HTTP (los dos de la clase 13):
  - headers: hasta la línea vacía \\r\\n\\r\\n          → delimitador
  - cuerpo:  Content-Length bytes                      → longitud
  - sin Content-Length (y sin chunked): hasta que el servidor cierre (HTTP/1.0 / Connection: close)
"""
import socket
import sys
import threading
import http.server
from urllib.parse import urlsplit


def leer_respuesta(sock, buffer=b""):
    """Devuelve (estado, headers, cuerpo, resto_del_buffer). El resto es el comienzo de la PRÓXIMA respuesta."""
    while b"\r\n\r\n" not in buffer:
        pedazo = sock.recv(4096)
        if not pedazo:
            raise ConnectionError("cerró antes de terminar los headers")
        buffer += pedazo
    cabecera, buffer = buffer.split(b"\r\n\r\n", 1)
    lineas = cabecera.decode("iso-8859-1").split("\r\n")    # los headers HTTP son latin-1 por norma
    estado = lineas[0]
    headers = {}
    for l in lineas[1:]:
        k, _, v = l.partition(":")
        headers[k.strip().lower()] = v.strip()               # los nombres de header no distinguen mayúsculas
    if "content-length" in headers:
        n = int(headers["content-length"])
        while len(buffer) < n:
            pedazo = sock.recv(4096)
            if not pedazo:
                raise ConnectionError("cerró antes de terminar el cuerpo")
            buffer += pedazo
        return estado, headers, buffer[:n], buffer[n:]
    if headers.get("transfer-encoding", "").lower() == "chunked":
        cuerpo = b""
        while True:
            while b"\r\n" not in buffer:
                buffer += sock.recv(4096)
            tam_txt, buffer = buffer.split(b"\r\n", 1)
            tam = int(tam_txt.split(b";")[0], 16)            # tamaño del chunk en HEXADECIMAL
            while len(buffer) < tam + 2:
                buffer += sock.recv(4096)
            cuerpo, buffer = cuerpo + buffer[:tam], buffer[tam + 2:]
            if tam == 0:
                return estado, headers, cuerpo, buffer
    while pedazo := sock.recv(4096):                         # sin longitud: hasta el cierre
        buffer += pedazo
    return estado, headers, buffer, b""


def get(url):
    u = urlsplit(url)
    host, puerto = u.hostname, u.port or 80
    with socket.create_connection((host, puerto), timeout=10) as s:
        s.sendall(f"GET {u.path or '/'} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
        estado, headers, cuerpo, _ = leer_respuesta(s)
    print(estado)
    for k, v in headers.items():
        print(f"  {k}: {v}")
    print(f"  ({len(cuerpo)} bytes de cuerpo) {cuerpo[:80]!r}…")


def keepalive():
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"                        # sin esto responde 1.0 y cierra tras cada pedido
        def do_GET(self):
            cuerpo = f"respuesta a {self.path}".encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(cuerpo)))   # OBLIGATORIO con keep-alive
            self.end_headers()
            self.wfile.write(cuerpo)
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with socket.create_connection(srv.server_address) as s:
        s.sendall(b"GET /uno HTTP/1.1\r\nHost: x\r\n\r\nGET /dos HTTP/1.1\r\nHost: x\r\n\r\n")   # los 2 juntos
        resto = b""
        for _ in range(2):
            estado, h, cuerpo, resto = leer_respuesta(s, resto)
            print(f"{estado} · {cuerpo!r}")
    print("→ misma conexión: el cliente sabe dónde termina cada respuesta gracias a Content-Length")
    srv.shutdown()


if __name__ == "__main__":
    if sys.argv[1:] == ["--keepalive"]:
        keepalive()
    else:
        get(sys.argv[1] if len(sys.argv) > 1 else "http://example.com/")
