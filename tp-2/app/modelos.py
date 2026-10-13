"""Modelos Pydantic: lo que manda el cliente y lo que devuelve el servidor."""
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

Estado = Literal['pendiente', 'ejecutando', 'completada', 'fallida', 'cancelada']
Tipo = Literal['descargar', 'hashear', 'esperar']


# ---------------------------------------------------------------
# Lo que el cliente manda en el cuerpo de un POST: un modelo por tipo
# ---------------------------------------------------------------

class TareaBase(BaseModel):
    """Lo que tienen en común los tres tipos."""
    timeout: float | None = Field(default=None, gt=0,
                                  description='Segundos. Si falta, se usa el de config')


class EsperarNueva(TareaBase):
    tipo: Literal['esperar']
    segundos: float = Field(gt=0)


class HashearNueva(TareaBase):
    tipo: Literal['hashear']
    texto: str
    iteraciones: int = Field(ge=1)


class DescargarNueva(TareaBase):
    tipo: Literal['descargar']
    urls: list[str] = Field(min_length=1)


# Pydantic mira el campo 'tipo' para saber con cuál de los tres validar.
TareaNueva = Annotated[EsperarNueva | HashearNueva | DescargarNueva,
                       Field(discriminator='tipo')]


# ---------------------------------------------------------------
# Lo que devolvemos: lo que mandó el cliente más lo que agrega el servidor
# ---------------------------------------------------------------

class Tarea(BaseModel):
    id: int
    tipo: Tipo
    parametros: dict[str, Any]          # segundos, o texto e iteraciones, o urls
    timeout: float
    estado: Estado = 'pendiente'
    resultado: Any = None               # se completa si termina bien
    error: str | None = None            # el motivo, si queda fallida
    creada: datetime
    iniciada: datetime | None = None
    terminada: datetime | None = None
