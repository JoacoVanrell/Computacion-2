"""Medición 1: 20 descargas secuenciales contra 20 concurrentes.

Corre ADENTRO del contenedor de la API (ahí ya está httpx):

    DESCARGA_SECUENCIAL=0 docker compose up -d --build
    docker compose exec api python mediciones/medicion1_descargas.py

    DESCARGA_SECUENCIAL=1 docker compose up -d
    docker compose exec api python mediciones/medicion1_descargas.py

Las 20 URLs apuntan al servicio `lento` del compose, cada una con una
demora fija entre 0.2 y 1 s (siempre las mismas: semilla fija).
"""
import os
import random
import time
from datetime import datetime

import httpx

API = 'http://localhost:8000'
REPETICIONES = 3

random.seed(2026)
DEMORAS = [round(random.uniform(0.2, 1.0), 2) for _ in range(20)]
URLS = [f'http://lento:9100/demora/{d}' for d in DEMORAS]


def correr_una_vez(c: httpx.Client) -> float:
    """Crea UNA tarea descargar con las 20 URLs y devuelve cuánto tardó."""
    tid = c.post('/tareas', json={'tipo': 'descargar', 'urls': URLS}).json()['id']
    while (t := c.get(f'/tareas/{tid}').json())['estado'] in ('pendiente', 'ejecutando'):
        time.sleep(0.02)
    errores = [r for r in t['resultado'] if 'error' in r]
    if errores:
        print(f'  OJO: {len(errores)} URLs fallaron, ej: {errores[0]["error"]}')
    # Tiempo de ejecución medido por la propia API: desde que un worker
    # la toma hasta que termina.
    return (datetime.fromisoformat(t['terminada'])
            - datetime.fromisoformat(t['iniciada'])).total_seconds()


def main():
    modo = ('SECUENCIAL (for + await)' if os.environ.get('DESCARGA_SECUENCIAL') == '1'
            else 'CONCURRENTE (gather)')
    print(f'Medición 1 — modo {modo}')
    print(f'  20 URLs: suma de demoras {sum(DEMORAS):.2f} s, '
          f'la más lenta {max(DEMORAS):.2f} s')
    with httpx.Client(base_url=API, timeout=60) as c:
        tiempos = [correr_una_vez(c) for _ in range(REPETICIONES)]
    for i, t in enumerate(tiempos, 1):
        print(f'  corrida {i}: {t:.2f} s')
    print(f'  promedio: {sum(tiempos) / len(tiempos):.2f} s')


if __name__ == '__main__':
    main()
