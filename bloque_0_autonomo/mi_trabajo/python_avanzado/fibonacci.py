def fibonacci(limite=None):
    """
    Generador de la secuencia de Fibonacci.
    Sin límite: secuencia infinita.
    Con límite: genera hasta el último número <= límite.
    """
    a, b = 0, 1
    while True:
        if limite is not None and a > limite:
            return
        yield a
        a, b = b, a + b


if __name__ == "__main__":
    print("=== PRUEBAS FIBONACCI ===\n")

    # Secuencia infinita - primeros 10
    print("Primeros 10 números:")
    fib = fibonacci()
    for _ in range(10):
        print(next(fib), end=" ")
    print()

    # Seguimos desde donde quedó
    print(f"\nSiguientes 2: {next(fib)}, {next(fib)}")

    # Con límite
    print("\nSecuencia hasta 100:")
    print(list(fibonacci(limite=100)))

    # Con límite grande
    print("\nSecuencia hasta 1000:")
    print(list(fibonacci(limite=1000)))

    # Demostración de eficiencia de memoria
    print("\nSuma de los primeros 50 números de Fibonacci:")
    print(sum(x for _, x in zip(range(50), fibonacci())))