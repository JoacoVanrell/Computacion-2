"""Volcado a estado_<timestamp>.json y aviso al arrancar."""
import json
from datetime import datetime
from pathlib import Path

from app import config, estado


def volcar() -> Path:
    """Escribe todas las tareas en estado_<timestamp>.json.

    Es I/O de disco bloqueante: se llama con asyncio.to_thread para no
    congelar el loop (I/O bloqueante -> thread, clase 21).
    """
    carpeta = Path(config.DIR_ESTADOS)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f'estado_{datetime.now():%Y%m%d_%H%M%S}.json'
    tareas = [t.model_dump(mode='json') for t in estado.tareas.values()]
    with open(archivo, 'w') as f:
        json.dump(tareas, f, indent=2, ensure_ascii=False)
    return archivo


def avisar_volcado_previo():
    """Al arrancar: si hay un volcado anterior, lo informa por log."""
    volcados = sorted(Path(config.DIR_ESTADOS).glob('estado_*.json'))
    if not volcados:
        print('No hay volcados previos')
        return
    ultimo = volcados[-1]
    with open(ultimo) as f:
        tareas = json.load(f)
    print(f'Hay un volcado previo: {ultimo} ({len(tareas)} tareas). '
          f'No se recarga: el estado arranca vacío.')
