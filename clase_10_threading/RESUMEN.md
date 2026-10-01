# Clase 10 — Threads · Resumen

**Thread (hilo)** = otra línea de ejecución **dentro del mismo proceso**. Comparten casi todo → comunicarse es trivial
(es la misma variable)… y pisarse también.

```
 ┌──────────────────── PROCESO ─────────────────────┐
 │   memoria compartida: globales, heap, fds        │
 │  ┌────────┐  ┌────────┐  ┌────────┐              │
 │  │ hilo 1 │  │ hilo 2 │  │ hilo 3 │  cada uno:   │
 │  │ stack  │  │ stack  │  │ stack  │  stack, PC,  │
 │  │ PC     │  │ PC     │  │ PC     │  registros   │
 │  └────────┘  └────────┘  └────────┘              │
 └──────────────────────────────────────────────────┘
```

| | Proceso | Thread |
|---|---|---|
| Memoria | **separada** | **compartida** |
| Comunicación | IPC (pipes, colas…) | variables directas |
| Crear | caro | barato |
| Aislamiento | alto (si uno crashea, los demás siguen) | bajo |
| Paralelismo real en Python | ✅ | ❌ para CPU (GIL) |

**Comparten:** memoria, fds, cwd, UID/GID, handlers de señales. **Propio:** stack, program counter, registros, ID.

## Crear threads
```python
import threading
t = threading.Thread(target=tarea, args=("x", 2), name="w1", daemon=False)
t.start(); t.join(timeout=5); t.is_alive()
threading.current_thread().name   threading.active_count()   threading.enumerate()
```
Como clase: heredar `threading.Thread` y sobreescribir `run()`. (Un thread **no devuelve** valor: guardalo en un atributo o en una cola.)

## El GIL (Global Interpreter Lock) ⭐
Un **mutex** del intérprete: **un solo thread ejecuta bytecode Python a la vez**.

```
 Sin GIL:   núcleo 1: T1 T1 T1 T1      Con GIL:  núcleo 1: T1 T2 T1 T2
            núcleo 2: T2 T2 T2 T2                núcleo 2: -- -- -- --
```
- El GIL **se suelta durante I/O** (red, disco, `sleep`) → los threads sí sirven para esperar cosas.

| Tarea | ¿Threads ayudan? | Usá |
|---|---|---|
| **I/O-bound** (red, disco, BD) | ✅ sí | threads o **asyncio** |
| **CPU-bound** (cálculos, imágenes, compresión) | ❌ no | **multiprocessing** |

**Novedad:** PEP 703 → Python 3.13 trae un build **free-threaded** (sin GIL) experimental; en **3.14** pasa a
"oficialmente soportado" (PEP 779). Sigue sin ser el default. Ver: `sys._is_gil_enabled()`.
Costo: ~5-10 % más lento en un solo hilo y algunas extensiones en C no andan.

## Race conditions
```python
contador += 1      # leer → sumar → escribir: NO es atómico → con 2 hilos se pierden incrementos
```
Solución básica: **`Lock`**
```python
lock = threading.Lock()
with lock:          # adquiere al entrar, libera al salir (aunque haya excepción)
    contador += 1
```
**Deadlock (adelanto):** hilo 1 tiene A y espera B; hilo 2 tiene B y espera A → se cuelgan para siempre.
Se evita tomando los locks **siempre en el mismo orden** (clase 11).

## `threading.local()`
Cada hilo ve **su propia copia** de los atributos: conexiones a BD por hilo, contexto de un request, etc.

## `queue.Queue`: la forma recomendada de comunicar threads
Es **thread-safe** (tiene los locks adentro).
```python
q = queue.Queue();  q.put(x);  x = q.get();  q.task_done();  q.join()
queue.LifoQueue()   # pila        queue.PriorityQueue()   # sale el menor: q.put((prioridad, dato))
```
Patrón productor-consumidor + **un centinela por consumidor** (o el consumidor cuenta los fines de cada productor).

## Daemon threads
`daemon=True` → muere cuando termina el programa principal (sin terminar su trabajo).
Para logging, monitoreo, heartbeats. ❌ Nunca para cosas críticas (escribir en una BD).

## Debug
- `threading.enumerate()` → qué hilos hay.
- `sys._current_frames()` + `traceback.print_stack(frame)` → dónde está trabado cada uno (deadlocks).
- `faulthandler.enable()` → vuelca el stack de todos los hilos si crashea.

## ❓ Autoevaluación
1. ¿Qué comparten y qué no comparten los threads de un proceso?
2. ¿Qué es el GIL? ¿Por qué los threads sirven para I/O y no para CPU?
3. ¿Por qué `contador += 1` no es seguro con dos hilos? ¿Cómo lo arreglás?
4. ¿Qué es un deadlock y cómo se previene?
5. ¿Para qué sirve `threading.local()`?
6. ¿Por qué `queue.Queue` evita la mayoría de los bugs de sincronización?
7. ¿Qué es un daemon thread y cuándo NO usarlo?
8. ¿Qué cambió con Python 3.13 / 3.14 respecto del GIL?
