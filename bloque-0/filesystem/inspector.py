import os
import stat
import sys
from datetime import datetime
from pathlib import Path

try:
    import pwd
    import grp
    UNIX = True
except ImportError:
    UNIX = False


def obtener_tipo(modo, ruta):
    if stat.S_ISREG(modo):
        return "archivo regular"
    elif stat.S_ISDIR(modo):
        return "directorio"
    elif stat.S_ISLNK(modo):
        destino = os.readlink(ruta)
        return f"enlace simbólico -> {destino}"
    elif stat.S_ISCHR(modo):
        return "dispositivo de caracteres"
    elif stat.S_ISBLK(modo):
        return "dispositivo de bloques"
    elif stat.S_ISFIFO(modo):
        return "pipe (FIFO)"
    elif stat.S_ISSOCK(modo):
        return "socket"
    else:
        return "desconocido"


def permisos_legibles(modo):
    permisos = ""
    for quien in ["USR", "GRP", "OTH"]:
        permisos += "r" if modo & getattr(stat, f"S_IR{quien}") else "-"
        permisos += "w" if modo & getattr(stat, f"S_IW{quien}") else "-"
        permisos += "x" if modo & getattr(stat, f"S_IX{quien}") else "-"
    return permisos


def permisos_octal(modo):
    return oct(stat.S_IMODE(modo))[2:]


def tamanio_legible(bytes_):
    if bytes_ < 1024:
        return f"{bytes_} bytes"
    elif bytes_ < 1024 ** 2:
        return f"{bytes_} bytes ({bytes_ / 1024:.2f} KB)"
    elif bytes_ < 1024 ** 3:
        return f"{bytes_} bytes ({bytes_ / 1024 ** 2:.2f} MB)"
    else:
        return f"{bytes_} bytes ({bytes_ / 1024 ** 3:.2f} GB)"


def formatear_fecha(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def obtener_propietario(uid, gid):
    if UNIX:
        try:
            usuario = pwd.getpwuid(uid).pw_name
        except KeyError:
            usuario = str(uid)
        try:
            grupo = grp.getgrgid(gid).gr_name
        except KeyError:
            grupo = str(gid)
    else:
        usuario = str(uid)
        grupo = str(gid)
    return usuario, grupo


def inspeccionar(ruta_str):
    ruta = Path(ruta_str)

    if not ruta.exists() and not ruta.is_symlink():
        print(f"Error: '{ruta_str}' no existe.")
        sys.exit(1)

    info = ruta.lstat()
    modo = info.st_mode

    tipo = obtener_tipo(modo, ruta_str)
    perms = permisos_legibles(modo)
    octal = permisos_octal(modo)
    usuario, grupo = obtener_propietario(info.st_uid, info.st_gid)

    print(f"Archivo:             {ruta_str}")
    print(f"Tipo:                {tipo}")
    print(f"Tamaño:              {tamanio_legible(info.st_size)}")
    print(f"Permisos:            {perms} ({octal})")
    print(f"Propietario:         {usuario} (uid: {info.st_uid})")
    print(f"Grupo:               {grupo} (gid: {info.st_gid})")
    print(f"Inodo:               {info.st_ino}")
    print(f"Enlaces duros:       {info.st_nlink}")
    print(f"Última modificación: {formatear_fecha(info.st_mtime)}")
    print(f"Último acceso:       {formatear_fecha(info.st_atime)}")

    if stat.S_ISDIR(modo):
        try:
            contenido = list(ruta.iterdir())
            print(f"Contenido:           {len(contenido)} elementos")
        except PermissionError:
            print("Contenido:           (sin permisos para listar)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Uso: python3 inspector.py <ruta>")
        sys.exit(1)

    inspeccionar(sys.argv[1])