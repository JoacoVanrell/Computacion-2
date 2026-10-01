#!/usr/bin/env python3
"""Clase 7 · Ej. 3.2: varios hijos escribiendo en regiones SEPARADAS de un mmap anónimo.

Cada hijo tiene su "casillero" de 4 bytes en el offset i*4 → nadie pisa a nadie → no hace falta lock.
"""
import mmap
import os
import struct

N_HIJOS = 5
mm = mmap.mmap(-1, N_HIJOS * 4)          # -1 = anónimo (sin archivo). fork() lo HEREDA compartido

pids = []
for i in range(N_HIJOS):
    pid = os.fork()
    if pid == 0:
        resultado = sum(range((i + 1) * 1000))        # "trabajo" distinto por hijo
        struct.pack_into("i", mm, i * 4, resultado % 2**31)   # escribe en SU offset
        os._exit(0)
    pids.append(pid)

for pid in pids:
    os.waitpid(pid, 0)

valores = struct.unpack_from(f"{N_HIJOS}i", mm, 0)
print("Resultados de cada hijo:", valores)
assert list(valores) == [sum(range((i + 1) * 1000)) % 2**31 for i in range(N_HIJOS)]
mm.close()
