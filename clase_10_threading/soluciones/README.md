# Clase 10 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu `hilos.py` está en `../mi_trabajo/`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `descargador.py` | **Ej. 9 (obligatorio)**: pool de threads a mano con `Queue` + estadísticas | `python3 descargador.py` · sin internet: `--demo-local` |
| `gil_io_vs_cpu.py` | Ej. 2 y 3: el GIL con I/O vs CPU (y comparación con procesos) | `python3 gil_io_vs_cpu.py` |
| `chat_hilos.py` | Adicional: chat multi-hilo con una `Queue` central | `python3 chat_hilos.py` |

## Resultados reales

```
descargador.py --demo-local --workers 4     (11 URLs que tardan 0.5 s cada una, una da 404)
  Exitosas: 10/11   ✗ /roto: Not Found
  Total: secuencial 5.54s vs 4 workers 1.51s → speedup 3.7x

gil_io_vs_cpu.py
  I/O-bound: secuencial 2.00s · 4 threads 0.50s (4.0x)                       ← threads SÍ sirven
  CPU-bound: secuencial 0.70s · 4 threads 0.73s (1.0x) · 4 procesos 0.41s    ← threads NO (GIL); procesos sí
```
(Mi máquina tiene 2 núcleos, por eso los procesos dan ~1.7x y no 4x.)

## Checklist del obligatorio
- ✅ **Pool fijo**: `--workers N` hilos que se reusan, no uno por URL.
- ✅ **En paralelo**: mientras un hilo espera la red, el GIL queda libre para los otros.
- ✅ **Errores sin crashear**: `URLError` (DNS, 404, conexión rechazada), timeouts → quedan en el resultado con `ok=False`.
- ✅ **Estadísticas**: exitosas, bytes, min/prom/max por URL, total y speedup vs. 1 worker.

## Preguntas de defensa
- **¿Cómo sabe cada worker que tiene que terminar?** Un **centinela `None` por worker**. Si mandás uno solo, termina uno y el resto queda bloqueado en `get()`.
- **¿Para qué `task_done()`?** Para usar `Queue.join()` (esperar a que todas las tareas *procesadas* terminen). Va en un `finally` para que se llame aunque la descarga falle.
- **¿Hace falta el Lock para `resultados.append`?** En CPython un `append` es atómico, pero el lock deja claro que la lista es compartida y te protege si después hacés algo de varios pasos (ej. actualizar un contador y la lista juntos).
- **¿Por qué threads y no procesos?** Es **I/O-bound**: el tiempo se va esperando la red, no calculando. Los threads son más livianos y comparten la lista de resultados sin IPC.
- **¿Qué hay dentro de `ThreadPoolExecutor`?** Exactamente esto: una cola de tareas, N hilos que hacen `get()` en bucle y centinelas para apagar.
- **Chat:** solo el hilo display hace `print()`; así las líneas no se mezclan y nadie más necesita locks.
