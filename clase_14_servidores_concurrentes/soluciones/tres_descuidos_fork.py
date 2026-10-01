#!/usr/bin/env python3
"""Clase 14 · Ej. 3 (OBLIGATORIO): los tres descuidos del fork, demostrados AUTOMÁTICAMENTE.

    python3 tres_descuidos_fork.py todo          # corre las partes A, A2, B, C y D y muestra los números

    # o el servidor solo, para probar a mano con benchmark.py / nc / ps:
    python3 tres_descuidos_fork.py servidor --padre guardar --sigchld nada --puerto 8080

Opciones del servidor:
    --padre   cerrar | guardar     ¿el padre hace conn.close() o se guarda la conexión en una lista?
    --sigchld nada | sinbucle | bucle | ign   cómo se recogen los hijos
"""
import argparse
import gc
import os
import signal
import socket
import subprocess
import sys
import time

# ════════════════════════ el servidor configurable ════════════════════════
def cosechar_sin_bucle(signum, frame):
    try:
        os.waitpid(-1, os.WNOHANG)           # recoge UNO por señal
    except ChildProcessError:
        pass


def cosechar_con_bucle(signum, frame):
    while True:                               # recoge TODOS los que haya
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return


def servidor(puerto, padre, sigchld):
    handlers = {"sinbucle": cosechar_sin_bucle, "bucle": cosechar_con_bucle, "ign": signal.SIG_IGN}
    if sigchld in handlers:
        signal.signal(signal.SIGCHLD, handlers[sigchld])
    guardadas = []
    srv = socket.create_server(("127.0.0.1", puerto))
    print("LISTO", os.getpid(), srv.getsockname()[1], flush=True)
    while True:
        try:
            conn, _ = srv.accept()
        except InterruptedError:              # (Python ya reintenta solo; por las dudas)
            continue
        pid = os.fork()
        if pid == 0:                          # ── HIJO ──
            srv.close()                       # descuido 2: el hijo no necesita el socket que escucha
            with conn:
                while datos := conn.recv(4096):
                    conn.sendall(datos)
            os._exit(0)
        if padre == "cerrar":                 # ── PADRE ──
            conn.close()                      # descuido 1: SIN esto la conexión no se cierra nunca del todo
        else:
            guardadas.append(conn)            # simula "guardar estadísticas": la referencia sobrevive


# ════════════════════════ herramientas de medición ════════════════════════
def lanzar(padre, sigchld):
    p = subprocess.Popen([sys.executable, __file__, "servidor", "--puerto", "0",
                          "--padre", padre, "--sigchld", sigchld], stdout=subprocess.PIPE, text=True)
    _, pid, puerto = p.stdout.readline().split()
    return p, int(pid), int(puerto)


def n_fds(pid):
    return len(os.listdir(f"/proc/{pid}/fd"))


def hijos(pid):
    """[(pid_hijo, estado)] leyendo /proc (sin depender de `ps`)."""
    res = []
    for e in os.listdir("/proc"):
        if not e.isdigit():
            continue
        try:
            with open(f"/proc/{e}/stat") as f:
                resto = f.read().rsplit(")", 1)[1].split()
        except OSError:
            continue
        if int(resto[1]) == pid:
            res.append((int(e), resto[0]))
    return res


def zombies(pid):
    return sum(1 for _, est in hijos(pid) if est == "Z")


def clientes(puerto, n):
    for _ in range(n):
        with socket.create_connection(("127.0.0.1", puerto)) as c:
            c.sendall(b"hola")
            c.recv(10)
    time.sleep(0.3)


# ════════════════════════ las partes del ejercicio ════════════════════════
def parte_a():
    print("── Parte A: ¿quién cierra un socket que nadie cerró? ──")
    def make():
        return socket.socket().fileno()
    fd = make()
    gc.collect()
    try:
        os.fstat(fd)
        print("  el fd sigue abierto")
    except OSError:
        print(f"  fd {fd} ya está CERRADO: al perder la última referencia, CPython destruyó el objeto")
        print("  socket y su __del__ cerró el descriptor (conteo de referencias). Por eso el bug se esconde.")


