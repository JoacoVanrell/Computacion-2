import argparse
import secrets
import string


LETRAS = string.ascii_letters
NUMEROS = string.digits
SIMBOLOS = "!@#$%&*?"


def generar_password(longitud, con_numeros, con_simbolos):
    pool = LETRAS
    if con_numeros:
        pool += NUMEROS
    if con_simbolos:
        pool += SIMBOLOS

    return "".join(secrets.choice(pool) for _ in range(longitud))


def main():
    parser = argparse.ArgumentParser(description="Generador de contraseñas seguras")

    parser.add_argument("-n", "--length", type=int, default=12,
                        help="Longitud de la contraseña (default: 12)")
    parser.add_argument("--no-numbers", action="store_true",
                        help="Excluir números")
    parser.add_argument("--no-symbols", action="store_true",
                        help="Excluir símbolos especiales")
    parser.add_argument("--count", type=int, default=1,
                        help="Cuántas contraseñas generar (default: 1)")

    args = parser.parse_args()

    if args.length < 4:
        parser.error("La longitud mínima es 4 caracteres")

    con_numeros = not args.no_numbers
    con_simbolos = not args.no_symbols

    for _ in range(args.count):
        print(generar_password(args.length, con_numeros, con_simbolos))


if __name__ == "__main__":
    main()