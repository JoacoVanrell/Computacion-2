import argparse
import os
import re
from pathlib import Path


def parsear_tamanio(texto):
    """Convierte '1M', '500K', '2G' a bytes."""
    match = re.match(r"^(\d+(?:\.\d+)?)([KMG]?)$", texto.upper())
    if not match:
        raise argparse.ArgumentTypeError(f"Tamaño inválido: '{texto}'. Usá ej: 100K, 1M, 2G")
    valor, unidad = float(match.group(1)), match.group(2)
    multiplicadores = {"K": 1024, "M": 1024**2, "G": 1024**3, "": 1}
    return int(valor * multiplicadores[unidad])


def tamanio_legible(bytes_):
    """Convierte bytes a formato legible."""
    for unidad, divisor in [("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)]:
        if bytes_ >= divisor:
            return f"{bytes_ / divisor:.1f} {unidad}"
    return f"{bytes_} bytes"


def buscar_archivos(directorio, min_size, tipo, top):
    resultados = []

    for ruta, dirs, archivos in os.walk(directorio):
        entradas = []

        if tipo == "f" or tipo is None:
            entradas += [Path(ruta) / a for a in archivos]
        if tipo == "d" or tipo is None:
            entradas += [Path(ruta) / d for d in dirs]

        for entrada in entradas:
            try:
                tamanio = entrada.stat().st_size
                if tamanio >= min_size:
                    resultados.append((entrada, tamanio))
            except (PermissionError, FileNotFoundError):
                continue

    # Ordenar de mayor a menor
    resultados.sort(key=lambda x: x[1], reverse=True)

    if top:
        return resultados[:top]
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Buscador de archivos grandes")

    parser.add_argument("directorio", nargs="?", default=".",
                        help="Directorio a buscar (default: actual)")
    parser.add_argument("--min-size", type=parsear_tamanio, default="1M",
                        help="Tamaño mínimo (ej: 100K, 1M, 2G). Default: 1M")
    parser.add_argument("--type", choices=["f", "d"], dest="tipo",
                        help="Filtrar por tipo: f=archivo, d=directorio")
    parser.add_argument("--top", type=int,
                        help="Mostrar solo los N más grandes")

    args = parser.parse_args()

    if not Path(args.directorio).is_dir():
        parser.error(f"'{args.directorio}' no es un directorio válido")

    resultados = buscar_archivos(args.directorio, args.min_size, args.tipo, args.top)

    if not resultados:
        print("No se encontraron archivos que cumplan los criterios.")
        return

    if args.top:
        print(f"Los {args.top} archivos más grandes:")
        for i, (ruta, tamanio) in enumerate(resultados, 1):
            print(f"  {i}. {ruta} ({tamanio_legible(tamanio)})")
    else:
        for ruta, tamanio in resultados:
            print(f"{ruta} ({tamanio_legible(tamanio)})")

    total = sum(t for _, t in resultados)
    print(f"\nTotal: {len(resultados)} archivos, {tamanio_legible(total)}")


if __name__ == "__main__":
    main()