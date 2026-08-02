"""
Señales que recibe el monitor mismo (patrón self-pipe):
SIGINT/SIGTERM -> shutdown limpio
SIGHUP         -> recargar config.json
SIGUSR1        -> dump del snapshot
SIGUSR2        -> toggle verbose

Distinto de analizadores/senales.py, que lee señales de OTROS procesos
desde /proc. Este módulo maneja las que le llegan al propio monitor.
"""
import os
import signal

SENALES_MANEJADAS = [signal.SIGINT, signal.SIGTERM, signal.SIGHUP,
                      signal.SIGUSR1, signal.SIGUSR2]

_w = None  # extremo de escritura del pipe, lo usa el handler


def _handler(signum, frame):
    # Async-signal-safe: un único os.write de un byte fijo. Nada de
    # lógica, locks ni memoria dinámica corre acá -- eso se hace después,
    # en el loop principal, fuera del contexto de señal.
    os.write(_w, bytes([signum]))


def instalar():
    """
    Arma el self-pipe y registra los handlers. Se llama en el proceso
    principal DESPUÉS de lanzar los hijos (mp.Process.start()), para que
    ellos se forkeen con la disposición de señal por default y no
    hereden este pipe.

    Devuelve el file descriptor de lectura, no bloqueante, para que el
    loop principal lo consulte sin trabarse.
    """
    global _w
    r, _w = os.pipe()
    os.set_blocking(r, False)
    for sig in SENALES_MANEJADAS:
        signal.signal(sig, _handler)
    return r


def leer_pendientes(r):
    """Números de señal recibidos desde la última consulta (puede ser [])."""
    try:
        return list(os.read(r, 4096))
    except BlockingIOError:
        return []