def parte_a2():
    print("\n── Parte A2: el padre GUARDA las conexiones ──")
    for padre in ("guardar", "cerrar"):
        p, pid, puerto = lanzar(padre, "bucle")
        antes = n_fds(pid)
        clientes(puerto, 30)
        despues = n_fds(pid)
        # conectar, hablar, matar al hijo que nos atiende y ver si nos enteramos del cierre
        c = socket.create_connection(("127.0.0.1", puerto))
        c.sendall(b"hola")
        c.recv(10)
        time.sleep(0.2)
        hijo = max(h for h, est in hijos(pid) if est != "Z")
        os.kill(hijo, signal.SIGKILL)
        c.settimeout(2)
        try:
            vio = "vio el cierre (recv → b'')" if c.recv(10) == b"" else "recibió datos"
        except TimeoutError:
            vio = "NO se enteró: recv se quedó esperando (timeout)"
        c.close()
        p.kill()
        print(f"  padre={padre:<8} fds del padre: {antes} → {despues} tras 30 clientes · al matar al hijo, el cliente {vio}")
    print("  → tras fork() hay DOS copias del fd de la conexión (padre e hijo). TCP manda el FIN recién cuando")
    print("    se cierra la ÚLTIMA. Si el padre guarda la suya, el hijo puede morir y el cliente no se entera.")


def parte_b():
    print("\n── Parte B: sin cosechar hijos (SIGCHLD por defecto) ──")
    p, pid, puerto = lanzar("cerrar", "nada")
    clientes(puerto, 50)
    z1 = zombies(pid)
    clientes(puerto, 50)
    z2 = zombies(pid)
    p.kill()
    print(f"  zombies tras 50 clientes: {z1} · tras 100: {z2}  → se ACUMULAN (estado Z, <defunct>)")
    print("  durante semanas → se agota la tabla de procesos / el límite de procesos del usuario → fork() falla.")


def experimento_60(con_bucle):
    """El script de la consigna: 60 hijos que mueren a la vez."""
    pid = os.fork()
    if pid:                                         # corremos el experimento en un proceso aparte
        _, status = os.waitpid(pid, 0)
        return os.WEXITSTATUS(status)
    recogidos = [0]

    def cosechar(signum, frame):
        while True:
            try:
                h, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if h == 0:
                return
            recogidos[0] += 1
            if not con_bucle:
                return
    signal.signal(signal.SIGCHLD, cosechar)
    for _ in range(60):
        if os.fork() == 0:
            time.sleep(0.5)                          # todos duermen lo mismo → mueren JUNTOS
            os._exit(0)
    time.sleep(2.0)
    os._exit(min(zombies(os.getpid()), 255))        # devolvemos la cantidad de zombies como código


def parte_c():
    print("\n── Parte C: el cosechador SIN bucle, con 60 hijos muriendo a la vez (5 corridas) ──")
    for con_bucle in (False, True):
        res = [experimento_60(con_bucle) for _ in range(5)]
        print(f"  {'CON bucle' if con_bucle else 'SIN bucle'}: zombies por corrida = {res}")
    print("  → las señales estándar NO se encolan: si mueren 10 hijos antes de que corra el handler, llega UNA")
    print("    SIGCHLD pendiente. Sin bucle se recoge uno y los demás quedan zombies. Es intermitente porque")
    print("    depende de cuántos hijos mueran dentro de la misma 'ventana' antes de que el handler se ejecute.")


def parte_d():
    print("\n── Parte D: signal(SIGCHLD, SIG_IGN) ──")
    p, pid, puerto = lanzar("cerrar", "ign")
    clientes(puerto, 50)
    z = zombies(pid)
    p.kill()
    print(f"  zombies tras 50 clientes: {z}  → con SIG_IGN el KERNEL descarta el estado de salida y nunca")
    print("    quedan zombies (comportamiento POSIX). Contra: el padre ya no puede saber CÓMO terminó cada hijo.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["todo", "servidor"])
    ap.add_argument("--puerto", type=int, default=8080)
    ap.add_argument("--padre", choices=["cerrar", "guardar"], default="cerrar")
    ap.add_argument("--sigchld", choices=["nada", "sinbucle", "bucle", "ign"], default="bucle")
    a = ap.parse_args()
    if a.modo == "servidor":
        servidor(a.puerto, a.padre, a.sigchld)
    else:
        parte_a()
        parte_a2()
        parte_b()
        parte_c()
        parte_d()
