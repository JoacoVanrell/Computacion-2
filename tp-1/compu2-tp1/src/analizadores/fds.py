"""
Analizador de File Descriptors: lista de FDs abiertos por proceso,
su destino y su tipo (tty/socket/pipe/device/file).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo, pids):
    """
    Igual que memoria: no hay estado entre ciclos, cada lectura es
    independiente. previo se devuelve sin tocar.
    """
    datos = {}

    for pid in pids:
        fds = procfs.listar_fds(pid)
        if fds is None:
            continue  # murió entre listar procesos y listar sus FDs

        datos[pid] = {
            'pid': pid,
            'cantidad': len(fds),
            'fds': fds,
        }

    return datos, previo