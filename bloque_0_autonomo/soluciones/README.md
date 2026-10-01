# Bloque 0 — Ejercicios resueltos

> Material de estudio armado con Claude. Los obligatorios de argparse (mini-grep),
> filesystem (inspector) y python avanzado (timer, retry) ya los tenías hechos en
> `../mi_trabajo/`, así que acá van los otros que más se toman o que preparan clases futuras.

| Archivo | Ejercicio | Cómo correrlo |
|---|---|---|
| `dual_stack_servidor.py` | IPv6 · Ej. 3 (obligatorio): servidor dual-stack | `python3 dual_stack_servidor.py demo` |
| `transaccion.py` | Python avanzado · Ej. 3.2: transacciones con `with` | `python3 transaccion.py` |
| `scheduler.py` | Python avanzado · Ej. 4.2: scheduler de corrutinas | `python3 scheduler.py` |

---

## IPv6 · Ejercicio 3 — respuestas

**Parte A.** Un servidor `AF_INET` en `0.0.0.0` solo escucha IPv4. Si un cliente se
conecta a `::1` da *Connection refused*: no hay nadie escuchando en ese puerto en la
familia IPv6. Son dos "mundos" distintos.

**Parte B.**
- La línea que falta es `s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)`.
- Cuando conecta el cliente IPv4, el servidor ve **`::ffff:127.0.0.1`**.
- Ese prefijo `::ffff:` indica una **dirección IPv4 mapeada en IPv6** (*IPv4-mapped IPv6 address*).

**Parte C.**
- Con `V6ONLY = 1` el cliente IPv4 recibe *Connection refused*: el socket ya no acepta IPv4.
- `cat /proc/sys/net/ipv6/bindv6only` en Ubuntu da `0` (dual-stack por defecto).
- Conviene ponerlo **explícito** porque el default cambia según el sistema (Windows/OpenBSD = 1).
  Si dependés del default, el servidor anda en tu máquina y en la del profe no.

**Parte D.** Con una lista de IPs bloqueadas, `192.168.1.5` y `::ffff:192.168.1.5` son el mismo
cliente escrito distinto. Si no normalizás, el bloqueo se saltea solo por cómo llegó la conexión.

**Parte E.**
- Con `localhost` normalmente viene primero `::1` (IPv6) y después `127.0.0.1`.
- Elegir solo la primera dirección es un error porque **tener IPv6 no significa que la ruta ande**
  (muy común en Argentina: el ISP da IPv6 pero sin salida). Hay que probar la siguiente.
- Como cliente, `socket.create_connection()` ya hace todo esto solo.

> ⚠️ No pude ejecutar la parte IPv6 en mi entorno (no tiene IPv6). El código sigue
> exactamente la referencia del profe (`../dual_stack.py`). En tu Ubuntu corré `demo`.

---

## Python avanzado · Ejercicio 3.2 — idea clave

`__enter__` saca una foto con `copy.deepcopy(vars(obj))`; `__exit__` mira si vino una excepción
(`tipo_exc is not None`) y, si vino, restaura la foto. Usamos **deepcopy** y no `.copy()` porque
con una copia superficial una lista modificada con `.append()` no se podría deshacer (las dos
"fotos" apuntarían a la misma lista). Devolvemos `False` para que la excepción siga su camino.

## Python avanzado · Ejercicio 4.2 — idea clave

Una cola (`deque`) de generadores. Saco uno, hago `next()` (corre hasta su próximo `yield`),
y si no terminó lo vuelvo a poner al final. Si lanza `StopIteration`, terminó y no vuelve.
**Esto es exactamente lo que hace el event loop de asyncio** (clase 18): las tareas ceden el
control voluntariamente; nadie las interrumpe.
