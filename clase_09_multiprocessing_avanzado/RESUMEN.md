# Clase 9 — Multiprocessing avanzado · Resumen

Tres temas: **Pool** (paralelizar muchas tareas), **compartir datos** (Value/Array/Manager) y **patrones**
(Map-Reduce y Pipeline).

---

## 1. Pool: reutilizar workers
Crear un proceso por tarea es carísimo. `Pool(n)` crea **n workers una vez** y les va dando tareas.

```python
from multiprocessing import Pool
if __name__ == "__main__":
    with Pool(4) as pool:                    # Pool() sin número = os.cpu_count()
        res = pool.map(f, range(10))
```

| Método | Devuelve | ¿Orden? | ¿Bloquea? | Args |
|---|---|---|---|---|
| `map(f, it)` | lista, **al final** | ✅ | sí | 1 |
| `imap(f, it)` | iterador, de a uno | ✅ | por item | 1 |
| `imap_unordered(f, it)` | iterador, **el que termina primero** | ❌ | por item | 1 |
| `starmap(f, [(a,b),…])` | lista al final | ✅ | sí | **varios** (desempaqueta) |
| `apply_async(f, (a,))` | `AsyncResult` | — | **no** | varios |
| `map_async`, `starmap_async` | `AsyncResult` | ✅ | **no** | |

`AsyncResult`: `.ready()`, `.successful()`, `.wait(t)`, `.get(timeout=t)`.

**¿Cuál uso?**
- Quiero todo junto y en orden → `map`.
- Muchas tareas, quiero ir mostrando progreso → `imap`.
- Tiempos muy distintos y no me importa el orden → `imap_unordered` (el más rápido).
- La función tiene varios parámetros → `starmap`.
- Pocas tareas distintas, quiero seguir haciendo otra cosa → `apply_async`.

**¿Cuántos workers?** Para **CPU-bound**: tantos como **núcleos**. Más no acelera: se pelean por la CPU.

---

## 2. Compartir datos entre procesos

| Mecanismo | Velocidad | Qué guarda | Cómo funciona |
|---|---|---|---|
| `Value` / `Array` | ⚡ alta | tipos C (`'i'`, `'d'`…) | **mmap** anónimo |
| `Manager().dict()/list()` | 🐢 baja | **cualquier objeto Python** | un **proceso servidor aparte**; los demás le hablan por IPC (proxies) |
| `shared_memory` | ⚡ alta | bytes crudos | bloque con nombre |
| `Queue` / `Pipe` | media | picklables | **mensajes**, no estado compartido |

> **Regla:** datos simples + velocidad → `Value`/`Array`. Datos complejos + comodidad → `Manager`.
> Siempre que varios escriben: `with x.get_lock():` (clase 11).

---

## 3. Patrones

### Map-Reduce
```
 textos ──► [map en paralelo: contar palabras de cada uno] ──► [reduce: sumar los conteos] ──► total
```
```python
conteos = pool.map(mapper, textos)       # paralelo
total = reduce(reducer, conteos)          # secuencial: combina de a dos
```
`reduce(f, [a, b, c, d])` = `f(f(f(a, b), c), d)`.

### Pipeline
```
 q1 ─► [etapa 1] ─► q2 ─► [etapa 2] ─► q3 ─► [etapa 3] ─► q4
```
Cada etapa en su proceso; `None` como centinela que **cada etapa propaga**.
- Si una etapa es lenta → **cuello de botella**. Se escala con **K procesos** en esa etapa (mandar/esperar K centinelas)
  y se pierde el orden.

---

## 4. Lo práctico

**Pickle:** todo lo que viaja (args, resultados, items de colas) se serializa.
✅ funciones a nivel de módulo, tipos básicos, clases simples.
❌ **lambdas**, funciones definidas adentro de otras (closures), sockets, archivos abiertos, conexiones.

**Overhead:** multiprocessing conviene cuando **cada tarea cuesta mucho más que serializar** sus datos.

| Caso | ¿multiprocessing? |
|---|---|
| Cálculo pesado (CPU-bound), procesar muchos archivos, comprimir | ✅ |
| Esperar la red (I/O-bound) | ❌ → threads o asyncio |
| Tareas de < 10 ms cada una | ❌ el overhead se come la ganancia |

**Speedup** = T_secuencial / T_paralelo · **Eficiencia** = speedup / workers.
Nunca llega a ser perfecto: pickle, crear procesos y la parte secuencial (**Ley de Amdahl**).

## ❓ Autoevaluación
1. ¿Por qué Pool es mejor que crear un Process por tarea?
2. Diferencia entre `map`, `imap` e `imap_unordered`. ¿Cuál es más rápido y por qué?
3. ¿Cuándo usás `starmap`? ¿Y `apply_async`?
4. ¿Por qué `pool.map(lambda x: x*2, ...)` falla?
5. ¿Cómo funciona un `Manager` por dentro y por qué es más lento que `Value`?
6. ¿Qué pasa en un pipeline si una etapa es 10 veces más lenta? ¿Cómo lo arreglás?
7. ¿Por qué el speedup con 4 workers no es 4?
