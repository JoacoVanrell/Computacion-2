# Clase 20 — Ejercicios resueltos

> Material de estudio armado con Claude. Necesitás `pip install httpx requests` (en un venv).

| Archivo | Ejercicio | Correr |
|---|---|---|
| `descargas_reales.py` | **Ej. 3 (obligatorio)**: partes B, C y D con `httpx` (secuencial / `gather` / semáforo / fallos) | `python3 descargas_reales.py` (o `--internet`) |
| `drain_y_lecturas.py` | Ej. 2: las 4 formas de leer + **para qué sirve `drain()`** (100 MB sin leer) | `python3 drain_y_lecturas.py` |
| `locks_y_cancelacion.py` | Ej. 4 y 5: cuándo hace falta `Lock`, timeouts, cancelación | `python3 locks_y_cancelacion.py` |
| `chat_async.py` | Adicionales: chat + comandos en asyncio, con **apagado ordenado de verdad** | `python3 chat_async.py --test` |

`descargas_reales.py` levanta su propio servidor HTTP local donde cada pedido tarda 0,3 s, así los números no dependen
de tu conexión y puede **contar cuántas conexiones TCP abrió** cada versión. Con `--internet` usa `https://example.com`.

## Ej. 3 — Parte A (`descargas.py` del profe, salida real)
```
12 descargas simuladas. Suma de demoras: 5.7s, la más lenta: 0.9s
  secuencial               5.71s
  gather (todas juntas)    0.85s
  con semáforo de 4        1.55s
  con timeout de 0.8s      0.80s  (1 canceladas por timeout)
```
1. **`gather` tarda lo que la más lenta** porque las 12 esperas **se solapan**: cada `await asyncio.sleep` cede el control,
   el loop arranca a la siguiente, y todas esperan **al mismo tiempo**. La secuencial espera una, después la otra → **la suma**.
2. **El semáforo da un tiempo intermedio:** solo 4 corren a la vez → son como "tandas" de 4. Ni la suma (1 a la vez) ni el máximo (todas a la vez).
3. Con timeout de 0,8 s se cortó **1** (la de 0,9 s). Esa tarea **no sigue corriendo de fondo**: el timeout la **cancela**
   (le inyecta `CancelledError` en su `await`), y `intentar()` atrapa el `TimeoutError` y devuelve `"TIMEOUT"`.

## Ej. 3 — Partes B, C y D (salida real de `descargas_reales.py`)
```
10 descargas de http://127.0.0.1:8765/demora/0.3
Parte B
  secuencial (un AsyncClient)                     3.46s   conexiones TCP: 1
  gather (un AsyncClient reutilizado)             0.33s   conexiones TCP: 10
  gather con un AsyncClient POR descarga          0.48s   conexiones TCP: 10
  gather con requests adentro de la corrutina     3.44s   conexiones TCP: 1
  gather con requests vía asyncio.to_thread       0.62s   conexiones TCP: 10
Parte C
  Semaphore(3)                                    1.35s   conexiones TCP: 3
  200 URLs, ulimit -n 64:
     ✗ ConnectError: All connection attempts failed
       causa real → OSError: [Errno 24] Too many open files
     con Semaphore(20)                            3.51s   conexiones TCP: 20
Parte D
  D.10) gather normal con una URL inválida:
     → gather lanzó ConnectError a los 0.00s; terminadas hasta ahí: 0 de 5 buenas — los resultados de las demás se PIERDEN
     → pero las otras NO se cancelaron: 1,2 s después ya terminaron 5 de 5
  D.11) gather(..., return_exceptions=True):
     ✓ 200  1256 bytes  …/demora/0.3      (× 4)
     ✗ ConnectError: All connection attempts failed
     ✓ 200  1256 bytes  …/demora/1.0
```

**B.4** Secuencial 3,46 s → concurrente 0,33 s: **~10× más rápido** (10 descargas que esperan, se solapan todas).

**B.5 ¿Por qué un solo `AsyncClient`?** Porque el cliente tiene un **pool de conexiones**: con keep-alive (clase 19) reutiliza
la conexión TCP en vez de pagar un handshake (y en HTTPS, también el handshake TLS) por pedido. Se ve en los números:
la **secuencial hizo 10 pedidos con 1 sola conexión**, y el `Semaphore(3)` hizo 10 pedidos con **3 conexiones**. Con un cliente
por descarga son siempre 10 conexiones nuevas (y acá, aun en localhost, tardó más: 0,48 s vs 0,33 s).
(Con `gather` sin límite son 10 conexiones igual porque HTTP/1.1 no multiplexa: 10 pedidos **simultáneos** = 10 conexiones.)

