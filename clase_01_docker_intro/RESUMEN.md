# Clase 1 — Docker: introducción · Resumen

## La idea en una frase
Docker empaqueta tu programa **con todo su entorno** (Python, librerías, sistema de archivos)
para que corra **igual en cualquier máquina**. Chau "en mi máquina anda".

## VM vs contenedor

```
     MÁQUINA VIRTUAL                         CONTENEDOR
 ┌───────────┬───────────┐           ┌─────────┬─────────┬─────────┐
 │  App A    │  App B    │           │  App A  │  App B  │  App C  │
 │  SO + KERNEL propio   │           │  libs   │  libs   │  libs   │
 ├───────────┴───────────┤           ├─────────┴─────────┴─────────┤
 │      hipervisor       │           │     Docker (aislamiento)    │
 │      hardware         │           │   KERNEL DEL HOST (uno solo)│
 └───────────────────────┘           └─────────────────────────────┘
   GB, arranca en minutos               MB, arranca en segundos
```

- **VM** = casa completa con cimientos propios. **Contenedor** = departamento: paredes propias, estructura compartida.
- El contenedor **comparte el kernel** del host. Por eso `uname -r` da lo mismo adentro y afuera.

## Imagen vs contenedor (¡no confundir!)

| | Imagen | Contenedor |
|---|---|---|
| Qué es | receta / plano **inmutable** | instancia **corriendo** de una imagen |
| Analogía | receta de la torta | la torta horneada |
| Cuántos | una | muchos desde la misma imagen |

- Las imágenes viven en un **registry** (Docker Hub). `docker run python` la baja si no la tenés.
- **Tags** = versiones: `python:3.11`, `python:3.11-slim` (liviana), `python:3.11-alpine` (mínima).
- **Dockerfile** = el archivo que describe cómo construir una imagen (clase 2).

## Comandos que tenés que saber de memoria

| Comando | Para qué |
|---|---|
| `docker run -it ubuntu bash` | contenedor interactivo (`-i` stdin abierto, `-t` terminal) |
| `docker run --rm imagen cmd` | corre y **borra** el contenedor al terminar |
| `docker run -d --name web imagen` | en background (daemon) |
| `docker ps` / `docker ps -a` | corriendo / todos |
| `docker images` | imágenes descargadas |
| `docker stop` · `start` · `rm` · `rmi` | parar, arrancar, borrar contenedor, borrar imagen |
| `docker logs -f nombre` | ver la salida |
| `docker system prune -a` | limpieza general |

### Correr TU script de Python en Docker
```bash
docker run --rm -v "$(pwd)":/app -w /app python:3.11 python mi_script.py
#               └ bind mount ┘  └ workdir ┘  └ imagen ┘ └── comando ──┘
```

## Contenedores efímeros
Todo lo que cambiás adentro **se pierde** al crear otro contenedor: cada `docker run` arranca de la imagen limpia.
Es a propósito (reproducibilidad). Para persistir: **volúmenes** o **construir otra imagen** (clase 2).

## Errores comunes
- *Cannot connect to the Docker daemon* → `sudo systemctl start docker`.
- *Permission denied* → `sudo usermod -aG docker $USER` y volver a iniciar sesión.
- *El contenedor termina al instante* → no tiene nada que hacer: usá `-it`, un comando o `-d`.
- *ModuleNotFoundError* dentro del contenedor → la imagen base no tiene esa librería → Dockerfile.

## ❓ Autoevaluación
1. ¿Por qué un contenedor arranca más rápido que una VM?
2. ¿Qué diferencia hay entre imagen y contenedor?
3. ¿Qué hacen `-i`, `-t`, `-d`, `--rm`, `-v` y `-w`?
4. Si instalo algo dentro de un contenedor y salgo, ¿está la próxima vez? ¿Por qué?
