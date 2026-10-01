import time
from contextlib import contextmanager


# Implementación 1: como clase
class Timer:
    def __init__(self, nombre=None):
        self.nombre = nombre
        self.elapsed = 0.0
        self._inicio = None

    def __enter__(self):
        self._inicio = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = time.time() - self._inicio
        if self.nombre:
            print(f"[Timer] {self.nombre}: {self.elapsed:.3f}s")


# Implementación 2: con @contextmanager
@contextmanager
def timer(nombre=None):
    inicio = time.time()
    class _T:
        elapsed = 0.0
    t = _T()
    try:
        yield t
    finally:
        t.elapsed = time.time() - inicio
        if nombre:
            print(f"[Timer] {nombre}: {t.elapsed:.3f}s")


if __name__ == "__main__":
    print("=== PRUEBAS TIMER ===")

    # Con nombre
    with Timer("Lista de cuadrados"):
        datos = [x**2 for x in range(1000000)]

    # Sin nombre, accedemos a elapsed
    with Timer() as t:
        time.sleep(0.3)
    print(f"El bloque tardó {t.elapsed:.3f} segundos")

    # Acceso durante el bloque
    with Timer() as t:
        time.sleep(0.1)
        print(f"Después del paso 1: {t.elapsed:.3f}s")
        time.sleep(0.1)
        print(f"Después del paso 2: {t.elapsed:.3f}s")