**B.6 Con `requests`:** **3,44 s = lo mismo que secuencial.** `requests.get()` es **bloqueante**: no tiene `await`, no cede;
congela el event loop hasta que vuelve → las corrutinas corren una después de la otra (es el `async def` + `time.sleep`
de la clase 19). Si no hay versión async de una biblioteca, `asyncio.to_thread(requests.get, url)` lo saca del loop (0,62 s).

**C.7** Con `Semaphore(3)`: **1,35 s** ≈ 4 tandas (3+3+3+1) × 0,3 s.

**C.8 Qué evita acotar la concurrencia:**
1. **Agotar los descriptores de archivo** del proceso (cada conexión es un fd → `Too many open files`).
2. **Saturar al servidor de destino** (o que te bloquee / te devuelva 429 por parecer un ataque) y saturar tu propia red.
3. (también) usar memoria de más y, en el TP2, que una ráfaga de tareas deje sin recursos al resto del sistema.

**C.9 200 URLs sin semáforo:** `OSError: [Errno 24] Too many open files` (httpx lo envuelve en `ConnectError`). Se relaciona
con `ulimit -n`: el límite de fds por proceso (en esta máquina era 20000, por eso lo bajé a 64 para que se vea; en Ubuntu suele ser **1024**).
Ojo: **httpx por defecto ya acota a 100 conexiones** (`httpx.Limits(max_connections=100)`): para ver el error hubo que sacarle el tope.

**D.10 `gather` normal + una URL inválida:** la **primera excepción sube** al que hizo `await gather(...)` y se **pierden los
resultados** de las demás. Detalle que casi nadie sabe: **las otras tareas NO se cancelan**, siguen corriendo de fondo
(1,2 s después habían terminado las 5) — nadie mira sus resultados.

**D.11 `return_exceptions=True`:** `gather` **no lanza**: devuelve una lista con un resultado **o el objeto excepción** en
cada posición (en el orden de los argumentos). Después revisás con `isinstance(r, Exception)`.

**D.12 Para el TP2: `return_exceptions=True`.** Cada tarea del TP2 es independiente: que una URL falle no puede tirar
abajo ni ocultar el resultado de las otras. Cada una debe terminar en su estado (`completada` / `fallida` con el error).
(La clase 21 muestra `TaskGroup`, que hace lo contrario: si una falla, **cancela** a las demás — sirve cuando las tareas
son partes de un mismo trabajo, no para tareas independientes.)

## Ej. 1 — el servidor eco (probado)
- **1–3.** Con 3 clientes conectados reporta **`threads: 1`** (y `/proc/<pid>/task` tiene 1 entrada). En `server_threads.py`
  serían **1 + 3**. En asyncio una conexión es **un objeto** (una `Task` + sus streams: cientos de bytes); con threads, **un hilo del SO** (~MB de stack).
- **4–5.** Con `--lento 1`, dos clientes que escriben a la vez reciben la respuesta los dos a **1,00 s**: el
  `await asyncio.sleep` **cede** el control y el loop atiende al otro mientras tanto.
- **6.** Cambiándolo por `time.sleep`: **1,00 s y 2,00 s**. `time.sleep` **bloquea el hilo** = bloquea el loop = **todo el servidor**.
- **7.** `kill -TERM` imprime `Cerrando: no se aceptan conexiones nuevas` y después un `- (dirección)` por cliente…
  ⚠️ **pero solo cuando los clientes cierran.** Lo probé: con 3 clientes conectados **el proceso no terminó** hasta que cerré
  los sockets. Desde **Python 3.12**, salir del `async with servidor:` (→ `wait_closed()`) **espera a que terminen todas las
  conexiones**. Para el TP2 hay que cortarlas: `chat_async.py` lo hace (aviso, 2 s de gracia, `cancel()` a las que quedan);
  en 3.13 también existe `servidor.close_clients()`.
- **8–9.** `signal.signal()` (clase 6) ejecuta el handler **en cualquier momento**, interrumpiendo el código por la mitad →
  solo se pueden hacer cosas *async-signal-safe* (por eso el patrón de la bandera). `loop.add_signal_handler()` hace que el
  **loop** reciba la señal (por debajo con `signal.set_wakeup_fd` = el **self-pipe** de la clase 6) y ejecute el callback
  **entre tareas**, como un evento más: ahí podés hacer cualquier cosa (`cerrar.set()`, loguear…) sin riesgo.

