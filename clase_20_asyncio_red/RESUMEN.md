# Clase 20 — Asyncio en red · Resumen

**Se cierra el círculo:** clase 13 (servidor de a uno) → 14 (threads/procesos, con techo) → 17 (un hilo + `epoll`, pero
callbacks) → 18 (corrutinas, pero solo con `sleep`) → **hoy: corrutinas haciendo I/O de red de verdad.**
Esperar *tiempo* solo necesita un reloj; esperar *datos* necesita que el loop vigile sockets (`selectors`/`epoll`).

## 1. Streams: `reader` / `writer`
```python
reader, writer = await asyncio.open_connection("localhost", 8080)   # cliente
writer.write(b"hola\n")          # SIN await: copia al buffer y vuelve
await writer.drain()             # CON await: frena si el buffer está lleno
linea = await reader.readline()
writer.close(); await writer.wait_closed()
```
Son los primos async de `rfile`/`wfile` (clase 16).

### ⭐ `write()` sin await, `drain()` con await
- `write()` **nunca espera** → no es corrutina.
- `drain()` **puede esperar** (si el buffer pasó ~64 KiB, se suspende hasta que baje) = **backpressure**.
- Sin `drain()` todo anda en pruebas… y con un cliente que no lee, el servidor **acumula todo en memoria**
  (medido: 100 MB → **+92 MB** de RAM; con `drain()`: 0,1 MB y TCP frena al cliente).

### Leer = el framing de la clase 13, ya hecho
| | devuelve | framing |
|---|---|---|
| `read(n)` | **hasta** n bytes · `b''` = el otro cerró | — |
| `readline()` | hasta `\n` inclusive | **delimitador** |
| `readuntil(sep)` | hasta `sep` inclusive | **delimitador** |
| `readexactly(n)` | **exactamente** n, o `IncompleteReadError` (`.partial`) | **longitud** |

## 2. Servidor: una Task por cliente
```python
async def manejar(reader, writer):            # = handle() de la clase 16
    try:
        while (datos := await reader.readline()):
            writer.write(datos)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    srv = await asyncio.start_server(manejar, "0.0.0.0", 8080)
    async with srv:
        await srv.serve_forever()
```
- Misma forma que `server_threads.py` (clase 14), pero `start_server` crea una **Task**, no un thread.
- **500 clientes → 1 thread, ~0,1 s.** Medido: **10 000 clientes en 2,6 s con 1 thread** → respuesta al **C10K**.
  El techo pasa a ser **`ulimit -n`** (descriptores), no la memoria ni el scheduler.

## 3. ⭐ ¿Hace falta Lock?
- El cambio de tarea **solo ocurre en un `await`** → código sin `await` en el medio es **atómico**.
- `contador += 1` con 1000 corrutinas → siempre 1000 (con threads se pierden sumas).
- **Pero** si hay un `await` **entre leer y escribir** → race condition (medido: 100 transferencias → saldo 999 en vez de 900).
```python
lock = asyncio.Lock()
async with lock:          # async with: tomar el lock puede ESPERAR (ceder al loop)
    saldo = cuentas[o]
    await registrar()
    cuentas[o] = saldo - monto
```
> **Regla: lock solo si la sección crítica contiene un `await`.** Y se ve leyendo el código.
> (Nunca `threading.Lock` en una corrutina: bloquearía el loop.) También: `asyncio.Semaphore`, `Event`, `Queue`.

