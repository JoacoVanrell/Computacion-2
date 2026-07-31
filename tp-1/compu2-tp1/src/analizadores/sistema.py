"""
Analizador de Sistema: CPU global (user/system/idle/iowait), memoria,
load average, boot time/uptime, y conteos de procesos por estado.

El top 3 por CPU/memoria NO se calcula acá: se deriva del snapshot
en el Display, para no darle a este analizador acceso de lectura al
snapshot (ver decisión de diseño en el README).
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo, pids):
    """
    previo: {'jiffies': {...}, 'ts': float} del ciclo anterior, o {}
            en la primera pasada (ahí el CPU% global da 0.0, igual
            que en resumen.py).
    """
    ahora = time.time()

    stat = procfs.leer_stat_global()
    cpu_actual = stat['cpu']

    cpu_pct = {'user': 0.0, 'system': 0.0, 'idle': 0.0, 'iowait': 0.0}
    if previo:
        j_antes = previo['jiffies']
        delta_total = sum(cpu_actual.values()) - sum(j_antes.values())
        if delta_total > 0:
            for campo in cpu_pct:
                delta = cpu_actual[campo] - j_antes[campo]
                cpu_pct[campo] = round(delta / delta_total * 100, 1)

    nuevo_previo = {'jiffies': cpu_actual, 'ts': ahora}

    meminfo = procfs.leer_meminfo()

    total = 0
    por_estado = {}
    threads_totales = 0
    zombies = 0
    for pid in pids:
        st = procfs.leer_stat(pid)
        if st is None:
            continue  # murió entre listar y leer (TOCTOU)

        total += 1
        por_estado[st['estado']] = por_estado.get(st['estado'], 0) + 1
        threads_totales += st['num_threads']
        if st['estado'] == 'Z':
            zombies += 1

    datos = {
        'cpu_pct': cpu_pct,
        'mem_total_kb': procfs.kb(meminfo.get('MemTotal', '0 kB')),
        'mem_libre_kb': procfs.kb(meminfo.get('MemFree', '0 kB')),
        'mem_buffers_kb': procfs.kb(meminfo.get('Buffers', '0 kB')),
        'mem_cached_kb': procfs.kb(meminfo.get('Cached', '0 kB')),
        'swap_total_kb': procfs.kb(meminfo.get('SwapTotal', '0 kB')),
        'swap_libre_kb': procfs.kb(meminfo.get('SwapFree', '0 kB')),
        'loadavg': procfs.leer_loadavg(),
        'procesos_totales': total,
        'procesos_por_estado': por_estado,
        'threads_totales': threads_totales,
        'zombies': zombies,
        'boot_time': stat.get('btime'),
        'uptime_seg': procfs.leer_uptime(),
    }

    return datos, nuevo_previo