## Ej. 2 — write, drain y framing (salida real)
```
  read(100)                        → b'hola\nmundo\n'
  readline()                       → b'hola\n'
  readexactly(4)                   → b'hola'
  readuntil(b'\n')                 → b'hola\n'
  readexactly(100)                 → IncompleteReadError: 11 bytes read on a total of 100 expected bytes  (partial=b'hola\nmundo\n')
  read() en bucle hasta el final   → [b'hola\nmundo\n', b'']
  readline() × 3                   → [b'hola\n', b'mundo\n', b'']

=== 2.1 Cliente que manda 100 MB y nunca lee ===
  SIN drain(): el cliente mandó 100 MB en  0.3s · buffer de escritura máx. del servidor:   91.8 MB · memoria del servidor: +  92 MB
  CON drain(): el cliente mandó   8 MB en  2.1s · buffer de escritura máx. del servidor:    0.1 MB · memoria del servidor: +   1 MB
```
1. `write()` **no espera nunca**: copia al buffer del transporte y vuelve. `drain()` **puede tener que esperar** (si el buffer
   pasó el umbral, se suspende hasta que baje) → por eso es corrutina.
2. Sin `drain()`, **con `nc` anda igual** (el cliente lee, el buffer se vacía solo).
3. **Para qué sirve:** con un cliente que no lee, sin `drain()` el servidor siguió leyendo y **acumuló 92 MB en memoria**
   (con 10 clientes así, 1 GB…). Con `drain()` el buffer nunca pasó de **0,1 MB**: el handler se suspendió → dejó de leer →
   se llenaron los buffers del kernel → **TCP frenó al cliente** (mandó 8 MB y quedó bloqueado). Es **backpressure**: control de
   flujo de punta a punta, igual que la ventana de TCP (clase 12) pero en la aplicación.
4. Ver salida arriba. **5.** `readline()`/`readuntil()` = framing por **delimitador**; `readexactly(n)` = framing por **longitud**
   (leés el prefijo con `readexactly(4)` y después `readexactly(largo)`). Los dos de la clase 13, con el buffer ya hecho.
6. `readexactly(100)` con menos datos y cierre → **`asyncio.IncompleteReadError`**, con lo que sí llegó en `.partial`.
7. `read()` con el otro lado cerrado devuelve **`b''`** — igual que `recv()` en la clase 13. (`readline()` también: `b''`, no excepción.)

## Ej. 4 — locks (salida real)
```
  1000 corrutinas (+1 cada una):           contador = 1000
  10 threads × 10 000 (+1 cada vez):       contador = 56280  ← esperado 100000: race condition
  10 corrutinas × 10 000 (cediendo afuera): contador = 100000
  sin Lock:  A =  999  B = 100  total = 1099   ← esperado A = 900: ¡se crearon 99 pesos de la nada!
  con Lock:  A =  900  B = 100  total = 1000
```
1–3. Con corrutinas da **siempre** bien: el cambio de tarea **solo ocurre en un `await`**, y `contador += 1` no tiene ninguno →
   es atómico "por construcción". Con threads el intérprete/SO puede cambiar de hilo **entre** leer y guardar → se pierden sumas.
   (En los threads del ejemplo puse una llamada a función entre leer y guardar: es donde CPython suele cambiar de thread.)
4–5. Con un `await asyncio.sleep(0)` **entre leer y escribir**, las 100 transferencias leen todas `1000` antes de que
   ninguna escriba → A queda en 999. Es **un solo hilo**, pero hay **intercalado**: el `await` es un punto donde corre otra tarea.
6. `async with lock`: **tomar** el lock puede tener que **esperar** a que otra tarea lo suelte, y esperar en asyncio = ceder al loop
   (`await lock.acquire()`). Un `with` común no puede hacer `await`. (Y un `threading.Lock` acá **bloquearía el loop entero** → deadlock.)
7. **Regla: en asyncio hace falta un lock solo si la sección crítica tiene un `await` adentro.** Y lo ves leyendo el código.

## Ej. 5 — timeouts y cancelación (salida real)
```
    [timeout()] me llegó CancelledError → el timeout me CANCELÓ (no sigo corriendo de fondo)
  asyncio.timeout(0.5) → TimeoutError a los 0.50s
    [wait_for()] me llegó CancelledError → …
  asyncio.wait_for(…, 0.5) → TimeoutError a los 0.50s (¿asyncio.TimeoutError is TimeoutError? True)
    [timer] cancel() pedido a los 0.20s
    [calcular] terminé de calcular a los 2.00s; ahora hago un await…
  6) se canceló recién a los 2.00s (en su primer await), no a los 0,2 s
    [mentirosa] me cancelaron… y sigo como si nada
  7) 0,5 s después del cancel(): done()=False, cancelled()=False → sigue viva
     timeout(0.3) alrededor de la mentirosa: devolvió 'terminé igual' a los 1.00s — el timeout NO cortó
  8) `except Exception:` NO atrapó la cancelación (CancelledError hereda de BaseException)
```
1. Lanza **`TimeoutError`** (el builtin; desde 3.11 `asyncio.TimeoutError` es el mismo).
2. La operación **se cancela** (recibe `CancelledError`): no queda corriendo de fondo.
3. `wait_for(coro, timeout)` hace **lo mismo** (desde 3.12 está implementado con `timeout()`); `asyncio.timeout()` es un
   *context manager* que puede envolver **varios** `await` juntos, y se puede reprogramar (`cm.reschedule()`).
