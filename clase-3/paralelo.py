#!/usr/bin/env python3
"""
Ejecutor de comandos en paralelo.
Uso: python3 paralelo.py "cmd1" "cmd2" ...
"""
import os
import sys
import time

def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} comando1 [comando2 ...]")
        sys.exit(1)

    comandos = sys.argv[1:]
    procesos = {}  # pid -> comando
    inicio = time.time()

    # Loop 1: lanzar todos en paralelo
    for cmd in comandos:
        pid = os.fork()

        if pid == 0:
            # Hijo: ejecutar el comando
            partes = cmd.split()
            try:
                os.execvp(partes[0], partes)
            except OSError as e:
                print(f"Error ejecutando '{cmd}': {e}", file=sys.stderr)
                os._exit(127)
        else:
            # Padre: registrar el hijo
            procesos[pid] = cmd
            print(f"[{pid}] Iniciado: {cmd}")

    # Loop 2: esperar a todos
    exitosos = 0
    fallidos = 0

    while procesos:
        pid, status = os.wait()
        cmd = procesos.pop(pid)
        codigo = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1

        print(f"[{pid}] Terminado: {cmd} (código: {codigo})")

        if codigo == 0:
            exitosos += 1
        else:
            fallidos += 1

    tiempo_total = time.time() - inicio

    print(f"\nResumen:")
    print(f"- Comandos ejecutados: {len(comandos)}")
    print(f"- Exitosos: {exitosos}")
    print(f"- Fallidos: {fallidos}")
    print(f"- Tiempo total: {tiempo_total:.2f}s")

if __name__ == "__main__":
    main()