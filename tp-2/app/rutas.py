"""Los 5 endpoints de la API."""
from datetime import datetime
from typing import get_args

from fastapi import APIRouter, HTTPException, Query

from app import config, estado
from app.modelos import Estado, Tarea, TareaNueva

router = APIRouter()

# Estados de los que una tarea ya no sale: no tiene sentido cancelarla.
TERMINADOS = ('completada', 'fallida', 'cancelada')


def buscar(tarea_id: int) -> Tarea:
    if tarea_id not in estado.tareas:
        raise HTTPException(status_code=404, detail='No existe esa tarea')
    return estado.tareas[tarea_id]


@router.post('/tareas', response_model=Tarea, status_code=201)
async def crear(nueva: TareaNueva):
    """Responde enseguida: la tarea queda pendiente, no se ejecuta acá."""
    tarea = Tarea(
        id=estado.nuevo_id(),
        tipo=nueva.tipo,
        parametros=nueva.model_dump(exclude={'tipo', 'timeout'}),
        timeout=nueva.timeout or config.TIMEOUT_DEFECTO,
        creada=datetime.now(),
    )
    estado.tareas[tarea.id] = tarea
    # TODO: encolar la tarea (todavía no hay cola ni workers)
    return tarea


@router.get('/tareas', response_model=list[Tarea])
async def listar(
    estado_filtro: Estado | None = Query(default=None, alias='estado',
                                         description='Filtrar por estado'),
):
    items = list(estado.tareas.values())
    if estado_filtro:
        items = [t for t in items if t.estado == estado_filtro]
    return items


@router.get('/tareas/{tarea_id}', response_model=Tarea)
async def obtener(tarea_id: int):
    return buscar(tarea_id)


@router.delete('/tareas/{tarea_id}', status_code=204)
async def cancelar(tarea_id: int):
    """No la borra del dict: la marca cancelada, para poder consultarla después."""
    tarea = buscar(tarea_id)
    if tarea.estado in TERMINADOS:
        raise HTTPException(status_code=409,
                            detail=f'La tarea ya está {tarea.estado}')
    # TODO: si está ejecutando, cancelar también su Task
    tarea.estado = 'cancelada'
    tarea.terminada = datetime.now()


@router.get('/estadisticas')
async def estadisticas():
    por_estado = {e: 0 for e in get_args(Estado)}
    for tarea in estado.tareas.values():
        por_estado[tarea.estado] += 1
    return {
        'total': len(estado.tareas),
        'por_estado': por_estado,
        'tiempo_promedio': None,        # TODO: cuando haya tareas terminadas
        'workers_ocupados': 0,          # TODO: cuando haya workers
    }
