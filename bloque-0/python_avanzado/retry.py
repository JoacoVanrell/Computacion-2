import time
import random
from functools import wraps


def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_error = None
            for intento in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    ultimo_error = e
                    if intento < max_attempts:
                        print(f"Intento {intento}/{max_attempts} falló: {e}. Esperando {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"Intento {intento}/{max_attempts} falló: {e}.")
            raise ultimo_error
        return wrapper
    return decorador


if __name__ == "__main__":
    print("=== PRUEBAS RETRY ===")

    @retry(max_attempts=3, delay=0.5)
    def conectar_servidor():
        if random.random() < 0.7:
            raise ConnectionError("Servidor no disponible")
        return "Conectado exitosamente"

    try:
        resultado = conectar_servidor()
        print(resultado)
    except ConnectionError:
        print("Falló después de 3 intentos")

    print()

    @retry(max_attempts=2, delay=0.2, exceptions=(ValueError,))
    def solo_valida():
        raise ValueError("Error de validación")

    try:
        solo_valida()
    except ValueError:
        print("Falló con ValueError después de 2 intentos")