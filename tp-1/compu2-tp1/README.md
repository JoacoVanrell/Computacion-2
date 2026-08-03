# Monitor de Procesos y Threads — TP1 Computación II

## Descripción general

Monitor de procesos tipo `htop`, en Python 3.11+, que lee `/proc` directamente
(sin `psutil` ni equivalentes) y muestra la anatomía interna de cada proceso:
estado, memoria, file descriptors, threads, señales, scheduling y stats
globales del sistema. Arquitectura 100% multiproceso: un recolector, 7
analizadores independientes, un agregador y una TUI en `curses`.

### Cómo correr y testear

```bash
cd tp-1/compu2-tp1
docker compose run --rm monitor
```

(usar `run`, no `up` — ver "Limitaciones conocidas" más abajo).

Dentro de la TUI:

| Tecla | Acción |
|---|---|
| `1`-`7` / `r m f t s p g` | cambiar de vista (resumen/memoria/fds/threads/señales/scheduling/sistema) |
| `↑` `↓` | navegar la lista de procesos |
| `Enter` | pin/despin del proceso seleccionado |
| `/` | filtrar por comando |
| `u` | filtrar por usuario |
| `c` | alternar orden (CPU% / RSS / PID) |
| `+` `-` | ajustar el intervalo de refresco de la vista activa |
| `h` / `?` | ayuda |
| `q` | salir |

Para probar el ajuste de intervalos: pará en una vista y apretá `+`/`-` varias
veces, se nota en el "dato de hace Xs" del encabezado. Para probar el pin:
parate en cualquier fila que no sea la primera, apretá `Enter`, confirmá que
sube arriba de todo y no se mueve aunque cambie el orden.

### Señales que recibe el monitor

Con el monitor corriendo (`pid: "host"` en el compose hace que su proceso
sea visible como cualquier otro proceso del host):

```bash
pgrep -f "python -u src/main.py"      # el más chico de los que devuelve
sudo kill -USR1 <pid>                 # dump del snapshot a dumps/
sudo kill -USR2 <pid>                 # toggle verbose (más FDs visibles)
sudo kill -HUP  <pid>                 # recarga config.json en caliente
```

(hace falta `sudo` porque el proceso corre como root dentro del
contenedor). `Ctrl+C` en la terminal donde corre manda `SIGINT` directo,
sin necesidad de `kill`.

---

## Diagrama de arquitectura

```
                         ┌─────────────────────┐
                         │      RECOLECTOR      │
                         │  lista /proc cada 1s │
                         └──────────┬───────────┘
                                    │ escribe (clave entera)
                                    ▼
                    ┌───────────────────────────────┐
                    │  pids_compartidos (Manager)    │
                    │        {'pids': [...]}         │
                    └───┬───┬───┬───┬───┬───┬───┬────┘
                        │   │   │   │   │   │   │   lee cada uno,
                        ▼   ▼   ▼   ▼   ▼   ▼   ▼   su propio intervalo
                    ┌────────────────────────────────┐
                    │  7 analizadores (Process c/u)   │
                    │  resumen memoria fds threads    │
                    │  señales scheduling sistema     │
                    └────────────────┬─────────────────┘
                                     │ queue.put({'nombre', 'ts', 'datos'})
                                     ▼
                              ┌─────────────┐
                              │    Queue    │  (multi-productor, 1 consumidor)
                              └──────┬──────┘
                                     │ queue.get(timeout=0.5)
                                     ▼
                              ┌─────────────┐
                              │  AGREGADOR  │  único que escribe el snapshot
                              └──────┬──────┘
                                     │ snapshot[nombre] = {...} (clave entera)
                                     ▼
                    ┌────────────────────────────────┐
                    │   snapshot (Manager().dict())    │
                    │  {'resumen':{...}, 'memoria':{}  │
                    │   'fds':{}, 'threads':{}, ...}   │
                    └────────────────┬─────────────────┘
                                     │ lee (snapshot.get(nombre))
                                     ▼
                              ┌─────────────┐
                              │   DISPLAY   │  corre en el proceso principal
                              │  (curses)   │  (necesita control de la TTY)
                              └─────────────┘

Compartido por todos los procesos: corriendo = Value('b') (flag de apagado).
Compartido por cada analizador con el Display: intervalo = Value('d'), uno
por vista, ajustable en vivo con +/-.
```

