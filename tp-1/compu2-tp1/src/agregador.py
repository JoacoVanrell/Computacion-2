"""
Agregador: único proceso que escribe en el snapshot compartido.
Los analizadores mandan sus resultados por Queue en vez de tocar
el snapshot directamente.
"""
import signal
import time
from queue import Empty


def loop_agregador(queue, snapshot, corriendo):
    """
    queue     : Queue donde los analizadores hacen put({'nombre', 'ts', 'datos', ...})
    snapshot  : Manager().dict() compartido, único punto de escritura
    corriendo : Value('b') - flag de apagado
    """
    # Mismo motivo que en base.py/recolector.py: solo el proceso
    # principal maneja SIGINT (Ctrl+C llega a todo el grupo).
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while corriendo.value:
        try:
            paquete = queue.get(timeout=0.5)
        except Empty:
            continue

        nombre = paquete.pop('nombre')
        snapshot[nombre] = paquete