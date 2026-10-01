#!/usr/bin/env python3
"""Clase 4 · Ej. 4: crear un zombie, VERLO (leyendo /proc) y después limpiarlo con wait()."""
import os
import time


def estado(pid):
    with open(f"/proc/{pid}/stat") as f:
        return f.read().rsplit(")", 1)[1].split()[0]     # 3er campo: R/S/Z...


pid = os.fork()
if pid == 0:
    os._exit(7)                    # el hijo termina enseguida

time.sleep(0.5)                    # el padre NO hace wait todavía
print(f"Hijo {pid} en estado: {estado(pid)}   ← Z = zombie (en ps aparece <defunct>)")
print("   (en otra terminal: ps -o pid,stat,cmd --ppid", os.getpid(), ")")

_, status = os.waitpid(pid, 0)     # recoger
print(f"wait() recogió al hijo: código {os.WEXITSTATUS(status)}")
print(f"¿Existe /proc/{pid}? {os.path.exists(f'/proc/{pid}')}   ← ya no hay zombie")
