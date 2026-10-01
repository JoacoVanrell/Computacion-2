#!/usr/bin/env python3
"""Clase 4 · Ej. 5 (OBLIGATORIO): mini-shell con el patrón fork + exec + wait.

Cumple la consigna (prompt, exit, cd interno, fork+exec+wait, mostrar código != 0) y agrega:
  - comandos en background con '&' al final (no se espera al hijo)
  - cosecha de hijos en background con waitpid(-1, WNOHANG) → no quedan zombies
  - 'export VAR=valor' (interno: tiene que cambiar el entorno DEL SHELL)
  - muestra si un hijo murió por una señal (ej: kill -9)

    python3 mini_shell.py
"""
import os
import shlex
import signal
import sys


def cosechar_background(bg):
    """Recoge hijos en background que ya terminaron, SIN bloquear."""
    while bg:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:          # no quedan hijos
            break
        if pid == 0:                       # hay hijos, pero ninguno terminó todavía
            break
        cmd = bg.pop(pid, "?")
        print(f"[{pid}] terminó: {cmd} ({describir(status)})")


def describir(status):
    if os.WIFEXITED(status):
        return f"código {os.WEXITSTATUS(status)}"
    if os.WIFSIGNALED(status):
        return f"muerto por señal {signal.Signals(os.WTERMSIG(status)).name}"
    return "estado raro"


def internos(partes):
    """Ejecuta comandos internos. Devuelve True si lo era (y no hay que hacer fork)."""
    cmd = partes[0]
    if cmd == "exit":
        sys.exit(int(partes[1]) if len(partes) > 1 else 0)
    if cmd == "cd":
        # INTERNO: si lo hiciera un hijo, cambiaría SU directorio y al morir se perdería.
        try:
            os.chdir(os.path.expanduser(partes[1]) if len(partes) > 1 else os.environ["HOME"])
        except OSError as e:
            print(f"cd: {e.strerror}: {partes[1]}")
        return True
    if cmd == "export":
        for asignacion in partes[1:]:
            if "=" in asignacion:
                clave, valor = asignacion.split("=", 1)
                os.environ[clave] = valor      # los hijos futuros lo heredan
        return True
    return False


def ejecutar(partes, en_background, bg):
    pid = os.fork()
    if pid == 0:                               # ─── HIJO ───
        try:
            os.execvp(partes[0], partes)       # si anda, NUNCA vuelve
        except FileNotFoundError:
            print(f"{partes[0]}: comando no encontrado", file=sys.stderr)
            os._exit(127)                      # 127 = convención de "command not found"
        except PermissionError:
            print(f"{partes[0]}: permiso denegado", file=sys.stderr)
            os._exit(126)
    # ─── PADRE ───
    if en_background:
        bg[pid] = " ".join(partes)
        print(f"[{pid}] en background")
        return
    _, status = os.waitpid(pid, 0)             # esperar a ESTE hijo (no a uno en background)
    if not (os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0):
        print(f"[{describir(status)}]")


def main():
    bg = {}                                    # pid -> comando de los procesos en background
    while True:
        cosechar_background(bg)
        try:
            linea = input(f"{os.path.basename(os.getcwd()) or '/'} $ ")
        except EOFError:                       # Ctrl+D
            print()
            break
        except KeyboardInterrupt:              # Ctrl+C: nueva línea, no cierra el shell
            print()
            continue
        try:
            partes = shlex.split(linea)        # respeta comillas: echo "hola mundo"
        except ValueError as e:
            print(f"error de sintaxis: {e}")
            continue
        if not partes:
            continue
        en_background = partes[-1] == "&"
        if en_background:
            partes = partes[:-1]
            if not partes:
                continue
        if not internos(partes):
            ejecutar(partes, en_background, bg)


if __name__ == "__main__":
    main()
