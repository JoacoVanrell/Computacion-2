# Plataforma de Tareas Distribuidas — TP2 Computación II

## Descripción general

Servicio HTTP al que se le encargan trabajos, que los ejecuta de forma
concurrente y permite consultar su estado y su resultado. Está hecho con
FastAPI sobre un solo event loop de asyncio: una `asyncio.Queue` reparte las
tareas entre N workers (corrutinas), y lo que es CPU-bound se manda a un
`ProcessPoolExecutor` para no congelar el loop.

Tres tipos de tarea:

| Tipo | Recibe | Devuelve | Naturaleza |
|---|---|---|---|
| `descargar` | `urls`: lista de URLs | por cada URL: código HTTP, bytes y segundos (o el error) | I/O-bound: se descargan todas a la vez con `httpx` + `gather` |
| `hashear` | `texto`, `iteraciones` | SHA-256 aplicado N veces, en hexadecimal | CPU-bound: corre en otro proceso |
| `esperar` | `segundos` | `"Dormí N s"` | I/O simulado con `asyncio.sleep` |

Todas aceptan además un `timeout` opcional en segundos (si no se manda, 30 s).

### Cómo correr

```bash
cd tp-2
docker compose up --build
```

La API queda en `http://localhost:8000`, con documentación interactiva en
**http://localhost:8000/docs**: desde ahí se pueden probar todos los
endpoints sin escribir `curl`.

El compose levanta dos servicios: `api` (el TP) y `lento`, un servidor de
prueba que solo se usa para las mediciones (ver más abajo).

Para apagar: `Ctrl+C`, o `docker compose stop` si se levantó con `-d`. Al
apagar se escribe el estado en `tp-2/estados/estado_<fecha>.json`.

### Endpoints

| Método | Ruta | Qué hace | Códigos |
|---|---|---|---|
| `POST` | `/tareas` | Encola una tarea y responde **al instante** con su `id` y estado `pendiente` | 201, 422 (datos inválidos), 503 (cola llena) |
| `GET` | `/tareas` | Lista las tareas. Filtro opcional: `?estado=pendiente` | 200, 422 (estado inexistente) |
| `GET` | `/tareas/{id}` | Estado, resultado y error de una tarea | 200, 404 |
| `DELETE` | `/tareas/{id}` | Cancela una tarea encolada **o en ejecución** | 204, 404, 409 (ya terminó) |
| `GET` | `/estadisticas` | Totales por estado, tiempo promedio por tipo, workers ocupados | 200 |

Estados: `pendiente` → `ejecutando` → `completada` / `fallida` / `cancelada`.

### Ejemplos con `curl`

```bash
# Crear una tarea de cada tipo
curl -s -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo":"esperar","segundos":5}'

curl -s -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo":"hashear","texto":"hola","iteraciones":5000000}'

curl -s -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo":"descargar","urls":["https://www.python.org","https://www.google.com"]}'

# Con un timeout propio: a los 2 s queda fallida
curl -s -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo":"esperar","segundos":10,"timeout":2}'

# Consultar
curl -s localhost:8000/tareas
curl -s "localhost:8000/tareas?estado=completada"
curl -s localhost:8000/tareas/1
curl -s localhost:8000/estadisticas

# Cancelar (funciona también si ya se está ejecutando)
curl -i -X DELETE localhost:8000/tareas/1
```

Datos inválidos dan 422 sin llegar al código: por ejemplo
`{"tipo":"esperar"}` (falta `segundos`) o `{"tipo":"esperar","segundos":-1}`.

### Configuración

Por variables de entorno, leídas en `app/config.py`. En el compose se pueden
cambiar al levantar, sin tocar archivos: `WORKERS=16 docker compose up -d`.

