#!/usr/bin/env python3
import sys, os, platform

print("=== Version de Python ===")
print(sys.version)

print("\n=== Sistema Operativo ===")
print(platform.system(), platform.version())

print("\n=== CPUs disponibles ===")
print(os.cpu_count())

print("\n=== Memoria disponible ===")
try:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith(("MemTotal", "MemAvailable")):
                print(line.strip())
except FileNotFoundError:
    print("No disponible en este sistema")

print("\n=== Variables de entorno PYTHON* ===")
for k, v in os.environ.items():
    if k.startswith("PYTHON"):
        print(f"{k}={v}")
