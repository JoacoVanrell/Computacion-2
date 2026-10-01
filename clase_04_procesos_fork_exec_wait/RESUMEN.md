# Clase 4 — fork, exec, wait · Resumen

Las 3 syscalls con las que se construye todo en UNIX (el shell, los servidores, los subprocesos).

```
 fork()  → DUPLICA el proceso         ("clonarme")
 exec()  → REEMPLAZA el programa       ("transformarme en otro programa", mismo PID)
 wait()  → RECOGE al hijo que terminó   ("enterarme cómo terminó y liberar su entrada")
```

---

## fork(): un proceso entra, dos salen

```python
pid = os.fork()
if pid == 0:
    # HIJO   (fork le devuelve 0)
    ...
    os._exit(0)
else:
    # PADRE  (fork le devuelve el PID del hijo)
    ...
```

| Valor que devuelve | Quién lo ve |
|---|---|
| `0` | el **hijo** |
| `> 0` (PID del hijo) | el **padre** |
| error | en Python lanza `OSError` (en C devuelve -1) |

- Después del fork los dos siguen **desde la misma línea**; el `if` decide qué hace cada uno.
- El orden en que imprimen padre e hijo **no está garantizado** (decide el scheduler).
- **Copy-on-Write (COW):** no se copia la memoria al hacer fork. Padre e hijo comparten las páginas
  en solo lectura; recién cuando alguno **escribe** una página, el kernel copia *esa* página.
  → fork es rapidísimo, y si el hijo hace exec enseguida, casi nada se copia.

### Qué hereda el hijo
✅ memoria (copia COW), **file descriptors abiertos**, variables de entorno, directorio actual, máscara de señales, UID/GID.
❌ su PID (tiene uno nuevo), locks de archivos, alarmas/timers pendientes, señales pendientes.

---

## exec(): convertirse en otro programa

`exec` **no crea** un proceso: borra el programa actual y carga otro. Mismo PID, todo lo demás nuevo.
Si `exec` funciona, **nunca vuelve** (lo que está después solo corre si falló).

| Letra | Significa | Ejemplo |
|---|---|---|
| `l` | argumentos como **l**ista de parámetros | `os.execlp("ls", "ls", "-l")` |
| `v` | argumentos como **v**ector (lista) | `os.execvp("ls", ["ls", "-l"])` |
| `p` | busca en el **P**ATH | `execlp`, `execvp` |
| `e` | le pasás el **e**ntorno | `os.execve("/bin/ls", ["ls"], {"PATH": "/bin"})` |

> ⚠️ El primer argumento de la lista es el **nombre del programa** (`argv[0]`): `["ls", "-l"]`, no `["-l"]`.

### El patrón fork-exec-wait (así funciona TODO shell)
```python
pid = os.fork()
if pid == 0:
    try:
        os.execvp(cmd, [cmd] + args)
    except OSError:
        os._exit(127)
_, status = os.waitpid(pid, 0)
```

---

## wait(): evitar zombies

Un hijo que termina **no desaparece**: el kernel guarda cómo terminó hasta que el padre lo pida.
Mientras tanto es un **zombie** (`Z`, `<defunct>` en `ps`). No usa CPU ni memoria, pero ocupa la tabla de procesos.

| Llamada | Hace |
|---|---|
| `os.wait()` | bloquea hasta que termine **cualquier** hijo → `(pid, status)` |
| `os.waitpid(pid, 0)` | espera a **ese** hijo |
| `os.waitpid(-1, os.WNOHANG)` | **no bloquea**: si nadie terminó devuelve `(0, 0)` |

Interpretar `status` (está codificado, no es el código directo):
```python
if os.WIFEXITED(status):    código = os.WEXITSTATUS(status)   # terminó normal con exit(n)
elif os.WIFSIGNALED(status): señal = os.WTERMSIG(status)      # lo mató una señal
```

| | Zombie | Huérfano |
|---|---|---|
| Qué pasó | el **hijo** murió y el padre no hizo wait | el **padre** murió antes que el hijo |
| Qué pasa | queda en la tabla como `Z` | lo adopta **init/systemd** (PPID = 1), que hace wait por él |

---

## Comunicación padre ↔ hijo (por ahora)
- **Código de salida** (0–255): 0 = éxito, distinto de 0 = error. Sirve para "funcionó / no funcionó".
- **Variables de entorno**: se setean antes del fork y el hijo las hereda.
- Para mandar datos de verdad → **pipes** (clase 5).

## ¿Por qué `cd` es interno en un shell?
Porque cambia el directorio del **proceso que lo ejecuta**. Si lo hiciera un hijo, el cambio muere con él.

## ❓ Autoevaluación
1. ¿Qué devuelve `fork()` al padre y qué al hijo?
2. ¿Qué es Copy-on-Write y por qué hace que fork sea barato?
3. ¿`exec` crea un proceso? ¿Cambia el PID? ¿Qué pasa con el código después del exec?
4. ¿Qué diferencia hay entre `execvp` y `execlp`? ¿Y la `e`?
5. ¿Qué es un zombie y cómo se evita? ¿Y un huérfano?
6. ¿Para qué sirve `WNOHANG`?
7. ¿Por qué `os._exit()` en el hijo y no `sys.exit()`?
