# Clase 4 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu `mini_shell.py` en `../mi_trabajo/` estaba empezado; acá está completo.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `mini_shell.py` | **Ej. 5 (obligatorio)**: mini-shell fork + exec + wait | `python3 mini_shell.py` |
| `zombie_demo.py` | Ej. 4: crear un zombie, verlo en `/proc` y limpiarlo | `python3 zombie_demo.py` |
| `pool_manual.py` | Adicional: pool de N workers solo con `fork`/`wait` | `python3 pool_manual.py --workers 3` |

## Probar el mini-shell

```
soluciones $ echo "hola mundo"        → hola mundo
soluciones $ cd /tmp                  → cambia el directorio DEL SHELL (interno)
tmp $ export SALUDO=che               → interno: lo heredan los próximos hijos
tmp $ sh -c 'echo $SALUDO; exit 3'    → che  [código 3]
tmp $ noexiste                        → comando no encontrado [código 127]
tmp $ sleep 5 &                       → [PID] en background (el prompt vuelve enseguida)
tmp $ exit
```

## Preguntas que te pueden hacer en la defensa

- **¿Por qué `cd` tiene que ser interno?** Porque el directorio de trabajo es **propio de cada proceso**.
  Si lo hiciera un hijo, cambiaría el directorio *del hijo*, el hijo muere y el shell sigue donde estaba.
  Lo mismo con `export` y `exit`.
- **¿Qué pasa después de `execvp` si funciona?** Nada: el código del shell en ese hijo ya no existe,
  fue reemplazado por el programa nuevo. Por eso lo que está después del `exec` solo corre si **falló**.
- **¿Por qué `os._exit()` y no `sys.exit()` en el hijo?** `sys.exit` lanza una excepción que puede ser
  atrapada y ejecuta limpieza del padre heredada (buffers de stdout duplicados, `finally`, `atexit`).
  `_exit` termina el proceso **ya**.
- **¿Por qué `waitpid(pid, 0)` y no `wait()` para el comando en foreground?** Porque si hay hijos en
  background, `wait()` podría devolver uno de ellos y no el que estamos esperando.
- **¿Cómo evito zombies de los procesos en background?** Antes de cada prompt hago
  `waitpid(-1, os.WNOHANG)` en bucle: recoge los que terminaron sin bloquear (devuelve `pid == 0` si nadie terminó).
- **¿Qué significan 126 y 127?** Convención de los shells: 127 = comando no encontrado, 126 = no se puede ejecutar.

## Pool manual — la idea
```
mientras haya tareas o hijos vivos:
    mientras haya lugar (vivos < N) y tareas → fork() un hijo por tarea
    wait()  → un hijo terminó → anoto su resultado (código de salida) → libera un lugar
```
Detalle: después del fork todos los hijos heredan **la misma semilla** de `random`; por eso cada hijo hace
`random.seed(os.getpid())`. El código de salida solo puede valer 0–255, por eso el resultado va `% 256`
(para devolver datos de verdad hacen falta **pipes** → clase 5).
