"""
Analizador de Scheduling: nice, priority, policy, RT priority,
afinidad de CPU, context switches, utime/stime, SID/PGID.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo):
    """
    Sin estado entre ciclos, igual que memoria/fds/senales.
    """
    datos = {}

    for pid in procfs.listar_pids():
        st = procfs.leer_stat(pid)
        if st is None:
            continue  # murió entre listar y leer (TOCTOU)

        status = procfs.leer_status(pid)
        if status is None:
            continue

        datos[pid] = {
            'pid': pid,
            'nice': st['nice'],
            'priority': st['priority'],
            'policy': procfs.nombre_policy(st['policy']),
            'rt_priority': st['rt_priority'],
            'cpu_affinity': status.get('Cpus_allowed_list', ''),
            'voluntary_ctxt_switches': int(status.get('voluntary_ctxt_switches', 0)),
            'nonvoluntary_ctxt_switches': int(status.get('nonvoluntary_ctxt_switches', 0)),
            'utime': st['utime'],
            'stime': st['stime'],
            'sid': st['sid'],
            'pgid': st['pgid'],
        }

    return datos, previo