# Clase 1 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu versión está en `../mi_trabajo/`.

| Archivo | Ejercicio |
|---|---|
| `info_sistema.py` | Ejercicio de síntesis (comparar host vs. contenedores) |
| `con_dependencias/` | Ej. 5.3: la "solución correcta" con Dockerfile |

## Cómo correrlo

```bash
# síntesis: comparar tres entornos
python3 info_sistema.py
docker run --rm -v "$(pwd)":/app -w /app python:3.11 python info_sistema.py
docker run --rm -v "$(pwd)":/app -w /app python:3.9  python info_sistema.py

# ej. 5.3
cd con_dependencias
docker build -t con-deps .
docker run --rm con-deps
```

## Qué tenés que notar en la síntesis

| Dato | Host | Contenedor | Por qué |
|---|---|---|---|
| Versión de Python | la tuya | la del **tag** (3.11 / 3.9) | cada imagen trae su Python |
| Distro (`/etc/os-release`) | Ubuntu | **Debian** (base de la imagen `python`) | el filesystem es el de la imagen |
| Kernel (`uname -r`) | el tuyo | **el mismo** | 👉 los contenedores **comparten el kernel** del host (no son VMs) |
| CPUs / memoria | | casi igual | el contenedor ve el hardware del host (salvo que lo limites con `--cpus`/`--memory`) |
| Hostname | tu PC | un ID raro (`a1b2c3...`) | cada contenedor tiene su propio hostname |
| `PYTHON*` | casi nada | `PYTHON_VERSION`, `PYTHON_SHA256`… | las pone la imagen oficial con `ENV` |

## Respuestas cortas de los ejercicios 1–4

- **1.2 ¿Por qué desaparece lo que instalé?** Cada `docker run` crea un contenedor **nuevo** desde la imagen,
  que es inmutable. Los cambios vivían en la capa escribible de *ese* contenedor.
- **1.3 `docker ps` vs `docker ps -a`:** el primero muestra solo los que están corriendo; `-a` también los detenidos.
- **2.3 Versiones distintas:** con tags (`python:3.9`, `python:3.11-slim`, `-alpine`). `slim` y `alpine` pesan mucho menos.
- **3.3 El montaje:** `-v $(pwd):/app` es un **bind mount**: la misma carpeta vista desde los dos lados.
  Si el script escribe un archivo en `/app`, aparece en tu carpeta.
- **4.1 Background:** `docker run -d --name x ...`, ver salida con `docker logs -f x`, parar con `docker stop x`.
- **4.2 Limpieza:** `docker rm`, `docker container prune`, `docker image prune`, `docker system prune -a`. `--rm` borra el contenedor al terminar.
- **5.2 ¿Por qué no alcanza con `pip install` en el `run`?** Se instala en cada ejecución (lento) y no queda
  documentado qué versión usás. Con un Dockerfile la dependencia queda **dentro de la imagen**.

> ⚠️ En mi entorno no había Docker, así que los comandos de Docker no los pude ejecutar;
> `info_sistema.py` sí lo probé.
