# Clase 2 — Docker aplicado · Resumen

Cuatro herramientas para pasar de "correr un contenedor" a "armar un sistema":
**volúmenes** (persistir), **redes** (comunicar), **Dockerfile** (crear imágenes) y **Compose** (orquestar).

---

## 1. Volúmenes — que los datos no se pierdan

| Tipo | Sintaxis | Uso típico |
|---|---|---|
| **Bind mount** | `-v $(pwd):/app` (`ruta_host:ruta_contenedor`) | código fuente, config (lo editás en tu PC) |
| **Named volume** | `-v mis-datos:/data` | bases de datos, datos que deben sobrevivir |

```bash
docker volume create mis-datos   ·   docker volume ls   ·   docker volume rm mis-datos
```

## 2. Redes — que los contenedores se encuentren

| Driver | Qué hace |
|---|---|
| `bridge` (default) | red virtual interna entre contenedores |
| `host` | usa la red del host directamente (sin aislamiento) |
| `none` | sin red |

- En la `bridge` **por defecto** solo se ven por IP (que cambia).
- En una **red propia** (`docker network create mi-red`) hay **DNS automático**: te conectás a `redis` por nombre.

### `EXPOSE` vs `-p` (pregunta clásica)

| | `EXPOSE 8000` (Dockerfile) | `-p 8000:8000` / `ports:` |
|---|---|---|
| ¿Abre el puerto? | **No**, es solo documentación | **Sí**, mapea `host:contenedor` |

> Entre contenedores de la misma red **no hace falta `-p`**. `-p` es para entrar *desde el host*.

## 3. Dockerfile — tu propia imagen

```dockerfile
FROM python:3.11-slim                 # base (siempre primero)
WORKDIR /app                          # directorio de trabajo
COPY requirements.txt .               # 1º lo que cambia poco...
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                              # ...último el código (cambia seguido)
ENV REDIS_HOST=redis                  # variables de entorno
EXPOSE 8000                           # documenta el puerto
CMD ["python", "-u", "app.py"]        # comando por defecto
```

- `RUN` se ejecuta al **construir**; `CMD` al **correr**.
- **Caché de capas:** cada instrucción es una capa. Si cambiás solo el código, no reinstala dependencias
  (por eso `requirements.txt` va antes que `COPY . .`).
- `.dockerignore` = `.gitignore` del build (`__pycache__`, `.git`, `venv`, `.env`).
- `docker build -t mi-app .` (`.` = contexto de build) → `docker run mi-app`.

## 4. Docker Compose — todo junto con un archivo

```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    volumes: [".:/app"]            # hot reload del código
    environment: [REDIS_HOST=redis]
    depends_on: [redis]            # arranca después de redis (¡no espera a que esté LISTO!)
  redis:
    image: redis:alpine
    volumes: ["redis-data:/data"]
volumes:
  redis-data:
```

Compose crea **una red** para todos los servicios: se llaman por el **nombre del servicio**.

| Comando | |
|---|---|
| `docker compose up` / `up -d` / `up --build` | levantar (foreground / background / reconstruyendo) |
| `docker compose ps` · `logs -f app` | estado · logs |
| `docker compose exec app bash` | entrar a un servicio |
| `docker compose down` | parar y **borrar contenedores** (los volúmenes quedan) |
| `docker compose down -v` | además borra **volúmenes** |

> `docker compose` (sin guión) es el actual; `docker-compose` es el viejo.

## Buenas prácticas
1. Imágenes `-slim` · 2. instrucciones ordenadas por frecuencia de cambio · 3. **un proceso por contenedor** ·
4. **nunca secretos en la imagen** (pasalos con `-e` en runtime).

## ❓ Autoevaluación
1. ¿Cuándo usás bind mount y cuándo named volume?
2. ¿Por qué en la red bridge por defecto no podés hacer `ping redis`?
3. ¿`EXPOSE` publica el puerto? ¿Qué hace `-p 9999:6379`?
4. ¿Por qué `COPY requirements.txt` va antes que `COPY . .`?
5. Después de `docker compose down`, ¿se pierden los datos de Redis? ¿Y con un named volume? ¿Y con `down -v`?
6. ¿`depends_on` garantiza que la base esté lista para recibir conexiones?
