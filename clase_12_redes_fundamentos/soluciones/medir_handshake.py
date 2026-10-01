#!/usr/bin/env python3
"""Clase 12 · Adicional: cuánto cuesta el handshake TCP (local vs remoto).

    python3 medir_handshake.py [host_remoto] [puerto]

create_connection() vuelve cuando terminó el handshake de 3 vías (SYN → SYN-ACK → ACK),
así que su duración ≈ 1 RTT (ida y vuelta) + resolver el nombre por DNS.
"""
import socket
import statistics
import sys
import threading
import time


def medir(host, puerto, n=10):
    tiempos = []
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, puerto), timeout=3):
                tiempos.append((time.perf_counter() - t0) * 1000)
        except OSError as e:
            return None, str(e)
    return tiempos, None


def aceptar_siempre(srv):
    """Servidor local mínimo: acepta y cierra, para tener contra quién medir."""
    while True:
        conn, _ = srv.accept()
        conn.close()


if __name__ == "__main__":
    srv = socket.create_server(("127.0.0.1", 0))
    threading.Thread(target=aceptar_siempre, args=(srv,), daemon=True).start()
    destinos = [("127.0.0.1", srv.getsockname()[1])]
    remoto = (sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 80) if len(sys.argv) > 1 else ("example.com", 80)
    destinos.append(remoto)

    for host, puerto in destinos:
        tiempos, error = medir(host, puerto)
        if error:
            print(f"{host}:{puerto:<6} no se pudo conectar ({error})")
        else:
            print(f"{host}:{puerto:<6} mediana {statistics.median(tiempos):8.3f} ms   "
                  f"(min {min(tiempos):.3f} · max {max(tiempos):.3f})")
    print("\nLa diferencia es la distancia: en local el 'viaje' no sale de la máquina (µs);\n"
          "hacia afuera cada handshake paga un RTT completo por la red (decenas de ms) + DNS.")
