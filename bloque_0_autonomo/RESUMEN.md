# Bloque 0 (autónomo) — Resumen para estudiar

> Las herramientas que se usan TODO el año: Git, argparse, filesystem de Linux,
> Python avanzado e IPv6. Si entendés esto, el resto de la materia se apoya acá.

---

## 1. Git en 5 minutos

**Idea central:** Git guarda **fotos (snapshots)** completas del proyecto, no "diferencias".
Es **distribuido**: tu copia tiene TODA la historia, podés trabajar sin internet.

### Las 3 áreas (lo más importante)

```
 directorio de trabajo  --git add-->  staging (index)  --git commit-->  repositorio (historia)
   (lo que editás)                    (sala de espera)                   (fotos permanentes)
```

| Quiero... | Comando |
|---|---|
| ver qué cambió | `git status`, `git diff`, `git diff --staged` |
| guardar | `git add archivo` → `git commit -m "qué y por qué"` |
| ver la historia | `git log --oneline` |
| trabajar aparte | `git switch -c rama` … `git switch main` → `git merge rama` |
| sincronizar | `git pull` (bajar) / `git push` (subir) |
| deshacer cambios sin commitear | `git restore archivo` |
| sacar del staging | `git restore --staged archivo` |

- Un **branch** es solo un **puntero** a un commit (crearlo no copia nada).
- **Conflicto:** Git te marca `<<<<<<<` / `=======` / `>>>>>>>`; elegís qué queda, borrás las marcas y commiteás.
- Mensaje de commit: decí **qué** y **por qué**, no cómo ("Corregir promedio con lista vacía").
- `.gitignore`: `venv/`, `__pycache__/`, `.env`, `.vscode/`…

> 💡 **En este repo:** el profe es el remoto `upstream`. Para traer clases nuevas:
> `git pull upstream main` (si hay conflicto en README.md: `git checkout --ours README.md`).

---

## 2. argparse — argumentos de línea de comandos

```bash
python script.py datos.csv --output res.json -v
#                 ^posicional  ^opción con valor  ^flag
```

`sys.argv` es una lista cruda (`['script.py', 'datos.csv', ...]`): sin validación ni `--help`.
**argparse** te da todo eso gratis.

```python
import argparse
p = argparse.ArgumentParser(description="Qué hace")
p.add_argument("archivo")                                   # posicional (obligatorio)
p.add_argument("-n", "--lineas", type=int, default=10)       # opción con valor y tipo
p.add_argument("-v", "--verbose", action="store_true")       # flag True/False
p.add_argument("--formato", choices=["json", "csv"])         # valores permitidos
p.add_argument("-v", action="count", default=0)              # -v, -vv, -vvv
args = p.parse_args()          # args.archivo, args.lineas, args.verbose
```

| Patrón | Cómo |
|---|---|
| Leer de stdin si no pasan archivo | `nargs="?", type=argparse.FileType('r'), default=sys.stdin` |
| Opciones incompatibles | `g = p.add_mutually_exclusive_group()` |
| Subcomandos tipo `git commit` | `sub = p.add_subparsers(dest="comando")` |

**Códigos de salida:** `0` = OK · `1` = error · `130` = Ctrl+C. Siempre `if __name__ == "__main__":`.

---

## 3. Filesystem de Linux

**"Todo es un archivo":** documentos, dispositivos (`/dev/sda`), procesos (`/proc/1234`).

| Directorio | Para qué |
|---|---|
| `/home` | usuarios · `/etc` config · `/tmp` temporales · `/var/log` logs |
| `/dev` | dispositivos (`/dev/null` = agujero negro) |
| `/proc` | info del kernel y procesos, **generada al vuelo** (no está en disco) |

### Inodos (concepto clave)

```
 nombre "notas.txt"  ──►  INODO 12345  ──►  bloques de datos
 (entrada de directorio)  (permisos, dueño, tamaño, tiempos, punteros)
```

- El **nombre NO es parte del archivo**: es una entrada que apunta al inodo.
- Por eso: renombrar es instantáneo; podés borrar un archivo abierto y el programa sigue usándolo
  (el inodo vive hasta que nadie lo use y no tenga nombres).
- `stat archivo` muestra el inodo. **ctime = change time (metadatos), NO creation time** ⚠️.

### Permisos `rwx` para usuario / grupo / otros

```
-rwxr-xr--   →   7 5 4   (r=4, w=2, x=1)
```

| Octal | Uso típico |
|---|---|
| 644 | archivo normal · 755 script/directorio · 600 privado · 777 evitar |

- En **directorios**: `r` = listar, `w` = crear/borrar dentro, `x` = entrar (`cd`).
- **Sticky bit** (`t` en `/tmp`): solo podés borrar tus propios archivos.

### Enlaces

| | Enlace duro (`ln`) | Enlace simbólico (`ln -s`) |
|---|---|---|
| Qué es | otro nombre para **el mismo inodo** | archivo que contiene **una ruta** |
| Si borro el original | sigue andando | queda **roto** |
| Cruza particiones / a directorios | ❌ / ❌ | ✅ / ✅ |

