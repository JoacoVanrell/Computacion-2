# Clase 19 — Ejercicios resueltos

> Material de estudio armado con Claude. Necesitás `pip install fastapi uvicorn httpx` (en un venv).

| Archivo | Ejercicio | Correr |
|---|---|---|
| `api.py` | **Ej. 3 (obligatorio)**: API de tareas + `PATCH`, `/estadisticas`, límite de pendientes, middleware `X-Tiempo` | `python3 api.py` → `localhost:8000/docs` |
| `probar_api.py` | Las pruebas de la consigna contra `api.py` (sin levantar servidor) | `python3 probar_api.py` |
| `estilos.py` | Ej. 5: async bien / async mal / def + **4to caso: cálculo pesado** | `python3 estilos.py` |
| `cliente_http.py` | Adicionales: cliente HTTP a mano (Content-Length, chunked) + keep-alive | `python3 cliente_http.py --keepalive` |

## Ej. 3 — salida real de `probar_api.py`

```
GET /tareas/abc                          → 422  int_parsing en ['path', 'tarea_id']
POST {"tipo":"volar"}                    → 422  literal_error en ['body', 'tipo']: Input should be 'descargar', 'hashear' or 'esperar'
POST {"tipo":"esperar","prioridad":99}   → 422  less_than_equal en ['body', 'prioridad']: Input should be less than or equal to 5
[obtener] me llamaron con tarea_id=999 de tipo int        ← el print solo aparece acá
GET /tareas/999                          → 404  No existe esa tarea
POST válido                              → 201  (+ header Location: /tareas/1)
PATCH /tareas/1 {estado: ejecutando}     → 200
PATCH /tareas/1 {estado: volando}        → 422  literal_error en ['body', 'estado']
POST con 10 pendientes                   → 503  Hay 10 tareas pendientes (máximo 10)   Retry-After: 5
GET /estadisticas                        → 200  {'total': 11, 'por_estado': {'pendiente': 10, 'ejecutando': 1, 'completada': 0}}
DELETE /tareas/1                         → 204
```

## Respuestas (checklist)

- **`/docs`** la escribió **FastAPI** a partir de las anotaciones y los modelos (estándar **OpenAPI**; `/openapi.json` es la
  descripción de la API en JSON, de la que se genera la página y se pueden generar clientes).
- **422 vs 404:** **422** = el pedido **no pasa la validación** (tipo/valor inválido): FastAPI lo rechaza **antes** de llamar a tu
  función. **404** = el pedido es **válido** pero el recurso **no existe**: lo decide **tu código** (`HTTPException`).
- **`loc`** dice **dónde** está el error: `['path', 'tarea_id']`, `['body', 'prioridad']`, `['query', 'limite']`.
- **¿Cuándo valida?** **Antes**: el `print` de `obtener()` no aparece con `/tareas/abc` y sí con `/tareas/999`.
- **PATCH:** modelo `CambioTarea` con **todos los campos opcionales** (`= None`) y `model_dump(exclude_unset=True)` para
  cambiar **solo lo que vino**. (Si no viene nada → 422.)
- **Límite de 10 pendientes → `503 Service Unavailable` + `Retry-After`.** No es error del cliente (el pedido es válido):
  es el **servidor** el que no puede aceptar más trabajo **ahora**, y `Retry-After` le dice cuándo reintentar.
  Alternativas defendibles: **429 Too Many Requests** si el límite fuera **por cliente** (rate limit), o **409 Conflict**
  si lo pensás como conflicto con el estado actual. **No** 400/422 (el pedido está bien) ni 500 (no se rompió nada).
- **Parte D:** sin `: int`, `tarea_id` llega como **str** → `/tareas/abc` ya no da 422, y `/tareas/1` da **404** porque
  `"1" != 1` en el diccionario. Con `prioridad: str` acepta `"99"`, `"hola"`… y deja de validar el rango.
  **Lo que hace FastAPI con cada anotación:** (1) **convierte** (str de la URL → int), (2) **valida** (422 si no se puede),
  (3) **documenta** (aparece en `/docs`).

