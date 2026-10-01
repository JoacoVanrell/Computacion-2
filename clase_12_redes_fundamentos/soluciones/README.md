# Clase 12 — Ejercicios resueltos

> Material de estudio armado con Claude.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `tcp_flujo_vs_udp.py` | **Ej. 6 (obligatorio)**: TCP es un flujo vs. UDP datagramas (todo automático) | `python3 tcp_flujo_vs_udp.py` |
| `escaneo_puertos.py` | Adicional: escanear **tu** máquina (1–1024) y comparar con `ss -tlnp` | `python3 escaneo_puertos.py` |
| `medir_handshake.py` | Adicional: costo del handshake local vs. remoto | `python3 medir_handshake.py [host] [puerto]` |

## Salida real del obligatorio

```
A)  TCP sin pausa     → 1 recv():      [b'HOLACOMOESTAS']          ← los 3 send() llegaron PEGADOS
A2) TCP con pausa     → 3 recv():      [b'HOLA', b'COMO', b'ESTAS'] ← "funcionó"… por casualidad
C)  UDP               → 3 recvfrom():  [b'HOLA', b'COMO', b'ESTAS'] ← siempre uno por datagrama
```
Handshake: `127.0.0.1` ≈ **0.06 ms** · `example.com` ≈ **17 ms**.

## Respuestas (checklist del obligatorio)

1. **¿Se distinguen los tres envíos?** No: llegan como `HOLACOMOESTAS`.
2. **¿Y con `sleep`?** Probablemente llegan separados, porque cuando el receptor hace `recv` solo hay un mensaje en el buffer.
   **No se puede confiar:** con una red lenta, un receptor ocupado, o mensajes grandes que TCP parte en segmentos,
   vuelven a mezclarse o a cortarse. Además, agregar demoras para "arreglar" un protocolo lo hace lento y frágil.
3. **¿Es un bug de TCP?** No. El contrato de TCP es: **todos los bytes, en orden, sin duplicados**. Nunca prometió
   respetar los "límites" de cada `send()`: es un **flujo de bytes**, no de mensajes.
4. **Dos formas de delimitar mensajes:**
   - **Delimitador** (ej. `\n` al final de cada mensaje). Problema: si el mensaje contiene `\n`, se corta en dos.
     Solución: *escapar* el delimitador (como `\\n`) o codificar el contenido (base64/JSON).
   - **Prefijo de longitud** (ej. 4 bytes con el largo y después el cuerpo). El contenido puede tener cualquier byte,
     no hay problema con delimitadores. Hay que leer **exactamente** N bytes (un `recv` puede devolver menos).
   - (Bonus) **formato autodelimitado**: JSON que se parsea hasta cerrar llaves, HTTP con `Content-Length`.
5. **¿Cuántos `recvfrom` en UDP?** **Tres**: uno por cada `sendto`. En TCP hubo **uno** solo.
6. **¿Por qué la diferencia?** UDP manda **datagramas**: cada `sendto` es un paquete independiente, que llega entero o no llega.
   TCP mantiene un **buffer de bytes** de cada lado y los manda como le conviene (agrupando, partiendo) para ser eficiente.
7. **¿Por qué UDP no necesita `listen()` ni `accept()`?** Porque **no hay conexión**: no hay handshake que aceptar ni un
   socket nuevo por cliente. El mismo socket recibe datagramas de cualquiera y `recvfrom` te dice de quién vino.

## Ejercicio 7 — puertos efímeros (respuestas)
- `cat /proc/sys/net/ipv4/ip_local_port_range` en Linux da **32768–60999** (≈28 000 puertos), distinto del 49152–65535 de IANA:
  el de IANA es una **recomendación**; cada SO elige el suyo (y se puede cambiar).
- Hacia **el mismo** servidor:puerto podés tener ≈28 000 conexiones simultáneas (lo que cambia en la cuádrupla es solo tu
  puerto de origen). Hacia servidores **distintos** se pueden reusar los mismos puertos de origen, porque cambia otra parte
  de la cuádrupla. Por eso un **balanceador** que habla siempre con los mismos backends se puede quedar **sin puertos**.

> ⚠️ El escáner tiene el host fijo en `127.0.0.1` a propósito.
