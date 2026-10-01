# Clase 13 — Sockets TCP · Resumen

**Socket** = un **descriptor de archivo** para la red (idea de Berkeley, 1983): se lee y escribe como un archivo.
```python
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # IPv4 + TCP
```
| Familia | | Tipo | |
|---|---|---|---|
| `AF_INET` / `AF_INET6` | IPv4 / IPv6 | `SOCK_STREAM` | TCP (flujo) |
| `AF_UNIX` | local, por ruta | `SOCK_DGRAM` | UDP (datagramas) |
Siempre con `with` (libera el fd aunque haya excepción).

---

## Cliente: 3 pasos
```python
with socket.create_connection(("localhost", 8080), timeout=5) as s:   # resuelve nombre, prueba IPv4/IPv6, handshake
    s.sendall(b"hola\n")
    datos = s.recv(4096)
```

## Servidor: 5 pasos
```python
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # 1) ANTES del bind
    srv.bind(("0.0.0.0", 8080))                                 # 2) reclamar dirección:puerto
    srv.listen(128)                                             # 3) socket PASIVO + cola de pendientes
    while True:
        conn, addr = srv.accept()                               # 4) devuelve un socket NUEVO por cliente
        with conn:                                              # 5) hablar con ESE socket
            ...
```
- **`SO_REUSEADDR`:** evita `Address already in use` por conexiones en **TIME_WAIT** al reiniciar el server.
- **`listen(n)`:** tamaño de la cola de conexiones esperando `accept()`.
- **`accept()`** ⭐: el socket que escucha **nunca** manda datos; cada `conn` tiene la cuádrupla completa.

```
 srv (escucha :8080)
   ├─ accept() → conn A
   └─ accept() → conn B
```

---

## `recv` y `send`: las reglas que rompen intuiciones
1. `recv(n)` devuelve **hasta** n bytes — menos es normal.
2. Bloquea si no hay nada; vuelve **apenas** hay algo.
3. **`b''` = el otro cerró** → chequealo SIEMPRE (si no, `while True` gira infinito).
- `send()` puede mandar **menos** de lo pedido → usá **`sendall()`**.

---

## Framing (el tema central) ⭐
TCP es un **flujo**: 3 `sendall` pueden llegar en 1 `recv`, o en 5. Los mensajes los armás vos.

### 1) Delimitador (`\n`)
```python
buffer = b""
while (pedazo := sock.recv(4096)):
    buffer += pedazo
    while b"\n" in buffer:                  # WHILE: puede haber varias líneas
        linea, buffer = buffer.split(b"\n", 1)
        yield linea
```
Atajo: `conn.makefile("rwb")` → `for linea in f:` (¡y `f.flush()` después de escribir!).

### 2) Prefijo de longitud
```python
sock.sendall(struct.pack("!I", len(p)) + p)          # 4 bytes, big-endian ("!") + contenido
largo, = struct.unpack("!I", recibir_exacto(sock, 4))
cuerpo = recibir_exacto(sock, largo)                  # recibir_exacto = bucle hasta tener N bytes
```

| | Delimitador | Longitud |
|---|---|---|
| Binario | ❌ (escapar) | ✅ |
| Depurable con `nc` | ✅ | ❌ |
| Saber el tamaño antes | no | sí |
| Ejemplos | HTTP headers, SMTP, Redis | gRPC, WebSocket, binarios |

---

## Bytes, no strings
- `sendall('hola')` → `TypeError`. Usá `'hola'.encode()` o `b'hola'`.
- Un carácter UTF-8 puede ocupar varios bytes (`'ñ'` = 2) y un `recv` lo puede **partir** → **decodificá el mensaje completo**.
- **Orden de bytes de red = big-endian** → siempre `!` en `struct` (`'!I'`, `'!H'`, `'!Q'`).

## Cerrar una sola dirección
`s.shutdown(socket.SHUT_WR)` = "no mando más" (FIN) pero sigo leyendo → el otro ve `b''` y responde.
Sin eso, si el server lee "hasta que cierres" y vos esperás su respuesta: **deadlock distribuido**.

## Errores típicos
| Excepción | Cuándo | Qué hacer |
|---|---|---|
| `ConnectionRefusedError` | no hay nadie escuchando | reintentar con **backoff** |
| `ConnectionResetError` | el otro cortó de golpe | cerrar y seguir |
| `BrokenPipeError` | escribir en conexión cerrada | cerrar y seguir |
| `TimeoutError` | venció `settimeout()` | reintentar o abandonar |
| `OSError` Errno 98 | puerto ocupado | `SO_REUSEADDR` / otro puerto |
**Poné timeouts siempre** (un `recv` sin timeout puede colgarse para siempre).

## El límite: servidor secuencial
Mientras atiende a uno, no vuelve a `accept()`. El 2do cliente **conecta** (el **kernel** completa el handshake y lo deja
en la cola) pero **nadie lo atiende**. Solución → clase 14 (threads, fork, pool) y 17-20 (select, asyncio).

## ❓ Autoevaluación
1. ¿Qué devuelve `accept()` y por qué no se usa el socket que escucha para hablar?
2. Las 3 reglas de `recv`. ¿Qué significa `b''`?
3. ¿Por qué `sendall` y no `send`?
4. ¿Para qué `SO_REUSEADDR` y por qué antes del `bind`?
5. Implementá de memoria `recibir_exacto` y el generador de líneas.
6. ¿Por qué `'!I'` y no `'I'`?
7. ¿Para qué sirve `shutdown(SHUT_WR)`?
8. ¿Por qué un cliente "conectado" puede no estar siendo atendido?
