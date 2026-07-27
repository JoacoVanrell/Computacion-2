"""
Analizador de Threads (LWPs): estado, CPU% (delta de jiffies), nombre
y context switches de cada thread de cada proceso.
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo):
    """
    previo: dict {tid: (jiffies, timestamp)} del ciclo anterior.
            El tid solo alcanza como clave: es único en todo el sistema
            (es un PID real, no algo que se repita entre procesos).
    """
    ahora = time.time()
    datos = {}
    nuevo_previo = {}

    for pid in procfs.listar_pids():
        tids = procfs.listar_tids(pid)
        if tids is None:
            continue  # el proceso murió entre listar_pids y listar_tids

        threads = {}
        for tid in tids:
            st = procfs.leer_stat(pid, tid)
            if st is None:
                continue  # el thread murió en el medio

            status = procfs.leer_status(pid, tid)
            if status is None:
                continue

            jiffies = st['utime'] + st['stime']
            nuevo_previo[tid] = (jiffies, ahora)

            cpu = 0.0
            if tid in previo:
                j_antes, t_antes = previo[tid]
                dt = ahora - t_antes
                if dt > 0:
                    posibles = dt * procfs.HZ
                    cpu = max(0.0, (jiffies - j_antes) / posibles * 100)

            threads[tid] = {
                'tid': tid,
                'nombre': status.get('Name', ''),
                'estado': st['estado'],
                'cpu': round(cpu, 1),
                'voluntary_ctxt_switches': int(status.get('voluntary_ctxt_switches', 0)),
                'nonvoluntary_ctxt_switches': int(status.get('nonvoluntary_ctxt_switches', 0)),
            }

        datos[pid] = threads

    return datos, nuevo_previo