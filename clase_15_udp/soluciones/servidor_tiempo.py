#!/usr/bin/env python3
"""Clase 15 · Adicional: servidor de tiempo estilo RFC 868 sobre UDP, y cliente que calcula el desfasaje.

    python3 servidor_tiempo.py servidor [--puerto 8037]
    python3 servidor_tiempo.py cliente  [--host localhost] [--puerto 8037]
    python3 servidor_tiempo.py demo

RFC 868 manda los segundos desde 1900 en 4 bytes big-endian. (Le sumamos 2208988800 = segundos
entre 1900 y 1970, el epoch de Unix.) Como tiene resolución de 1 s, mandamos también los
microsegundos en otros 4 bytes para que el desfasaje sea interesante.
"""
import argparse
import socket
import struct
import threading
import time

DESDE_1900 = 2_208_988_800


def servidor(puerto, listo=None):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("0.0.0.0", puerto))
        if listo:
            listo.set()
        while True:
            _, origen = s.recvfrom(64)          # cualquier datagrama = "¿qué hora es?"
            t = time.time()
            s.sendto(struct.pack("!II", int(t) + DESDE_1900, int((t % 1) * 1e6)), origen)


def cliente(host, puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(2)                          # UDP: sin timeout esperaríamos para siempre
        t_envio = time.time()
        s.sendto(b"", (host, puerto))
        datos, _ = s.recvfrom(64)
        t_llegada = time.time()
    seg, micro = struct.unpack("!II", datos)
    t_servidor = seg - DESDE_1900 + micro / 1e6
    rtt = t_llegada - t_envio
    desfasaje = t_servidor - (t_envio + rtt / 2)     # suponemos que la ida y la vuelta tardan lo mismo
    print(f"hora del servidor: {time.strftime('%H:%M:%S', time.localtime(t_servidor))} · "
          f"RTT {rtt * 1000:.3f} ms · desfasaje estimado {desfasaje * 1000:+.3f} ms")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["servidor", "cliente", "demo"])
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--puerto", type=int, default=8037)
    a = ap.parse_args()
    if a.modo == "servidor":
        servidor(a.puerto)
    elif a.modo == "cliente":
        cliente(a.host, a.puerto)
    else:
        listo = threading.Event()
        threading.Thread(target=servidor, args=(a.puerto, listo), daemon=True).start()
        listo.wait()
        cliente("127.0.0.1", a.puerto)