| Variable | Por defecto | Qué controla |
|---|---|---|
| `WORKERS` | 4 | Workers que consumen de la cola |
| `MAXSIZE_COLA` | 100 | Lugares en la cola; si se llena, el POST da 503 |
| `PROCESOS` | `os.cpu_count()` (12 en mi máquina) | Procesos del pool para `hashear` |
| `TIMEOUT_DEFECTO` | 30 | Timeout de una tarea si el cliente no manda uno |
| `LIMITE_APAGADO` | 5 | Cuánto se espera a las tareas en curso al apagar |
| `USAR_EXECUTOR` | 1 | `0` = `hashear` dentro del loop (**mal a propósito**, para la medición 2) |
| `DESCARGA_SECUENCIAL` | 0 | `1` = descargar con `for` + `await` (**mal a propósito**, para la medición 1) |

---

## Diagrama de arquitectura

```
                    Cliente HTTP (curl, /docs)
                              │
                              ▼
   ┌────────────────────────── uvicorn: UN proceso, UN event loop ───────────────────────────┐
   │                                                                                         │
   │   rutas.py (FastAPI)                       estado.py                                    │
   │   POST /tareas ── crea Tarea ────────────► tareas: {id: Tarea}  ◄──── todos leen y     │
   │        │                                   en_curso: {id: Task}       escriben acá     │
   │        │ put_nowait(id)                          ▲                                      │
   │        │ (si está llena → 503)                   │ DELETE: cancel() a la Task           │
   │        ▼                                         │                                      │
   │   ┌──────────────────────────┐            ┌──────┴─────────────────────────────┐        │
   │   │ asyncio.Queue(maxsize)   │──get()────►│ N workers (corrutinas)             │        │
   │   │ solo viajan los ids      │            │ por cada id:                       │        │
   │   └──────────────────────────┘            │  · si está cancelada, la saltea    │        │
   │                                           │  · create_task(ejecutar(...))      │        │
   │                                           │  · await con asyncio.timeout       │        │
   │                                           │  · completada / fallida / cancel.  │        │
   │                                           │  · task_done() en el finally       │        │
   │                                           └──┬──────────────┬──────────────┬───┘        │
   │                                              │              │              │            │
   │                                        esperar        descargar        hashear          │
   │                                     asyncio.sleep   httpx.AsyncClient   run_in_executor │
   │                                     (en el loop)    + gather            │               │
   │                                                     (en el loop)        │               │
   └─────────────────────────────────────────────────────────────────────────┼───────────────┘
                                                                             ▼
                                                        ┌─────────────────────────────────┐
                                                        │ ProcessPoolExecutor             │
                                                        │ un proceso por núcleo,          │
                                                        │ cada uno con su propio GIL      │
                                                        └─────────────────────────────────┘

   lifespan (main.py):  al arrancar → avisa si hay un volcado previo, crea cola, pool y workers
                        al apagar   → centinelas, espera con límite, volcado a JSON, cierra el pool
```

### Flujo de una tarea

1. `POST /tareas`: Pydantic valida el cuerpo según el `tipo`. Se crea la
   `Tarea` en estado `pendiente`, se mete **su id** en la cola con
   `put_nowait` y se responde 201. El endpoint no ejecuta nada: por eso
   responde en milisegundos aunque la tarea tarde minutos.
2. Un worker libre saca el id de la cola. Si mientras esperaba la cancelaron,
   la saltea.
3. La marca `ejecutando` y lanza el trabajo en **su propia `Task`**, que
   guarda en `estado.en_curso`. La espera con `asyncio.timeout(timeout)`.
4. Termina de una de cuatro formas:
   - bien → `completada`, con el `resultado`;
   - se pasó del tiempo → `fallida`, con `error: "Timeout: tardó más de N s"`;
   - un `DELETE` canceló su Task → `cancelada`;
   - cualquier otra excepción → `fallida`, con el tipo y el mensaje del error.
5. En el `finally`, el worker la saca de `en_curso`, llama a `task_done()` y
   vuelve a la cola por la siguiente.

### Archivos

