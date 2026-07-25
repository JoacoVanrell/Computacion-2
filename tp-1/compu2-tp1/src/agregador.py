"""
Agregador: único proceso que escribe en el snapshot compartido.
Los analizadores mandan sus resultados por Queue en vez de tocar
el snapshot directamente.
"""
import time
from queue import Empty


def loop_agregador(queue, snapshot, corriendo):
    """
    queue     : Queue donde los analizadores hacen put({'nombre', 'ts', 'datos', ...})
    snapshot  : Manager().dict() compartido, único punto de escritura
    corriendo : Value('b') - flag de apagado
    """
    while corriendo.value:
        try:
            paquete = queue.get(timeout=0.5)
        except Empty:
            continue

        nombre = paquete.pop('nombre')
        snapshot[nombre] = paquete