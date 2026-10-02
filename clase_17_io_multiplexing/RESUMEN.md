# Clase 17 — I/O multiplexing · Resumen

Threads/procesos = **un recurso por conexión** → no escala a miles (C10K).
Idea nueva: **un solo hilo** le pregunta al kernel **"¿cuáles de estas mil conexiones están listas?"** y duerme hasta que alguna lo esté.
Base de nginx, Redis, Node.js y **asyncio**.

## El problema
- `conn_a.recv()` bloquea → `conn_b` queda ignorada aunque tenga datos.
- `setblocking(False)` + preguntar en bucle = **busy-waiting**: un núcleo al 100 % sin hacer nada.
- Hace falta: **"dormime hasta que alguno tenga algo"**.

## select() (1983)
```python
listos_r, listos_w, excep = select.select(rlist, wlist, [], timeout)   # timeout en SEGUNDOS
```
- Devuelve **los mismos objetos** que pasaste (comparás con `is`).
- **El socket que escucha también se vigila**: "listo para leer" = hay una conexión para `accept()`.
- Al cerrar un cliente: **sacarlo de la lista** (si no, aparece "listo" para siempre).
- **"Listo" = no va a bloquear**, NO "llegó un mensaje completo" → el framing de la clase 13 sigue haciendo falta.
- Límites: **FD_SETSIZE = 1024** → falla si **algún fd tiene número ≥ 1024** (aunque vigiles uno solo) · **O(n)** por llamada.

## poll()
```python
p = select.poll();  p.register(sock, select.POLLIN)
for fd, mascara in p.poll(timeout_ms):           # ⚠️ MILISEGUNDOS
    sock = por_fd[fd]                              # devuelve el NÚMERO → diccionario fd → socket
    if mascara & select.POLLIN: ...                # máscara de bits: POLLIN|POLLHUP = "hay datos Y cerró"
```
Sin límite de 1024, pero **sigue O(n)** (le pasa todo al kernel en cada llamada).

## epoll() (Linux, 2002) ⭐
```python
ep = select.epoll();  ep.register(sock.fileno(), select.EPOLLIN)
for fd, mascara in ep.poll(timeout_s): ...        # SEGUNDOS (acepta decimales)
ep.close()                                          # es un fd: cerrarlo
```
**El kernel mantiene el conjunto**; registrás una vez y `poll()` devuelve **solo los listos** → **O(listos)**.
Equivalentes: **kqueue** (BSD/macOS), **IOCP** (Windows).

| | Pasar la lista | Costo | Límite |
|---|---|---|---|
| `select` | cada llamada | O(n) | fd < 1024 |
| `poll` | cada llamada | O(n) | — |
| `epoll` | una vez | **O(listos)** | — |
Medido: 5000 conexiones, 3 activas → poll ~280 µs, epoll ~0,6 µs. Si la **mitad** está activa, la ventaja se achica.

## selectors: lo que se usa en Python (portable)
```python
sel = selectors.DefaultSelector()                  # elige epoll / kqueue / select según el SO
sel.register(srv, selectors.EVENT_READ, aceptar)   # data = lo que quieras (ej. el callback)
while True:
    for clave, mascara in sel.select():
        clave.data(clave.fileobj)                  # despachar al handler → ¡esto es un EVENT LOOP!
```
- `sel.unregister(conn)` **antes** de `conn.close()`.
- `sel.modify(conn, EVENT_READ | EVENT_WRITE, data)` para cambiar el interés.

## Escribir sin bloquear
Un `sendall()` a un cliente lento **congela a todos**. Solución:
- **buffer de salida** por conexión + `send()` (lo que entre) + registrar **`EVENT_WRITE` solo cuando hay pendiente**.
- `EVENT_WRITE` permanente = el socket siempre está listo para escribir → bucle al 100 % de CPU.
- Poner un **tope** al buffer (si el cliente nunca lee, la memoria crece sin límite).

## El costo: todo tiene que ser rápido ⚠️
Un solo hilo → cualquier cosa lenta (cálculo, BD, `open()` en red, **DNS**) **frena a todos**.
**Regla de oro del event loop:** lo pesado va a un **pool** (threads o procesos) y el resultado vuelve al loop
(un socketpair registrado lo despierta). En asyncio: `run_in_executor`.
Bonus: sin threads → **sin locks** ni race conditions entre handlers.

## ¿Qué uso?
| Situación | |
|---|---|
| pocas conexiones, lógica compleja | threads |
| CPU-bound por conexión | procesos / pool |
| miles de conexiones, trabajo liviano | multiplexing |
| miles de conexiones, código legible | **asyncio** (clases 18–20) |
| portable | `selectors`, nunca epoll directo |

## Extra de la clase: direcciones en el código
`ipaddress.ip_network('192.168.1.0/24')` (no parsees strings) · IPv6: `::1`, `::`, tupla de 4 elementos
(`info[0], info[1]`), `getaddrinfo()`/`create_connection()` para no elegir familia a mano, dual-stack con `IPV6_V6ONLY` explícito.

## ❓ Autoevaluación
1. ¿Por qué busy-waiting es malo y qué hace distinto `select()`?
2. ¿Qué significa que un socket esté "listo"? ¿Garantiza un mensaje completo?
3. ¿Por qué `select()` falla con un solo socket? ¿Qué es FD_SETSIZE?
4. ¿Por qué poll es O(n) y epoll O(listos)?
5. ¿Qué devuelve `poll()` y por qué hace falta un diccionario?
6. ¿Por qué `send()` y no `sendall()` en un event loop? ¿Por qué no dejar `EVENT_WRITE` siempre?
7. ¿Cuál es la regla de oro del event loop y cómo se respeta con un cálculo pesado?