| Archivo | Qué tiene |
|---|---|
| `app/main.py` | La app, el `lifespan` y el apagado ordenado (`apagar()`) |
| `app/rutas.py` | Los 5 endpoints |
| `app/modelos.py` | Modelos Pydantic: uno por tipo de tarea nueva, y `Tarea` |
| `app/estado.py` | El dict de tareas y el de tareas en ejecución |
| `app/workers.py` | El bucle del worker |
| `app/tareas.py` | `esperar`, `descargar` y `hashear` |
| `app/persistencia.py` | Volcado a JSON y aviso al arrancar |
| `app/config.py` | Variables de entorno |
| `mediciones/` | Los scripts de las tres mediciones y el servidor lento |

---

## Decisiones de diseño

### ¿Por qué `asyncio.Queue` y no `queue.Queue`?

Porque todo corre en **un solo hilo**, el del event loop. `queue.Queue.get()`
bloquea el hilo hasta que llegue algo: un worker esperando trabajo
congelaría el loop entero, y no se atendería ningún pedido HTTP. Es el mismo
bug que `time.sleep()` en una corrutina.

`await asyncio.Queue.get()` en cambio **suspende solo esa corrutina** y le
devuelve el control al loop, que sigue atendiendo pedidos y corriendo a los
otros workers. Además `queue.Queue` trae locks para threads que acá no hacen
falta (ver "¿Por qué no hace falta un `Lock`?").

### ¿Cómo evito que una tarea CPU-bound congele la API?

`hashear` es un `for` de SHA-256 sin ningún `await`: si corre en el loop, lo
congela hasta terminar. Por eso se manda a otro proceso:

```python
loop = asyncio.get_running_loop()
return await loop.run_in_executor(pool, calcular_hash, texto, iteraciones)
```

El cálculo **tarda lo mismo**: el executor no lo acelera. Lo que cambia es
que el loop queda libre y sigue atendiendo mientras tanto. La medición 2 lo
muestra: el peor `GET /tareas` pasa de 3269 ms a 3.5 ms.

Las decisiones de detalle:

- **Procesos y no threads**, por el GIL: en un thread, el hash competiría con
  el loop por el único intérprete. Cada proceso tiene el suyo y calcula en
  otro núcleo.
- **El pool se crea una sola vez**, en el `lifespan`, y se guarda en
  `app.state.pool`. Crear un proceso es caro (arranca un intérprete nuevo):
  crearlo por tarea costaría más que muchos de los hashes.
- **`calcular_hash` es una función de módulo y no una `lambda`**: el pool le
  manda la función al otro proceso con `pickle`, que la manda por su nombre.
  Una `lambda` no tiene nombre y da `PicklingError`.

### ¿Cómo implementé la cancelación? ¿Qué pasa con los recursos a medio usar?

El `DELETE` nunca borra la tarea: la marca `cancelada` para que se pueda
seguir consultando. Si ya terminó, responde 409 para no pisar un estado final.

- **Tarea encolada:** de una `asyncio.Queue` no se puede sacar algo del
  medio. Se marca `cancelada` y el worker, cuando la saca, ve el estado y la
  saltea.
- **Tarea en ejecución:** el trabajo de cada tarea corre en **su propia
  `Task`**, no en el worker. El `DELETE` le hace `cancel()` a esa Task, que
  recibe un `CancelledError` en el `await` donde esté esperando. Cancelar al
  worker no servía: se moriría y quedaría un worker menos.

El worker distingue tres orígenes del corte:

| Qué pasó | Qué le llega al worker | Estado final |
|---|---|---|
| Se pasó del timeout | `TimeoutError` (de `asyncio.timeout`) | `fallida` |
| Un `DELETE` | `CancelledError`, y el estado ya es `cancelada` | `cancelada` |
| Se apaga el servidor y cancela al worker | `CancelledError`, y el estado **no** es `cancelada` | se **relanza** con `raise`, para que el worker se apague |

