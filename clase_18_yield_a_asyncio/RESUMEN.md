# Clase 18 — De yield a asyncio · Resumen

**Problema de la clase 17:** con callbacks, una conversación de 3 pasos queda partida en 3 funciones y el estado
viaja a mano. **Queremos** escribir código lineal (`leer → consultar → responder`) que **en las esperas ceda el control**.
**Respuesta:** funciones que se suspenden y recuerdan dónde iban → **generadores** → `async`/`await`.

## 1. Un generador se suspende y recuerda
```python
def contar():
    yield 1        # se detiene acá; sus variables locales siguen vivas
    yield 2
g = contar(); next(g)  # 1 ;  next(g)  # 2 ;  next(g) → StopIteration
```
- Crear el generador **no ejecuta nada**.
- Cada generador tiene **su propio estado** (dos `contador()` no comparten `n`): vive en el *frame* del generador, que no se destruye entre `next()`.
- El `return` de un generador viaja en **`StopIteration.value`**.

## 2. También recibe: `send()`
```python
def acumulador():
    total = 0
    while True:
        n = yield total      # produce total y RECIBE n
        total += n
a = acumulador(); next(a)    # ⚠️ obligatorio arrancarlo (si no: TypeError)
a.send(10)  # 10      a.send(5)  # 15
```
→ ya no es un iterador: es **una tarea que se pausa, recibe un dato y sigue**.

## 3. Scheduler cooperativo (event loop en 20 líneas)
```python
def scheduler(tareas):
    pendientes = deque(tareas)
    while pendientes:
        t = pendientes.popleft()
        try:
            next(t)                 # corre hasta su próximo yield
            pendientes.append(t)    # sigue viva → al final
        except StopIteration:
            pass                    # terminó
```
- **Cooperativa:** cada tarea decide cuándo ceder (`yield`). **Preventiva** (threads): el SO interrumpe.
- ⚠️ **Regla de oro:** si una tarea no cede (calcula, `time.sleep`, I/O bloqueante) → **todas se congelan**.
- **Esperar sin bloquear:** `def dormir(s): yield time.monotonic() + s` → la tarea dice "despertame a tal hora"
  y el scheduler corre a otras mientras tanto → las esperas **se solapan**.
- **`yield from otro()`** delega en otro generador (componer tareas). Olvidarlo = crear el generador y tirarlo, **sin error**.

## 4. `async` / `await` = la misma idea con sintaxis propia (PEP 492, Python 3.5)
| Antes (≤ 2015) | Ahora | Significa |
|---|---|---|
| `def` + `yield from` (`@asyncio.coroutine`) | `async def` | esta función se puede suspender |
| `yield from algo` | `await algo` | suspendeme hasta que `algo` termine |
Resolvió: **ambigüedad** (yield from para iterar o para esperar) y **olvidos silenciosos**.
Prueba de que es lo mismo: una corrutina tiene `.send()`; `c.send(None)` la arranca y termina con `StopIteration(value)`.
`await` por debajo = un `send()` que suspende y le pasa el control al loop; el loop luego hace `send(resultado)`.

## 5. asyncio
```python
async def tarea(n):
    await asyncio.sleep(0.1)          # CEDE el control
async def main():
    resultados = await asyncio.gather(tarea(1), tarea(2), tarea(3))   # en paralelo; resultados en el orden pasado
asyncio.run(main())                   # crea el loop, corre, cierra. UNA vez (no adentro de otra corrutina)
```
| asyncio | nuestro scheduler |
|---|---|
| `async def` | `def` con `yield` |
| `await asyncio.sleep(n)` | `yield from dormir(n)` |
| `gather(...)` | encolar varias tareas |
| `asyncio.run(main())` | `scheduler(...)` |

- **Crear ≠ ejecutar:** `saludar()` solo crea la corrutina ("coroutine was never awaited").
- `await asyncio.gather(a(), b(), c())` → ~1 s · `for f in (a,b,c): await f()` → ~3 s.

### ⚠️ `asyncio.sleep` vs `time.sleep`
```python
await asyncio.sleep(1)    # cede: los demás corren
time.sleep(1)             # BLOQUEA EL LOOP ENTERO
```
Nada bloqueante en una corrutina: `time.sleep`, `requests.get`, `urllib`, BD sincrónica, cálculo pesado.
Alternativas: versión async (`aiohttp`, `httpx.AsyncClient`) o `await asyncio.to_thread(func)`.

## 6. ¿Cuándo sirve?
| | Secuencial | asyncio |
|---|---|---|
| 3 tareas que **esperan** 1 s | 3 s | **1 s** |
| 3 tareas que **calculan** 1 s | 3 s | 3 s (o un poco más) |
→ **I/O-bound sí, CPU-bound no** (mismo criterio que el GIL). FastAPI usa `async def` por esto.

## ❓ Autoevaluación
1. ¿Qué pasa si hacés `send(10)` a un generador recién creado?
2. ¿Dónde vive una variable local de un generador mientras está suspendido?
3. ¿Cómo termina una tarea en el scheduler y cómo viaja su resultado?
4. Diferencia entre concurrencia cooperativa y preventiva. ¿Qué pasa con una tarea egoísta?
5. ¿Por qué `dormir()` no puede usar `time.sleep()`?
6. ¿Qué problema de `yield from` resolvió `await`?
7. ¿Qué devuelve llamar a una `async def`? ¿Cuándo se ejecuta?
8. ¿Por qué `urllib` dentro de una corrutina no se solapa? ¿Cómo se arregla?
