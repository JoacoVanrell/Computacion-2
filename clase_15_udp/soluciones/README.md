# Clase 15 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu eco UDP con reintentos está en `../mi_trabajo/nuevo.py`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `protocolo_confiable.py` | **Ej. 3 (obligatorio)**: reintentos, duplicados y números de secuencia, medido | `python3 protocolo_confiable.py` · `--timeouts` |
| `udp_connect_icmp.py` | Ej. 4: qué hace `connect()` en UDP (ICMP + filtro) | `python3 udp_connect_icmp.py` |
| `servidor_tiempo.py` | Adicional: servidor de tiempo RFC 868 + desfasaje | `python3 servidor_tiempo.py demo` |

## Salida real del obligatorio
Pérdida simulada **en los dos sentidos** (pedido y respuesta) + algunas respuestas **demoradas** más que el timeout.

```
=== pérdida 30% · 60 mensajes ===
ingenuo  trabajos del servidor:  91 (debería ser 60) · respuestas EQUIVOCADAS 2
CON seq  trabajos del servidor:  60 (debería ser 60) · respuestas EQUIVOCADAS 0

=== pérdida 70% · 60 mensajes ===
ingenuo  trabajos del servidor: 171 (debería ser 60) · intentos prom 9.4 · sin respuesta 0 · EQUIVOCADAS 1
CON seq  trabajos del servidor:  60 (debería ser 60) · intentos prom 12.9 · sin respuesta 0 · EQUIVOCADAS 0

timeout 0.01s → 4.9 intentos prom · timeout 0.05s → 2.1 · timeout 0.3s → 1.7 pero 6.3 s en total
```

## Respuestas

**A.** De 200 llegan ~140 con 30 %. El emisor **no recibe ningún error** por los perdidos: `sendto` devuelve
`len(datos)` igual. *"UDP no te avisa si algo se perdió."* Con `tc netem reorder` aparecen saltos hacia atrás:
un protocolo que asuma orden se rompe.

**B.**
4–5. Con 30 % ≈ 2 intentos; con 70 % ≈ 10 (la probabilidad de que salgan **pedido y respuesta** es 0,3 × 0,3 = 9 %,
así que en promedio hacen falta ~11 intentos). Sigue funcionando si das suficientes intentos.
6. **Timeout muy corto** (0,01 s): reintenta antes de que la respuesta llegue → más intentos y más trabajo duplicado.
**Muy largo** (5 s): cada pérdida te hace esperar 5 s → lentísimo. TCP lo resuelve **midiendo el RTT** y ajustando.

**C.**
7. **No puede saberlo**: desde el cliente, "se perdió el pedido" y "se perdió la respuesta" se ven igual (silencio).
8. El servidor ingenuo trabajó **91 veces para 60 mensajes** (171 con 70 %): cada respuesta perdida = trabajo repetido.
9. Con "transferir $100" eso es **cobrarte dos (o tres) veces**. Las operaciones no **idempotentes** necesitan deduplicación.

**D.**
10. El servidor guarda `(origen, seq) → respuesta`. Si llega repetido, **reenvía la guardada** sin trabajar → 60 de 60.
11. El cliente descarta respuestas con `seq` distinto: una respuesta **demorada** del pedido anterior podría llegar
    mientras espera la del actual y la tomaría como propia (las "EQUIVOCADAS" del ingenuo).

**E.**
13. Tres garantías de TCP que esto **no** tiene: **orden** de los mensajes (cada uno va solo, pero no hay ventana),
    **control de flujo** (no frena si el servidor no da abasto), **control de congestión** (no baja el ritmo si la red se satura).
    Tampoco: **timeout adaptativo** (RTT), **conexión/cierre**, ni límite de memoria del diccionario de respuestas.
14. Cuando necesitás **todo** eso (transferir un archivo, una conversación larga ordenada) → usá **TCP**.
    UDP vale la pena si solo necesitás **parte** de las garantías (DNS: reintento simple; juegos y voz: ni siquiera).

## Ejercicio 4 (salida real)
```
CON connect: ConnectionRefusedError en 0.000s   ← el ICMP "port unreachable" llegó al socket
SIN connect: timeout después de 2.0s            ← el kernel no sabía a qué socket dárselo, lo tiró
Filtro: llegaron [b'soy el amigo']              ← el datagrama del tercero lo descartó el kernel
```
`connect()` en UDP **no manda nada**: fija el destino (`send`/`recv` sin dirección), **filtra** remitentes y habilita los
errores ICMP. No dependas de esto en Internet: muchos firewalls filtran ICMP → el timeout sigue siendo tu red de seguridad.

## Ejercicio 5–6 (respuestas cortas)
- Sin `SO_BROADCAST` → `PermissionError`: es una protección para no inundar la red por accidente.
- Los routers no reenvían broadcast (si no, un paquete llegaría a todo Internet). DHCP no puede usar TCP porque la
  máquina **no tiene IP** ni sabe a quién conectarse: grita a toda la red local.
- MTU 1500 − 20 (IP) − 8 (UDP) = **1472 bytes** sin fragmentar. 60 000 bytes ≈ **41 fragmentos**: si cada uno se pierde
  con 5 %, el datagrama llega entero con probabilidad 0,95⁴¹ ≈ **12 %**; uno de 1000 bytes, 95 %.