Los recursos, por tipo:

- **`descargar`:** el `httpx.AsyncClient` se abre con `async with`. Si cancelan
  la tarea a mitad de una descarga, el `CancelledError` sale del bloque y el
  `async with` cierra las conexiones igual. No quedan sockets abiertos.
- **`esperar`:** no tiene recursos.
- **`hashear`:** cancelar corta la **espera** del resultado, pero el proceso
  del pool **sigue calculando** hasta terminar (ver "Limitaciones").

Un bug que encontré en el camino: al principio el `DELETE` solo cambiaba el
estado. El worker seguía durmiendo y, al despertar, ponía `completada` y
pisaba el `cancelada`. Al cliente se le había dicho "cancelada" y la tarea
corría igual.

### ¿Qué pasa si un worker lanza una excepción no capturada?

Si una excepción saliera del `while True`, **el worker moriría en silencio**:
quedaría uno menos y nadie se enteraría, y la tarea quedaría `ejecutando` para
siempre. Para que no pase, cada tarea corre dentro de `try/except Exception`:
la tarea queda `fallida` con el motivo en `error`, y el worker vuelve al
`while` a buscar la siguiente.

`task_done()` va en el `finally` para ejecutarse siempre (bien, con error, con
`continue` o cancelada). Si faltara en algún camino, el contador interno de la
cola nunca volvería a cero y un `join()` esperaría para siempre.

### ¿Por qué no hace falta un `Lock`?

Los workers y los endpoints son corrutinas en un solo hilo. El event loop
solo cambia de corrutina en un `await`, así que entre dos `await` nadie
interrumpe. Ningún cambio de estado tiene un `await` entre leer y escribir.

El caso más delicado es el `POST`: primero hace `put_nowait(id)` y después
guarda la tarea en el dict. Parecería que un worker podría sacar el id antes
de que la tarea exista, pero entre esas dos líneas no hay `await`, así que
ningún worker corre en el medio.

### ¿Por qué un solo `AsyncClient` y `gather(..., return_exceptions=True)` en `descargar`?

- **Un cliente para todas las URLs de una tarea:** el cliente reusa las
  conexiones (keep-alive). Uno por URL abriría y cerraría una conexión por
  descarga.
- **`gather`:** lanza todas las descargas a la vez. Tarda lo que la más lenta,
  no la suma (medición 1).
- **`return_exceptions=True`:** si una URL falla, su error vuelve como un
  valor más de la lista. Sin eso, el primer error se lanzaría y se perderían
  los resultados de las otras. La tarea queda `completada`, con el resultado
  URL por URL (código o error). Un 404 no es un error de descarga: es una
  respuesta, y se informa su código.
- Cada URL tiene un tope de 10 s, aparte del timeout de la tarea.

### ¿Por qué httpx?

- `requests` está prohibido, y con razón: es sincrónico, así que mientras
  espera la respuesta congela el loop.
- `httpx` tiene `AsyncClient`, que se usa con `await`, y una forma de uso casi
  igual a `requests`. Es la que usamos en la clase 20.
- `aiohttp` también es asíncrono y habría servido. Elegí `httpx` porque ya lo
  conocía de la clase y porque su API es más directa (`await cliente.get(url)`
  devuelve la respuesta completa, sin otro `async with` para leerla).

### ¿Cómo es el apagado ordenado?

Lo hace la función `apagar()` en `main.py`, que corre después del `yield` del
`lifespan`:

1. **Dejar de aceptar tareas:** de esto se encarga uvicorn. Al recibir
   SIGTERM o SIGINT cierra el puerto, y recién después corre el cierre del
   `lifespan`. Un `POST` durante el apagado recibe *conexión rechazada*.
