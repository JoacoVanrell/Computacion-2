# Clase 15 — UDP · Resumen

UDP = "mandá el paquete y olvidate". **Sin conexión, sin confirmación, sin reintento, sin orden.**
Y aun así es la base de DNS, streaming, juegos y **QUIC/HTTP/3**. La clave: *qué ganás por no tener garantías*.

## Socket UDP
```python
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    # DGRAM en vez de STREAM
```
**Servidor (2 pasos):**
```python
s.bind(("0.0.0.0", 8080))
while True:
    datos, origen = s.recvfrom(65535)    # DATOS + QUIÉN lo mandó
    s.sendto(datos, origen)              # responderle a ese origen
```
- **No hay `listen()` ni `accept()`**, y **un solo socket atiende a todos** (no hay conexión → no hay socket por cliente).

**Cliente:**
```python
s.settimeout(2.0)                         # ⚠️ OBLIGATORIO: no hay "cierre" que detectar
s.sendto(b"hola", ("localhost", 8080))   # el kernel asigna puerto efímero en el 1er sendto
resp, origen = s.recvfrom(65535)
```

## bind() vs connect() en UDP
| | Fija | ¿Quién lo usa? |
|---|---|---|
| `bind()` | extremo **local** (mi puerto) | **servidor** siempre (si no, queda en puerto 0 y nadie le puede escribir) |
| `connect()` | extremo **remoto** | **cliente** que habla con un solo servidor |
`connect()` en UDP **no manda ningún paquete**. Hace 3 cosas: `send`/`recv` sin dirección · **filtra** remitentes ·
habilita **errores ICMP** (`ConnectionRefusedError` en vez de esperar el timeout entero).

## Límites de mensaje
✅ **Un `sendto` = un `recvfrom`** → no hay framing que implementar.
⚠️ Si el buffer de `recvfrom(n)` es más chico que el datagrama, **el resto se descarta** (no queda para después).
→ usá `recvfrom(65535)`.

## Tamaño: quedate debajo del MTU
MTU Ethernet 1500 − IP 20 − UDP 8 = **1472 bytes** sin fragmentar.
Si fragmentás en *k* pedazos y cada uno se pierde con prob *p*: llega entero con **(1−p)ᵏ**. Fragmentar multiplica la pérdida.
DNS usa 512 B; si no entra, marca TC y el cliente reintenta por TCP.

## Confiabilidad encima de UDP (lo que TCP daba gratis)
1. **Timeout + retransmisión.** Problema: el timeout fijo es una apuesta (TCP mide el RTT).
2. **Duplicados:** si se perdió la **respuesta**, el servidor ya hizo el trabajo y al reintentar lo hace **dos veces**
   (grave si es "transferir $100").
3. **Números de secuencia** (`struct.pack("!I", seq)`): el servidor guarda `(origen, seq) → respuesta` y reenvía la guardada;
   el cliente descarta respuestas con otro `seq` (las **demoradas**).
4. Si seguís (ventana, control de flujo, congestión)… reimplementás TCP, probablemente peor.

**Pregunta correcta: ¿qué garantías necesito?** DNS: reintento simple · video/voz: ni reintenta (lo viejo no sirve) ·
juegos: mandan el estado completo cada tick (perder uno no importa) · QUIC: confiabilidad completa, años de trabajo.

## Lo que solo UDP puede hacer
- **Broadcast** `255.255.255.255` (con `SO_BROADCAST`): a toda la red local. DHCP, descubrimiento de impresoras.
  Los routers **no** lo reenvían.
- **Multicast** `224.0.0.0–239.255.255.255`: solo a los suscriptos (`IP_ADD_MEMBERSHIP`). Ej.: mDNS `224.0.0.251:5353` (los `.local`).

## Ver pérdidas reales
En localhost no se pierde nada → simular en código (`sendto` que "miente") o con
`sudo tc qdisc add dev lo root netem loss 30%` (también `delay`, `duplicate`, `reorder`). **¡Sacarlo después!**

## TCP o UDP
| Necesitás | |
|---|---|
| todo, en orden · archivos · no querer implementar confiabilidad | **TCP** |
| consulta corta · datos que **envejecen** (audio, video, posición) · hablarle a muchos | **UDP** |
> Si retransmitir un dato viejo no tiene sentido, **TCP te estorba**.

## ❓ Autoevaluación
1. ¿Por qué el servidor UDP no tiene `listen`/`accept` ni un socket por cliente?
2. ¿Por qué el timeout es obligatorio en un cliente UDP?
3. ¿Qué hace `connect()` en UDP? ¿Manda algo?
4. ¿Qué pasa si `recvfrom(10)` recibe un datagrama de 100 bytes?
5. ¿Por qué conviene no pasar el MTU? Calculá la probabilidad con 10 fragmentos y 1 % de pérdida.
6. ¿Por qué reintentar sin número de secuencia puede ejecutar un pedido dos veces?
7. Nombrá 3 garantías de TCP que un "UDP con reintentos" no tiene.
