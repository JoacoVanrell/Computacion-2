# Clase 2 — Ejercicios resueltos

> Material de estudio armado con Claude. Tus versiones están en `../mi_trabajo/`.

## Ejercicio 5 — Proyecto integrador (`proyecto_integrador/`)

```
proyecto_integrador/
├── docker-compose.yml     web + worker + redis (con volumen)
├── web/      server.py    GET / → JSON con el contador (http.server de la stdlib)
└── worker/   worker.py    incrementa "contador" en Redis cada segundo
```

```bash
cd proyecto_integrador
docker compose up --build        # Ctrl+C para cortar
curl localhost:8000              # o abrilo en el navegador
docker compose logs -f worker
docker compose down              # el contador sigue la próxima vez
docker compose down -v           # borra el volumen → vuelve a 0
```

**Decisiones que te pueden preguntar:**
- `web` escucha en `0.0.0.0` y no en `127.0.0.1`: dentro del contenedor, `127.0.0.1` es *el propio contenedor*;
  el tráfico que entra por `-p 8000:8000` llega por la interfaz de red, no por loopback.
- `worker` y `redis` **no** publican puertos: entre servicios de la misma red se ven directo por nombre (`redis:6379`).
- El worker reintenta `ping()` porque `depends_on` solo ordena el **arranque**; no espera a que Redis esté listo.
- `python -u` para que los `print` salgan al instante en los logs (sin buffer).
- En el Dockerfile se copia `requirements.txt` **antes** que el código → si cambiás solo el código no se reinstala nada (caché de capas).

## Respuestas de los ejercicios 1–4

- **1.1 Bind mount:** si editás el archivo en tu editor, el contenedor ve el cambio al instante (es la misma carpeta).
- **1.2 Named volume:** el dato sobrevive aunque el contenedor se borre; vive en `/var/lib/docker/volumes/...`.
- **2.1 Comunicación entre contenedores:** en la red `bridge` por defecto **no hay DNS por nombre**;
  en una red creada con `docker network create` sí (`ping redis` anda).
- **3.3 Optimización del Dockerfile:** ordenar de lo que menos cambia a lo que más cambia; usar `-slim`;
  `--no-cache-dir`; `.dockerignore` para no copiar `.git`, `venv`, `__pycache__`.
- **4.1 ¿El contador sigue o arranca de 0 al volver a levantar?**
  Si solo hacés Ctrl+C y `up`, **sigue** (el contenedor de Redis se detuvo pero no se borró).
  Si hacés `docker compose down`, **arranca de 0**: se borró el contenedor y con él sus datos.
- **4.2 Con el volumen `redis-data` y `--appendonly yes`:** después de `down` + `up` **continúa**,
  porque los datos están en el volumen, que `down` no borra (salvo `down -v`).
- **4.3 Hot reload:** con `- .:/app` el código del contenedor es tu carpeta; basta reiniciar el servicio
  (`docker compose restart app`) para que Python lea el archivo nuevo.

> ⚠️ Docker no estaba disponible en mi entorno: probé `server.py` y `worker.py` con un Redis simulado
> (fakeredis) y funcionan; los `docker compose` corrélos vos.