2. Las tareas `pendiente` se marcan `cancelada` ("El servidor se apagó antes
   de ejecutarla"). Si no, los workers las ejecutarían todas antes de llegar
   a su centinela, porque los centinelas entran al final de la cola.
3. **Un centinela por worker:** cada worker termina la tarea que tiene, saca su
   centinela y se retira solo. Uno por worker, porque cada uno consume uno.
4. Los pasos 3 y 4 corren **con límite** (`LIMITE_APAGADO`, 5 s). Si se pasa,
   se cancela a los workers que quedan y sus tareas quedan `cancelada`
   ("Cortada por el apagado del servidor").
5. **Volcado** a `estados/estado_<fecha>.json`, con
   `await asyncio.to_thread(persistencia.volcar)`. Escribir a disco bloquea, y
   como es I/O y no cálculo, alcanza con un thread.
6. Se cierra el pool.

Por qué 5 s: `docker compose stop` manda SIGTERM y, si a los 10 s el proceso
sigue vivo, manda SIGKILL, que no se puede atrapar. Después de esperar todavía
hay que escribir el JSON: con 5 s queda margen.

Para que la señal llegue a uvicorn, el `CMD` del Dockerfile está en forma
**exec** (con corchetes): así uvicorn es el PID 1 del contenedor. No uso
`loop.add_signal_handler` (como el chat de la clase 20) porque uvicorn ya
maneja esas señales: es el dueño del loop.

La carpeta `estados/` es un volumen, así que los JSON sobreviven al
contenedor. Al arrancar, si hay un volcado previo, se avisa por log:
`Hay un volcado previo: /app/estados/estado_... (6 tareas)`. No se recarga:
la consigna solo pide reportarlo.

---

## Mediciones

Todas corren **adentro del contenedor** (`docker compose exec api python
mediciones/...`), contra la API levantada con Docker y Python 3.11. Las
descargas van al servicio `lento` del compose, para que los números no
dependan de internet y se puedan repetir.

Máquina: Intel Core i7-1355U, 12 hilos: 2 núcleos de rendimiento con
hyperthreading (4 hilos) y 8 núcleos de eficiencia.

### 1. Concurrencia I/O: 20 descargas secuenciales contra concurrentes

```bash
docker compose up -d --build
docker compose exec api python mediciones/medicion1_descargas.py
DESCARGA_SECUENCIAL=1 docker compose up -d
docker compose exec api python mediciones/medicion1_descargas.py
```

Una tarea `descargar` con 20 URLs con demoras fijas entre 0.2 y 1 s
(**suma: 12.55 s**, **la más lenta: 0.89 s**). Tres corridas por modo; tiempo
medido por la API, desde que un worker toma la tarea hasta que termina.

| Modo | Corrida 1 | Corrida 2 | Corrida 3 | Promedio |
|---|---|---|---|---|
| Secuencial (`for` + `await`) | 13.42 s | 13.41 s | 13.41 s | **13.41 s** |
| Concurrente (`gather`) | 0.93 s | 0.92 s | 0.93 s | **0.93 s** |

**Speedup: 13.41 / 0.93 = 14.4 veces.**

**Interpretación:** el secuencial tarda **la suma** (12.55 s, más ~40 ms de
cada pedido HTTP); el concurrente tarda **lo que la más lenta** (0.89 s, más
lo mismo). Con el `for`, cada `await` espera a que termine una descarga antes
de empezar la siguiente. Con `gather`, las 20 se lanzan juntas y, mientras
una espera la red, el loop avanza con las otras. Es un solo hilo: la
concurrencia sale de que el tiempo de cada descarga es casi todo espera, no
cálculo.

### 2. El event loop bloqueado

```bash
docker compose up -d
docker compose exec api python mediciones/medicion2_loop_bloqueado.py
USAR_EXECUTOR=0 docker compose up -d
docker compose exec api python mediciones/medicion2_loop_bloqueado.py
```

Un `hashear` de 10 millones de iteraciones y, mientras calcula, un
`GET /tareas` cada 100 ms.

| | El hash tardó | `GET /tareas` durante el hash | Peor | Mediana |
|---|---|---|---|---|
| **Con executor** | 3.46 s | 33 pedidos | **3.5 ms** | 1.9 ms |
| **Sin executor** | 3.47 s | 1 pedido | **3269 ms** | 3269 ms |

**Interpretación:** el hash tarda **lo mismo** en los dos casos: el executor
no lo acelera. La diferencia está en los demás:

- **Sin executor**, el único `GET` que se llegó a mandar esperó **3.3 s**, casi
  todo lo que duró el hash: el loop estaba calculando y no atendió a nadie.
  Ni siquiera se pudo mandar un segundo pedido.
- **Con executor**, el cálculo corre en otro proceso y el loop siguió
  respondiendo en milisegundos: 33 pedidos, el peor en 3.5 ms.

Esta es la diferencia entre "el trabajo tarda" y "el servidor está colgado":
un servidor asíncrono solo sirve si **nada** dentro del loop deja de ceder el
control.

### 3. Techo del pool

```bash
docker compose up -d
docker compose exec api python mediciones/medicion3_techo.py
WORKERS=16 docker compose up -d
docker compose exec api python mediciones/medicion3_techo.py
```

Tres experimentos, con 4 y con 16 workers.

**A. M tareas `esperar` de 1 s, todas a la vez (I/O):**

| Tareas | 4 workers | 16 workers |
|---|---|---|
| 1 | 1.03 s | 1.03 s |
| 2 | 1.02 s | 1.02 s |
| 4 | 1.02 s | 1.03 s |
| 8 | **2.02 s** | 1.04 s |
| 16 | **4.02 s** | 1.05 s |
| 32 | **8.04 s** | **2.04 s** |

**B. M tareas `hashear` de 2 millones de iteraciones, todas a la vez (CPU).**
Una sola tarda ~0.75 s.

| Tareas | 4 workers | 16 workers |
|---|---|---|
| 1 | 0.74 s | 0.75 s |
| 4 | 0.95 s (1.3×) | — |
| 12 | **2.91 s** (4.0×) | 1.38 s (1.8×) |
| 16 | — | **2.29 s** (3.0×) |
| 24 | **5.28 s** (7.2×) | **2.79 s** (3.7×) |

**C. 150 `POST` de golpe** (tareas `esperar` de 2 s, cola de 100 lugares):

| | Aceptadas (201) | Rechazadas (503) |
|---|---|---|
| 4 workers | 104 | 46 |
| 16 workers | 116 | 34 |

**Interpretación:** aparecen tres techos, en este orden:

1. **La cantidad de workers.** Es el primero que se toca, para los dos tipos
   de tarea. Cada tarea en ejecución ocupa a un worker, aunque solo esté
   esperando. Con 4 workers, las tareas `esperar` van de a 4: 8 tardan 2 s,
   16 tardan 4 s, 32 tardan 8 s (exactamente `M / 4` segundos). Con 16
   workers, recién se degrada con 32 tareas (2 s). Lo mismo pasa con
   `hashear`: con 4 workers, 12 hashes tardan 4 veces lo de uno, aunque haya
   12 procesos libres en el pool, porque solo 4 workers los están pidiendo.
   **El techo de las tareas I/O es solo este**, y subirlo es barato: un
   worker es una corrutina, no un thread.

2. **Los núcleos de la CPU** (solo para `hashear`). Con 16 workers el límite
   ya no son los workers sino el pool de 12 procesos: 16 hashes tardan 3
   veces lo de uno (12 en una tanda y 4 en otra). Incluso 12 a la vez tardan
   1.8 veces lo de uno y no 1 vez: esta CPU tiene 12 hilos pero solo 2
   núcleos rápidos con hyperthreading y 8 núcleos de eficiencia, así que 12
   cálculos simultáneos no corren todos a la velocidad de uno solo. Para lo
   CPU-bound no sirve agregar workers: el techo es el hardware.

3. **El tamaño de la cola.** Con 150 pedidos de golpe se aceptan exactamente
   `MAXSIZE_COLA + WORKERS` (100 + 4 = 104, y 100 + 16 = 116): los que ya
   tomó un worker y los que entran en la cola. El resto recibe 503 al
   instante. Es el límite que protege la memoria: sin `maxsize`, la cola
   crecería sin control.

No llegué a tocar otros límites posibles: el de 100 conexiones de `httpx`
(cada tarea `descargar` tiene su propio cliente, así que el límite es por
tarea) ni el de descriptores de archivo del sistema.

---

## Conceptos del curso aplicados

**Clase 1-2 — Docker.** Todo levanta con `docker compose up --build`. El
`CMD` en forma exec hace que uvicorn sea el PID 1 y reciba las señales. La
configuración entra por variables de entorno, y `estados/` es un volumen para
que el volcado sobreviva al contenedor.

**Clase 6 — Señales.** SIGTERM y SIGINT disparan el apagado ordenado. Hay que
terminar antes del SIGKILL que manda Docker a los 10 s, que no se puede
atrapar: por eso el límite de espera es de 5 s.

**Clase 9 — Multiprocessing.** `hashear` corre en un `ProcessPoolExecutor`.
Los procesos no comparten memoria: la función y sus argumentos viajan con
`pickle`, por eso `calcular_hash` es una función de módulo y no una `lambda`.

**Clase 10 — Threads y el GIL.** Por el GIL, el cálculo va a procesos y no a
threads: en un thread competiría con el event loop por el intérprete. En
cambio el volcado a disco, que es I/O, va con `asyncio.to_thread`. La regla:
CPU-bound → procesos, I/O bloqueante → threads.

**Clase 11 — Sincronización.** La cola con workers es el patrón
productor-consumidor de la clase 11, pero con corrutinas en vez de threads:
el productor es el `POST` y los consumidores son los workers. Acá no hace
falta lock porque el event loop no interrumpe entre `await`s.

**Clase 17 — I/O multiplexing.** El event loop de asyncio está construido
sobre `epoll`. Por eso un solo hilo puede tener abiertas las 20 conexiones de
una tarea `descargar` a la vez: el loop le pide al sistema operativo que le
avise cuál socket tiene datos.

**Clase 18 — De `yield` a asyncio.** Una corrutina solo cede el control en un
`await`. `await asyncio.sleep()` suspende la corrutina; `time.sleep()`
congelaría todo el hilo. Lo mismo vale para `queue.Queue.get()`, `requests`
o un cálculo largo dentro del loop: son todos el mismo bug.

**Clase 19 — HTTP y FastAPI.** Los códigos de estado (201, 204, 404, 409,
422, 503), la validación con Pydantic (un modelo por tipo de tarea con
`discriminator='tipo'`), el `lifespan` para crear y cerrar la cola, el pool y
los workers, y `app.state` como lugar del estado compartido. Quien tiene el
event loop es uvicorn, no FastAPI.

**Clase 20 — asyncio en red.** `httpx.AsyncClient` reutilizado,
`gather(..., return_exceptions=True)`, `asyncio.timeout`, y la cancelación:
`cancel()` le tira un `CancelledError` en el `await` donde está la tarea, y
el `CancelledError` se relanza si no es propio.

**Clase 21 — asyncio avanzado.** `asyncio.Queue` con `maxsize` como
backpressure, `task_done()` en `finally`, un centinela por worker para el
apagado ordenado, y `run_in_executor` para sacar el trabajo CPU-bound del
loop. La medición 2 es la misma que `executor.py`, pero sobre la API.

---

## Limitaciones conocidas

- **Un `hashear` cancelado sigue calculando.** El `cancel()` corta la espera
  del resultado, pero a un proceso del pool no se le puede tirar un
  `CancelledError`: calcula hasta terminar y ocupa su lugar en el pool. Lo
  medí con un pool de 1 proceso: después de cancelar un hash largo, un hash
  de 10 iteraciones tardó 2.32 s en vez de milisegundos. Lo mismo al apagar:
  fuera de Docker, un hash en curso queda como proceso huérfano hasta
  terminar. En Docker no pasa, porque al terminar el proceso principal se
  terminan todos los procesos del contenedor.
- **El historial de tareas crece sin límite.** `estado.tareas` nunca se vacía:
  la cola tiene techo, pero el dict acumula todas las tareas que pasaron por
  el servidor. Con suficiente tiempo de uso, la memoria crece.
- **El estado vive en memoria.** El volcado se escribe al apagar, pero no se
  recarga al arrancar (solo se avisa). Si el proceso muere sin apagado
  ordenado (por ejemplo, un SIGKILL), se pierde todo.
- **Un solo proceso de uvicorn.** Con `uvicorn --workers 2` habría dos
  procesos, cada uno con su propio dict, su propia cola y sus propios ids: un
  `GET` podría no encontrar una tarea creada por el otro proceso.
- **Al apagar se corta lo que dure más de 5 s.** Las tareas largas en
  ejecución terminan `cancelada`, y las pendientes no se ejecutan (quedan
  `cancelada` en el volcado).
- **Durante el apagado no hay 503:** uvicorn cierra el puerto antes de correr
  el apagado, así que un cliente recibe "conexión rechazada" en lugar de una
  respuesta HTTP.
- **El tope de 10 s por URL es fijo** (`TIMEOUT_URL` en `tareas.py`), no
  configurable por tarea.
- **Los JSON de `estados/` son del usuario root**, porque el contenedor corre
  como root. Para borrarlos desde el host hace falta `sudo`.

---

## Lo que aprendí

Lo que más me costó fue entender qué gana uno al sacar un cálculo del event loop. Al principio pensaba que el executor servía para que el hash terminara más rápido, y no: tarda lo mismo. Lo terminé de entender con mis propios números, cuando sin executor un `GET /tareas` tardó 3269 ms en responder y con executor 3.5 ms, con el hash tardando 3.5 s en los dos casos. Ahí me cayó la ficha de que el executor no ayuda al que calcula, ayuda a todos los demás. Algo parecido me pasó con `task_done()` en el `finally`: lo razonaba al revés, pensando que sin el `finally` una tarea fallida "pasaba como si estuviera bien". Cuando lo probé vi que era peor: la excepción se saltea las líneas de abajo, el contador de la cola nunca baja, y el programa se cuelga sin mostrar ningún error.

Me sorprendió lo engañosos que pueden ser algunos bugs. El `DELETE` respondía 204 y la tarea aparecía `cancelada`, pero el worker seguía durmiendo y al despertarse la marcaba `completada`, pisando la cancelación. Si no lo hubiera probado esperando hasta el final, no me habría dado cuenta. También me sorprendió la medición 3: tenía 12 procesos en el pool y pensaba que el límite iban a ser los núcleos, pero con 4 workers solo se usaban 4, porque cada tarea ocupa un worker mientras espera su resultado. Y que cancelar un `hashear` no frena el cálculo, porque a otro proceso no se le puede tirar un `CancelledError`.

Lo que más me sirvió fue predecir antes de correr cada prueba y medir en vez de suponer. Muchas de mis predicciones estaban mal (con 3 workers pensaba que 12 tareas iban a tardar lo mismo que en secuencial), y justamente esas fueron las que más me enseñaron. También aprendí que no todo error es del código: el primer `docker compose up` fallaba con un error de DNS, y el problema resultó ser que tenía dos Docker instalados y el de snap estaba bloqueado por AppArmor. Me llevo que asyncio no es magia: un solo hilo puede atender a muchos clientes a la vez, pero solo si ningún pedazo de código deja de ceder el control en un `await`.
