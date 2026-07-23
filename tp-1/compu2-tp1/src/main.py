import multiprocessing as mp
import time
from analizadores import base, resumen


def main():
    manager = mp.Manager()
    snapshot = manager.dict()

    # Value = memoria compartida real para tipos simples.
    # 'd' = double, 'b' = byte (lo usamos como booleano).
    intervalo = mp.Value('d', 2.0)
    corriendo = mp.Value('b', True)

    p = mp.Process(
        target=base.loop_analizador,
        args=('resumen', resumen.recolectar, snapshot, intervalo, corriendo),
        name='analizador-resumen',
    )
    p.start()
    print(f'proceso principal PID {mp.current_process().pid}')
    print(f'analizador-resumen  PID {p.pid}\n')

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

            # A mitad de camino aceleramos el analizador EN VIVO.
            if i == 2:
                intervalo.value = 0.5
                print('>>> intervalo bajado a 0.5s\n')

    finally:
        corriendo.value = False
        p.join(timeout=3)
        print(f'analizador terminado, exitcode={p.exitcode}')


if __name__ == '__main__':
    main()