Procesos totales en ejecución: 1 recolector + 7 analizadores + 1 agregador +
1 principal (que hace de Display) = **10 procesos**.

---

## Decisiones de diseño

### ¿Por qué Queue para analizadores → agregador, y no Pipe?

Son **7 productores y 1 consumidor**. Un `Pipe` da dos extremos pensados para
comunicación punto a punto (un proceso de cada lado); si varios analizadores
escribieran al mismo extremo, no está protegido para eso. `Queue` trae un
lock interno que permite muchos `.put()` y muchos `.get()` sin pisarse — es
exactamente el escenario que tenemos. Por dentro, `Queue` arma un pipe real
del sistema operativo (visto en clase 5) más un lock y un thread que
serializa (pickle) los objetos antes de mandarlos por ese pipe.

### ¿Por qué Manager y no Value/Array para el snapshot y los PIDs?

`Value`/`Array` sirven para tipos simples de **tamaño fijo** (un float, un
booleano, un array de C). El snapshot necesita guardar diccionarios anidados
de tamaño variable (un dict distinto por cada PID vivo, que cambia de
cantidad todo el tiempo). Eso solo lo puede dar un `Manager().dict()`: vive
en un proceso servidor aparte, y cuando accedés a una clave, el proxy hace
una llamada IPC que serializa (pickle) el valor y te lo manda — no es una
referencia al original, es una copia. Por eso el patrón en todo el código es
reemplazar la clave **entera** (`snapshot[nombre] = {...}`) y nunca mutar
algo ya guardado (`snapshot[nombre]['datos'][pid] = x` nunca le llega al
servidor, porque `snapshot[nombre]` te devuelve una copia local, no el
original).

`Value` sí se usa donde hace falta: `intervalo` y `corriendo` son escalares
simples, leídos en un loop ajustado cada 0.1s — usar el Manager (con su
ida y vuelta de IPC) ahí sería más lento e innecesario. `Value` pide memoria
con `mmap` en modo `MAP_SHARED`, que el kernel nunca copia en el `fork()` (a
diferencia de la memoria normal, que es copy-on-write) — por eso el cambio
que hace el Display con `+`/`-` lo ve el analizador casi al instante.

### ¿Cómo se manejan las race conditions?

- **TOCTOU al leer `/proc`**: un proceso puede morir entre que se lista su
  PID y se lee su archivo. Todo `procfs.py` envuelve las lecturas en
  `try/except FileNotFoundError/ProcessLookupError/PermissionError` y
  descarta ese PID para el ciclo actual, en vez de verificar existencia
  antes (`os.path.exists` sería una verificación que puede quedar vieja un
  instante después).
- **Escritura concurrente al snapshot**: si los 7 analizadores escribieran
  directo al `Manager().dict()`, sería seguro a nivel de una sola operación,
  pero mezclaría responsabilidades y no resolvería que dos escrituras
  simultáneas de ciclos distintos se pisen sin orden claro. Se resolvió
  arquitectónicamente: los analizadores nunca tocan el snapshot, mandan sus
  datos por `Queue` (que serializa el acceso), y el agregador es el único
  escritor.
- **Lectura de `pids_compartidos`**: mismo patrón — un único escritor
  (recolector), muchos lectores (los 7 analizadores). Nunca hay dos
  escritores compitiendo por la misma clave.
- **`corriendo`/`intervalo`**: son `Value` de un solo escritor (el Display)
  y muchos lectores (los analizadores). Al ser un solo proceso el que
  escribe, no hay una race de "quién gana la escritura" — la única
  condición a cuidar era que los lectores no se queden esperando para
  siempre un cambio, resuelto durmiendo en tramos cortos (0.1s) en vez de
  un sleep largo. Dato aparte: `Value`/`Array` traen un `Lock` asociado por
  default (no lo usamos explícitamente porque no lo necesitamos con un solo
  escritor, pero existe justamente porque, al ser memoria *realmente*
  compartida, dos procesos escribiendo al mismo tiempo sería una race
  condition de verdad — no hay copy-on-write que los aísle).

### ¿Por qué `pid: "host"` en el `docker-compose.yml`?

