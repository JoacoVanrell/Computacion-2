"""
Helpers para leer y parsear /proc.
Todo el acceso al kernel pasa por acá: los analizadores no abren archivos.
"""
import os

# Jiffies por segundo: el kernel cuenta el tiempo de CPU en "ticks".
# En Linux moderno son 100, pero se lo preguntamos al sistema.
HZ = os.sysconf('SC_CLK_TCK')


def listar_pids():
    """PIDs vivos: las carpetas numéricas de /proc."""
    return [int(n) for n in os.listdir('/proc') if n.isdigit()]


def leer_stat(pid, tid=None):
    """
    Parsea /proc/<pid>/stat (o /proc/<pid>/task/<tid>/stat si se pasa tid).
    Devuelve un dict, o None si el proceso ya no existe.
    """
    ruta = f'/proc/{pid}/task/{tid}/stat' if tid else f'/proc/{pid}/stat'
    try:
        with open(ruta) as f:
            linea = f.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None

    # OJO: el campo 2 (comm) viene entre paréntesis y puede tener
    # espacios y hasta paréntesis adentro. Si hacés split() a lo bruto,
    # todos los campos siguientes se te corren.
    ini = linea.index('(')
    fin = linea.rindex(')')
    comm = linea[ini + 1:fin]
    resto = linea[fin + 2:].split()

    # resto[0] es el campo 3 del man page => campo N == resto[N - 3]
    def c(n):
        return resto[n - 3]

    return {
        'pid': int(linea[:ini]),
        'comm': comm,
        'estado': c(3),
        'ppid': int(c(4)),
        'pgid': int(c(5)),
        'sid': int(c(6)),
        'minflt': int(c(10)),
        'majflt': int(c(12)),
        'utime': int(c(14)),
        'stime': int(c(15)),
        'priority': int(c(18)),
        'nice': int(c(19)),
        'num_threads': int(c(20)),
        'starttime': int(c(22)),
        'rt_priority': int(c(40)),
        'policy': int(c(41)),
    }


def leer_status(pid, tid=None):
    """
    Parsea /proc/<pid>/status: formato 'Clave:\tvalor'.
    Devuelve dict de strings crudos, o None si el proceso murió.
    """
    ruta = f'/proc/{pid}/task/{tid}/status' if tid else f'/proc/{pid}/status'
    try:
        with open(ruta) as f:
            datos = {}
            for linea in f:
                if ':' in linea:
                    clave, valor = linea.split(':', 1)
                    datos[clave.strip()] = valor.strip()
            return datos
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None


def leer_cmdline(pid):
    """
    /proc/<pid>/cmdline: argumentos separados por bytes nulos.
    Si viene vacío es un kernel thread -> devolvemos [comm].
    """
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            crudo = f.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return ''

    if not crudo:
        st = leer_stat(pid)
        return f'[{st["comm"]}]' if st else ''
    return ' '.join(crudo.decode(errors='replace').split('\0')).strip()


def kb(valor):
    """'1234 kB' -> 1234 (int). Devuelve 0 si no matchea."""
    try:
        return int(valor.split()[0])
    except (ValueError, IndexError, AttributeError):
        return 0


_usuarios = None

def usuario_de_uid(uid):
    """UID -> nombre, leyendo /etc/passwd una sola vez."""
    global _usuarios
    if _usuarios is None:
        _usuarios = {}
        try:
            with open('/etc/passwd') as f:
                for linea in f:
                    partes = linea.split(':')
                    if len(partes) > 2:
                        _usuarios[int(partes[2])] = partes[0]
        except OSError:
            pass
    return _usuarios.get(uid, str(uid))