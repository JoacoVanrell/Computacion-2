# Clase 11 — Sincronización · Resumen

Cierre del bloque de concurrencia local: **las primitivas** y **los problemas clásicos**.

## Por qué hace falta
- **Race condition:** el resultado depende de *quién llega primero*. Ej.: `if saldo >= x: saldo -= x` → dos hilos pasan el `if` y el saldo queda negativo.
- **Datos inconsistentes:** dos campos que deberían cambiar juntos (`contador` y `suma`) y alguien lee en el medio.
- **Sección crítica:** el pedazo de código que toca datos compartidos → que lo ejecute **uno a la vez**.

---

## Las primitivas (tabla para memorizar)

| Primitiva | Para qué | Cómo se usa |
|---|---|---|
| **Lock** | exclusión mutua: uno a la vez | `with lock:` · `acquire(timeout=5)` · `acquire(blocking=False)` |
| **RLock** | el **mismo hilo** lo puede tomar varias veces | método con lock que llama a otro método con el mismo lock |
| **Condition** | esperar a que **una condición** sea verdadera | `with c: while not cond: c.wait()` / `c.notify()` · `notify_all()` |
| **Semaphore(n)** | como mucho **n** a la vez | pool de conexiones, limitar concurrencia |
| **BoundedSemaphore(n)** | igual, pero error si hacés `release()` de más | detecta bugs |
| **Event** | flag "esto ya pasó" | `set()`, `clear()`, `wait(timeout)`, `is_set()` |
| **Barrier(n)** | esperar a que lleguen **los n** | algoritmos por **fases**; `action=` corre una vez cuando llegan todos |

### Lock
- `acquire(timeout=t)` → `True`/`False`. `acquire(blocking=False)` → no espera ("si está ocupado, hago otra cosa").
- Siempre con `with` (o `try/finally`), así se libera aunque haya excepción.

### RLock
Un `Lock` común **se traba solo** si el mismo hilo lo pide dos veces. `RLock` cuenta cuántas veces lo tomó el dueño.
Ej.: `transferir()` toma el lock y llama a `retirar()`, que también lo toma.

### Condition (la más importante para patrones)
```python
with cond:
    while not hay_datos:      # ¡WHILE, no IF! → spurious wakeups / otro se adelantó
        cond.wait()           # SUELTA el lock mientras espera y lo RETOMA al despertar
    usar_datos()
# del otro lado:
with cond:
    hay_datos = True
    cond.notify()             # despierta a uno · notify_all() a todos
```
**Buffer acotado** (productor-consumidor): el productor espera mientras está **lleno**, el consumidor mientras está **vacío**,
y cada uno hace `notify_all()` después de cambiar el buffer.

### Semaphore vs Lock
`Semaphore(1)` ≈ Lock, pero **cualquier hilo** puede hacer `release()` (no solo el que adquirió) → sirve para **señalizar**:
`Semaphore(0)`: uno hace `acquire()` y espera; otro hace `release()` para dejarlo seguir.

### Event vs Condition
| Event | Condition |
|---|---|
| un flag booleano | cualquier condición (predicado) |
| `set()` despierta a **todos** | `notify()` puede despertar a **uno** |
| queda en `True` hasta `clear()` | no tiene estado propio |
Usos de Event: **largada** (todos esperan `inicio.wait()` hasta `inicio.set()`) y **cancelación** (`while not detener.is_set(): ... detener.wait(1)`).

### Barrier
`barrera.wait()` bloquea hasta que llegan los N. Con `timeout`, si alguno no llega → `BrokenBarrierError` para todos.

---

## Deadlock

**Las 4 condiciones de Coffman** (tienen que darse **todas**):
1. **Exclusión mutua** · 2. **Retener y esperar** · 3. **Sin expropiación** · 4. **Espera circular**.
Rompé **una** y no hay deadlock.

| Solución | Qué rompe |
|---|---|
| **Orden global** de locks (siempre A antes que B; ordenar por **índice**) | espera circular |
| **Un solo lock** para los dos recursos | (deja de haber dos recursos) |
| `acquire(timeout)` y soltar todo si falla | retener y esperar / expropiación "voluntaria" |
| Limitar participantes (`Semaphore(N-1)` en filósofos) | el ciclo no puede cerrarse |

| | Qué pasa |
|---|---|
| **Deadlock** | **nadie** avanza, todos esperan a otro |
| **Livelock** | se mueven pero no progresan (se ceden el paso para siempre) |
| **Starvation** | **alguno** espera indefinidamente mientras los demás avanzan |

---

## Problemas clásicos

### Readers-Writers
Muchos lectores **a la vez**, un escritor **solo**, nunca mezclados.
- Versión simple: el **primer lector** toma el lock del recurso y el **último** lo suelta → **favorece lectores** → *writer starvation*.
- Versión con Condition + contador de escritores esperando → **favorece escritores**.

### Filósofos comensales (Dijkstra)
5 filósofos, 5 tenedores; para comer hacen falta los dos de al lado.
- Ingenuo (todos el izquierdo primero) → **deadlock** si los 5 toman el izquierdo a la vez.
- Solución 1: **jerarquía** → tomar primero el de **menor índice** (`sorted((izq, der))` — ordená los índices, no los Lock).
- Solución 2: **`Semaphore(N-1)`** → como mucho 4 a la mesa.

### Double-checked locking (singleton lazy)
```python
if cls._inst is None:            # 1er chequeo SIN lock (rápido, el caso común)
    with cls._lock:
        if cls._inst is None:    # 2do chequeo CON lock (correcto)
            cls._inst = cls()
```

## ❓ Autoevaluación
1. ¿Cuándo necesitás RLock en vez de Lock?
2. ¿Por qué `while` y no `if` antes de `cond.wait()`? ¿Qué hace `wait()` con el lock?
3. Diferencia entre Semaphore y Lock. ¿Para qué sirve `Semaphore(0)`?
4. ¿Cuándo usás Event y cuándo Condition?
5. Enumerá las 4 condiciones de Coffman. ¿Cuál rompe "ordenar los locks"?
6. Diferencia entre deadlock, livelock y starvation.
7. ¿Por qué la versión simple de readers-writers puede dejar al escritor esperando para siempre?
8. ¿Por qué con 4 comensales y 5 tenedores no hay deadlock?