Sin esa línea, el contenedor tiene su propio namespace de PIDs y `/proc`
solo mostraría los procesos del propio contenedor (básicamente el monitor
mismo y poco más). `pid: "host"` hace que el contenedor comparta el PID
namespace del host, así `/proc` adentro del contenedor es el mismo `/proc`
del sistema real — necesario para que el monitor tenga sentido como
herramienta de inspección.

### ¿Por qué el top 3 de CPU/memoria se calcula en el Display y no en `sistema.py`?

La tabla de datos de la consigna pide el top 3 "derivado del snapshot", no
de `/proc`. Ningún analizador tiene acceso de lectura al snapshot (esa
regla la mantienen los 7 sin excepción: solo mandan datos por `Queue`), así
que calcularlo en `sistema.py` hubiera significado romper esa regla para un
solo analizador, o recalcular CPU%/RSS por proceso de cero (duplicando lo
que `resumen.py`/`memoria.py` ya hacen). El Display, en cambio, ya lee el
snapshot completo para las 7 vistas — ahí el top 3 es una consulta más
(`dibujar_sistema` lee `snapshot.get('resumen')` y `snapshot.get('memoria')`
directamente), sin ensuciar la separación de responsabilidades.

### ¿Por qué esos intervalos por defecto?

Los valores salen directo de la tabla de vistas de la consigna (resumen 2s,
memoria 3s, FDs 5s, threads 2s, señales 10s, scheduling 10s, sistema 2s). El
criterio detrás: los datos que cambian rápido y son baratos de leer
(resumen, threads, sistema) se refrescan seguido; los que implican más
syscalls por proceso (FDs, con un `readlink` por cada descriptor abierto) o
cambian poco de ciclo a ciclo (señales, scheduling) se refrescan más
espaciado, para no gastar CPU del propio monitor innecesariamente.

---

## Conceptos del curso aplicados

- **TOCTOU y `try/except` en vez de `os.path.exists`** (clase 3-4): todo
  `procfs.py` lee `/proc/<pid>/...` asumiendo que el proceso puede morir en
  cualquier momento entre el listado y la lectura — race condition
  inherente a inspeccionar procesos vivos desde afuera.
- **Zombies** (clase 4, fork/exec/wait): en `analizadores/sistema.py`
  cuento zombies mirando `estado == 'Z'` en `/proc/<pid>/stat` campo 3. Un
  zombie es un proceso terminado cuyo padre todavía no llamó a `wait()`, por
  eso sigue apareciendo en `/proc` aunque ya no ejecute nada.
- **Estados de proceso más allá de R/S/D/T/Z** (clase 3): el campo `estado`
  se muestra tal cual viene del kernel, sin restringirlo a los 5 obligatorios
  de la consigna, así que en sistemas reales también aparece `I` (idle
  kernel thread — no cuenta para el load average) y `t` (traced, detenido
  por un debugger). De los cinco obligatorios, `D` (uninterruptible sleep)
  es el más particular: el proceso espera I/O y el kernel no lo despierta ni
  le entrega señales mientras está en ese estado — por eso un proceso en `D`
  ni siquiera se puede matar con `SIGKILL` hasta que termine esa espera.
- **Copy-on-write y por qué `Value` es la excepción** (clase 4 y 7): un
  `fork()` normal da a cada proceso su propia copia de la memoria en cuanto
  alguien escribe. `multiprocessing.Value` evita eso a propósito pidiendo
  memoria con `mmap(MAP_SHARED)`, que el kernel nunca copia — por eso es la
  única forma de que un cambio en el proceso principal (`+`/`-` de
  intervalo) lo vea un analizador ya en ejecución sin pasar por IPC.
- **Pipes** (clase 5): `multiprocessing.Queue` arma, por dentro, un pipe real
  del sistema operativo entre los procesos (más un lock y un thread que
  serializa con pickle) — es el mismo mecanismo que un pipe crudo de shell,
  aplicado con una capa de seguridad para múltiples productores.
