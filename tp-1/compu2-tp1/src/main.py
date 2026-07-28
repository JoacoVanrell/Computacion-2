import multiprocessing as mp
import time
from analizadores import base, resumen, memoria, fds, threads, senales, scheduling, sistema
from agregador import loop_agregador

# (nombre, función recolectora, intervalo default en segundos)
# Los defaults salen de la tabla de vistas de la consigna.
ANALIZADORES = [
    ('resumen', resumen.recolectar, 2.0),
    ('memoria', memoria.recolectar, 3.0),
    ('fds', fds.recolectar, 5.0),
    ('threads', threads.recolectar, 2.0),
    ('senales', senales.recolectar, 10.0),
    ('scheduling', scheduling.recolectar, 10.0),
    ('sistema', sistema.recolectar, 2.0),
]


def main():
    manager = mp.Manager()
    snapshot = manager.dict()
    queue = mp.Queue()

    # 'b' = byte (lo usamos como booleano). Un solo flag de apagado
    # compartido por todos; los intervalos SÍ son uno por analizador,
    # para poder ajustarlos en vivo de forma independiente.
    corriendo = mp.Value('b', True)

    intervalos = {}
    procesos = []

    for nombre, funcion, default in ANALIZADORES:
        intervalo = mp.Value('d', default)
        intervalos[nombre] = intervalo
        procesos.append(mp.Process(
            target=base.loop_analizador,
            args=(nombre, funcion, queue, intervalo, corriendo),
            name=f'analizador-{nombre}',
        ))

    procesos.append(mp.Process(
        target=loop_agregador,
        args=(queue, snapshot, corriendo),
        name='agregador',
    ))

    for p in procesos:
        p.start()

    print(f'proceso principal PID {mp.current_process().pid}')
    for p in procesos:
        print(f'{p.name:<20} PID {p.pid}')
    print()

    try:
        for i in range(6):
            time.sleep(2)

            entrada = snapshot.get('resumen')
            if entrada is None:
                print('todavía no hay datos')
                continue

            datos = entrada['datos']
            edad = time.time() - entrada['ts']
            top = sorted(datos.values(), key=lambda x: x['cpu'], reverse=True)[:8]

            print(f'--- lectura {i}  ({len(datos)} procs, dato de hace {edad:.1f}s) ---')
            for pr in top:
                print(f'{pr["pid"]:>7} {pr["estado"]:<2} {pr["cpu"]:>6.1f}% '
                      f'{pr["rss_kb"]/1024:>7.1f}MB  {pr["comando"][:40]}')
            print()

            # A mitad de camino aceleramos resumen EN VIVO, para probar
            # que el intervalo de cada vista es independiente.
            if i == 2:
                intervalos['resumen'].value = 0.5
                print('>>> intervalo de resumen bajado a 0.5s\n')

    finally:
        corriendo.value = False
        for p in procesos:
            p.join(timeout=3)
        for p in procesos:
            print(f'{p.name:<20} terminado, exitcode={p.exitcode}')


if __name__ == '__main__':
    main()