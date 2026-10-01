import argparse
import sys
import re

def buscar_en_texto(lineas, patron, ignorar_case, invertir, mostrar_numero, prefijo=""):
    """Busca el patrón en una lista de líneas y devuelve los resultados."""
    resultados = []
    flags = re.IGNORECASE if ignorar_case else 0

    for num, linea in enumerate(lineas, start=1):
        linea = linea.rstrip("\n")
        coincide = bool(re.search(patron, linea, flags))

        # -v invierte la lógica: queremos las que NO coinciden
        if coincide != invertir:
            if mostrar_numero and prefijo:
                resultados.append(f"{prefijo}:{num}: {linea}")
            elif mostrar_numero:
                resultados.append(f"{num}: {linea}")
            elif prefijo:
                resultados.append(f"{prefijo}: {linea}")
            else:
                resultados.append(linea)

    return resultados

def main():
    parser = argparse.ArgumentParser(
        description="Busca un patrón en archivos (mini-grep)"
    )

    parser.add_argument("patron", help="Patrón a buscar")
    parser.add_argument("archivos", nargs="*", help="Archivos donde buscar (opcional)")
    parser.add_argument("-i", "--ignore-case", action="store_true",
                        help="Búsqueda insensible a mayúsculas")
    parser.add_argument("-n", "--line-number", action="store_true",
                        help="Mostrar número de línea")
    parser.add_argument("-c", "--count", action="store_true",
                        help="Solo mostrar conteo de coincidencias")
    parser.add_argument("-v", "--invert", action="store_true",
                        help="Mostrar líneas que NO coinciden")

    args = parser.parse_args()

    # Si hay múltiples archivos, mostrar nombre de archivo por defecto
    mostrar_prefijo = len(args.archivos) > 1

    total_coincidencias = 0

    # --- Caso 1: leer de stdin (pipe) ---
    if not args.archivos:
        if sys.stdin.isatty():
            parser.error("Debés especificar al menos un archivo o usar con pipe.")
        lineas = sys.stdin.readlines()
        resultados = buscar_en_texto(
            lineas, args.patron, args.ignore_case, args.invert, args.line_number
        )
        if args.count:
            print(f"{len(resultados)} coincidencias")
        else:
            print("\n".join(resultados))
        return

    # --- Caso 2: uno o más archivos ---
    for archivo in args.archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                lineas = f.readlines()
        except FileNotFoundError:
            print(f"Error: No se puede leer '{archivo}'", file=sys.stderr)
            continue
        except PermissionError:
            print(f"Error: Sin permisos para leer '{archivo}'", file=sys.stderr)
            continue

        prefijo = archivo if mostrar_prefijo else ""
        resultados = buscar_en_texto(
            lineas, args.patron, args.ignore_case, args.invert,
            args.line_number or mostrar_prefijo, prefijo
        )

        if args.count:
            print(f"{archivo}: {len(resultados)} coincidencias")
            total_coincidencias += len(resultados)
        else:
            print("\n".join(resultados))

    if args.count and mostrar_prefijo:
        print(f"Total: {total_coincidencias} coincidencias")

if __name__ == "__main__":
    main()