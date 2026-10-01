# Clase 8 — Multiprocessing: fundamentos · Resumen

`multiprocessing` = procesos con una API **portable y de alto nivel**. En Linux por debajo sigue siendo `fork()`,
pero te ahorrás `wait`, zombies, `os._exit`, el `if pid == 0`…

## Process: lo básico
```python
from multiprocessing import Process

def tarea(nombre):
    ...

if __name__ == "__main__":                 # ¡siempre! (con spawn el hijo re-importa el archivo)
    p = Process(target=tarea, args=("w1",))  # args es una TUPLA → ("w1",) con coma
    p.start()                              # arranca (una sola vez)
    p.join()                               # espera
    print(p.exitcode)                      # 0 ok · >0 error · <0 murió por señal (-15 = SIGTERM)
```
Como clase: heredar de `Process` y sobreescribir **`run()`** (se llama solo al hacer `start()`).

| Método / atributo | |
|---|---|
| `start()` · `join(timeout)` · `is_alive()` | arrancar · esperar · ¿sigue vivo? |
| `terminate()` / `kill()` | SIGTERM / SIGKILL |
| `pid` · `name` · `exitcode` · `daemon` | |

## fork vs spawn vs forkserver

| Método | Cómo arranca el hijo | Velocidad | Hereda estado | Default en |
|---|---|---|---|---|
| **fork** | clona al padre (COW) | ⚡ muy rápida | **todo** (variables, módulos, locks, conexiones…) | Linux (hasta 3.13) |
| **spawn** | intérprete **nuevo**, re-importa el módulo, recibe la función por **pickle** | 🐢 lenta (~25×) | nada | Windows, macOS |
| **forkserver** | le pide a un proceso servidor **limpio** que haga fork | media | casi nada | Linux desde Python 3.14 |

- Windows **no tiene fork**: usa `CreateProcess()` ("arrancame este ejecutable desde cero").
- Peligro de **fork con threads**: el hijo hereda locks que podían estar tomados por un hilo que en el hijo **no existe** → deadlock. Para eso está forkserver.
- Con spawn solo podés pasar cosas **picklables** (no lambdas, closures ni archivos abiertos).
```python
mp.set_start_method("spawn")          # global, al inicio, una vez
ctx = mp.get_context("forkserver")    # o un contexto puntual: ctx.Process(...)
```

## "Daemon" en multiprocessing ≠ daemon de Unix
- `Process(..., daemon=True)` = **hijo desechable**: cuando el padre termina, Python le manda SIGTERM (y luego SIGKILL).
- Un daemon de Unix (sshd, cron) hace fork + `setsid()` + cierra stdin/out/err + `chdir("/")`… y vive solo.
- Un proceso daemon **no puede tener hijos** (`AssertionError`).
- Sirve para: monitoreo, heartbeats, logging. **No** para cosas críticas (las cortan a la mitad).

## Pasar datos
- Por **argumentos**: se copian (pickle). Si el hijo los modifica, **el padre no se entera**.
- Globales con fork: el hijo ve una **copia** (COW) del momento del fork.

## Comunicación básica

| | `Queue()` | `Pipe()` |
|---|---|---|
| Extremos | muchos productores / muchos consumidores | **2** extremos |
| Sentido | — | **bidireccional** por defecto (`duplex=True`) |
| API | `put()` / `get()` (bloquea) | `send()` / `recv()` |
| Por dentro | pipe + hilo alimentador + pickle | pipe/socket + pickle |

```python
q.put(item);  item = q.get()                 # None como centinela de fin (uno por consumidor)
a, b = Pipe();  a.send("hola");  b.recv()
```

## ❓ Autoevaluación
1. ¿Para qué sirve `if __name__ == "__main__":` y cuándo es imprescindible?
2. ¿Qué significa `exitcode = -9`?
3. Compará fork, spawn y forkserver (velocidad, qué heredan, dónde son default).
4. ¿Por qué es peligroso hacer fork en un programa con threads?
5. ¿Qué hace `daemon=True` en multiprocessing? ¿En qué se diferencia de un daemon de Unix?
6. Si le paso un dict a un `Process` y lo modifica, ¿lo ve el padre? ¿Por qué?
7. ¿Diferencia entre `Queue` y `Pipe`? ¿Cuántos centinelas mando con 3 consumidores?
