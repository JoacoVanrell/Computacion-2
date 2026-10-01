#!/usr/bin/env python3
"""Clase 12 · Adicional: escaneo de puertos TCP de TU PROPIA máquina (y comparar con `ss -tlnp`).

    python3 escaneo_puertos.py               # 1..1024 en 127.0.0.1
    python3 escaneo_puertos.py --hasta 65535

⚠️ Solo contra localhost: escanear máquinas ajenas sin permiso es ilegal en muchos lugares.
Por eso el host está fijo en 127.0.0.1.

connect_ex() devuelve 0 si alguien aceptó la conexión (puerto abierto) y un código de error
(ECONNREFUSED) si no hay nadie escuchando. Uso un pool de threads porque es I/O-bound.
"""
import argparse
import socket
from concurrent.futures import ThreadPoolExecutor

HOST = "127.0.0.1"


def probar(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return puerto if s.connect_ex((HOST, puerto)) == 0 else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", type=int, default=1)
    ap.add_argument("--hasta", type=int, default=1024)
    a = ap.parse_args()
    with ThreadPoolExecutor(max_workers=100) as pool:
        abiertos = [p for p in pool.map(probar, range(a.desde, a.hasta + 1)) if p]
    print(f"Puertos TCP abiertos en {HOST} ({a.desde}-{a.hasta}):")
    for p in abiertos:
        try:
            servicio = socket.getservbyport(p, "tcp")      # nombre según /etc/services
        except OSError:
            servicio = "?"
        print(f"  {p:>5}  {servicio}")
    if not abiertos:
        print("  (ninguno)")
    print("\nCompará con:  ss -tlnp")