## Ej. 4 — dónde está el event loop
- `async def` corre en **MainThread**, dentro del **único** event loop del proceso (`id_del_loop` igual en cada pedido,
  tipo `_UnixSelectorEventLoop` = `selectors`/epoll de la clase 17). Un `def` común corre en un **AnyIO worker thread**,
  **fuera** del loop (por eso "NO hay loop").
- El loop lo crea **uvicorn** (servidor **ASGI**); FastAPI es la aplicación ASGI que uvicorn invoca. ASGI = la
  especificación del contrato entre los dos.
- Con `--workers 3` el `pid` cambia entre pedidos: son **3 procesos con 3 diccionarios `tareas`** distintos. Creás una tarea
  en uno y al pedirla puede atenderte otro → **404**. Para el TP2 el estado tiene que vivir **afuera del proceso**:
  base de datos, Redis, etc.

## Ej. 5 — salida real de `estilos.py` (3 pedidos simultáneos + un `/ping` en el medio)

```
endpoint         3 pedidos   /ping en el medio
/async-bien          1.00s              0.00s
/async-mal           3.01s              2.91s    ← bloquea el loop: hasta el /ping espera
/sync                1.02s              0.00s    ← def → threadpool: anda igual que el async bien
/cpu-async-mal       0.99s              0.89s    ← cálculo en el loop: todo congelado
/cpu-def             1.16s              0.01s    ← threadpool: el loop responde, pero los 3 cálculos se pelean por el GIL
/cpu-procesos        0.94s              0.00s    ← run_in_executor + ProcessPool: loop libre y cálculos en paralelo
```
(Mi máquina tiene 2 núcleos; con más, `/cpu-procesos` se despega más.)
- **`/async-mal` tarda el triple** porque `time.sleep` dentro de una corrutina **no cede**: es la regla de la clase 18.
- **`/sync` anda bien** porque FastAPI manda los `def` a un **threadpool** y el loop queda libre.
- **Regla:** `async def` solo si **todo lo que esperás es async** (`await httpx…`, `asyncpg`…). Si usás algo **bloqueante**, `def`.
  Para **CPU pesado**: `run_in_executor` con un **ProcessPoolExecutor** (ni async def ni def lo resuelven del todo).
- **El endpoint con `requests.get` dentro de `async def` está MAL** (bloquea el loop). Arreglos:
  (1) cambiarlo a **`def`** (va al threadpool); (2) usar **`httpx.AsyncClient`** con `await`.
- ⚠️ El pool de procesos lo creo con contexto **spawn**: el proceso de uvicorn ya tiene threads, y `fork` con threads puede
  heredar locks tomados → **deadlock** (clase 8). Con `fork` me pasó: el pedido quedaba colgado.

## Ej. 1–2 (respuestas cortas)
- Pedido/respuesta: **línea inicial**, **headers**, **línea vacía** (`\r\n\r\n`), **cuerpo**.
- Sin `Host:` un servidor HTTP/1.1 responde **400**: es obligatorio porque **muchos sitios comparten una IP**.
- **Seguros:** GET, HEAD. **Idempotentes:** GET, HEAD, PUT, DELETE. POST no: repetirlo **crea otro** recurso.
  Reintentar un POST tras un timeout puede **duplicar** (el mismo problema que la deduplicación de UDP en la clase 15); un PUT no.
- `BaseHTTPRequestHandler` hereda de `StreamRequestHandler`; `ThreadingHTTPServer` usa el **mismo `ThreadingMixIn`** de la clase 16.
- En `do_POST` hay que leer **exactamente `Content-Length`** bytes: después de eso, en la misma conexión, empieza el **próximo pedido**.
- `protocol_version = "HTTP/1.1"` habilita **keep-alive** (y entonces `Content-Length` es obligatorio). Un método no
  implementado (`PATCH` sin `do_PATCH`) → **501 Not Implemented** automático. Para `DELETE`: **204 No Content** (o 200 con cuerpo).
