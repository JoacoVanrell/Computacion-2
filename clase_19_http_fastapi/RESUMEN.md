# Clase 19 — HTTP + FastAPI · Resumen

Subimos de capa: del **transporte** (bytes, framing) al **protocolo de aplicación** de la web.

## 1. HTTP es texto sobre TCP
```
GET /tareas/42 HTTP/1.1          ← línea de pedido: MÉTODO RUTA VERSIÓN
Host: ejemplo.com                ← headers (uno por línea)
Accept: application/json
                                 ← LÍNEA VACÍA (\r\n\r\n): fin de headers
(cuerpo)
```
```
HTTP/1.1 200 OK                  ← línea de estado: VERSIÓN CÓDIGO TEXTO
Content-Type: application/json
Content-Length: 27
                                 
{"id": 42, "estado": "ok"}
```
- Framing = los dos de la clase 13: **línea vacía** (delimitador) para los headers, **`Content-Length`** (longitud) para el cuerpo.
- Separador **`\r\n`** (no `\n`).

## 2. Métodos
| Método | Para | Seguro | Idempotente |
|---|---|---|---|
| GET | traer | ✅ | ✅ |
| HEAD | solo headers | ✅ | ✅ |
| POST | **crear** | ❌ | ❌ |
| PUT | reemplazar completo | ❌ | ✅ |
| PATCH | modificar una parte | ❌ | ❌ (en general) |
| DELETE | borrar | ❌ | ✅ |
- **Seguro** = no modifica nada (nunca pongas una acción destructiva detrás de un GET).
- **Idempotente** = repetirlo da lo mismo que hacerlo una vez → reintentar un PUT es seguro; un **POST puede duplicar**.

## 3. Códigos de estado
| | | |
|---|---|---|
| **2xx** éxito | 200 OK · **201 Created** (POST que crea) · **204 No Content** | |
| **3xx** redirección | 301 · 304 Not Modified | |
| **4xx** culpa del **cliente** | 400 · **404 Not Found** · **422** datos inválidos · 429 demasiados pedidos | |
| **5xx** culpa del **servidor** | **500** · **503** no disponible (+ `Retry-After`) | |
> La división 4xx/5xx dice **de quién es la culpa**: no devuelvas 500 si el cliente mandó datos mal.

## 4. Headers clave
`Host` (**obligatorio** en 1.1: varios sitios por IP) · `Content-Type` · `Content-Length` · `Accept` · `Authorization` ·
`Connection: keep-alive / close` (en 1.1 la conexión **queda abierta** por defecto → no pagar un handshake por pedido).

## 5. `http.server` = socketserver (clase 16)
`HTTPServer` es un `TCPServer`; `ThreadingHTTPServer` usa `ThreadingMixIn`; `BaseHTTPRequestHandler` hereda de
`StreamRequestHandler` y **despacha** a `do_GET`, `do_POST`… (template method). Leer **exactamente** `Content-Length`
con `self.rfile.read(n)`.

## 6. FastAPI
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

class TareaNueva(BaseModel):
    tipo: str = Field(min_length=1)
    prioridad: int = Field(default=1, ge=1, le=5)

@app.get("/tareas/{tarea_id}")             # parámetro de RUTA
def obtener(tarea_id: int):                 # ← el tipo NO es decorativo: convierte y valida
    if tarea_id not in tareas:
        raise HTTPException(404, "No existe esa tarea")
    return tareas[tarea_id]                 # dict → JSON solo

@app.get("/tareas")                          # parámetros de QUERY: ?estado=x&limite=5
def listar(estado: str = "todos", limite: int = 10): ...

@app.post("/tareas", status_code=201)
def crear(t: TareaNueva): ...                # cuerpo JSON validado por Pydantic → 422 con 'loc' si falla
```
- Cada anotación de tipo: **convierte**, **valida** (422 **antes** de llamar a tu función) y **documenta** (`/docs`, OpenAPI).
- `PATCH`: modelo con campos **opcionales** + `model_dump(exclude_unset=True)`.
- `uvicorn mi_api:app --reload` (modo desarrollo) o `uvicorn.run(app, ...)`.

## 7. ¿Dónde está el event loop? ⭐
```
 uvicorn  ← servidor: socket, HTTP, EVENT LOOP (asyncio sobre selectors/epoll)
   │ ASGI ← el contrato (una especificación)
 FastAPI  ← tu aplicación: rutas, validación, respuestas
```
- **Un solo loop por proceso**, en el MainThread; cada pedido es una tarea.
- `async def` → corre **en el loop**. `def` → lo manda a un **threadpool** (fuera del loop).
- `--workers N` = **N procesos con N loops** → **no comparten memoria** (un dict global = N dicts distintos).
  El estado real va en una **BD / Redis**. (`--reload` = 1 worker: por eso "anda" en desarrollo.)

## 8. async bien, async mal ⭐
| Endpoint (3 pedidos de 1 s) | Tiempo |
|---|---|
| `async def` + `await asyncio.sleep(1)` | **~1 s** |
| `async def` + `time.sleep(1)` | **~3 s** (bloquea el loop: ¡todo el servidor!) |
| `def` + `time.sleep(1)` | **~1 s** (threadpool) |
> **Un `def` común es mejor que un `async def` mal escrito.**

| Tu función… | Escribila como |
|---|---|
| solo espera I/O con librerías **async** (`httpx`, `asyncpg`) | `async def` |
| usa librerías **bloqueantes** (`requests`, BD sincrónica) | `def` |
| hace **cálculo pesado** | `def` o, mejor, `run_in_executor` con un ProcessPool |

## ❓ Autoevaluación
1. ¿Qué tres partes tiene un pedido HTTP y qué las separa? ¿Qué framing usa HTTP?
2. ¿Qué métodos son seguros e idempotentes? ¿Por qué reintentar un POST es peligroso?
3. ¿Cuándo devolvés 201, 204, 404, 422, 503?
4. ¿Por qué `Host` es obligatorio en HTTP/1.1?
5. ¿Qué hace FastAPI con `tarea_id: int`? ¿Cuándo valida?
6. ¿Quién tiene el event loop, FastAPI o uvicorn? ¿Qué es ASGI?
7. ¿Por qué con `--workers 3` un dict global "pierde" tareas?
8. ¿Por qué `async def` con `time.sleep` es peor que un `def`?
