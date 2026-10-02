# Clase 18 — Ejercicios resueltos

> Material de estudio armado con Claude.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `scheduler.py` | **Ej. 2 (obligatorio)**: scheduler cooperativo — partes A, B, C y D | `python3 scheduler.py` |
| `asyncio_equivalente.py` | Ej. 3, 4 y 5: corrutinas por dentro, `gather`, `asyncio.run`, el bloqueo escondido | `python3 asyncio_equivalente.py` |
| `scheduler_extras.py` | Adicionales: prioridades + detector de tareas egoístas | `python3 scheduler_extras.py` |

## Salida real del obligatorio (resumida)

```
A) A1 B1 C1 A2 B2 C2 A3 C3 C4        next() llamados: 12
B) [A] paso 1 a los 0.00s · [EGO] calcula 1,5 s · [B] paso 1 a los 1.50s   ← todos congelados
C) 3 tareas × 3 esperas de 0,15 s → total 0.45s (secuencial: 1,35 s)
D) sin `yield from`: tardó 0.00s en vez de 1 s, y no hubo ningún error
```

## Respuestas

**A.**
1. Salen **intercaladas** (round-robin): un paso de cada una por vuelta; las cortas terminan antes.
2. **12** `next()`: 9 pasos + 3 llamadas más (una por tarea) que dan `StopIteration`.
3. Una función **sin `yield` no es un generador**: al llamarla se ejecuta entera y devuelve `None`. Pasarla al scheduler → `TypeError` en `next(None)`.

**B.**
4. Durante los 3 s las demás **no avanzan nada**: el scheduler solo recupera el control cuando la tarea hace `yield`.
5. Con **threads** no: el sistema operativo interrumpe al hilo cuando se le acaba su tiempo (**concurrencia preventiva**).
   Acá cada tarea decide cuándo ceder (**cooperativa**): más simple y sin race conditions, pero una egoísta frena a todas.
6. Es la **regla de oro del event loop** (clase 17): *nada que tarde puede correr sin ceder el control.*

**C.**
7. `dormir()` hace `yield time.monotonic() + segundos`: **cede** diciendo "no me despiertes antes de esta hora".
8. No puede usar `time.sleep()` porque **eso duerme al hilo entero** = al scheduler y a todas las tareas.
9. El total (0,45 s) es **menor que la suma** (1,35 s): mientras una espera, el scheduler corre a las otras. Las esperas se **solapan**.
   (Mi versión usa un **heap** por hora de despertar y, si nadie está listo, el *scheduler* duerme hasta el próximo:
   no gira en vacío. En asyncio real eso es `select`/`epoll` con timeout.)

**D.**
10. `yield from dormir(t)` **delega**: los `yield` de `dormir` suben hasta el scheduler, y cuando `dormir` termina, la tarea sigue.
11. `dormir(t)` a secas **crea** el generador y lo tira: no se ejecuta nada, la tarea no se suspende. No falla porque crear un
    generador es válido — el bug aparece lejos (acá: "dormí 1 s" y pasaron 0,00 s). Es justo el problema que resolvió `await`.

## Ejercicios 3–5 (salida real y respuestas)
```
type(f()) = coroutine · tiene send · c.send(None) → StopIteration con value = 99
gather devolvió ['a', 'b', 'c'] aunque terminaron b, c, a
gather de 3 × 1 s: 1.00s · for con await uno por uno: 3.00s
asyncio.run() dos veces seguidas: anda · adentro de una corrutina: RuntimeError
5 descargas con urllib directo: 2.53s · con asyncio.to_thread: 0.51s
```
- `async def` al llamarla devuelve un objeto **corrutina** y **no ejecuta nada** (igual que crear un generador sin `next()`).
  Si nunca se la espera, Python avisa *"coroutine was never awaited"*.
- El `value` del `StopIteration` es el `return` de la corrutina: **el mismo mecanismo** que el ej. 1.3.
- `@types.coroutine` + `await` sobre un generador → las dos sintaxis son **el mismo mecanismo** por debajo.
- Traducción: `async def buscar(id): conn = await abrir(); datos = await leer(conn, id); return datos`.
- Por qué `async/await`: (1) `yield from` era **ambiguo** (¿iterar o suspender?) y (2) era **fácil olvidarlo** sin error.
- `gather` devuelve en el **orden de los argumentos**; `for … await` las corre **una después de otra** (3 s vs 1 s).
- Olvidarse el `await` de `gather` → no espera nada (y avisa que no se esperó).
- `asyncio.run()` **dos veces seguidas funciona** (cada una crea y cierra su loop); **adentro** de una corrutina → `RuntimeError`.
- **5.1:** `urllib.request.urlopen` es **bloqueante**: congela el loop → las 5 descargas van en serie (2,5 s).
  Hay que usar un cliente **asíncrono** (`aiohttp`, `httpx.AsyncClient`) o mandarlo a un thread con `asyncio.to_thread`.
  Tres llamadas bloqueantes típicas: `time.sleep()`, `requests.get()`, consultas a BD con un driver sincrónico (también: `input()`,
  `open().read()` de archivos grandes, `socket.gethostbyname()`).
- **¿Cuándo conviene asyncio?** Cuando el programa pasa el tiempo **esperando I/O** con muchas tareas. Con CPU no mejora
  (incluso un poco peor por el overhead del loop). Es el **mismo criterio** que el GIL: I/O-bound vs CPU-bound.

## Adicionales (salida real)
```
Orden (A peso 3, b peso 1): A0 b0 A1 A2 b1 A3 A4 A5 b2 b3 b4 b5
⚠ tarea egoísta: lenta0 tardó 100 ms sin ceder (umbral 50 ms)
```
Para prioridades conviene un **heap** (`heapq`) ordenado por "turno virtual" en vez de la `deque`.
