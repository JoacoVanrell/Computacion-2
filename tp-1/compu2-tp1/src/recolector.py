"""
Recolector: lista los PIDs vivos vía /proc y se los pasa a los 7
analizadores, para que ninguno tenga que listar /proc por su cuenta.
"""
import signal
import time
import procfs


def loop_recolector(pids_compartidos, corriendo, intervalo=1.0):
    """
    pids_compartidos : Manager().dict() con la clave 'pids' -- se
                        reemplaza entera cada ciclo (mismo patrón que
                        el snapshot: nunca se muta anidado).
    corriendo         : Value('b') - flag de apagado, compartido con
                        el resto del sistema.
    intervalo         : no es ajustable en vivo (no es una de las 7
                        vistas), listar PIDs es barato.
    """
    # Mismo motivo que en base.py: Ctrl+C llega a todo el grupo de
    # procesos, no solo al principal. Solo él maneja SIGINT.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    while corriendo.value:
        inicio = time.time()

        pids_compartidos['pids'] = procfs.listar_pids()

        objetivo = inicio + intervalo
        while time.time() < objetivo and corriendo.value:
            time.sleep(0.1)