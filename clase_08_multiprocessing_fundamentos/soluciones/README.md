# Clase 8 — Ejercicios resueltos

> Material de estudio armado con Claude. Tus ejemplos de Process/Pipe/Queue están en `../mi_trabajo/`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `productor_consumidor.py` | Ej. 3: productor + **varios** consumidores con `Queue` | `python3 productor_consumidor.py --consumidores 3` |
| `ping_pong.py` | Ej. 4: ping-pong con `Pipe()` bidireccional | `python3 ping_pong.py` |
| `fork_vs_spawn.py` | Ej. 5: medir fork / forkserver / spawn con 100 procesos | `python3 fork_vs_spawn.py` |

## Resultado real del ej. 5 (100 procesos, mi máquina)

```
fork          0.085 s   ( 0.85 ms por proceso,  1.0× fork)
forkserver    0.157 s   ( 1.57 ms por proceso,  1.8× fork)
spawn         2.154 s   (21.54 ms por proceso, 25.3× fork)
```
**Por qué:** `fork` solo copia estructuras de control (memoria con copy-on-write). `spawn` arranca **un intérprete
de Python nuevo**, re-importa el módulo y le pasa la función por pickle. `forkserver` hace fork desde un proceso
"limpio" ya levantado: un poco más caro que fork, mucho más barato que spawn.

## Ej. 1 — ¿qué te ahorrás con `Process` respecto de `os.fork()`?
- El `if pid == 0` y el `os._exit()` (si te olvidabas del `_exit`, el hijo seguía ejecutando el código del padre).
- El `wait()`/`waitpid()` y decodificar el status: tenés `p.join()` y `p.exitcode` (negativo = murió por señal, ej. `-15`).
- Los zombies: `multiprocessing` recoge solo a los hijos terminados.
- Portabilidad: funciona en Windows (con spawn).

## Detalles que te pueden preguntar
- **Centinelas:** con *K* consumidores hay que mandar *K* `None`. Con uno solo, los otros quedan bloqueados en `get()`.
- **Leer la Queue antes del `join()`:** un proceso que hizo `put()` no termina hasta que sus datos se "vacían"
  del pipe interno. Si el padre hace `join()` antes de leer y la cola está llena → **deadlock**.
- **Pipe:** el padre cierra el extremo del hijo (igual que con `os.pipe`), así si el hijo muere el `recv()` del padre
  tira `EOFError` en vez de quedarse esperando.
- **Todo lo que viaja (args, Queue, Pipe) se copia con pickle** → si el hijo lo modifica, el padre no se entera.
  Lambdas y closures no se pueden mandar con `spawn`.
