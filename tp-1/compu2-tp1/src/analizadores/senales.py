"""
Analizador de Señales: decodifica las máscaras hexadecimales de
señales bloqueadas/ignoradas/con handler/pendientes de cada proceso.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo, pids):
    """
    Sin estado entre ciclos, igual que memoria y fds.
    """
    datos = {}

    for pid in pids:
        status = procfs.leer_status(pid)
        if status is None:
            continue  # murió entre listar y leer (TOCTOU)

        datos[pid] = {
            'pid': pid,
            'bloqueadas': procfs.decodificar_mascara(status.get('SigBlk', '0')),
            'ignoradas': procfs.decodificar_mascara(status.get('SigIgn', '0')),
            'con_handler': procfs.decodificar_mascara(status.get('SigCgt', '0')),
            'pendientes_proceso': procfs.decodificar_mascara(status.get('SigPnd', '0')),
            'pendientes_grupo': procfs.decodificar_mascara(status.get('ShdPnd', '0')),
        }

    return datos, previo