#!/usr/bin/env python3
"""Clase 3 · Adicional: cuántos procesos tiene cada usuario (leyendo /proc, sin `ps`).

El UID real está en la línea "Uid:" de /proc/<pid>/status (primer número).
"""
import os
import pwd
from collections import Counter


def uid_de(pid):
    with open(f"/proc/{pid}/status") as f:
        for linea in f:
            if linea.startswith("Uid:"):
                return int(linea.split()[1])          # real, efectivo, guardado, fs
    return None


conteo = Counter()
for entrada in os.listdir("/proc"):
    if not entrada.isdigit():                        # cada proceso = un directorio numérico
        continue
    try:
        uid = uid_de(entrada)
    except (FileNotFoundError, ProcessLookupError):
        continue                                     # el proceso terminó mientras leíamos
    try:
        nombre = pwd.getpwuid(uid).pw_name
    except KeyError:
        nombre = str(uid)
    conteo[nombre] += 1

for usuario, n in conteo.most_common():
    print(f"{usuario:<15} {n:>5}")
print(f"{'TOTAL':<15} {sum(conteo.values()):>5}")
