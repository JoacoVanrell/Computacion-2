# Clase 7 — mmap y memoria compartida · Resumen

## La idea
Con pipes/colas los datos **se copian dos veces** (proceso → kernel → proceso).
Con **memoria compartida** dos procesos acceden a **la misma memoria física**: **cero copias**, velocidad máxima…
y **toda la sincronización corre por tu cuenta**.

```
 Pipe:      A ──copia──► kernel ──copia──► B
 Compartida: A ──┐
                 ├──► misma región de RAM
             B ──┘
```

| | Pipe / Queue | Memoria compartida |
|---|---|---|
| Copias | 2 (+ serializar en Queue) | 0 |
| Velocidad | buena | excelente |
| Sincronización | **incluida** (el lector espera) | **manual** (locks) |
| Datos grandes | ineficiente | ideal |
| Riesgo de bugs | bajo | **alto** (race conditions) |

---

## 1. `mmap`: un archivo (o RAM) que se usa como array de bytes

```python
with open("datos.bin", "r+b") as f:
    mm = mmap.mmap(f.fileno(), 0)    # 0 = todo el archivo
    mm[0:5] = b"HOLA!"               # como bytearray
    mm.seek(0); mm.readline()        # o como archivo
    mm.find(b"x"); mm.size()
    mm.close()
```
- ⚠️ **No se puede mapear un archivo vacío**: primero darle tamaño (`f.write(b"\0" * n)`).
- Modos: `ACCESS_READ`, `ACCESS_WRITE` (cambios van al archivo), `ACCESS_COPY` (copia privada).
- Entre dos procesos que mapean el mismo archivo **no hace falta `flush()`**: comparten las páginas del kernel.
  `flush()` solo para **persistir en disco** o si el otro lee con `read()` normal (y es lento).

### mmap anónimo: memoria sin archivo para padre ↔ hijos
```python
mm = mmap.mmap(-1, 1024)    # -1 = sin archivo
pid = os.fork()             # el hijo HEREDA el mapeo, y es COMPARTIDO (no copy-on-write)
```
Para guardar números: `struct.pack_into('i', mm, offset, valor)` / `struct.unpack_from('i', mm, offset)`.

---

## 2. `multiprocessing.Value` y `Array` (lo cómodo)

```python
from multiprocessing import Value, Array, Process
c = Value('i', 0)            # un int compartido     → c.value
a = Array('d', 100)          # 100 doubles            → a[i], list(a)
a2 = Array('i', [1, 2, 3])
```

| Código | Tipo C | Python |
|---|---|---|
| `'i'` | int (4 B) | int |
| `'d'` | double (8 B) | float |
| `'f'` | float | float |
| `'c'` / `'b'` | char / signed char | bytes / int |

- Traen un **lock interno**: `with c.get_lock(): c.value += 1`.
- ⚠️ Ese lock protege cada lectura/escritura **suelta**, NO el `+=` completo → hay que tomarlo vos.

---

## 3. `shared_memory` (Python 3.8+): bloques con **nombre**

```python
from multiprocessing import shared_memory
shm = shared_memory.SharedMemory(create=True, size=1024, name="canal")   # el DUEÑO crea
shm.buf[0:5] = b"Hola!";  struct.pack_into('i', shm.buf, 8, 42)
otro = shared_memory.SharedMemory(name="canal")                          # otro proceso se CONECTA
sl = shared_memory.ShareableList([0, 0.0, "txt", True], name="lista")    # lista de tamaño fijo
```
Como tiene **nombre**, la pueden usar procesos que **no son parientes** (Value/Array necesitan heredarse).

### `close()` ≠ `unlink()` (pregunta segura)
| | Qué hace | Quién |
|---|---|---|
| `close()` | **este** proceso se desconecta; el bloque sigue existiendo | todos |
| `unlink()` | **borra** el bloque del sistema | solo el **dueño**, al final |

Si nadie hace `unlink()`, la memoria queda tomada hasta reiniciar (está en `/dev/shm`).

---

## 4. El peligro: race condition

```python
contador.value += 1      #  1) leer   2) sumar   3) escribir   ← otro proceso se mete entre 1 y 3
```
4 procesos × 100.000 incrementos → obtenido **≈150.000** en vez de 400.000.
Una race necesita: **dato compartido** + **al menos uno escribe** + **sin coordinación**.

**Solución (anticipo de la clase 11):**
```python
lock = Lock()
with lock:               # sección crítica: de a uno
    contador.value += 1
```
Tip: acumulá en una variable **local** y tocá lo compartido **una sola vez** (menos tiempo con el lock).

## ¿Cuándo usar qué?
- **Memoria compartida:** datos **grandes** (arrays, imágenes), actualizados **in-place**, leídos seguido, velocidad crítica.
- **Pipe / Queue:** mensajes **en secuencia**, datos chicos, querés **simplicidad** y sincronización gratis.

## ❓ Autoevaluación
1. ¿Cuántas copias hace un pipe y cuántas la memoria compartida?
2. ¿Por qué no podés mapear un archivo vacío?
3. ¿Cuándo hace falta `flush()` en un mmap?
4. ¿Qué significa el `-1` en `mmap.mmap(-1, 1024)` y por qué sirve con fork?
5. ¿Por qué `x.value += 1` no es seguro aunque `Value` tenga un lock interno?
6. Diferencia entre `close()` y `unlink()`. ¿Quién llama a cada uno?
7. ¿Qué ventaja tiene `SharedMemory` sobre `Value`/`Array`?