**Python:** usá `pathlib` → `Path.home() / "dir" / "a.txt"`, `.exists()`, `.stat().st_mtime`, `.glob("**/*.py")`.
`shutil` para copiar/mover árboles (`rmtree` borra todo sin preguntar ⚠️).

---

## 4. Python avanzado (lo que vas a usar en procesos, hilos y sockets)

### Context managers (`with`) — limpiar SIEMPRE
```python
with open("a.txt") as f: ...     # se cierra aunque haya excepción
```
Por dentro: `__enter__` (al entrar, lo que devuelve va al `as`) y `__exit__(tipo, valor, tb)`
(al salir; si devuelve `True` **traga** la excepción — casi siempre querés `False`).
Atajo con `@contextmanager`: lo de antes del `yield` = enter; el `finally` = exit.
**Sirve para:** archivos, sockets, locks, procesos hijos, conexiones a BD.

### Decoradores — envolver funciones
```python
from functools import wraps
def log(f):
    @wraps(f)                       # conserva nombre y docstring
    def wrapper(*args, **kwargs):
        print("antes"); r = f(*args, **kwargs); print("después"); return r
    return wrapper
```
`@log` = `funcion = log(funcion)`. Si el decorador **recibe parámetros** (`@reintentar(3)`)
hay un nivel más de anidamiento. Útiles de la stdlib: `@lru_cache`, `@property`, `@staticmethod`.

### Generadores — datos bajo demanda (lazy)
- Una función con `yield` **no se ejecuta al llamarla**: devuelve un generador; cada `next()` avanza hasta el próximo `yield`.
- `(x**2 for x in ...)` usa memoria constante; `[x**2 ...]` crea toda la lista.
- `yield from otro()` delega. Pipelines: `leer → filtrar → parsear`, de a un elemento.
- **`send(valor)`**: el generador también RECIBE. Primero `next()` para llevarlo al primer `yield`.
  👉 Esto es la base de **asyncio** (`await` = suspenderse y que te reanuden con un resultado).

### Closures, `nonlocal`, `partial`
- Una función interna "recuerda" variables de afuera (closure). Para **modificarlas**: `nonlocal`.
- `partial(potencia, exponente=2)` fija argumentos.

### Excepciones bien usadas
- `try / except Específica / else (si no falló) / finally (siempre)`.
- ❌ `except Exception: pass` oculta bugs. Capturá solo lo que sabés manejar.
- Excepciones propias heredando de `Exception`; encadenar con `raise Nueva(...) from e`.

### Estructuras útiles
`defaultdict(int)`, `Counter(...).most_common(2)`, `deque(maxlen=5)` (O(1) en ambos extremos),
`namedtuple`, `@dataclass` (genera `__init__`, `__repr__`, `__eq__`), type hints.

---

## 5. IPv6 (para redes)

- IPv4 = 32 bits, **se agotó en 2011**. NAT lo estiró pero rompe conexiones entrantes y el modelo extremo a extremo.
- IPv6 = **128 bits** en hexadecimal: `2001:db8:85a3::8a2e:370:7334`.
  Reglas: sacar ceros a la izquierda; reemplazar **una sola** racha de ceros por `::`.

| IPv4 | IPv6 | |
|---|---|---|
| `127.0.0.1` | `::1` | loopback |
| `0.0.0.0` | `::` | todas las interfaces |
| | `fe80::/10` | link-local (siempre existe, necesita `%interfaz`) |
| | `::ffff:1.2.3.4` | IPv4 **mapeada** (cliente IPv4 en socket dual) |

- URL con puerto: `http://[2001:db8::1]:8080/` (corchetes).
- La tupla de dirección IPv6 tiene **4 campos**: `(host, puerto, flowinfo, scope_id)`.
  ⚠️ `host, puerto = sock.getsockname()` **se rompe** → usá `info[0], info[1]`.
- **Cliente:** `getaddrinfo()` y probar TODAS las direcciones (o directamente `socket.create_connection()`).
- **Servidor dual-stack:** socket `AF_INET6` en `::` con `IPV6_V6ONLY = 0` **explícito**.
- Cambios del protocolo: encabezado fijo de 40 bytes, sin checksum de red (por eso el de UDP pasa a obligatorio),
  los routers **no fragmentan**, MTU mínimo 1280, y **no se puede bloquear ICMPv6** (hace descubrimiento de vecinos y path MTU).

---

## ❓ Preguntas típicas para autoevaluarte

1. ¿Qué diferencia hay entre `git add` y `git commit`? ¿Para qué existe el staging?
2. ¿Por qué un branch es "barato"?
3. ¿Cuándo usás `action="store_true"` y cuándo `type=int`?
4. ¿Qué pasa con un enlace duro y uno simbólico si borrás el original? ¿Por qué?
5. ¿Qué significa `ctime`? (no es creación)
6. ¿Qué hace `__exit__` si devuelve `True`?
7. ¿Por qué un generador usa memoria constante? ¿Qué agrega `send()`?
8. ¿Por qué hay que poner `IPV6_V6ONLY` explícito y normalizar las `::ffff:`?
