# Clase 13 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu eco cliente/servidor está en `../mi_trabajo/`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `framing.py` | **Ej. 3 (obligatorio)**: framing por `\n` y por longitud + todas las pruebas de la consigna | `python3 framing.py test` |
| `servidor_comandos.py` | Adicional: servidor de comandos `TIME` / `ECHO` / `QUIT` | `python3 servidor_comandos.py` + `nc localhost 8080` |
| `transferir_archivo.py` | Adicional: transferencia de archivos con longitud + md5 | `python3 transferir_archivo.py demo` |

## Salida real del obligatorio

```
DELIMITADOR \n
  ✓ 3 mensajes en 1 sendall: [b'UNO', b'DOS', b'TRES']
  ✓ byte por byte: [b'HOLA']
  ✓ mensaje con \n adentro (se PARTE en 2): [b'LÍNEA', b'CON ENTER']   ← el problema del delimitador
PREFIJO DE LONGITUD
  ✓ 3 mensajes en 1 sendall
  ✓ byte por byte (¡también la cabecera llega de a 1 byte!)
  ✓ mensaje con \n adentro (llega ENTERO)
  ✓ mensaje de 0 bytes: b''
  ✓ cabecera de 4 GB → el servidor corta la conexión
TODO OK ✓
```
Transferencia: **120 MB en 0.24 s** por loopback, md5 coincide.

## Respuestas

1–2. **Parte A:** el servidor hace **un** `recv()` con `b'HOLACOMOESTAS'`. No viola nada: TCP promete bytes en orden, no límites.
6. **¿Por qué `recibir_exacto` no puede ser `return sock.recv(n)`?** Porque `recv(n)` devuelve **hasta** n bytes. Si la
   cabecera llega en dos partes y leíste 2 de 4 bytes, interpretás mal el largo y el protocolo queda **desincronizado para siempre**.
7. **`\n` en el medio:** con longitud llega entero; con delimitador se corta en dos mensajes.
8. **0 bytes:** es un mensaje válido (vacío); hay que no confundirlo con "cerró" (por eso devuelvo `b""` y no `None`).
   **5 GB:** con `!I` (4 bytes) el máximo es 4 GB; y un servidor ingenuo intentaría **reservar** esa memoria. Por eso
   hay un **máximo** (`MAX_MENSAJE`) y si se supera se corta la conexión. Para archivos grandes: leer y escribir de a bloques.
9. Tabla:

| | Delimitador | Longitud |
|---|---|---|
| Contenido binario arbitrario | ❌ necesita escape | ✅ directo |
| Depurable con `nc` | ✅ | ❌ (bytes binarios) |
| Hay que saber el tamaño antes | ❌ no | ✅ sí |

10. **HTTP:** los headers son **texto corto** → delimitador (`\r\n`, y una línea vacía para terminar), cómodo y legible.
    El cuerpo puede ser **binario y grande** (una imagen) → `Content-Length`, así no hay que buscar un delimitador
    adentro de datos binarios y se sabe exactamente cuánto leer.

### Ejercicio 4 (encoding)
- `s.sendall('hola')` → `TypeError`: los sockets mandan **bytes**, hay que `.encode()`.
- `len('año') = 3` caracteres pero `len('año'.encode()) = 4` bytes: la `ñ` ocupa 2 en UTF-8.
- `datos[:2].decode()` → `UnicodeDecodeError`: cortaste la `ñ` por la mitad. Se evita **decodificando el mensaje completo**
  (después del framing). `errors='replace'` solo para logs/debug.

### Ejercicio 5–6
- Sin servidor → `ConnectionRefusedError`. Reintentos con espera creciente (*backoff*).
- `recv()` sin timeout contra alguien que no responde → **se cuelga para siempre**. Con `settimeout(3)` → `TimeoutError`.
- El 2do cliente de un servidor secuencial aparece `ESTAB` en `ss`: **el handshake lo completa el kernel**, no tu programa;
  la conexión espera en la **cola de `listen()`** (la columna `Recv-Q` de la línea LISTEN = cuántas esperan `accept()`).
  "Conectó" ≠ "lo están atendiendo". Soluciones: thread por cliente, fork por cliente, pool, `select`, asyncio.
