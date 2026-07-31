"""
Analizador de Resumen: estado, CPU%, RSS, threads, comando.
Necesita memoria entre ciclos para calcular CPU% por delta de jiffies.
"""
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procfs


def recolectar(previo, pids):
    """
    Arma el resumen de los procesos que le pasó el recolector.

    previo: dict {pid: (jiffies, timestamp)} del ciclo anterior.
            Vacío en la primera pasada -> todos los CPU% dan 0.0.
    pids  : lista de PIDs vivos, la arma el recolector.

    Devuelve (datos, nuevo_previo).
    """
    ahora = time.time()
    datos = {}
    nuevo_previo = {}

    for pid in pids:
        st = procfs.leer_stat(pid)
        if st is None:
            continue  # murió entre listar y leer (TOCTOU)

        status = procfs.leer_status(pid)
        if status is None:
            continue

        # Tiempo total de CPU consumido desde que arrancó el proceso.
        jiffies = st['utime'] + st['stime']
        nuevo_previo[pid] = (jiffies, ahora)

        # Delta contra el ciclo anterior.
        cpu = 0.0
        if pid in previo:
            j_antes, t_antes = previo[pid]
            dt = ahora - t_antes
            if dt > 0:
                # Cuántos jiffies "cabían" en ese intervalo a 1 core al 100%.
                posibles = dt * procfs.HZ
                cpu = (jiffies - j_antes) / posibles * 100
                # Puede dar negativo si el PID se reciclÓ (murió y nació otro
                # con el mismo número). Lo clampeamos.
                cpu = max(0.0, cpu)

        uid = int(status.get('Uid', '0').split()[0])
        gid = int(status.get('Gid', '0').split()[0])

        datos[pid] = {
            'pid': pid,
            'ppid': st['ppid'],
            'usuario': procfs.usuario_de_uid(uid),
            'uid': uid,
            'gid': gid,
            'estado': st['estado'],
            'cpu': round(cpu, 1),
            'rss_kb': procfs.kb(status.get('VmRSS', '0 kB')),
            'threads': st['num_threads'],
            'comando': procfs.leer_cmdline(pid),
        }

    return datos, nuevo_previo