#!/usr/bin/env python3
"""Clase 9 · Ej. 5 (OBLIGATORIO): procesador de imágenes paralelo con Pool.map.

    python3 procesador_imagenes.py                       # 8 imágenes 400x400, 4 workers
    python3 procesador_imagenes.py --imagenes 16 --size 300 --workers 2

Sobre el esqueleto agrega:
  - verificación: el resultado paralelo es IDÉNTICO al secuencial (mismos checksums)
  - prueba con distintas cantidades de workers para ver hasta dónde escala
  - eficiencia = speedup / workers (1.0 = escalado perfecto)
"""
import argparse
import os
import random
import time
from multiprocessing import Pool


def crear_imagen(size, semilla):
    rnd = random.Random(semilla)                      # semilla fija → imágenes reproducibles
    return [[rnd.randint(0, 255) for _ in range(size)] for _ in range(size)]


def aplicar_filtro(img):
    """Blur 3x3: cada pixel = promedio de sus 9 vecinos (bordes quedan en 0)."""
    n = len(img)
    out = [[0] * n for _ in range(n)]
    for i in range(1, n - 1):
        arriba, fila, abajo = img[i - 1], img[i], img[i + 1]
        for j in range(1, n - 1):
            out[i][j] = (arriba[j - 1] + arriba[j] + arriba[j + 1] +
                         fila[j - 1] + fila[j] + fila[j + 1] +
                         abajo[j - 1] + abajo[j] + abajo[j + 1]) // 9
    return out


def procesar_imagen(args):
    """Recibe UNA tupla (Pool.map pasa un solo argumento) y devuelve métricas, no la imagen
    entera: devolver la imagen implicaría serializarla con pickle de vuelta al padre."""
    idx, img = args
    t0 = time.perf_counter()
    res = aplicar_filtro(img)
    return idx, time.perf_counter() - t0, sum(map(sum, res)), os.getpid()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--imagenes", type=int, default=8)
    ap.add_argument("--size", type=int, default=400)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()

    print(f"Creando {a.imagenes} imágenes de {a.size}x{a.size}… (CPUs: {os.cpu_count()})")
    imagenes = [(i, crear_imagen(a.size, i)) for i in range(a.imagenes)]

    t0 = time.perf_counter()
    secuencial = [procesar_imagen(img) for img in imagenes]
    t_seq = time.perf_counter() - t0
    print(f"\nSecuencial: {t_seq:.2f}s")

    for w in sorted({1, 2, a.workers}):
        t0 = time.perf_counter()
        with Pool(w) as pool:
            paralelo = pool.map(procesar_imagen, imagenes)
        t_par = time.perf_counter() - t0
        ok = [r[2] for r in paralelo] == [r[2] for r in secuencial]
        pids = len({r[3] for r in paralelo})
        speedup = t_seq / t_par
        print(f"Pool({w}): {t_par:.2f}s  speedup {speedup:.2f}x  eficiencia {speedup / w:.0%}  "
              f"procesos usados {pids}  resultado {'idéntico ✓' if ok else 'DISTINTO ✗'}")

    print("\nDetalle por imagen (último pool):")
    for idx, dur, checksum, pid in paralelo:
        print(f"  imagen {idx}: {dur:.3f}s  checksum {checksum}  (PID {pid})")


if __name__ == "__main__":
    main()
