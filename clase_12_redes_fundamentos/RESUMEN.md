# Clase 12 — Redes: fundamentos · Resumen

En red **no hay memoria compartida ni reloj común**, el canal puede **perder, duplicar, demorar o reordenar**,
y **no podés distinguir** un proceso lento de uno caído. Esta clase es el vocabulario para todo lo que sigue.

## Capas
```
 tu código        "mandá este texto"
 Transporte (TCP/UDP)   "que llegue completo y en orden" / "mandalo y listo"
 Red (IP)         "que llegue a ESTA máquina"
 Enlace (Ethernet/wifi) "que llegue a la próxima placa"
 Físico           bits, voltajes, ondas
```
Cada capa habla con su par "como si" fuera directo, pero delega en la de abajo.
**Encapsulamiento:** `[ Ethernet 14B | IP 20B | TCP 20B | datos ]` → mandar 1 byte cuesta mucho más que 1 byte.

| OSI (7, teórico) | TCP/IP (4, el real) | Ejemplos |
|---|---|---|
| 7 Aplicación · 6 Presentación · 5 Sesión | Aplicación | HTTP, DNS, SMTP, TLS |
| 4 Transporte | Transporte | TCP, UDP |
| 3 Red | Internet | IP, ICMP |
| 2 Enlace · 1 Física | Enlace | Ethernet, wifi, cables |

## Direccionamiento
- **IP** identifica la **máquina** · **puerto** (16 bits, 0–65535) identifica el **proceso** (multiplexación).

| Dirección | Significado |
|---|---|
| `127.0.0.1` | loopback: solo esta máquina |
| `0.0.0.0` | (en bind) **todas** las interfaces → cualquiera que llegue a tu máquina |
| `10.x`, `172.16–31.x`, `192.168.x` | privadas (no ruteables en Internet) |
| `255.255.255.255` | broadcast local |

| Puertos | |
|---|---|
| 0–1023 | bien conocidos (necesitan **root**) |
| 1024–49151 | registrados |
| 49152–65535 | efímeros según IANA (Linux usa 32768–60999) |

Memorizá: **22** SSH · **25** SMTP · **53** DNS · **80** HTTP · **443** HTTPS · **5432** PostgreSQL · **6379** Redis.

**Una conexión TCP = cuádrupla** `(IP origen, puerto origen, IP destino, puerto destino)`.
Por eso un servidor en el puerto 80 atiende miles de clientes: cada uno aporta un origen distinto.

## DNS
Traduce nombres → IPs. Distribuido y jerárquico. **TTL** = cuánto se puede cachear ("tarda en propagarse").
Un nombre puede dar **varias IPs** (reparto de carga). Resolver es **bloqueante** (importa en asyncio).

## TCP vs UDP ⭐

| | **TCP** | **UDP** |
|---|---|---|
| Conexión | sí (**handshake de 3 vías**) | no |
| Entrega | **garantizada** (retransmite) | no |
| Orden | sí | no |
| Límites de mensaje | **NO** (es un **flujo**) | **sí** (un sendto = un recvfrom) |
| Encabezado | 20 B | 8 B |
| Extras | control de flujo y de congestión | nada |
| Usos | web, mail, BD, SSH, archivos | voz/video, juegos, DNS, métricas |

### Handshake
```
 cliente ── SYN ──────► servidor     "quiero conectarme"
         ◄── SYN-ACK ──               "dale, yo también"
         ── ACK ──────►               "listo"
```
Cuesta ~1 RTT antes del primer byte útil. El cierre es de **4 pasos** (cada lado cierra su dirección).

### ⚠️ TCP es un flujo, no mensajes
`send("HOLA"); send("COMO"); send("ESTAS")` → el otro puede recibir `"HOLACOMOESTAS"` o `"HOLACO"` + `"MOESTAS"`.
**Hay que delimitar vos:** separador (`\n`), **prefijo de longitud**, o formato autodelimitado. (Clase 13.)

"UDP es más rápido" es una simplificación: si le agregás confiabilidad a mano, terminás con algo peor que TCP (salvo QUIC/HTTP/3).

## Herramientas
| | |
|---|---|
| `ip addr` / `ip route` | interfaces / rutas |
| `ss -tlnp` / `ss -tunap` | quién **escucha** / todas las conexiones |
| `ping` | ¿hay ruta? (ICMP; que no responda ≠ caído) |
| `traceroute` | por qué routers pasa |
| `dig nombre +short`, `host` | DNS |
| `nc -l 8080` / `nc host 80` | servidor / cliente TCP crudo (`-u` UDP) |
| `sudo tcpdump -i lo -n port 8080` | ver los paquetes (handshake incluido) |

Protocolos de texto de Internet usan **`\r\n`**, no `\n`.

## ❓ Autoevaluación
1. ¿Por qué se organiza la red en capas? ¿Qué es el encapsulamiento?
2. ¿Qué identifica la IP y qué el puerto? ¿Qué es la cuádrupla?
3. Diferencia entre bindear en `127.0.0.1` y en `0.0.0.0`.
4. Dibujá el handshake de 3 vías.
5. ¿Por qué `send` 3 veces puede llegar como 1 `recv`? ¿Es un bug?
6. Dos formas de delimitar mensajes y el problema de cada una.
7. ¿Cuándo elegís UDP sobre TCP?
