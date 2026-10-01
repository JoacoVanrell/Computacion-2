# Clase 16 — Ejercicios resueltos

> Material de estudio armado con Claude.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `mixins.py` | **Ej. 2 (obligatorio)**: partes A, B, C y D medidas automáticamente | `python3 mixins.py` |
| `chat_comandos.py` | Ej. 4: servidor con `NICK`, `BROADCAST`, `WHO`, timeout de inactividad | `python3 chat_comandos.py` + varios `nc localhost 8080` |

## Salida real del obligatorio

```
Parte A  ThreadingMixIn: ['process_request_thread', 'process_request', 'server_close']
         ForkingMixIn:   ['collect_children', 'handle_timeout', 'service_actions', 'process_request', 'server_close']
         Código propio de ThreadingTCPServer:  class ThreadingTCPServer(ThreadingMixIn, TCPServer): pass

Parte B  Bien  MRO [Bien, ThreadingMixIn, TCPServer, BaseServer] → process_request de ThreadingMixIn
         Mal   MRO [Mal, TCPServer, BaseServer, ThreadingMixIn]  → process_request de BaseServer
         Bien  3 clientes que tardan 1 s: 1.00s
         Mal   3 clientes que tardan 1 s: 3.50s        ← sin ningún error

Parte C  ForkingTCPServer + int          → ['visita 1', 'visita 1', 'visita 1']
         ForkingTCPServer + Value('i')   → ['visita 1', 'visita 2', 'visita 3']

Parte D  daemon_threads=False → Ctrl+C con un cliente conectado: SIGUE VIVO esperando
         daemon_threads=True  → termina en el acto
```

## Respuestas (checklist)

1–2. **Qué método produce la concurrencia:** `process_request()`. En `BaseServer` atiende al cliente **en el mismo hilo**
(`finish_request` + `shutdown_request`) y recién después vuelve al loop. El mixin lo reemplaza por "creá un thread
(o hacé fork) que lo atienda y **volvé enseguida**".

3. **Dónde cosecha `ForkingMixIn`:** en `collect_children()`, que se llama desde `service_actions()` — **en cada vuelta**
del loop de `serve_forever()` (cada ~0,5 s) —, desde `handle_timeout()` y al cerrar. Si hay `max_children` (40) vivos,
espera bloqueando. Además el padre hace `close_request()` (cierra su copia del socket del cliente). Por eso no hay
zombies ni fds filtrados: los tres descuidos de la clase 14 ya están resueltos.

4. **Código propio de `ThreadingTCPServer`:** ninguno. `class ThreadingTCPServer(ThreadingMixIn, TCPServer): pass`.

5–8. **El orden:** el MRO se busca de izquierda a derecha. En `Mal`, `BaseServer` aparece **antes** que el mixin → gana el
`process_request` secuencial. **No da error**: anda, pero de a uno (3,5 s en vez de 1 s). Es peligroso porque pasa las
pruebas y se nota recién con carga. **Mixins siempre a la izquierda.**

9–12. **Forking y memoria:** el contador da siempre 1 porque cada hijo tiene una **copia** de la memoria del padre
(fork, clase 4): incrementa su copia y muere. No se arregla con un Lock: es **aislamiento**, no sincronización.
Se arregla con **`multiprocessing.Value`** creado en el **`__init__` del servidor** (antes de cualquier fork, así todos los
hijos heredan el **mismo** bloque compartido). Creado en el handler sería uno nuevo por cliente. Y el `+=` va con `get_lock()`.

13–14. **daemon_threads:** sin él, `server_close()` hace `join()` de los threads de clientes → un cliente conectado sin
hablar frena el apagado. Con `daemon_threads = True` se cortan al salir.

## Ejercicio 4 — decisiones
- **NICK** vive en el **handler** (uno por conexión, muere con ella). La **lista de conectados** vive en el **servidor**
  (uno solo, compartido por todos los threads) → **Lock**.
- **BROADCAST:** se copia la lista **dentro** del lock y se escribe **fuera** (si un cliente lento bloquea el `sendall`, no
  frena a todos). Si un cliente se desconecta mientras le escribimos → `OSError` → se lo saca de la lista.
- Cada cliente tiene su propio lock de **escritura**: dos threads (dos broadcasts) podrían escribirle a la vez y mezclar líneas.
- **Timeout:** el atributo `timeout` de `StreamRequestHandler` → `TimeoutError` en `rfile` → aviso y desconexión.
- **¿Con `ForkingTCPServer` andaría el BROADCAST?** **No**: cada cliente está en otro proceso; la lista de sockets
  de un hijo no tiene los sockets de los otros hijos. Haría falta IPC (o un proceso central).
- (Ojo al probar: `makefile()` también mantiene abierto el fd. Para que el servidor vea el cierre hay que cerrar el
  socket **y** el archivo.)

## Respuestas cortas de los ejercicios 1 y 3
- `self.request` en TCP es el **socket de la conexión**; en UDP es la **tupla `(datos, socket)`** → hay que `sendto(…, self.client_address)`.
- `id(self)` cambia en cada conexión: **un handler nuevo por conexión** (por eso un contador en el handler siempre da 1).
- `handle()` corre **una vez por conexión**, no por mensaje.
- El "Address already in use" solo aparece si **hubo una conexión** (hace falta `TIME_WAIT`).
- No mezclar `rfile` con `self.request.recv()`: `rfile` tiene **su propio buffer** y se lleva del socket más de lo que pediste.
- `finish()` corre **aunque `handle()` falle** (antes de `handle_error()`); sin `super().setup()` no existen `rfile`/`wfile`.
- `ThreadingUDPServer` existe y tiene sentido si el handler tarda: sin threads, un datagrama lento frena a los demás.
- Que 200 conexiones sin lock "no pierdan cuentas" no prueba nada: la ventana de la race es chica, pero existe.
