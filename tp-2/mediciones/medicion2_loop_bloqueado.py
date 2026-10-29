"""Medición 2: cuánto tarda GET /tareas mientras corre un hash pesado.

Corre ADENTRO del contenedor de la API:

    USAR_EXECUTOR=1 docker compose up -d --build
    docker compose exec api python mediciones/medicion2_loop_bloqueado.py

    USAR_EXECUTOR=0 docker compose up -d
    docker compose exec api python mediciones/medicion2_loop_bloqueado.py

Manda un hashear pesado y, mientras se calcula, pide GET /tareas cada
100 ms y anota cuánto tarda cada respuesta.
"""
import os
import statistics
import time
from datetime import datetime

import httpx

API = 'http://localhost:8000'
ITERACIONES = 10_000_000          # unos segundos de CPU
PAUSA = 0.1


def main():
    modo = 'SIN executor' if os.environ.get('USAR_EXECUTOR') == '0' else 'CON executor'
    print(f'Medición 2 — {modo}')
    with httpx.Client(base_url=API, timeout=120) as c:
        tid = c.post('/tareas', json={'tipo': 'hashear', 'texto': 'hola',
                                      'iteraciones': ITERACIONES}).json()['id']
        time.sleep(0.2)                       # que el worker ya esté calculando
        tiempos = []
        while True:
            t0 = time.perf_counter()
            lista = c.get('/tareas').json()   # <- el pedido que medimos
            tiempos.append((time.perf_counter() - t0) * 1000)
            estado = next(t['estado'] for t in lista if t['id'] == tid)
            if estado not in ('pendiente', 'ejecutando'):
                break                         # el hash ya terminó
            time.sleep(PAUSA)
        t = c.get(f'/tareas/{tid}').json()

    hash_s = (datetime.fromisoformat(t['terminada'])
              - datetime.fromisoformat(t['iniciada'])).total_seconds()
    print(f'  el hash ({ITERACIONES:,} iteraciones) tardó {hash_s:.2f} s')
    if not tiempos:
        print('  no llegué a pedir ningún GET mientras calculaba')
        return
    print(f'  GET /tareas mientras calculaba: {len(tiempos)} pedidos')
    print(f'    peor:    {max(tiempos):8.1f} ms')
    print(f'    mediana: {statistics.median(tiempos):8.1f} ms')


if __name__ == '__main__':
    main()
