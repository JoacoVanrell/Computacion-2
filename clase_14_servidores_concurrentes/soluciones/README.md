# Clase 14 — Ejercicios resueltos

> Material de estudio armado con Claude. Tus 4 estrategias están en `../mi_trabajo/estrategia1..4.py`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `tres_descuidos_fork.py` | **Ej. 3 (obligatorio)**: partes A, A2, B, C y D medidas automáticamente | `python3 tres_descuidos_fork.py todo` |
| `cpu_threads_vs_fork.py` | Ej. 6: trabajo CPU real, threads vs fork | `python3 cpu_threads_vs_fork.py --clientes 8` |
| `servidor_threads_completo.py` | Adicionales: límite de conexiones + `STATS` + cierre ordenado | `python3 servidor_threads_completo.py --max 3` |

## Salida real del obligatorio

```
Parte A:  fd 3 ya está CERRADO → lo cerró el recolector de CPython al perder la última referencia
Parte A2: padre=guardar  fds del padre: 4 → 34 tras 30 clientes · matar al hijo → el cliente NO se entera (timeout)
          padre=cerrar   fds del padre: 4 → 4                   · matar al hijo → el cliente ve el cierre (b'')
Parte B:  zombies tras 50 clientes: 50 · tras 100: 100          ← se acumulan
Parte C:  SIN bucle: zombies por corrida = [17, 11, 13, 9, 16]  ← intermitente
          CON bucle: zombies por corrida = [0, 0, 0, 0, 0]
Parte D:  SIG_IGN → zombies: 0
```

## Respuestas

**A (2–5).** El fd lo cerró **CPython**: cuando un objeto se queda sin referencias se destruye enseguida y el `socket`
cierra su descriptor. En el bucle del servidor, `conn` se reasigna en cada vuelta → el socket viejo pierde su referencia
→ se cierra solo. **Pero el `close()` explícito sigue siendo correcto** porque eso es un detalle de implementación:
- en **C** `accept()` devuelve un `int` y nadie lo cierra por vos → fuga segura;
- si el padre **guarda** la conexión (lista de estadísticas) la referencia sobrevive → fuga (lo mide A2);
- en **PyPy** (sin conteo de referencias) la recolección es diferida → los fds se acumulan hasta que corra el GC.
Conclusión: *el `close()` expresa la intención y no depende de cuándo pase el recolector.*

**A2 (6–8).** Sí crecen (4 → 34). Tras `fork()` existen **dos copias** del fd de la conexión (padre e hijo) que apuntan
al **mismo** socket del kernel. TCP manda el FIN cuando se cierra **la última** copia. Si el hijo muere pero el padre
conserva la suya, la conexión sigue "viva" y el cliente queda esperando.

**B.** Los hijos quedan en estado **`Z`** (zombie, `<defunct>`) y **se acumulan** (50 → 100). En semanas se llena la tabla
de procesos (o el límite de procesos del usuario) y `fork()` empieza a fallar: el servidor deja de atender.

**C (8–12).** No da siempre lo mismo (17, 11, 13…). Las señales estándar **no se encolan**: si varios hijos mueren antes de
que corra el handler, queda **una** SIGCHLD pendiente; un handler sin bucle recoge **uno** y el resto queda zombie.
**`WNOHANG`** = "si no hay hijos terminados, volvé ya con `pid == 0`". Sin él, el `waitpid` dentro del handler
**bloquearía** al proceso (¡dentro de un handler!) esperando a hijos que siguen vivos.
¿Cómo lo encontrarías en producción? Monitoreando la cantidad de procesos en `Z` (`ps -eo stat | grep -c Z`), alertas
sobre el crecimiento de procesos hijos, y reproduciéndolo con una prueba de carga que haga terminar muchos hijos **a la vez**.

**D.** Con `SIG_IGN` no hay zombies: POSIX define que si el padre ignora SIGCHLD **el kernel descarta** el estado de
salida de los hijos (los "cosecha" el kernel). Costo: no podés saber con qué código terminó cada hijo.

## Ej. 6 (salida real, 2 núcleos)
```
1 cálculo solo: 0.08s → 4 en serie ~0.33s
threads  4 clientes: 0.35s  (1.0x)   ← con GIL los threads se turnan: no escalan en CPU
fork     4 clientes: 0.19s  (1.7x)   ← cada hijo es otro intérprete: usa los 2 núcleos
```
Con un build **free-threaded** los threads también escalarían; lo que **no** cambia es el **aislamiento**: si un cliente
crashea a su proceso, con fork el resto sigue; con threads se cae todo el servidor.

## Adicionales (prueba real con `--max 2`)
```
3er cliente: 503 servidor ocupado
stats: activos=2 total=2 rechazados=1 bytes=11 uptime=1s
Ctrl+C → apagando: espero a los clientes (máx 5 s)… listo
```
Detalle de sincronización: el chequeo `activos >= max` y el `activos += 1` van **dentro del mismo lock**; si no, dos
conexiones simultáneas podrían pasar el límite (es el banco de la clase 7 otra vez).
