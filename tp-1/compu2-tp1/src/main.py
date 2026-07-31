import curses
import multiprocessing as mp
from analizadores import base, resumen, memoria, fds, threads, senales, scheduling, sistema
from agregador import loop_agregador
import display

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

    try:
        curses.wrapper(display.loop_display, snapshot, corriendo, intervalos)
    finally:
        corriendo.value = False
        for p in procesos:
            p.join(timeout=3)


if __name__ == '__main__':
    main()