- **Señales y máscaras hexadecimales** (clase 6): `SigBlk`/`SigIgn`/`SigCgt`
  son máscaras de 64 bits donde el bit `N` representa la señal `N+1` (no
  existe la señal 0). Decodificadas en `procfs.decodificar_mascara` con
  `numero & (1 << n)` para chequear cada bit, usando el módulo `signal` de
  la stdlib para el nombre. Bloqueada (`SigBlk`) y con handler (`SigCgt`)
  son ejes independientes: una señal bloqueada no dispara su handler hasta
  que se desbloquea, aunque tenga uno registrado.
- **Self-pipe y handlers async-signal-safe** (clase 6): `src/senales.py`
  maneja las señales que recibe el monitor mismo (distinto del analizador
  que lee señales de OTROS procesos). El handler registrado con
  `signal.signal()` hace **una sola cosa**: `os.write()` de un byte con el
  número de señal a un pipe (`os.pipe()`) — eso es lo único garantizado
  async-signal-safe, porque un handler puede interrumpir al programa en
  cualquier punto, incluso en medio de un `malloc` o de una estructura de
  datos a mitad de modificar. Toda la lógica real (apagar, recargar
  `config.json`, volcar el snapshot, togglear verbose) se ejecuta después,
  en el loop principal de `loop_display`, leyendo ese pipe de forma no
  bloqueante — nunca dentro del contexto de la señal. Los handlers se
  instalan en `main.py` **después** de lanzar los 7 analizadores y el
  agregador (`p.start()`), para que esos hijos hereden la disposición de
  señal por default y no compartan el pipe del proceso principal.
- **Por qué los hijos ignoran `SIGINT` explícitamente**: `Ctrl+C` en una
  terminal manda `SIGINT` a **todo el grupo de procesos** en primer plano,
  no solo al principal (comportamiento de control de trabajos de la shell,
  no algo que el programa elija). Sin protección, cada analizador,
  el recolector y el agregador recibían la señal por su cuenta y Python les
  tiraba `KeyboardInterrupt` en medio del `time.sleep()`/`queue.get()` —
  crasheaban todos en paralelo, cada uno con su propio traceback, antes de
  que el apagado coordinado por `corriendo.value` llegara a tiempo. La
  solución: `signal.signal(signal.SIGINT, signal.SIG_IGN)` al arrancar cada
  hijo (`base.py`, `recolector.py`, `agregador.py`) — así solo el proceso
  principal reacciona a `Ctrl+C`, y son los hijos los que se enteran del
  apagado de la forma prolija que ya tenían (viendo `corriendo.value` en su
  propio loop), no por la señal cruda. Si en cambio matás un solo
  analizador puntual con `kill <pid>` (sin pasar por el grupo), *ese*
  proceso muere y dejás de recibir datos frescos para esa vista, pero el
  resto del monitor sigue funcionando — no hay dependencia dura entre
  analizadores.
- **`mmap` y memoria compartida** (clase 7): la base de por qué `Value`
  cruza la frontera entre procesos (ver decisión de diseño más arriba).
- **`multiprocessing.Process`, `Queue`, `Manager`** (clases 8-9): toda la
  arquitectura — recolector, 7 analizadores y agregador como procesos
  independientes, `Queue` para IPC muchos-a-uno, `Manager().dict()` para el
  estado compartido de tamaño variable.
- **Threads como LWPs, PID vs TID** (clase 10): en `analizadores/threads.py`
  cada thread se lista con `/proc/<pid>/task/<tid>/`. El TID no es un
  identificador secundario: es un PID real y único en todo el sistema (el
  "PID" del proceso completo es, en el kernel, el TID de su thread
  principal) — por eso el estado de CPU% por thread se puede indexar solo
  por `tid`, sin combinarlo con el `pid`. Mirado al revés: un *thread*
  comparte el mismo PID que su proceso (todos los threads de un proceso
  tienen el mismo valor de "PID" visible), mientras que un *proceso* nuevo
  siempre se lleva un PID propio — esa es la diferencia concreta entre
  crear un thread y hacer `fork()`, y se ve directo comparando la salida de
  la vista Resumen (un PID por proceso) contra la vista Threads (varios TID
  bajo el mismo PID).
