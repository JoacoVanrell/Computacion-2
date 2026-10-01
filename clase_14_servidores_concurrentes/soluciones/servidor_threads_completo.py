#!/usr/bin/env python3
"""Clase 14 · Adicionales juntos: servidor de threads con LÍMITE de conexiones, comando STATS
y CIERRE ORDENADO.

    python3 servidor_threads_completo.py --max 3 --puerto 8080
    nc localhost 8080     → cualquier línea vuelve como eco ·  STATS  ·  QUIT
    Ctrl+C                → deja de aceptar, espera hasta 5 s a que los clientes terminen, y sale

- Límite: pasado --max clientes simultáneos responde "503 servidor ocupado" y cierra (no los deja colgados).
- STATS: activos, total atendidos, bytes, uptime. Los contadores son COMPARTIDOS entre threads → Lock.
- Cierre ordenado: threading.Event "apagando"; los hilos NO son daemon y se hace join con timeout.
"""
import argparse
import signal
import socket
import threading
import time


class Estadisticas:
    def __init__(self):
        self.lock = threading.Lock()
        self.activos = self.total = self.bytes = self.rechazados = 0
        self.inicio = time.time()

    def texto(self):
        with self.lock:                       # leer TODO junto, para que los números sean coherentes entre sí
            return (f"activos={self.activos} total={self.total} rechazados={self.rechazados} "
                    f"bytes={self.bytes} uptime={time.time() - self.inicio:.0f}s")


def atender(conn, stats, apagando):
    conn.settimeout(1.0)                      # para poder revisar 'apagando' cada tanto
    with conn, conn.makefile("rwb") as f:
        while not apagando.is_set():
            try:
                linea = f.readline()
            except TimeoutError:
                continue
            except (ConnectionResetError, OSError):
                break
            if not linea:
                break
            with stats.lock:
                stats.bytes += len(linea)
            cmd = linea.strip().upper()
            if cmd == b"STATS":
                f.write(stats.texto().encode() + b"\n")
            elif cmd == b"QUIT":
                f.write(b"chau\n")
                f.flush()
                break
            else:
                f.write(linea)
            f.flush()
        else:
            try:
                f.write(b"servidor apagandose\n")
                f.flush()
            except OSError:
                pass
    with stats.lock:
        stats.activos -= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=8080)
    ap.add_argument("--max", type=int, default=10)
    a = ap.parse_args()

    stats, apagando, hilos = Estadisticas(), threading.Event(), []
    signal.signal(signal.SIGINT, lambda s, f: apagando.set())
    signal.signal(signal.SIGTERM, lambda s, f: apagando.set())

    srv = socket.create_server(("0.0.0.0", a.puerto))
    srv.settimeout(0.5)                        # accept() con timeout → podemos revisar 'apagando'
    print(f"escuchando en :{a.puerto} (máx {a.max} clientes)", flush=True)
    while not apagando.is_set():
        try:
            conn, _ = srv.accept()
        except TimeoutError:
            continue
        with stats.lock:                       # chequear y sumar JUNTOS (si no, dos podrían pasar el límite)
            lleno = stats.activos >= a.max
            if lleno:
                stats.rechazados += 1
            else:
                stats.activos += 1
                stats.total += 1
        if lleno:
            with conn:
                conn.sendall(b"503 servidor ocupado\n")
            continue
        h = threading.Thread(target=atender, args=(conn, stats, apagando))   # NO daemon
        h.start()
        hilos.append(h)
        hilos = [x for x in hilos if x.is_alive()]

    srv.close()
    print("apagando: espero a los clientes (máx 5 s)…", flush=True)
    limite = time.time() + 5
    for h in hilos:
        h.join(max(0, limite - time.time()))
    print("listo:", stats.texto(), flush=True)


if __name__ == "__main__":
    main()
