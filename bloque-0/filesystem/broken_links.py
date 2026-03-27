import argparse
import os
from pathlib import Path


def buscar_enlaces_rotos(directorio):
    rotos = []
    for ruta, dirs, archivos in os.walk(directorio):
        for nombre in dirs + archivos:
            entrada = Path(ruta) / nombre
            if entrada.is_symlink() and not entrada.exists():
                destino = os.readlink(entrada)
                rotos.append((entrada, destino))
    return rotos


def main():
    parser = argparse.ArgumentParser(description="Detector de enlaces simbólicos rotos")

    parser.add_argument("directorio", nargs="?", default=".",
                        help="Directorio a buscar (default: actual)")
    parser.add_argument("--delete", action="store_true",
                        help="Ofrecer borrar los enlaces rotos")
    parser.add_argument("--quiet", action="store_true",
                        help="Solo mostrar el conteo")

    args = parser.parse_args()

    if not Path(args.directorio).is_dir():
        parser.error(f"'{args.directorio}' no es un directorio válido")

    rotos = buscar_enlaces_rotos(args.directorio)

    if args.quiet:
        print(len(rotos))
        return

    if not rotos:
        print("No se encontraron enlaces rotos.")
        return

    print(f"Buscando enlaces simbólicos rotos en {args.directorio}...\n")
    print("Enlaces rotos encontrados:")
    for enlace, destino in rotos:
        print(f"  {enlace} -> {destino} (no existe)")

    print(f"\nTotal: {len(rotos)} enlaces rotos")

    if args.delete:
        print()
        for enlace, destino in rotos:
            respuesta = input(f"¿Eliminar {enlace}? [s/N] ")
            if respuesta.lower() == "s":
                enlace.unlink()
                print(f"  Eliminado: {enlace}")
            else:
                print(f"  Omitido: {enlace}")


if __name__ == "__main__":
    main()