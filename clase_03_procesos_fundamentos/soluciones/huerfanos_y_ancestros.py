#!/usr/bin/env python3
"""Clase 3 · Ej. 2 + adicional "detector de huérfanos".

1) Sube la jerarquía desde este proceso hasta el PID 1 (lo que pide el ej. 2).
2) Lista los procesos cuyo PPID es 1 (adoptados por init/systemd).

Del archivo /proc/<pid>/stat: "pid (comando) estado ppid ...". El comando va entre
paréntesis y PUEDE tener espacios, por eso partimos desde el último ')'.
"""
import os


def leer_stat(pid):
    with open(f"/proc/{pid}/stat") as f:
        datos = f.read()
    comando = datos[datos.index("(") + 1:datos.rindex(")")]
    resto = datos[datos.rindex(")") + 2:].split()
    estado, ppid = resto[0], int(resto[1])
    return comando, estado, ppid


print("== Cadena de ancestros ==")
pid = os.getpid()
while pid > 0:
    comando, estado, ppid = leer_stat(pid)
    print(f"  PID {pid:>6}  {comando:<20} estado={estado}  padre={ppid}")
    pid = ppid                          # el PID 1 tiene PPID 0 → corta el bucle

print("\n== Procesos con PPID 1 (hijos de init/systemd o huérfanos adoptados) ==")
for entrada in sorted(os.listdir("/proc"), key=lambda x: int(x) if x.isdigit() else 0):
    if not entrada.isdigit() or entrada == "1":
        continue
    try:
        comando, estado, ppid = leer_stat(entrada)
    except FileNotFoundError:
        continue
    if ppid == 1:
        print(f"  PID {entrada:>6}  {comando}")
