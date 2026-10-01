#!/usr/bin/env python3
"""Clase 6 · Ej. 6: supervisor que mantiene N workers vivos (los reinicia si mueren).

    python3 supervisor.py --workers 3
    kill -9 <pid de un worker>      → el supervisor lo detecta (SIGCHLD) y lanza otro
    Ctrl+C / kill <pid supervisor>  → manda SIGTERM a todos y espera a que terminen

Tanto SIGCHLD como SIGTERM se manejan con el patrón flag: el handler anota y el
loop principal hace el waitpid / los reinicios.
"""
import argparse
import os
import random
import signal
import time

hubo_sigchld = False
apagar = False


def on_sigchld(sig, frame):
    global hubo_sigchld
    hubo_sigchld = True


def on_shutdown(sig, frame):
    global apagar
    apagar = True


def worker(wid):
    signal.signal(signal.SIGINT, signal.SIG_IGN)         # el Ctrl+C lo maneja el supervisor
    signal.signal(signal.SIGTERM, lambda s, f: os._exit(0))
    random.seed(os.getpid())
    while True:
        time.sleep(random.uniform(0.3, 1.0))
        if random.random() < 0.15:                       # a veces "crashea"
            os._exit(1)


def lanzar(wid):
    pid = os.fork()
    if pid == 0:
        worker(wid)
    print(f"[sup] worker {wid} → PID {pid}")
    return pid


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--duracion", type=float, default=0, help="segundos (0 = hasta Ctrl+C)")
    a = p.parse_args()
    global hubo_sigchld

    signal.signal(signal.SIGCHLD, on_sigchld)
    signal.signal(signal.SIGINT, on_shutdown)
    signal.signal(signal.SIGTERM, on_shutdown)
    vivos = {lanzar(i): i for i in range(a.workers)}     # pid -> id de worker
    reinicios = 0
    fin = time.time() + a.duracion if a.duracion else None

    while not apagar and (fin is None or time.time() < fin):
        time.sleep(0.1)                                  # el sleep se corta si llega una señal
        if hubo_sigchld:
            hubo_sigchld = False
            while True:                                  # pueden haber muerto VARIOS (las señales no se encolan)
                try:
                    pid, status = os.waitpid(-1, os.WNOHANG)
                except ChildProcessError:
                    break
                if pid == 0:
                    break
                wid = vivos.pop(pid)
                causa = (f"código {os.WEXITSTATUS(status)}" if os.WIFEXITED(status)
                         else f"señal {signal.Signals(os.WTERMSIG(status)).name}")
                print(f"[sup] worker {wid} (PID {pid}) murió: {causa} → reinicio")
                vivos[lanzar(wid)] = wid
                reinicios += 1

    print(f"[sup] apagando {len(vivos)} workers…")
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    for pid in vivos:
        os.kill(pid, signal.SIGTERM)
    for pid in vivos:
        os.waitpid(pid, 0)
    print(f"[sup] listo. Reinicios hechos: {reinicios}")


if __name__ == "__main__":
    main()
