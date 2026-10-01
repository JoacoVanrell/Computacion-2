#!/usr/bin/env python3
"""Clase 5 · Ej. 5 (OBLIGATORIO): mini-shell con redirección... y pipelines.

Soporta:
    cmd > archivo      stdout a archivo (trunca)          ← obligatorio
    cmd >> archivo     stdout a archivo (agrega)          ← bonus
    cmd < archivo      stdin desde archivo                ← bonus
    cmd 2> archivo     stderr a archivo                   ← extra
    a | b | c          pipeline de N comandos             ← extra (lo que viene en la teoría)
    cd, exit           internos

    python3 minish.py
"""
import os
import re
import shlex
import sys

REDIRS = {">", ">>", "<", "2>"}


def parsear_comando(tokens):
    """['sort', '<', 'in.txt', '>', 'out'] -> {'argv': ['sort'], '<': 'in.txt', '>': 'out'}"""
    cmd = {"argv": []}
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in REDIRS:
            if i + 1 >= len(tokens):
                raise ValueError(f"falta el archivo después de '{t}'")
            cmd[t] = tokens[i + 1]
            i += 2
        else:
            cmd["argv"].append(t)
            i += 1
    if not cmd["argv"]:
        raise ValueError("comando vacío")
    return cmd


def parsear_linea(linea):
    """Divide por '|' y parsea cada comando. shlex respeta las comillas ("a | b" no es un pipe)."""
    # "2>" solo es redirección de stderr si está pegado y empieza una palabra ("ls 2> e.txt"),
    # no en "echo 2 > x". Lo marcamos con un caracter invisible ANTES de que shlex lo separe.
    MARCA = "\x01"
    linea = re.sub(r"(^|\s)2>", lambda m: m.group(1) + MARCA, linea)
    lexer = shlex.shlex(linea, posix=True, punctuation_chars="|<>")
    lexer.whitespace_split = True
    unidos = []
    for t in lexer:
        if t == MARCA:
            unidos.append("2>")
        elif t.startswith(MARCA):                 # "2>err.txt" sin espacio
            unidos += ["2>", t[1:]]
        else:
            unidos.append(t.replace(MARCA, "2>"))  # estaba dentro de comillas: lo devolvemos
    comandos, actual = [], []
    for t in unidos:
        if t == "|":
            comandos.append(parsear_comando(actual))
            actual = []
        else:
            actual.append(t)
    comandos.append(parsear_comando(actual))
    return comandos


def aplicar_redirecciones(cmd):
    """Se llama en el HIJO, antes del exec. dup2 hace que 0/1/2 apunten al archivo."""
    if "<" in cmd:
        fd = os.open(cmd["<"], os.O_RDONLY)
        os.dup2(fd, 0)
        os.close(fd)
    if ">" in cmd:
        fd = os.open(cmd[">"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(fd, 1)
        os.close(fd)
    if ">>" in cmd:
        fd = os.open(cmd[">>"], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        os.dup2(fd, 1)
        os.close(fd)
    if "2>" in cmd:
        fd = os.open(cmd["2>"], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        os.dup2(fd, 2)
        os.close(fd)


def ejecutar_pipeline(comandos):
    """
    Para N comandos hacen falta N-1 pipes:
        cmd0 ──pipe0──► cmd1 ──pipe1──► cmd2
    El hijo i lee de pipe[i-1] y escribe en pipe[i].
    """
    pipes = [os.pipe() for _ in range(len(comandos) - 1)]
    pids = []
    for i, cmd in enumerate(comandos):
        pid = os.fork()
        if pid == 0:
            if i > 0:                                  # no soy el primero: stdin <- pipe anterior
                os.dup2(pipes[i - 1][0], 0)
            if i < len(comandos) - 1:                  # no soy el último: stdout -> pipe siguiente
                os.dup2(pipes[i][1], 1)
            for r, w in pipes:                         # CLAVE: cerrar TODOS los extremos originales
                os.close(r)                            # (si queda un escritor abierto, el lector
                os.close(w)                            #  nunca ve EOF y se cuelga)
            try:
                aplicar_redirecciones(cmd)             # una redirección explícita gana al pipe
                os.execvp(cmd["argv"][0], cmd["argv"])
            except FileNotFoundError as e:
                print(f"minish: {e.filename or cmd['argv'][0]}: no existe", file=sys.stderr)
                os._exit(127)
            except OSError as e:
                print(f"minish: {e}", file=sys.stderr)
                os._exit(126)
        pids.append(pid)
    for r, w in pipes:                                 # el padre tampoco usa los pipes
        os.close(r)
        os.close(w)
    status = 0
    for pid in pids:
        _, status = os.waitpid(pid, 0)
    return os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status)


def main():
    while True:
        try:
            linea = input("minish$ ").strip()
        except EOFError:
            print("\nChau!")
            break
        if not linea:
            continue
        try:
            comandos = parsear_linea(linea)
        except ValueError as e:
            print(f"minish: error de sintaxis: {e}")
            continue
        argv = comandos[0]["argv"]
        if len(comandos) == 1 and argv[0] == "exit":
            break
        if len(comandos) == 1 and argv[0] == "cd":
            try:
                os.chdir(argv[1] if len(argv) > 1 else os.environ["HOME"])
            except OSError as e:
                print(f"cd: {e.strerror}")
            continue
        codigo = ejecutar_pipeline(comandos)
        if codigo:
            print(f"[código {codigo}]")


if __name__ == "__main__":
    main()
