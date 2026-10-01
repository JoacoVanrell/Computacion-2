# Clase 6 — Señales · Resumen

**Señal** = notificación **asíncrona** del kernel a un proceso ("pasó algo"). Llega en **cualquier momento**,
interrumpe lo que esté haciendo. Pipes = datos que hay que leer; señales = *notificaciones* (como las del celular).

Ante una señal, el proceso puede: **ignorarla**, dejar la **acción por defecto**, o **manejarla** con una función propia.

---

## Las señales que tenés que saber

| Señal | Nº | Origen típico | Default | ¿Capturable? |
|---|---|---|---|---|
| **SIGINT** | 2 | Ctrl+C | terminar | sí |
| **SIGTERM** | 15 | `kill <pid>` | terminar | sí → "andate **prolijo**" |
| **SIGKILL** | 9 | `kill -9` | terminar | **NO** |
| **SIGSTOP** | 19 | `kill -STOP` | pausar | **NO** |
| SIGTSTP | 20 | Ctrl+Z | pausar | sí |
| SIGCONT | 18 | `fg`, `kill -CONT` | continuar | sí |
| **SIGHUP** | 1 | terminal cerrada | terminar | sí → por convención: **recargar config** |
| **SIGCHLD** | 17 | un hijo terminó/cambió | **ignorar** | sí → hacer `waitpid` |
| SIGALRM | 14 | `alarm()`, `setitimer()` | terminar | sí → timeouts |
| SIGPIPE | 13 | escribir en pipe sin lectores | terminar | sí |
| SIGUSR1 / SIGUSR2 | 10 / 12 | vos | terminar | sí → lo que quieras |
| SIGSEGV | 11 | acceso inválido a memoria | terminar + core | (sí, pero no lo hagas) |

> **Regla de oro:** SIGKILL y SIGSTOP **no se pueden capturar ni ignorar**. Por eso primero se manda SIGTERM
> (dejás que limpie) y recién si no responde, SIGKILL.

## Enviar señales

```bash
kill 1234            # SIGTERM          kill -9 1234 / kill -KILL 1234
kill -USR1 1234      # una específica   kill -TERM -1234  (a todo el GRUPO 1234)
pkill -TERM python   # por nombre
```
```python
os.kill(pid, signal.SIGTERM)      os.killpg(pgid, signal.SIGTERM)      signal.raise_signal(signal.SIGUSR1)
```

## Manejar señales

```python
def handler(signum, frame):            # signum = número, frame = dónde estaba el programa
    ...
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGUSR1, signal.SIG_IGN)   # ignorar
signal.signal(signal.SIGUSR2, signal.SIG_DFL)   # volver al default
signal.pause()                                   # dormir hasta que llegue una señal
```

## ⚠️ Reentrancia: qué NO hacer en un handler
El handler puede interrumpir tu código **en la mitad de cualquier línea** (incluso en medio de un `print`).
Evitá ahí: `print`, logging, archivos con buffer, locks, `malloc`… (no son **async-signal-safe**).

| Patrón | Cómo |
|---|---|
| ✅ **Flag** (el más seguro) | el handler solo pone `ejecutando = False`; el loop principal lo revisa |
| ✅ `os.write(fd, b"...")` | escritura directa sin buffer |
| ✅ **Self-pipe** | el handler escribe 1 byte en un pipe; el loop hace `select()` sobre ese pipe junto con otros fds |

## SIGCHLD → chau zombies sin bloquear
```python
def on_sigchld(sig, frame):
    while True:                              # ¡en bucle! pueden haber terminado VARIOS
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            break
```
> Las señales estándar **no se encolan**: si llegan 3 SIGCHLD juntas, podés recibir **una**. Por eso el bucle.

## Timeouts con SIGALRM
```python
def se_paso(sig, frame):
    raise TimeoutError("tardó demasiado")
signal.signal(signal.SIGALRM, se_paso)
signal.alarm(3)          # en 3 s llega SIGALRM  (alarm(0) = cancelar, ¡siempre en un finally!)
signal.setitimer(signal.ITIMER_REAL, 0.5, 0.5)   # cada 0.5 s, con decimales
```

## Señales + threads (Python)
- Los handlers corren **siempre en el hilo principal**.
- `signal.signal()` solo se puede llamar desde el hilo principal.
- `signal.pthread_sigmask(SIG_BLOCK, {...})` bloquea señales en un hilo.

## Patrones típicos de servidor
| Señal | Acción |
|---|---|
| SIGTERM / SIGINT | shutdown limpio (cerrar conexiones, terminar workers, flush) |
| SIGHUP | recargar configuración sin reiniciar |
| SIGUSR1 | mostrar estadísticas |
| SIGUSR2 | rotar logs |
| SIGCHLD | recoger hijos / reiniciar workers |

## ❓ Autoevaluación
1. ¿Qué tres cosas puede hacer un proceso ante una señal?
2. ¿Qué diferencia hay entre SIGTERM y SIGKILL? ¿Cuál mandás primero y por qué?
3. ¿Cuáles dos señales no se pueden capturar?
4. ¿Por qué no conviene hacer `print` dentro de un handler? ¿Qué patrón usás?
5. ¿Por qué el handler de SIGCHLD hace `waitpid` en un bucle con `WNOHANG`?
6. ¿Qué hace Ctrl+C con los procesos hijos del mismo grupo?
7. ¿En qué hilo se ejecutan los handlers en Python?
