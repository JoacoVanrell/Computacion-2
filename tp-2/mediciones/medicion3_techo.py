"""Medición 3: techo del pool. ¿Dónde se degradan los tiempos y por qué?

Corre ADENTRO del contenedor de la API:

    docker compose up -d --build
    docker compose exec api python mediciones/medicion3_techo.py

    WORKERS=16 docker compose up -d          # repetir con más workers
    docker compose exec api python mediciones/medicion3_techo.py

Tres experimentos:
  A. M tareas `esperar` de 1 s a la vez (I/O): ¿cuándo dejan de tardar 1 s?
  B. M tareas `hashear` a la vez (CPU): ¿cuándo dejan de tardar lo que tarda una?
  C. Muchos POST de golpe: ¿cuántos entran antes de que la cola se llene?
"""
import os
import time

import httpx

API = 'http://localhost:8000'
ITER_HASH = 2_000_000


def lanzar_y_esperar(c: httpx.Client, cuerpo: dict, m: int) -> float:
    """Manda m tareas iguales y devuelve cuánto tardan TODAS en terminar."""
    t0 = time.perf_counter()
    ids = {c.post('/tareas', json=cuerpo).json()['id'] for _ in range(m)}
    while True:
        estados = {t['id']: t['estado'] for t in c.get('/tareas').json() if t['id'] in ids}
        if all(e not in ('pendiente', 'ejecutando') for e in estados.values()):
            return time.perf_counter() - t0
        time.sleep(0.02)


def main():
    workers = int(os.environ.get('WORKERS', '4'))
    nucleos = os.cpu_count()
    print(f'Medición 3 — {workers} workers, {nucleos} núcleos (= procesos del pool)')

    with httpx.Client(base_url=API, timeout=120) as c:
        print('\n  A. tareas esperar de 1 s, todas a la vez')
        for m in (1, 2, 4, 8, 16, 32):
            dt = lanzar_y_esperar(c, {'tipo': 'esperar', 'segundos': 1}, m)
            print(f'     {m:3} tareas -> {dt:5.2f} s')

        print(f'\n  B. tareas hashear de {ITER_HASH:,} iteraciones, todas a la vez')
        una = lanzar_y_esperar(c, {'tipo': 'hashear', 'texto': 'x',
                                   'iteraciones': ITER_HASH}, 1)
        print(f'     {1:3} tareas -> {una:5.2f} s')
        for m in sorted({workers, nucleos, 2 * nucleos}):
            dt = lanzar_y_esperar(c, {'tipo': 'hashear', 'texto': 'x',
                                      'iteraciones': ITER_HASH}, m)
            print(f'     {m:3} tareas -> {dt:5.2f} s   ({dt / una:.1f} veces una sola)')

        print('\n  C. 150 POST de golpe de tareas esperar de 2 s (cola de 100 lugares)')
        codigos = [c.post('/tareas', json={'tipo': 'esperar', 'segundos': 2}).status_code
                   for _ in range(150)]
        print(f'     aceptadas (201): {codigos.count(201)}   '
              f'rechazadas (503): {codigos.count(503)}')
        # Limpieza: cancelar todo lo que quedó, para no dejar 2 minutos de trabajo.
        for t in c.get('/tareas', params={'estado': 'pendiente'}).json():
            c.delete(f'/tareas/{t["id"]}')
        for t in c.get('/tareas', params={'estado': 'ejecutando'}).json():
            c.delete(f'/tareas/{t["id"]}')


if __name__ == '__main__':
    main()
