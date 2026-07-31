"""
Analizador de Memoria: VmSize/RSS/Data/Stk/Exe/Lib/HWM/Swap, page faults,
y segmentos agrupados de /proc/<pid>/maps.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo, pids):
    """
    A diferencia de resumen (que necesita el ciclo anterior para el delta
    de jiffies), memoria no tiene estado entre ciclos: cada lectura es
    independiente. previo se devuelve sin tocar.
    """
    datos = {}

    for pid in pids:
        status = procfs.leer_status(pid)
        if status is None:
            continue  # murió entre listar y leer (TOCTOU)

        st = procfs.leer_stat(pid)
        if st is None:
            continue

        datos[pid] = {
            'pid': pid,
            'vm_size_kb': procfs.kb(status.get('VmSize', '0 kB')),
            'vm_rss_kb': procfs.kb(status.get('VmRSS', '0 kB')),
            'vm_data_kb': procfs.kb(status.get('VmData', '0 kB')),
            'vm_stk_kb': procfs.kb(status.get('VmStk', '0 kB')),
            'vm_exe_kb': procfs.kb(status.get('VmExe', '0 kB')),
            'vm_lib_kb': procfs.kb(status.get('VmLib', '0 kB')),
            'vm_hwm_kb': procfs.kb(status.get('VmHWM', '0 kB')),
            'vm_swap_kb': procfs.kb(status.get('VmSwap', '0 kB')),
            'minflt': st['minflt'],
            'majflt': st['majflt'],
            'segmentos': procfs.leer_maps(pid) or {},
        }

    return datos, previo