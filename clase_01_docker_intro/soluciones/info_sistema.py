#!/usr/bin/env python3
"""Clase 1 · Ejercicio de síntesis: info del sistema, para comparar host vs contenedores.

    python3 info_sistema.py
    docker run --rm -v "$(pwd)":/app -w /app python:3.11 python info_sistema.py
    docker run --rm -v "$(pwd)":/app -w /app python:3.9  python info_sistema.py
"""
import os
import platform
import sys


def memoria():
    """Lee /proc/meminfo (Linux). Devuelve (total_MB, disponible_MB) o None."""
    try:
        datos = {}
        with open("/proc/meminfo") as f:
            for linea in f:
                clave, valor = linea.split(":", 1)
                datos[clave] = int(valor.split()[0])      # viene en kB
        return datos["MemTotal"] // 1024, datos["MemAvailable"] // 1024
    except (OSError, KeyError, ValueError):
        return None


def os_release():
    """Nombre lindo de la distro (en un contenedor es la de la IMAGEN, no la del host)."""
    try:
        with open("/etc/os-release") as f:
            for linea in f:
                if linea.startswith("PRETTY_NAME="):
                    return linea.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


print(f"Python      : {platform.python_version()} ({sys.executable})")
print(f"Distro      : {os_release()}")
print(f"Kernel      : {platform.system()} {platform.release()}")
print(f"CPUs        : {os.cpu_count()}")
mem = memoria()
print(f"Memoria     : {mem[1]} MB libres de {mem[0]} MB" if mem else "Memoria     : no disponible")
print(f"Hostname    : {platform.node()}")
print("Variables PYTHON*:")
for k, v in sorted(os.environ.items()):
    if k.startswith("PYTHON"):
        print(f"   {k}={v}")
