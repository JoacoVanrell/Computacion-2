#!/usr/bin/env python3
"""Bloque 0 · IPv6 · Ejercicio 3 (obligatorio): servidor dual-stack + cliente agnóstico.

    python3 dual_stack_servidor.py servidor [--v6only] [--puerto 8080]
    python3 dual_stack_servidor.py cliente  [--host localhost] [--puerto 8080]
    python3 dual_stack_servidor.py demo      # levanta el server y prueba con 127.0.0.1 y ::1

Respuestas a las preguntas del ejercicio: ver README.md de esta carpeta.
"""
import argparse
import ipaddress
import socket
import threading


def normalizar(host):
    """'::ffff:1.2.3.4' -> '1.2.3.4'. Cualquier otra cosa queda igual."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host                        # no es una IP (ej: un nombre)
    if ip.version == 6 and ip.ipv4_mapped:
        return str(ip.ipv4_mapped)
    return host


def crear_servidor(puerto, v6only=False):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # SIEMPRE explícito: Linux trae 0 por defecto, Windows/OpenBSD traen 1.
    s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1 if v6only else 0)
    s.bind(("::", puerto))                 # '::' = todas las interfaces (como 0.0.0.0)
    s.listen(16)
    return s


def atender(s, cantidad=None):
    atendidos = 0
    while cantidad is None or atendidos < cantidad:
        conn, peer = s.accept()
        crudo = peer[0]                    # peer IPv6 = (host, puerto, flowinfo, scope_id)
        limpio = normalizar(crudo)
        marca = "   <- IPv4 mapeada" if crudo != limpio else ""
        print(f"[srv] conexión de {crudo:<22} normalizado: {limpio}{marca}")
        with conn:
            conn.sendall(f"hola {limpio}\n".encode())
        atendidos += 1


def conectar(host, puerto, timeout=5):
    """Prueba TODAS las direcciones que da getaddrinfo (IPv6 e IPv4) hasta que una ande."""
    ultimo_error = None
    for familia, tipo, proto, _, direccion in socket.getaddrinfo(host, puerto, type=socket.SOCK_STREAM):
        s = socket.socket(familia, tipo, proto)
        try:
            s.settimeout(timeout)
            s.connect(direccion)
            return s
        except OSError as e:
            s.close()
            ultimo_error = e              # no nos rendimos: probamos la siguiente
    raise ultimo_error or OSError(f"no se pudo resolver {host}")


def demo(puerto):
    try:
        srv = crear_servidor(puerto)
    except OSError as e:
        print(f"Este sistema no soporta IPv6 ({e}). Probá en tu Ubuntu, que sí lo tiene.")
        return
    hilo = threading.Thread(target=atender, args=(srv, 2), daemon=True)
    hilo.start()
    for host in ("127.0.0.1", "::1"):
        with conectar(host, puerto) as c:
            print(f"[cli {host}] recibió: {c.recv(100).decode().strip()}")
    hilo.join(2)
    srv.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("modo", choices=["servidor", "cliente", "demo"])
    p.add_argument("--puerto", type=int, default=8080)
    p.add_argument("--host", default="localhost")
    p.add_argument("--v6only", action="store_true", help="solo IPv6 (rechaza clientes IPv4)")
    a = p.parse_args()

    assert normalizar("::ffff:127.0.0.1") == "127.0.0.1"
    assert normalizar("::1") == "::1"
    assert normalizar("localhost") == "localhost"

    if a.modo == "servidor":
        print(f"Escuchando en [::]:{a.puerto} ({'solo IPv6' if a.v6only else 'dual-stack'})")
        atender(crear_servidor(a.puerto, a.v6only))
    elif a.modo == "cliente":
        with conectar(a.host, a.puerto) as c:
            print(c.recv(100).decode().strip(), "— conectado por", c.getpeername()[0])
    else:
        demo(a.puerto)