4. Orden en `descargas.py`: `la tarea recibió CancelledError en su await` → `finally: limpieza hecha` → `quien la canceló también la ve`.
5. **En el próximo punto de suspensión**: la tarea estaba parada en `await asyncio.sleep(10)`; el `CancelledError` aparece
   **ahí**, como si esa línea lo hubiera lanzado.
6. **No funciona** a tiempo: una tarea que calcula sin `await` **no cede**, y la cancelación solo se entrega en un `await`.
   (Ni siquiera se puede llamar a `cancel()` desde otra corrutina: el loop está tomado. Lo hice desde un thread con
   `call_soon_threadsafe`, y la cancelación llegó recién a los 2 s.) Mismo problema de la clase 18 → el CPU va a procesos.
7. Si la capturás y no la relanzás, **la tarea sigue viva** (`done()=False`): quien pidió la cancelación cree que terminó y un
   `await tarea` cuelga. **Y rompe los timeouts**, que funcionan cancelando: `timeout(0.3)` dejó correr 1 s entero.
8. Hereda de **`BaseException`** (desde 3.8) para que un `except Exception:` puesto para "atrapar errores" **no se la coma
   sin querer**: cancelar no es un error, es una orden. (Mismo motivo que `KeyboardInterrupt` y `SystemExit`.)

## Ej. 6 — la escala (`escala.py` del profe, salida real en una máquina de 2 núcleos)
```
  clientes       ok    tiempo   threads
       100      100     0.02s         1
       500      500     0.08s         1
      1000     1000     0.17s         1
      2000     2000     0.38s         1
      5000     5000     2.19s         1
     10000    10000     2.63s         1
```
1. **1 thread** siempre. 2–3. Acá aguantó **10 000** sin fallar porque `ulimit -n` era 20000 (cada cliente usa **2 fds** en
   esta prueba: el del cliente y el del servidor, porque los dos están en el mismo proceso). En una Ubuntu típica
   (`ulimit -n` = **1024**) lo **primero que falla** es eso: `OSError: Too many open files` alrededor de ~500 clientes. Se sube con `ulimit -n 65535`.
   El salto de 2000 → 5000 (0,38 s → 2,19 s) es probablemente el **backlog** (2048) llenándose: el kernel descarta SYNs y el cliente reintenta.
4. **Como threads:** 10 000 × 4 MB = **~40 GB** de stack reservado (se reserva virtual, pero igual: miles de threads + el
   scheduler del kernel repartiendo tiempo entre todos). Con asyncio, cada cliente es una `Task` de unos cientos de bytes.
5. **Párrafo (C10K):** con threads, cada conexión es un hilo del sistema operativo: 4 MB de stack, una entrada en el scheduler
   del kernel y cambios de contexto caros; con 10 000 clientes eso son ~40 GB de stack y un kernel que pasa más tiempo
   repartiendo CPU que trabajando. Asyncio cambia **qué es una conexión**: un objeto `Task` de unos cientos de bytes dentro de un
   único hilo, que solo se despierta cuando `epoll` avisa que su socket tiene datos. En mi máquina, **10 000 clientes en 2,6 s con
   un solo thread**: el techo deja de ser la memoria o el scheduler y pasa a ser la cantidad de descriptores (`ulimit -n`).

## Adicional — `chat_async.py --test` (salida real)
```
--- lo que vio beto ---
* anon41836 entró
* anon41836 ahora es caro
[ana] hola a todos
--- lo que vio ana ---
* conectados: ana, beto, caro
--- beto, después de que caro cerró ---
* caro salió
--- SIGTERM con 2 clientes conectados ---
ana recibe:
* el servidor se cierra en 2 s
servidor: cerrando: no acepto más conexiones; 2 clientes tienen 2.0s
servidor: listo: 2 clientes cortados después de la gracia
el proceso terminó solo en 2.0s (rc=0) aunque ana y beto nunca cerraron
```
- **¿Más legible que el chat de la 17?** Sí: cada cliente es **una función lineal** (`leer → interpretar → responder`) con su
  estado en variables locales (`nick`), en vez de callbacks y un diccionario de buffers por socket.
- **¿Hace falta el `Lock` del servidor de comandos de la 16?** No para modificar `clientes` (no hay `await` en el medio).
  Lo que sí cuidé: `difundir()` recorre una **copia** del diccionario, porque mientras espera el `drain()` de un cliente
  otro puede entrar o salir — es exactamente la regla del "await en el medio".
- Para el TP2 queda el patrón de apagado: **dejar de aceptar → avisar → gracia → cancelar las que quedan → esperar**.
