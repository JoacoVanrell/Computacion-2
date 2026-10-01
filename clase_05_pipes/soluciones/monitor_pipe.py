#!/usr/bin/env python3
"""Clase 5 · Adicional: monitor que se mete en el medio de un pipeline.

    cat /etc/services | python3 monitor_pipe.py | wc -l

Pasa los datos tal cual por stdout y manda las estadísticas por STDERR
(si las mandara por stdout, se mezclarían con los datos que lee el siguiente comando).
"""
import sys
import time

total_bytes = lineas = 0
inicio = time.time()
entrada, salida = sys.stdin.buffer, sys.stdout.buffer
for linea in entrada:
    salida.write(linea)
    total_bytes += len(linea)
    lineas += 1
    if lineas % 1000 == 0:
        print(f"[monitor] {lineas} líneas, {total_bytes} bytes...", file=sys.stderr)
salida.flush()
dur = time.time() - inicio
print(f"[monitor] total: {lineas} líneas, {total_bytes} bytes en {dur:.3f}s", file=sys.stderr)
