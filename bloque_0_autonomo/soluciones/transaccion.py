#!/usr/bin/env python3
"""Bloque 0 · Python avanzado · Ejercicio 3.2: Transacciones con context manager.

Idea: al ENTRAR al `with` sacamos una "foto" de los atributos del objeto.
Al SALIR, si hubo excepción, restauramos la foto. Si no, no tocamos nada.

    python3 transaccion.py
"""
import copy


class Transaction:
    """Revierte TODOS los atributos de `obj` si el bloque lanza una excepción."""

    def __init__(self, obj):
        self.obj = obj
        self._foto = None

    def __enter__(self):
        # deepcopy: si un atributo es una lista y la modificás con .append(),
        # una copia superficial (vars(obj).copy()) guardaría LA MISMA lista
        # y no podríamos deshacer el cambio.
        self._foto = copy.deepcopy(vars(self.obj))
        return self.obj

    def __exit__(self, tipo_exc, valor_exc, tb):
        if tipo_exc is not None:
            estado = vars(self.obj)
            estado.clear()                 # borra también atributos NUEVOS creados en el bloque
            estado.update(self._foto)      # y vuelve a la foto
        return False                       # False = la excepción se sigue propagando


class Cuenta:
    def __init__(self, saldo):
        self.saldo = saldo
        self.nombre = "Sin nombre"
        self.movimientos = []


if __name__ == "__main__":
    cuenta = Cuenta(1000)

    with Transaction(cuenta):
        cuenta.saldo -= 100
        cuenta.saldo -= 200
        cuenta.movimientos.append(-300)
    print("Después de la transacción OK:", cuenta.saldo, cuenta.movimientos)   # 700 [-300]

    try:
        with Transaction(cuenta):
            cuenta.saldo -= 100
            cuenta.nombre = "Test"
            cuenta.movimientos.append(-100)
            cuenta.atributo_nuevo = 123
            raise ValueError("Error simulado")
    except ValueError as e:
        print("Falló:", e)

    print("Después de la transacción fallida:", cuenta.saldo, cuenta.nombre, cuenta.movimientos)
    assert cuenta.saldo == 700
    assert cuenta.nombre == "Sin nombre"
    assert cuenta.movimientos == [-300]
    assert not hasattr(cuenta, "atributo_nuevo")
    print("✓ todo se revirtió")
