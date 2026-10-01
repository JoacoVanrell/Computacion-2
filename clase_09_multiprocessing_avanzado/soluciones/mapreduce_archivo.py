#!/usr/bin/env python3
"""Clase 9 · Ej. 6 + extensión: Map-Reduce de conteo de palabras sobre un ARCHIVO GRANDE en chunks.

    python3 mapreduce_archivo.py                         # usa /usr/share/dict o genera un texto
    python3 mapreduce_archivo.py mi_libro.txt --workers 4 --top 15

Map:    cada worker recibe un CHUNK de líneas y devuelve un Counter.
Reduce: se suman los Counters (Counter + Counter suma las cuentas).
"""
import argparse
import os
import random
import re
import time
from collections import Counter
from functools import reduce
from itertools import islice
from multiprocessing import Pool

PALABRA = re.compile(r"[a-záéíóúñü]+")


def mapper(lineas):
    c = Counter()
    for linea in lineas:
        c.update(PALABRA.findall(linea.lower()))
    return c


def chunks(ruta, tam):
    """Generador: no carga el archivo entero, va leyendo de a `tam` líneas."""
    with open(ruta, encoding="utf-8", errors="replace") as f:
        while bloque := list(islice(f, tam)):
            yield bloque


def generar_texto(ruta, lineas=200_000):
    vocab = ("el zorro perro salta rápido árbol corre duerme sobre bajo viento mira juega "
             "viejo curiosidad marrón perezoso proceso hilo socket señal pipe").split()
    rnd = random.Random(42)
    with open(ruta, "w") as f:
        for _ in range(lineas):
            f.write(" ".join(rnd.choices(vocab, k=12)) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--chunk", type=int, default=10_000, help="líneas por tarea")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    ruta = a.archivo or "/tmp/texto_grande.txt"
    if not a.archivo and not os.path.exists(ruta):
        generar_texto(ruta)
    print(f"Archivo: {ruta} ({os.path.getsize(ruta) / 1e6:.1f} MB)")

    t0 = time.perf_counter()
    secuencial = reduce(lambda x, y: x + y, map(mapper, chunks(ruta, a.chunk)), Counter())
    t_seq = time.perf_counter() - t0

    t0 = time.perf_counter()
    with Pool(a.workers) as pool:
        # imap_unordered: no importa el orden en que vuelven los chunks (sumar es conmutativo)
        parciales = pool.imap_unordered(mapper, chunks(ruta, a.chunk))
        total = reduce(lambda x, y: x + y, parciales, Counter())   # reduce va consumiendo a medida que llegan
    t_par = time.perf_counter() - t0

    assert total == secuencial
    print(f"Secuencial {t_seq:.2f}s · Pool({a.workers}) {t_par:.2f}s · speedup {t_seq / t_par:.2f}x")
    print(f"\nTop {a.top} de {len(total)} palabras distintas ({sum(total.values())} en total):")
    for palabra, n in total.most_common(a.top):
        print(f"  {palabra:<15} {n}")


if __name__ == "__main__":
    main()
