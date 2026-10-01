# Clase 16 — socketserver · Resumen

Todos los servidores repiten `socket → bind → listen → accept → … → close`. Lo único que cambia es **qué hacés con
cada cliente**. `socketserver` es un **framework**: escribe la parte fija y te deja un hueco.

> **Biblioteca:** vos llamás a su código. **Framework:** **él llama al tuyo** (inversión de control).

## Lo mínimo
```python
import socketserver
class Eco(socketserver.BaseRequestHandler):
    def handle(self):                         # ← TU código: corre UNA VEZ POR CONEXIÓN
        datos = self.request.recv(1024)       # self.request = socket del cliente (el de accept)
        self.request.sendall(datos.upper())
socketserver.TCPServer(("localhost", 8080), Eco).serve_forever()
```
- **Un handler nuevo por conexión** (`id(self)` cambia) → no se mezcla estado entre clientes.

## Configurar = heredar con atributos de clase (diseño de los 90)
```python
class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True     # SO_REUSEADDR
    daemon_threads = True          # Ctrl+C no espera a los clientes
    request_queue_size = 128       # listen(128)
    address_family = socket.AF_INET6
```

## Concurrencia: cambiar una palabra
| Clase | Modelo |
|---|---|
| `TCPServer` | secuencial |
| `ThreadingTCPServer` | un thread por cliente |
| `ForkingTCPServer` | un proceso por cliente (**cosecha zombies solo**) |
`UDPServer`, `ThreadingUDPServer`, `ForkingUDPServer` igual.

## Framing gratis: StreamRequestHandler
```python
class Comandos(socketserver.StreamRequestHandler):
    def handle(self):
        for linea in self.rfile:              # makefile(): lee por LÍNEAS
            self.wfile.write(b"ok: " + linea)
```
⚠️ No mezcles `self.rfile` con `self.request.recv()` (rfile tiene su buffer). Para binario/longitud: `BaseRequestHandler`.

| Handler | Cuándo |
|---|---|
| `BaseRequestHandler` | binario, control total |
| `StreamRequestHandler` | texto por líneas sobre TCP |
| `DatagramRequestHandler` | UDP con rfile/wfile |

## Dónde vive el estado ⭐
- En el **handler** → muere con la conexión (un contador ahí siempre da 1).
- En el **servidor** (`self.server.x`) → compartido.
  - Con **threads**: es la **misma** memoria → **Lock** (y la lectura también adentro).
  - Con **fork**: cada hijo tiene una **copia** → el lock no sirve: hace falta **memoria compartida** (`multiprocessing.Value`
    creado en el `__init__` del servidor, antes del fork).

## Los 3 momentos (template method)
```
setup()    → (StreamRequestHandler crea rfile/wfile)  ← si lo sobreescribís: super().setup() ¡primero!
handle()   → tu código
finish()   → limpieza; corre AUNQUE handle() falle   ← super().finish()
```
Otros ganchos del servidor: `handle_error()` (por defecto loguea y **sigue**: un cliente no tumba el servidor),
`verify_request()` (aceptar/rechazar antes de crear el handler), `service_actions()`.

## Mixins ⭐
```python
class ThreadingTCPServer(ThreadingMixIn, TCPServer): pass     # ¡cero código propio!
```
`ThreadingMixIn` sobreescribe **un solo método**: `process_request()` → en vez de atender en el mismo hilo,
lanza un thread y vuelve. `ForkingMixIn` hace fork, y cosecha con `collect_children()` en `service_actions()`.
- **2 protocolos × 3 modos** = con mixins 6 piezas que se combinan (sin mixins, 6 clases duplicadas).
- Condición: el **punto de variación tiene que ser un método** identificable.

### El orden importa (y falla en silencio)
```python
class Bien(ThreadingMixIn, TCPServer): pass   # MRO: Bien → ThreadingMixIn → TCPServer → BaseServer
class Mal(TCPServer, ThreadingMixIn): pass    # MRO: Mal → TCPServer → BaseServer → ThreadingMixIn  ← secuencial
```
**Mixins siempre a la izquierda.** `Mal` no da error: solo es lento bajo carga.

## UDP: la asimetría
```python
def handle(self):
    datos, sock = self.request                 # en UDP es una TUPLA (datagrama, socket)
    sock.sendto(datos.upper(), self.client_address)
```

## Límites
Sigue siendo **un thread/proceso por cliente** → los mismos límites de la clase 14 (no resuelve C10K). Sin TLS integrado.
Pero `http.server` está construido encima (`BaseHTTPRequestHandler` → `do_GET()`), y `serve_forever()` por dentro ya usa
un **selector** (clase 17) para vigilar su socket y poder hacer `shutdown()`.

## ❓ Autoevaluación
1. ¿Qué diferencia hay entre una biblioteca y un framework?
2. ¿Cuántas veces corre `handle()`? ¿Qué es `self.request` en TCP y en UDP?
3. ¿Por qué un contador en el handler siempre da 1? ¿Dónde va, y qué hace falta con threads y con fork?
4. ¿Qué método sobreescribe `ThreadingMixIn`? ¿Por qué el orden de herencia importa?
5. ¿Por qué `ForkingTCPServer` no deja zombies?
6. ¿Para qué sirve `daemon_threads`?
7. ¿Qué pasa si sobreescribís `setup()` sin llamar a `super().setup()`?
