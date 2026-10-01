#!/usr/bin/env python3
"""Clase 3 · Ej. 3: clasificar las regiones de /proc/<pid>/maps en text/data/heap/stack/libs.

    python3 segmentos_memoria.py            # analiza su propio proceso
    python3 segmentos_memoria.py 1234       # analiza otro PID (si tenés permiso)

Formato de cada línea de maps:
    inicio-fin  permisos  offset  dev  inodo  ruta
    55d1...-55d1...  r-xp  00001000  08:01  1234  /usr/bin/python3.11
"""
import os
import sys


def clasificar(permisos, ruta, ejecutable, anterior=""):
    if ruta == "" and anterior == ejecutable and "w" in permisos:
        return "BSS (globales sin inicializar, en cero)"
    if ruta == "[heap]":
        return "HEAP"
    if ruta == "[stack]":
        return "STACK"
    if ruta in ("[vdso]", "[vvar]", "[vsyscall]"):
        return "kernel (vdso)"
    if ruta == ejecutable:
        if "x" in permisos:
            return "TEXT (código del ejecutable)"
        if "w" in permisos:
            return "DATA (globales inicializadas)"
        return "solo lectura del ejecutable (constantes)"
    if ".so" in ruta:
        return "librería compartida" + (" (código)" if "x" in permisos else "")
    if ruta == "":
        return "anónima (malloc grande / mmap)"
    return "archivo mapeado"


def main():
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else os.getpid()
    ejecutable = os.path.realpath(f"/proc/{pid}/exe")
    print(f"PID {pid} → ejecutable {ejecutable}\n")
    print(f"{'rango':<34} {'perm':<5} {'tamaño':>9}  tipo")
    anterior = ""
    with open(f"/proc/{pid}/maps") as f:
        for linea in f:
            partes = linea.split(maxsplit=5)
            rango, permisos = partes[0], partes[1]
            ruta = partes[5].strip() if len(partes) == 6 else ""
            ini, fin = (int(x, 16) for x in rango.split("-"))
            kb = (fin - ini) // 1024
            tipo = clasificar(permisos, ruta, ejecutable, anterior)
            anterior = ruta
            nombre = os.path.basename(ruta) if ruta.startswith("/") else ruta
            print(f"{rango:<34} {permisos:<5} {kb:>7} kB  {tipo:<38} {nombre}")


if __name__ == "__main__":
    main()
