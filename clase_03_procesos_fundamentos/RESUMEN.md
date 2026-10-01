# Clase 3 — Procesos: fundamentos · Resumen

## Programa vs proceso
- **Programa** = archivo pasivo en disco (la receta).
- **Proceso** = programa **en ejecución** + todo su contexto (cocinar la receta, con tus ollas e ingredientes).
- El mismo programa puede correr como **muchos procesos** a la vez, cada uno independiente.

## El árbol de procesos
Todo proceso tiene un **padre** (PPID). El ancestro de todos es el **PID 1** (`init`, hoy `systemd`).

```
systemd(1)─┬─sshd──sshd──bash──python
           ├─dockerd──containerd
           └─nginx─┬─nginx
                   └─nginx
```
- **Huérfano:** el padre murió antes → lo **adopta** init (PPID pasa a 1).
- **Zombie:** el hijo terminó pero el padre **no recogió** su estado con `wait()` → ocupa una entrada en la tabla. (Clase 4.)

## Qué tiene cada proceso

| Componente | Qué es |
|---|---|
| **PID / PPID** | identificador propio / del padre (los PIDs se **reciclan**) |
| **Estado** | `R` running · `S` sleeping (esperando algo) · `T` stopped · `Z` zombie |
| **Memoria virtual** | su propio espacio de direcciones, **aislado** de los demás |
| **File descriptors** | tabla de archivos abiertos: 0 = stdin, 1 = stdout, 2 = stderr |
| **Credenciales** | UID / GID → qué permisos tiene |

## Memoria virtual: el mapa de un proceso

```
 direcciones altas
 ┌──────────────┐
 │    STACK     │  variables locales, argumentos, retornos — crece ↓
 │      ↓       │  (recursión infinita = stack overflow)
 │   (libre)    │
 │      ↑       │
 │    HEAP      │  memoria dinámica (malloc / objetos de Python) — crece ↑
 ├──────────────┤
 │    BSS       │  globales SIN inicializar → el kernel las pone en 0 (no ocupan lugar en el ejecutable)
 │    DATA      │  globales inicializadas (int x = 42;)
 │    TEXT      │  el código — SOLO LECTURA (escribir = SIGSEGV), compartible entre procesos
 └──────────────┘
 direcciones bajas
```

- Cada proceso cree que tiene toda la memoria para él: la **MMU** traduce direcciones virtuales → físicas.
  Dos procesos pueden usar "la misma" dirección virtual sin pisarse.
- Heap y stack crecen en **direcciones opuestas** para aprovechar el mismo hueco libre.

## Mirar todo esto en Linux

| Quiero ver… | Comando |
|---|---|
| el árbol | `pstree -p`, `ps -ef --forest` |
| PID de mi shell / del último proceso en background | `$$` / `$!` |
| mapa de memoria | `cat /proc/<pid>/maps` (`[heap]`, `[stack]`, `.so`) |
| archivos abiertos | `ls -l /proc/<pid>/fd` |
| estado, UID, memoria | `cat /proc/<pid>/status` |
| PID máximo | `cat /proc/sys/kernel/pid_max` |

En Python: `os.getpid()`, `os.getppid()`, `os.getcwd()`, `os.listdir(f"/proc/{pid}/fd")`.

## ❓ Autoevaluación
1. ¿Qué diferencia hay entre programa y proceso?
2. ¿Qué es un huérfano y quién lo adopta? ¿Y un zombie?
3. ¿Qué guarda cada segmento: text, data, BSS, heap, stack? ¿Cuál es de solo lectura?
4. ¿Por qué BSS no agranda el archivo ejecutable?
5. ¿Cómo pueden dos procesos usar la misma dirección virtual sin conflicto?
6. ¿Qué tres file descriptors hereda todo proceso?
