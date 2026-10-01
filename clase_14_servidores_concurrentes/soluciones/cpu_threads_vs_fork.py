#!/usr/bin/env python3
"""Clase 14 · Ej. 6: un servidor que hace trabajo de CPU real — threads vs fork, medido.

    python3 cpu_threads_vs_fork.py --clientes 8

Levanta los dos servidores (cada cliente pide un cálculo CPU-bound) y los mide con N clientes a la vez.
Con GIL: los threads se turnan el intérprete → no escalan. Con fork: cada hijo es un intérprete
aparte → usan varios núcleos.
"""
import argparse
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor


def trabajo_cpu(n=2_000_000):
    total = 0
    for i in range(n):
        total += i * i
    return total


def responder(conn):
    with conn:
        if conn.recv(100):
            conn.sendall(str(trabajo_cpu()).encode())


def servidor_threads(srv):
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=responder, args=(conn,), daemon=True).start()


def servidor_fork(srv):
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)
    while True:
        conn, _ = srv.accept()
        if os.fork() == 0:
            srv.close()
            responder(conn)
            os._exit(0)
        conn.close()


def medir(puerto, n):
    def cliente(_):
        with socket.create_connection(("127.0.0.1", puerto)) as c:
            c.sendall(b"calcula")
            return c.recv(100)
    t0 = time.perf_counter()
    with ThreadPoolExecutor(n) as pool:
        list(pool.map(cliente, range(n)))
    return time.perf_counter() - t0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clientes", type=int, default=8)
    n = ap.parse_args().clientes
    gil = getattr(sys, "_is_gil_enabled", lambda: True)()
    print(f"nproc = {os.cpu_count()} · Python {'CON' if gil else 'SIN'} GIL\n")
    t0 = time.perf_counter()
    trabajo_cpu()
    uno = time.perf_counter() - t0
    print(f"1 cálculo solo: {uno:.2f}s → {n} en serie serían ~{uno * n:.2f}s")
    for nombre, estrategia in (("threads", servidor_threads), ("fork", servidor_fork)):
        srv = socket.create_server(("127.0.0.1", 0))
        pid = os.fork()
        if pid == 0:
            estrategia(srv)
        srv_puerto = srv.getsockname()[1]
        srv.close()
        t = medir(srv_puerto, n)
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        print(f"{nombre:<8} {n} clientes: {t:.2f}s  (speedup vs serie {uno * n / t:.1f}x)")