## 4. Clientes concurrentes
```python
async with httpx.AsyncClient(timeout=10) as c:        # UNO, reutilizado (pool + keep-alive)
    sem = asyncio.Semaphore(10)                         # acotar
    async def bajar(url):
        async with sem:
            return await c.get(url)
    resultados = await asyncio.gather(*(bajar(u) for u in urls), return_exceptions=True)
```
| (10 descargas de 0,3 s, medido) | tiempo |
|---|---|
| secuencial | 3,46 s |
| `gather` | **0,33 s** (lo que la más lenta) |
| `Semaphore(3)` | 1,35 s (tandas de 3) |
| `requests` dentro de la corrutina | **3,44 s** (bloquea el loop = secuencial) |
- **Un solo cliente**: reutiliza conexiones (10 pedidos secuenciales = **1** conexión TCP).
- **Siempre timeout** (falacia "la red es confiable" / "la latencia es cero", clase 12).
- **Acotar** evita: agotar **descriptores** (`Too many open files`), **saturar/ser bloqueado** por el servidor, saturar la red.
- **`gather` normal:** la 1ra excepción sube y **perdés los demás resultados** (¡y las otras no se cancelan!).
  **`return_exceptions=True`:** lista con resultado **o** excepción en cada lugar → **lo que quiere el TP2** (tareas independientes).

## 5. Timeouts y cancelación
```python
try:
    async with asyncio.timeout(5):        # 3.11+ · o: await asyncio.wait_for(coro, 5)
        datos = await reader.read(4096)
except TimeoutError: ...
```
- El timeout **cancela** la tarea (no queda corriendo de fondo).
- `tarea.cancel()` **inyecta `CancelledError` en el próximo `await`**:
  - una tarea que **calcula sin `await` no se puede cancelar** (medido: pedido a 0,2 s, efectivo a 2 s).
  - limpieza con **`try/finally`**.
- ⚠️ **Si capturás `CancelledError`, relanzala (`raise`)**. Si no: la tarea sigue viva, `await tarea` cuelga y **los timeouts dejan de funcionar**.
- `CancelledError` hereda de **`BaseException`** para que un `except Exception:` no se la coma.

## 6. Apagado ordenado
```python
cerrar = asyncio.Event()
for s in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(s, cerrar.set)    # el callback corre ENTRE tareas: seguro
await cerrar.wait()
srv.close()                                    # dejar de aceptar
# avisar → esperar un rato → cancelar las tasks de los clientes que quedan → await srv.wait_closed()
```
- Mejor que `signal.signal()` (clase 6): no interrumpe en cualquier momento; por debajo es el **self-pipe** (`set_wakeup_fd`).
- ⚠️ **Desde Python 3.12, `async with srv:` / `wait_closed()` espera a que se cierren TODAS las conexiones**: con un `nc` abierto
  el proceso no termina. Hay que cortar los clientes (o `srv.close_clients()` en 3.13). Ver `soluciones/chat_async.py`.

## 7. ¿Cuándo asyncio?
| Situación | Herramienta |
|---|---|
| Muchas conexiones, trabajo liviano | **asyncio** |
| Pocas conexiones, lógica compleja | threads |
| CPU-bound | procesos |
| Biblioteca solo sincrónica | threads / `asyncio.to_thread` |
| Servidor simple que anda | `socketserver` |
Costo: **todo tiene que ser async**; una llamada bloqueante (`requests`, `time.sleep`, BD sincrónica) arruina la ventaja.

## ❓ Autoevaluación
1. ¿Por qué `write()` no lleva `await` y `drain()` sí? ¿Qué pasa sin `drain()` con un cliente lento?
2. ¿Qué método de lectura usás para framing por delimitador? ¿Y por longitud? ¿Qué devuelve `read()` si el otro cerró?
3. ¿Qué crea `start_server` por cada cliente? ¿Cuántos threads usa con 500 clientes?
4. ¿Cuándo hace falta un `asyncio.Lock`? ¿Por qué `async with`?
5. ¿Por qué hay que reutilizar el `AsyncClient`? ¿Qué pasa si usás `requests` dentro de una corrutina?
6. Diferencia entre `gather` normal y con `return_exceptions=True`. ¿Cuál para el TP2?
7. ¿Cuándo recibe una tarea el `CancelledError`? ¿Por qué una tarea que calcula no se puede cancelar?
8. ¿Qué pasa si capturás `CancelledError` sin relanzarla? ¿Por qué hereda de `BaseException`?
9. ¿Qué ventaja tiene `loop.add_signal_handler()` sobre `signal.signal()`?
