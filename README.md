# Computación II - 2026

## Datos del estudiante

- **Nombre:** Joaquin Vanrell
- **Legajo:** 64018
- **Email:** j.vanrell@alumno.um.edu.ar
- **GitHub:** @JoacoVanrell (https://github.com/JoacoVanrell)

## Estado

| Componente | Estado |
|------------|--------|
| Bloque 0   | Hecho |
| TP1        | Hecho |
| TP2        | Pendiente |

## Estructura

El repo incluye el material de la cátedra ([compu2_um_2026](https://github.com/Catedra-de-Computacion-II/compu2_um_2026))
y mi trabajo, **una carpeta por clase**:

```
clase_XX_tema/
├── contenido.md, ejercicios.md, …   ← teoría y consignas de la cátedra (sin tocar)
├── RESUMEN.md                       ← resumen para estudiar + preguntas de autoevaluación
├── soluciones/                      ← ejercicios clave resueltos y probados (README con salidas reales y respuestas)
└── mi_trabajo/                      ← lo que hice yo en clase (cuando hay)
```

| Carpeta | Tema | Resumen |
|---|---|---|
| `bloque_0_autonomo/` | Git, Python avanzado, argparse/getopt, filesystem Linux, IPv6 | [RESUMEN](bloque_0_autonomo/RESUMEN.md) |
| `clase_01_docker_intro/` | Docker: imágenes, contenedores, Dockerfile | [RESUMEN](clase_01_docker_intro/RESUMEN.md) |
| `clase_02_docker_aplicado/` | Volúmenes, redes, Compose | [RESUMEN](clase_02_docker_aplicado/RESUMEN.md) |
| `clase_03_procesos_fundamentos/` | Procesos, PID/PPID, `/proc`, estados | [RESUMEN](clase_03_procesos_fundamentos/RESUMEN.md) |
| `clase_04_procesos_fork_exec_wait/` | `fork`, `exec`, `wait`, zombies y huérfanos | [RESUMEN](clase_04_procesos_fork_exec_wait/RESUMEN.md) |
| `clase_05_pipes/` | Pipes, `dup2`, redirecciones | [RESUMEN](clase_05_pipes/RESUMEN.md) |
| `clase_06_senales/` | Señales, handlers, `SIGCHLD` | [RESUMEN](clase_06_senales/RESUMEN.md) |
| `clase_07_mmap_memoria_compartida/` | `mmap`, memoria compartida, `Value`/`Array` | [RESUMEN](clase_07_mmap_memoria_compartida/RESUMEN.md) |
| `clase_08_multiprocessing_fundamentos/` | `multiprocessing`: Process, Queue, Pipe, fork/spawn | [RESUMEN](clase_08_multiprocessing_fundamentos/RESUMEN.md) |
| `clase_09_multiprocessing_avanzado/` | Pool, `map`, Manager | [RESUMEN](clase_09_multiprocessing_avanzado/RESUMEN.md) |
| `clase_10_threading/` | Threads y el GIL | [RESUMEN](clase_10_threading/RESUMEN.md) |
| `clase_11_sincronizacion/` | Lock, Condition, Semaphore, deadlock | [RESUMEN](clase_11_sincronizacion/RESUMEN.md) |
| `clase_12_redes_fundamentos/` | TCP/IP, TCP vs UDP, puertos | [RESUMEN](clase_12_redes_fundamentos/RESUMEN.md) |
| `clase_13_sockets_tcp/` | Sockets TCP, framing | [RESUMEN](clase_13_sockets_tcp/RESUMEN.md) |
| `clase_14_servidores_concurrentes/` | Servidores con threads y procesos | [RESUMEN](clase_14_servidores_concurrentes/RESUMEN.md) |
| `clase_15_udp/` | UDP, confiabilidad a mano | [RESUMEN](clase_15_udp/RESUMEN.md) |
| `clase_16_socketserver/` | `socketserver`, mixins | [RESUMEN](clase_16_socketserver/RESUMEN.md) |
| `clase_17_io_multiplexing/` | `select`/`poll`/`epoll`, `selectors` | [RESUMEN](clase_17_io_multiplexing/RESUMEN.md) |
| `clase_18_yield_a_asyncio/` | Generadores → corrutinas → asyncio | [RESUMEN](clase_18_yield_a_asyncio/RESUMEN.md) |
| `clase_19_http_fastapi/` | HTTP, FastAPI, uvicorn, ASGI | [RESUMEN](clase_19_http_fastapi/RESUMEN.md) |
| `clase_20_asyncio_red/` | Streams, servidores asyncio, timeouts, cancelación | [RESUMEN](clase_20_asyncio_red/RESUMEN.md) |
| `tp-1/` · `tp-2/` | Trabajos prácticos | |
| `trabajos_practicos/`, `FINAL_REQUERIMIENTOS.md` | Consignas de la cátedra | |

`README_catedra.md` es el README original del repo de la cátedra.

### De dónde salió cada carpeta de `mi_trabajo/`
Antes tenía `bloque-0`, `clase-1` … `clase-15` numeradas por **día de clase**; las ubiqué según el **tema**:

| Antes | Ahora |
|---|---|
| `bloque-0` | `bloque_0_autonomo/mi_trabajo` |
| `clase-1`, `clase-2` | `clase_01…`, `clase_02…` |
| `clase-3` (fork, zombie, mini shell) | `clase_04_procesos_fork_exec_wait` |
| `clase-4` (mini_shell) | `clase_05_pipes` |
| `clase-5` (servidor_signals) | `clase_06_senales` |
| `clase-6` (obligatorio) | `clase_07_mmap_memoria_compartida` |
| `clase-7`, `clase-8`, `clase-9` | `clase_08…`, `clase_09…`, `clase_10…` |
| `clase-13`, `clase-14`, `clase-15` | `clase_13…`, `clase_14…`, `clase_15…` |

## Traer las clases nuevas de la cátedra

El repo de la cátedra está configurado como remoto `upstream`:

```bash
git pull upstream main          # trae las clases nuevas
git push origin main            # las sube a mi repo
```

Si hay conflicto en `README.md` (la cátedra también tiene uno), quedarse con el mío:

```bash
git checkout --ours README.md && git add README.md && git commit
```

## Sobre las soluciones y resúmenes

Los `RESUMEN.md` y las carpetas `soluciones/` son **material de estudio armado con Claude** (IA). Cada solución se ejecutó
y su README muestra la salida real. Lo que no se pudo probar en el entorno donde se armaron (Docker, IPv6) está aclarado
en el README de esa clase.