- **CPU% global sin `HZ` ni tiempo transcurrido** (clase 3, jiffies):
  `resumen.py` calcula CPU% por proceso con `delta_jiffies / (dt * HZ)`,
  porque un proceso no tiene una categoría "idle" propia — hace falta una
  vara externa (cuántos jiffies *podría* haber usado) para compararlo.
  `sistema.py` calcula el CPU% global distinto: las categorías de
  `/proc/stat` (`user`, `system`, `idle`, `iowait`...) ya son una partición
  completa del tiempo de CPU — cada jiffy transcurrido cae en alguna de
  ellas, incluido el tiempo sin hacer nada. Por eso ahí alcanza con
  `delta_categoria / delta_total_de_categorías`, sin necesitar `HZ` ni el
  tiempo transcurrido: la suma de todos los deltas ya es el 100%.
- **Scheduler: nice/priority, políticas, context switches** (clase 10):
  `priority = 20 + nice` para procesos `SCHED_OTHER`; `rt_priority` es una
  escala aparte (1-99) que solo aplica a `SCHED_FIFO`/`SCHED_RR`, por eso da
  0 en scheduling normal. Un proceso CPU-bound acumula más context switches
  **involuntarios** (el scheduler le saca la CPU al acabarse su quantum,
  aunque siga queriendo correr) que voluntarios (que ocurren cuando el
  propio proceso se bloquea a esperar algo, como I/O).

---

## Limitaciones conocidas

- `docker compose up` en primer plano no renderiza bien la TUI de curses
  (procesa la salida como logs con prefijo por servicio, no es transparente
  para los códigos de escape de curses). Usar `docker compose run --rm
  monitor`, o `docker compose up -d` + `docker attach <container>`.
- `analizadores/fds.py` no puede leer `/proc/<pid>/fd/` de procesos de otros
  usuarios (`PermissionError`) — esos PIDs simplemente no aparecen en la
  vista FDs, aunque sí en las demás vistas.
- El pin (`Enter`) en la vista Threads pinea **todos** los threads del PID
  seleccionado (porque ahí varias filas comparten el mismo `pid`, y el pin
  identifica por `pid`), no solo la fila puntual.
- La primera lectura de cualquier analizador con delta de CPU (resumen,
  threads, sistema) siempre muestra 0.0% — no hay lectura anterior contra
  la cual calcular el delta de jiffies.
- Terminales muy chicas pueden cortar contenido en el panel de detalle; no
  hay manejo de `SIGWINCH` para reflow dinámico ante un resize en vivo
  (opcional según la consigna).
- Para mandar señales al monitor desde afuera del contenedor hace falta
  `sudo` (el proceso corre como root dentro del contenedor, aunque el PID
  sea visible desde el host por `pid: "host"`).

---

## Decisiones sobre la TUI

Se eligió `curses` sobre `rich` porque necesitábamos entrada de teclado
**no bloqueante** para los keybindings en vivo (`stdscr.nodelay(True)` +
`timeout(200)`), que `rich` no da de fábrica. El layout es fijo: encabezado
de dos líneas, lista de procesos ordenable/filtrable, y hasta 1/3 de la
pantalla abajo para el panel de detalle del proceso seleccionado. El
Display corre en el **proceso principal**, no como un `Process` más, porque
`curses` necesita control exclusivo de la terminal — si fuera un hijo
aparte, competiría por la TTY con el proceso principal.

---

## Lo que aprendí

Lo que más me costó entender al principio fue por qué un Manager().dict() no es simplemente "una variable compartida" — cuando entendí que snapshot[clave] en realidad te devuelve una copia que viajó por pickle, y no una referencia al original, un montón de decisiones de diseño del código empezaron a tener sentido (como por qué siempre reemplazo la clave entera en vez de mutar algo ya guardado).

Una de las partes más entretenidas fue decodificar las máscaras de señales bit a bit — nunca había pensado las señales como un número binario donde cada posición significa algo puntual.

Lo que más me sorprendió fue un bug que encontré casi al final: pensé que con corriendo.value = False ya tenía el apagado resuelto, pero Ctrl+C manda la señal a todos los procesos a la vez, no solo al principal, y mis analizadores crasheaban por su cuenta antes de que mi lógica "prolija" llegara a actuar. Me hizo entender que el manejo de señales en un sistema con varios procesos no es solo "atajar la señal en algún lado", sino pensar bien QUIÉN la recibe y por qué.