#!/usr/bin/env python3
"""Clase 7 · Ejercicio de síntesis: banco con cuentas en memoria compartida.

    python3 banco.py                 # sin sincronización → se pierde/aparece plata
    python3 banco.py --seguro        # con lock → el total SIEMPRE se conserva
    python3 banco.py --n 10000       # más transferencias → la race se nota más

Además (tarea 3) cada transferencia queda registrada en un log de texto.
"""
import argparse
import os
import random
from multiprocessing import Array, Lock, Process

NUM_CUENTAS = 5
SALDO_INICIAL = 1000
NUM_CAJEROS = 3


def cajero(cuentas, lock, cid, n, seguro, ruta_log):
    random.seed(os.getpid())
    with open(ruta_log, "a") as log:
        for _ in range(n):
            origen, destino = random.sample(range(NUM_CUENTAS), 2)   # dos cuentas distintas
            monto = random.randint(1, 50)
            if seguro:
                # el CHEQUEO y las DOS escrituras tienen que pasar juntas (sección crítica)
                with lock:
                    if cuentas[origen] >= monto:
                        cuentas[origen] -= monto
                        cuentas[destino] += monto
                        log.write(f"cajero{cid} {origen}->{destino} ${monto}\n")
            else:
                if cuentas[origen] >= monto:
                    cuentas[origen] -= monto          # otro cajero puede meterse ACÁ
                    cuentas[destino] += monto
                    log.write(f"cajero{cid} {origen}->{destino} ${monto}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seguro", action="store_true")
    p.add_argument("--n", type=int, default=2000, help="transferencias por cajero")
    p.add_argument("--log", default="/tmp/banco_transferencias.log")
    a = p.parse_args()

    # lock=False: Array SIN lock interno, para poder ver la race. (Por defecto Array trae un RLock.)
    cuentas = Array("i", [SALDO_INICIAL] * NUM_CUENTAS, lock=False)
    lock = Lock()
    open(a.log, "w").close()

    ps = [Process(target=cajero, args=(cuentas, lock, i, a.n, a.seguro, a.log)) for i in range(NUM_CAJEROS)]
    for pr in ps:
        pr.start()
    for pr in ps:
        pr.join()

    saldos = list(cuentas)
    total, esperado = sum(saldos), NUM_CUENTAS * SALDO_INICIAL
    with open(a.log) as f:
        n_log = sum(1 for _ in f)
    print(f"Saldos finales: {saldos}")
    print(f"Total: {total} (esperado {esperado}) {'✓' if total == esperado else f'✗ diferencia {total - esperado}'}")
    print(f"Transferencias registradas en {a.log}: {n_log}")


if __name__ == "__main__":
    main()
