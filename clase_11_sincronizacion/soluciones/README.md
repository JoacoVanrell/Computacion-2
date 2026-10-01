# Clase 11 — Ejercicios resueltos

> Material de estudio armado con Claude.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `rw_lock.py` | **Ej. 5 (obligatorio)**: Readers-Writers con `Condition`, verificado | `python3 rw_lock.py` · `--preferir lectores` |
| `filosofos.py` | Ej. 7: filósofos — deadlock (A), jerarquía (B), semáforo (C), comparación (D) | `python3 filosofos.py ingenuo / jerarquia / semaforo / comparar` |
| `rate_limiter.py` | Adicional: rate limiter thread-safe (token bucket) | `python3 rate_limiter.py` |

## Readers-Writers — salida real

```
Preferencia: escritores
Lecturas 48 (esperadas 48) · escrituras 6 (esperadas 6)
Máximo de lectores leyendo A LA VEZ: 6        ← leen en paralelo de verdad
Violaciones de las reglas: 0                  ← nunca lector+escritor ni 2 escritores juntos
Espera de los escritores: prom 32 ms · máx 44 ms

--preferir lectores (la del esqueleto)
Espera de los escritores: prom 152 ms · máx 474 ms   ← 10× más: el escritor espera que se vacíe un chorro de lectores
```

**Checklist:** ✅ varios lectores a la vez · ✅ escritor bloqueado si hay lectores · ✅ lectores bloqueados si hay escritor ·
✅ un escritor a la vez · ✅ `Condition` · ✅ context managers (`with rw.lectura():`) · ✅ sin deadlock ni starvation de escritores.

**Para la defensa:**
- **Preferencia a escritores:** si hay `escritores_esperando > 0`, un lector nuevo no entra aunque haya otros leyendo.
  Así el escritor no queda esperando para siempre (*writer starvation*). El costo: si hay muchos escritores, ahora los
  que pueden esperar mucho son los lectores. No existe una política "gratis".
- **Dos `Condition` sobre el mismo `Lock`:** una para despertar lectores y otra para escritores; así no despertás a todos al pedo.
- **`while` y no `if` antes de `wait()`:** al despertar hay que **re-chequear** (otro hilo pudo entrar antes, o *spurious wakeup*).
- **Bug del esqueleto:** `datos["lecturas"] += 1` dentro del **read lock** es una race: varios lectores entran a la vez y
  ese `+=` es una **escritura**. Lo saqué a un lock aparte.

## Filósofos — salida real

```
ingenuo (con Barrier)        🔒 DEADLOCK — comidas por filósofo: [0, 3, 0, 3, 0]
ingenuo --sin-barrera ×10    Se colgó 0 de 10 veces            ← el bug existe pero casi nunca aparece
jerarquia                    ✓ terminó — [3, 3, 3, 3, 3]
semaforo                     ✓ terminó — [3, 3, 3, 3, 3]
comparar: en 2 s comieron    jerarquía [111, 122, 122, 136, 109] (80 %) · semáforo [110, 108, 105, 105, 101] (92 %)
```
(En la versión ingenua puse `acquire(timeout=…)` para poder **detectar** el deadlock y salir; los que se rinden sueltan
su tenedor y por eso algunos alcanzan a comer.)

### Respuestas a las preguntas

**Condiciones de Coffman** (las 4 tienen que darse para que haya deadlock):
1. **Exclusión mutua** – un tenedor lo usa uno solo.
2. **Retener y esperar** – tengo el izquierdo y espero el derecho.
3. **Sin expropiación** – nadie me puede sacar el tenedor.
4. **Espera circular** – 0 espera a 1, 1 a 2, … 4 espera a 0.

En la parte A se cumplen **las cuatro**.

1. **¿Por qué la Barrier lo hace seguro?** El deadlock necesita un entrelazado preciso: los 5 con su izquierdo **al mismo
   tiempo**. La barrera **fuerza** ese estado (nadie pide el derecho hasta que todos tienen el izquierdo). No crea el bug,
   lo hace reproducible. Sin barrera se colgó 0 de 10 → por eso los deadlocks pasan los tests y aparecen en producción.
2. **¿Qué condición rompe el semáforo?** Con `Semaphore(N-1)` hay a lo sumo 4 filósofos en la mesa y 5 tenedores →
   por el principio del palomar, **al menos uno consigue los dos**. Las condiciones 1, 2 y 3 siguen valiendo (siguen
   reteniendo y esperando); lo que nunca llega a cerrarse es el **ciclo de espera** (4). La diferencia con la jerarquía es
   el *cómo*: la jerarquía impone un **orden** a los pedidos; el semáforo limita **cuántos compiten** para que el ciclo
   completo sea imposible. (Si en clase lo plantean como "retener y esperar", fijate que igual retienen y esperan; vale
   discutirlo con el profe.)
   **¿Por qué basta N-1?** Con N-1 comensales y N tenedores siempre sobra uno, así que alguno completa su par, come y libera.
3. **Comer distinta cantidad de veces ¿es deadlock, starvation o ninguna?** Si **todos terminan comiendo** (como acá) no es
   ninguna de las dos: es **falta de equidad** (*unfairness*). **Starvation** sería que alguno pudiera quedarse esperando
   **indefinidamente** mientras los demás avanzan. Deadlock = **nadie** avanza.

## Rate limiter
Token bucket: hasta N fichas, se regeneran a N/s. `Condition.wait(timeout=lo que falta)` para dormir lo justo sin *busy waiting*.
Salida: 20 operaciones a 5/s → **3.00 s** (5 de ráfaga inicial + 15 a 5/s).
