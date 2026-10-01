# Clase 3 — Ejercicios resueltos

> Material de estudio armado con Claude. (El ej. 1 ya trae solución en `../ejercicios.md`.)

| Archivo | Ejercicio | Correr |
|---|---|---|
| `segmentos_memoria.py` | Ej. 3: identificar text/data/BSS/heap/stack en `/proc/<pid>/maps` | `python3 segmentos_memoria.py [pid]` |
| `huerfanos_y_ancestros.py` | Ej. 2 (subir hasta el PID 1) + adicional "detector de huérfanos" | `python3 huerfanos_y_ancestros.py` |
| `procesos_por_usuario.py` | Adicional: conteo de procesos por usuario | `python3 procesos_por_usuario.py` |

## Ej. 2 — respuestas
- **PID 1** en tu Ubuntu es `systemd` (en un contenedor Docker es el comando del contenedor, ej. `bash` o `python`).
- El padre de tu shell es la terminal (`gnome-terminal-server`, `sshd`, `code`…), y subiendo llegás a `systemd`.

## Ej. 3 — cómo reconocer cada segmento en `maps` (salida real de mi prueba)

```
00420000-00719000  r-xp  /usr/bin/python3.13   ← TEXT  (ejecutable + 'x', sin 'w')
009a8000-00a39000  rw-p  /usr/bin/python3.13   ← DATA  (globales inicializadas)
00a39000-00aad000  rw-p                        ← BSS   (anónima pegada a DATA, arranca en cero)
3cf96000-3d096000  rw-p  [heap]                ← HEAP  (crece hacia arriba ↑)
7f63...            r-xp  libc.so.6             ← librerías compartidas en el medio
7fff49386000-...   rw-p  [stack]               ← STACK (direcciones altas, crece hacia abajo ↓)
```
- Permisos: `r` leer, `w` escribir, `x` ejecutar, `p` privada (copy-on-write) / `s` compartida.
- El TEXT **nunca** tiene `w` → escribir ahí = SIGSEGV.
- Las regiones intermedias son las `.so` (libc, libm…) y mapeos anónimos (memoria grande de `malloc`/`mmap`).

## Ej. 4 — PIDs
Los PIDs crecen de a uno (cada `sh -c` es un proceso nuevo). Al llegar a `pid_max`
(`/proc/sys/kernel/pid_max`, normalmente 4194304 en 64 bits) vuelven a empezar desde los libres más bajos.
Por eso **un PID no identifica a un proceso para siempre**: si guardás un PID y el proceso muere,
ese número puede ser de otro proceso más adelante.

## Detalle técnico que te puede servir en el TP1
En `/proc/<pid>/stat` el nombre del comando va **entre paréntesis y puede tener espacios**
(`(Web Content)`), así que no alcanza con `split()`: hay que cortar desde el **último `)`**.
