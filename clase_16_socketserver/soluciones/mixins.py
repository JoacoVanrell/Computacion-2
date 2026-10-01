#!/usr/bin/env python3
"""Clase 16 · Ej. 2 (OBLIGATORIO): los mixins de socketserver — leer, ordenar, forking y daemon_threads.

    python3 mixins.py            # corre las partes A, B, C y D y muestra resultados medidos
"""
import inspect
import multiprocessing
import socket
import socketserver
import subprocess
import sys
import textwrap
import threading
import time


# ════════════════════════ Parte A: leer el código ════════════════════════
def parte_a():
    print("── Parte A: qué sobreescribe cada mixin ──")
    for mixin in (socketserver.ThreadingMixIn, socketserver.ForkingMixIn):
        propios = [n for n, v in vars(mixin).items() if callable(v) and not n.startswith("__")]
        print(f"  {mixin.__name__}: métodos propios {propios}")
    print("  → la concurrencia la produce process_request(): BaseServer lo hace EN EL MISMO hilo")
    print("    (finish_request + shutdown_request); el mixin lo reemplaza por 'lanzar thread/fork y volver'.")
    print("  ForkingMixIn cosecha en collect_children(), llamado desde service_actions() (en CADA vuelta del")
    print("    loop de serve_forever), desde handle_timeout() y al cerrar; además cierra el socket del cliente")
    print("    en el padre (close_request) → los 3 descuidos de la clase 14 ya vienen resueltos.")
    src = inspect.getsource(socketserver.ThreadingTCPServer).strip()
    print(f"  Código propio de ThreadingTCPServer:\n{textwrap.indent(src, '      ')}")


# ════════════════════════ Parte B: el orden (MRO) ════════════════════════
class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    allow_reuse_address = True
    daemon_threads = True


class Lento(socketserver.BaseRequestHandler):
    def handle(self):
        time.sleep(1)
        self.request.sendall(b"listo")


def medir(clase_servidor, n=3):
    srv = clase_servidor(("127.0.0.1", 0), Lento)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    puerto = srv.server_address[1]

    def cliente(_):
        with socket.create_connection(("127.0.0.1", puerto)) as c:
            c.sendall(b"x")
            return c.recv(10)
    t0 = time.perf_counter()
    hs = [threading.Thread(target=cliente, args=(i,)) for i in range(n)]
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    srv.shutdown()
    srv.server_close()
    return time.perf_counter() - t0


def parte_b():
    print("\n── Parte B: el orden de herencia ──")
    for C in (Bien, Mal):
        mro = [k.__name__ for k in C.__mro__][:4]
        quien = next(k.__name__ for k in C.__mro__ if "process_request" in k.__dict__)
        print(f"  {C.__name__:<5} MRO {mro}  → process_request de {quien}")
    for C in (Bien, Mal):
        print(f"  {C.__name__:<5} 3 clientes que tardan 1 s: {medir(C):.2f}s")
    print("  → 'Mal' NO tira ningún error: anda, pero secuencial. Solo se nota con carga → bug traicionero.")
    print("    Regla: los mixins SIEMPRE a la izquierda.")


# ════════════════════════ Parte C: forking y memoria ════════════════════════
class ContadorIngenuo(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.visitas = 0                         # int común: cada hijo modifica SU copia


class ContadorCompartido(socketserver.ForkingTCPServer):
    allow_reuse_address = True

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        # en el __init__ del SERVIDOR (antes de cualquier fork): así todos los hijos heredan
        # el MISMO bloque de memoria compartida. Creado en el handler, sería uno nuevo por cliente.
        self.visitas = multiprocessing.Value("i", 0)


class HandlerContador(socketserver.StreamRequestHandler):
    def handle(self):
        v = self.server.visitas
        if isinstance(v, int):
            self.server.visitas += 1
            n = self.server.visitas
        else:
            with v.get_lock():                   # += sobre memoria compartida: proteger
                v.value += 1
                n = v.value
        self.wfile.write(f"visita {n}\n".encode())


def parte_c():
    print("\n── Parte C: ForkingTCPServer y el estado ──")
    for clase in (ContadorIngenuo, ContadorCompartido):
        srv = clase(("127.0.0.1", 0), HandlerContador)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        respuestas = []
        for _ in range(3):
            with socket.create_connection(("127.0.0.1", srv.server_address[1])) as c:
                respuestas.append(c.recv(100).decode().strip())
        srv.shutdown()
        srv.server_close()
        print(f"  {clase.__name__:<19} → {respuestas}")
    print("  → con fork cada hijo tiene una COPIA de la memoria del padre (clase 4): incrementa su copia y muere.")
    print("    No es un problema de sincronización sino de AISLAMIENTO → hace falta memoria compartida (Value).")


# ════════════════════════ Parte D: daemon_threads ════════════════════════
SERVIDOR_D = """
import socketserver, sys, time
class H(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.recv(10)          # se queda esperando al cliente
class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = {daemon}
s = S(("127.0.0.1", 0), H)
print(s.server_address[1], flush=True)
try:
    s.serve_forever()
except KeyboardInterrupt:
    s.server_close()                     # ThreadingMixIn.server_close() hace join de los threads NO daemon
"""


def parte_d():
    print("\n── Parte D: daemon_threads con un cliente conectado y Ctrl+C ──")
    for daemon in (False, True):
        p = subprocess.Popen([sys.executable, "-c", SERVIDOR_D.format(daemon=daemon)], stdout=subprocess.PIPE, text=True)
        puerto = int(p.stdout.readline())
        c = socket.create_connection(("127.0.0.1", puerto))
        time.sleep(0.3)
        p.send_signal(2)                          # SIGINT = Ctrl+C
        try:
            p.wait(timeout=2)
            resultado = f"terminó en el acto (código {p.returncode})"
        except subprocess.TimeoutExpired:
            resultado = "SIGUE VIVO esperando que el cliente se vaya (tuve que matarlo)"
            p.kill()
        c.close()
        print(f"  daemon_threads={daemon!s:<5} → {resultado}")
    print("  → sin daemon, al cerrar se espera (join) a cada thread de cliente: un cliente colgado frena el apagado.")


if __name__ == "__main__":
    parte_a()
    parte_b()
    parte_c()
    parte_d()
