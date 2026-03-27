from functools import wraps
from datetime import datetime


def log_llamada(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Armar string de argumentos
        args_str = ", ".join(repr(a) for a in args)
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
        todos = ", ".join(filter(None, [args_str, kwargs_str]))

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Llamando a {func.__name__}({todos})")

        resultado = func(*args, **kwargs)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {func.__name__} retornó {repr(resultado)}")

        return resultado
    return wrapper


if __name__ == "__main__":
    @log_llamada
    def sumar(a, b):
        return a + b

    @log_llamada
    def saludar(nombre, entusiasta=False):
        sufijo = "!" if entusiasta else "."
        return f"Hola, {nombre}{sufijo}"

    @log_llamada
    def sin_retorno():
        print("  (ejecutando sin_retorno...)")

    print("=== PRUEBAS LOG_LLAMADA ===\n")

    sumar(3, 5)
    print()

    saludar("Ana", entusiasta=True)
    print()

    saludar("Carlos")
    print()

    sin_retorno()