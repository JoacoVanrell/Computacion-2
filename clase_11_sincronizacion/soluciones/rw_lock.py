#!/usr/bin/env python3
"""Clase 11 · Ej. 5 (OBLIGATORIO): Readers-Writers lock con Condition… y verificado.

    python3 rw_lock.py                      # preferencia a escritores (sin starvation de escritores)
    python3 rw_lock.py --preferir lectores  # la versión del esqueleto (escritores pueden morir de hambre)

Reglas: muchos lectores a la vez · un solo escritor · nunca lector y escritor juntos.

Mejoras sobre el esqueleto:
 1. PREFERENCIA A ESCRITORES: si hay un escritor ESPERANDO, los lectores nuevos no entran.
    Con el esqueleto, un chorro continuo de lectores puede dejar al escritor esperando para siempre.
 2. VERIFICACIÓN: un "auditor" registra cuántos lectores/escritores hay ADENTRO en cada instante
    y chequea las reglas (assert). También mide el máximo de lectores simultáneos (prueba de que
    de verdad leen en paralelo).
 3. Bug del esqueleto: `datos["lecturas"] += 1` DENTRO del read-lock es una race (varios lectores
    entran juntos y modifican lo mismo). Leer es compartido; ESCRIBIR un contador no. Lo protejo aparte.
"""
import argparse
import random
import threading
import time
from contextlib import contextmanager


class ReadWriteLock:
    def __init__(self, preferir_escritores=True):
        self._lock = threading.Lock()
        self._puede_leer = threading.Condition(self._lock)      # dos Conditions sobre el MISMO lock
        self._puede_escribir = threading.Condition(self._lock)
        self._lectores = 0                 # leyendo ahora
        self._escribiendo = False          # hay un escritor adentro
        self._escritores_esperando = 0
        self._pref_esc = preferir_escritores

    def acquire_read(self):
        with self._lock:
            # while (no if): al despertar hay que volver a chequear (spurious wakeups / otro se adelantó)
            while self._escribiendo or (self._pref_esc and self._escritores_esperando > 0):
                self._puede_leer.wait()
            self._lectores += 1

    def release_read(self):
        with self._lock:
            self._lectores -= 1
            if self._lectores == 0:
                self._puede_escribir.notify()        # el último lector deja pasar a UN escritor

    def acquire_write(self):
        with self._lock:
            self._escritores_esperando += 1
            while self._escribiendo or self._lectores > 0:
                self._puede_escribir.wait()
            self._escritores_esperando -= 1
            self._escribiendo = True

    def release_write(self):
        with self._lock:
            self._escribiendo = False
            if self._pref_esc and self._escritores_esperando:
                self._puede_escribir.notify()        # sigue otro escritor
            else:
                self._puede_leer.notify_all()        # o entran TODOS los lectores que esperaban
                self._puede_escribir.notify()

    @contextmanager
    def lectura(self):
        self.acquire_read()
        try:
            yield
        finally:
            self.release_read()

    @contextmanager
    def escritura(self):
        self.acquire_write()
        try:
            yield
        finally:
            self.release_write()


class Auditor:
    """Lleva la cuenta de quién está adentro y verifica las reglas en cada entrada."""
    def __init__(self):
        self.l = threading.Lock()
        self.lectores = self.escritores = 0
        self.max_lectores = 0
        self.violaciones = 0

    def entra(self, es_escritor):
        with self.l:
            if es_escritor:
                self.escritores += 1
            else:
                self.lectores += 1
                self.max_lectores = max(self.max_lectores, self.lectores)
            if self.escritores > 1 or (self.escritores and self.lectores):
                self.violaciones += 1

    def sale(self, es_escritor):
        with self.l:
            if es_escritor:
                self.escritores -= 1
            else:
                self.lectores -= 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preferir", choices=["escritores", "lectores"], default="escritores")
    ap.add_argument("--lectores", type=int, default=6)
    ap.add_argument("--escritores", type=int, default=2)
    a = ap.parse_args()

    rw = ReadWriteLock(preferir_escritores=a.preferir == "escritores")
    auditor = Auditor()
    datos = {"valor": 0}
    contadores = {"lecturas": 0, "escrituras": 0}
    lock_contadores = threading.Lock()
    espera_escritores = []

    def lector(i):
        for _ in range(8):
            with rw.lectura():
                auditor.entra(False)
                _ = datos["valor"]
                time.sleep(random.uniform(0.02, 0.06))
                auditor.sale(False)
            with lock_contadores:
                contadores["lecturas"] += 1
            time.sleep(random.uniform(0.0, 0.02))

    def escritor(i):
        for k in range(3):
            t0 = time.perf_counter()
            with rw.escritura():
                espera_escritores.append(time.perf_counter() - t0)
                auditor.entra(True)
                datos["valor"] = i * 100 + k
                time.sleep(random.uniform(0.02, 0.05))
                auditor.sale(True)
            with lock_contadores:
                contadores["escrituras"] += 1
            time.sleep(random.uniform(0.05, 0.1))

    hilos = [threading.Thread(target=lector, args=(i,)) for i in range(a.lectores)]
    hilos += [threading.Thread(target=escritor, args=(i,)) for i in range(a.escritores)]
    random.shuffle(hilos)
    t0 = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    print(f"Preferencia: {a.preferir}  ·  tiempo total {time.perf_counter() - t0:.2f}s")
    print(f"Lecturas {contadores['lecturas']} (esperadas {a.lectores * 8}) · "
          f"escrituras {contadores['escrituras']} (esperadas {a.escritores * 3})")
    print(f"Máximo de lectores leyendo A LA VEZ: {auditor.max_lectores}   ← >1 prueba que leen en paralelo")
    print(f"Violaciones de las reglas: {auditor.violaciones}")
    print(f"Espera de los escritores: prom {sum(espera_escritores) / len(espera_escritores) * 1000:.0f} ms · "
          f"máx {max(espera_escritores) * 1000:.0f} ms")
    assert auditor.violaciones == 0


if __name__ == "__main__":
    main()
