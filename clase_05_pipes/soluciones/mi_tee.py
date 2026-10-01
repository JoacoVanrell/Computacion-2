#!/usr/bin/env python3
"""Clase 5 · Adicional: tee casero. Copia stdin a stdout Y a uno o más archivos.

    ls -la | python3 mi_tee.py salida.txt
    ls -la | python3 mi_tee.py -a salida.txt otra.txt     # -a = append
"""
import argparse
import os
import sys

p = argparse.ArgumentParser()
p.add_argument("archivos", nargs="+")
p.add_argument("-a", "--append", action="store_true")
args = p.parse_args()

flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if args.append else os.O_TRUNC)
fds = [os.open(a, flags, 0o644) for a in args.archivos]
try:
    while True:
        bloque = os.read(0, 65536)        # leemos BYTES crudos del fd 0 (sirve para binarios)
        if not bloque:                    # b"" = EOF: el escritor del pipe cerró
            break
        for fd in [1] + fds:
            os.write(fd, bloque)          # (para bloques enormes habría que repetir hasta escribir todo)
except BrokenPipeError:                   # el que leía nuestro stdout se fue (ej: | head)
    pass
finally:
    for fd in fds:
        os.close(fd)
