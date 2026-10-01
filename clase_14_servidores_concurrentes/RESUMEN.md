# Clase 14 — Servidores concurrentes · Resumen

El servidor secuencial atiende **uno a la vez**. Solución: que el bucle de `accept()` **delegue rápido** y vuelva a aceptar.

## ¿Por qué acá sí sirven los threads?
Un servidor pasa casi todo el tiempo **esperando** (`recv`, el cliente, la red) → es **I/O-bound** → el **GIL se libera**
mientras espera. Diez threads en `recv()` no compiten por nada.

| | Threads (con GIL) | Threads free-threaded | Procesos |
|---|---|---|---|
| CPU-bound | ❌ | ✅ | ✅ |
| I/O-bound | ✅ | ✅ | ✅ (más caros) |

Free-threading: experimental en 3.13 → **oficialmente soportado (opcional) en 3.14** (PEP 779). La materia asume GIL.
`sys._is_gil_enabled()` · `sysconfig.get_config_var('Py_GIL_DISABLED')`.

---

## Las 4 estrategias

### 1) Un thread por cliente
```python
conn, addr = srv.accept()
threading.Thread(target=atender, args=(conn, addr), daemon=True).start()   # vuelve YA a accept()
```
- `daemon=True` → Ctrl+C no queda colgado (pero corta a los clientes de golpe).
- Cada thread = un stack (8 MB virtuales) → miles = problema.
- **Estado compartido** (contador de clientes, logs) → **Lock** (clase 11).

### 2) Un proceso por cliente (fork) — los 3 detalles ⭐
```python
signal.signal(signal.SIGCHLD, signal.SIG_IGN)      # 3) zombies
conn, addr = srv.accept()
if os.fork() == 0:
    srv.close()                                    # 2) el HIJO cierra el socket que escucha
    atender(conn); conn.close(); os._exit(0)
conn.close()                                       # 1) el PADRE cierra la conexión
```
1. **Padre cierra `conn`:** tras fork hay **2 copias** del fd; TCP cierra recién con la **última**. Si no, el cliente no ve el fin y se filtran fds.
2. **Hijo cierra `srv`:** no lo necesita.
3. **Zombies:** `SIG_IGN` (el kernel los cosecha) o handler con **`while` + `waitpid(-1, WNOHANG)`** (las señales **no se encolan**).

✅ aislamiento (un crash mata solo a ese hijo), sin estado compartido, sin GIL. ❌ caro (memoria, creación, contexto), compartir datos requiere IPC.

### 3) Pool de threads (`concurrent.futures`)
```python
with ThreadPoolExecutor(max_workers=20) as pool:
    while True:
        conn, addr = srv.accept()
        pool.submit(atender, conn, addr)          # encola y vuelve enseguida → devuelve un Future
```
- **Techo** de recursos conocido, workers reutilizados.
- `Future`: `done()` (no bloquea), `result()` (bloquea; **re-lanza la excepción** de la tarea).
- ⚠️ Si nadie llama a `result()`, **las excepciones se pierden en silencio** → envolver `atender` en try/except.
- ⚠️ Con **conexiones persistentes** cada cliente ocupa un worker toda la sesión → el cliente 21 espera (el secuencial, corrido 20 lugares).
  Ideal para tareas **cortas** (una petición, una respuesta).

### 4) `socketserver`
```python
class Eco(socketserver.StreamRequestHandler):
    def handle(self):
        for linea in self.rfile:                  # framing por líneas gratis (makefile)
            self.wfile.write(linea)
class Srv(socketserver.ThreadingTCPServer):       # o ForkingTCPServer
    allow_reuse_address = True; daemon_threads = True
Srv(("0.0.0.0", 8080), Eco).serve_forever()
```
Cómodo, pero **caja negra** cuando algo falla; y anticuado para miles de conexiones.

---

## Medidas (20 clientes, cada uno tarda 1 s)
| Servidor | Total | Latencia máx |
|---|---|---|
| Secuencial | **20 s** | 20 s (escalera: 1, 2, 3… 20) |
| Threads / Fork / Pool(20) | ~1 s | ~1 s |
| Pool(5) | 4 s | 4 s → 4 tandas de 5 (**demorados, no rechazados**) |

## Dónde se rompe cada una
- Threads: miles → cambios de contexto dominan (*thrashing*). Procesos: lo mismo, antes.
- Pool: no se rompe, **se satura** (degrada de forma predecible).
- Todas: límite de **descriptores** por proceso (`ulimit -n`).
- **C10K** (Dan Kegel, 1999): 10 000 conexiones con un thread/proceso por conexión = imposible.
  Solución: **un hilo que atiende muchas conexiones** preguntando cuáles están listas → **I/O multiplexing** (clase 17) → asyncio.

## ¿Cuál uso?
| Situación | Estrategia |
|---|---|
| pocos clientes, código simple | threads / socketserver |
| trabajo **CPU** por cliente | procesos |
| aislamiento ante crashes | procesos |
| mucha carga, **tareas cortas** | pool |
| **miles** de conexiones | select / asyncio |
| estado compartido complejo | threads + locks |

## ❓ Autoevaluación
1. ¿Por qué los threads sirven para un servidor si con GIL no sirven para CPU?
2. Explicá los 3 descuidos del fork y qué pasa si falta cada uno.
3. ¿Por qué el handler de SIGCHLD necesita `while` y `WNOHANG`?
4. ¿Qué es un `Future`? ¿Qué pasa con una excepción si nadie llama a `result()`?
5. ¿Por qué un pool se satura con conexiones persistentes?
6. ¿Qué es el problema C10K y cómo se resuelve?
