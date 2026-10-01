# Clase 5 — Pipes y redirección · Resumen

**Filosofía UNIX:** programas chicos que hacen una cosa bien y se **encadenan**.
Para eso: file descriptors + redirección (`dup2`) + pipes.

---

## 1. File descriptors (fd)
Un **fd** es un número entero = índice en la **tabla de archivos abiertos del proceso**.
"Todo es un archivo": archivos, pipes, sockets, terminales… se usan igual (`read`, `write`, `close`).

| fd | Nombre | Por defecto |
|---|---|---|
| 0 | stdin | teclado |
| 1 | stdout | pantalla |
| 2 | stderr | pantalla |

- `open()` devuelve **el fd libre más bajo** (normalmente 3).
- Cada proceso tiene **su propia** tabla. El hijo de un fork **hereda una copia** (apuntan a los mismos archivos).

```python
fd = os.open("/tmp/a.txt", os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
os.write(fd, b"bytes, no str\n");  os.close(fd)
```

## 2. Redirección = `dup2(viejo, nuevo)`
`dup2(old, new)` hace que **`new` apunte a donde apunta `old`**.

| Shell | Qué hace el hijo antes del exec |
|---|---|
| `cmd > f` | `fd=open(f, WRONLY\|CREAT\|TRUNC)`, `dup2(fd, 1)`, `close(fd)` |
| `cmd >> f` | igual con `O_APPEND` |
| `cmd < f` | `fd=open(f, RDONLY)`, `dup2(fd, 0)` |
| `cmd 2> f` | `dup2(fd, 2)` |
| `cmd > f 2>&1` | `dup2(fd, 1)` y después `dup2(1, 2)` |

> El programa no se entera: sigue escribiendo al fd 1. **El shell cambió adónde apunta el 1.**

## 3. Pipes
`r, w = os.pipe()` → un canal **unidireccional**, FIFO, con buffer en el kernel (~64 KB en Linux).

```
 [ls]  fd1 ──► w ═══ PIPE ═══ r ──► fd0  [grep]
```

### Receta del pipe padre → hijo
1. `pipe()` **antes** del `fork()` (así los dos tienen los fds).
2. Cada uno **cierra el extremo que no usa**.
3. El que escribe, al terminar, **cierra** → el que lee recibe EOF.

### Receta de `cmd1 | cmd2` (lo que hace el shell)
```python
r, w = os.pipe()
if os.fork() == 0:  os.dup2(w, 1); os.close(r); os.close(w); os.execvp(cmd1, ...)
if os.fork() == 0:  os.dup2(r, 0); os.close(r); os.close(w); os.execvp(cmd2, ...)
os.close(r); os.close(w)          # ¡el padre también cierra!
os.wait(); os.wait()
```

### Reglas de bloqueo (preguntan siempre)

| Situación | Resultado |
|---|---|
| leer de pipe **vacío** con escritores vivos | **bloquea** |
| leer de pipe vacío **sin escritores** | devuelve `b""` → **EOF** |
| escribir en pipe **lleno** | **bloquea** hasta que el lector lea |
| escribir **sin lectores** | **SIGPIPE** (mata al proceso) / `BrokenPipeError` en Python |

> 🐛 **Bug número 1:** olvidarse de cerrar un extremo de escritura → el lector espera EOF para siempre → se cuelga.

## 4. subprocess (lo que usás en la vida real)
```python
subprocess.run(["ls", "-la"], capture_output=True, text=True).stdout
subprocess.run(["grep", "error"], input="a\nerror\n", capture_output=True, text=True)
p1 = subprocess.Popen(["ls"], stdout=subprocess.PIPE)
p2 = subprocess.Popen(["wc", "-l"], stdin=p1.stdout, stdout=subprocess.PIPE, text=True)
p1.stdout.close(); print(p2.communicate()[0])
```
⚠️ **Nunca `shell=True` con datos del usuario** → inyección de comandos (`x; rm -rf /`).

## 5. Named pipes (FIFO)

| | Pipe anónimo `pipe()` | FIFO `mkfifo()` |
|---|---|---|
| Nombre en el filesystem | no | **sí** (`/tmp/mi_canal`) |
| Quién lo puede usar | procesos **parientes** (fork) | **cualquier** proceso |
| Dura | lo que los procesos | hasta que lo borres |
| Sentido | uno | uno |

`open()` de un FIFO **bloquea** hasta que haya alguien del otro lado.

## ❓ Autoevaluación
1. ¿Qué es un fd? ¿Qué número te da `open()` normalmente y por qué?
2. ¿Qué hace exactamente `dup2(fd, 1)`? ¿Por qué se hace en el hijo?
3. ¿Por qué el pipe se crea antes del fork?
4. ¿Qué pasa si el padre no cierra el extremo de escritura del pipe?
5. Completá la tabla: leer de pipe vacío sin escritores → ___; escribir sin lectores → ___.
6. ¿Diferencia entre pipe anónimo y FIFO?
7. ¿Por qué `shell=True` es peligroso?
