def chunked(iterable, tamanio):
    """
    Generador que divide un iterable en chunks de tamaño fijo.
    El último chunk puede tener menos elementos.
    """
    chunk = []
    for elemento in iterable:
        chunk.append(elemento)
        if len(chunk) == tamanio:
            yield chunk
            chunk = []
    if chunk:  # último chunk si quedaron elementos
        yield chunk


if __name__ == "__main__":
    print("=== PRUEBAS CHUNKED ===\n")

    # Lista de números
    print("range(10) en grupos de 3:")
    print(list(chunked(range(10), 3)))

    # String
    print("\n'abcdefgh' en grupos de 3:")
    print(list(chunked("abcdefgh", 3)))

    # Divisible exacto
    print("\nrange(9) en grupos de 3 (divisible exacto):")
    print(list(chunked(range(9), 3)))

    # Chunk más grande que el iterable
    print("\nrange(3) en grupos de 10:")
    print(list(chunked(range(3), 10)))

    # Caso práctico: procesar líneas en batches
    print("\nSimulando procesamiento de archivo en batches de 2:")
    lineas = ["línea 1", "línea 2", "línea 3", "línea 4", "línea 5"]
    for i, batch in enumerate(chunked(lineas, 2), 1):
        print(f"  Batch {i}: {batch}")