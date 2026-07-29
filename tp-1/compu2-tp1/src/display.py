"""
Display: TUI en curses. Corre en el proceso principal (no es un
Process aparte) porque necesita control exclusivo de la terminal.
"""
import curses
import time


def _sin_datos(stdscr):
    stdscr.erase()
    stdscr.addstr(0, 0, 'esperando datos...')
    stdscr.refresh()


def _encabezado(stdscr, entrada, titulo):
    edad = time.time() - entrada['ts']
    stdscr.addstr(0, 0, f'{titulo} - {len(entrada["datos"])} procesos - dato de hace {edad:.1f}s')


def _fila(stdscr, y, texto, seleccionada):
    """Dibuja una fila, resaltada (video invertido) si es la seleccionada."""
    atributo = curses.A_REVERSE if seleccionada else curses.A_NORMAL
    stdscr.addstr(y, 0, texto, atributo)


def _layout(stdscr):
    """
    Reparte la pantalla en dos zonas: la lista (arriba) y el panel de
    detalle (abajo, hasta 1/3 de la pantalla). Devuelve cuántas filas
    le tocan a cada una.
    """
    filas, columnas = stdscr.getmaxyx()
    filas_detalle = min(10, max(3, filas // 3))
    max_filas_lista = max(0, filas - 2 - filas_detalle - 1)
    fila_detalle = filas - filas_detalle
    return columnas, max_filas_lista, fila_detalle, filas_detalle


def _panel_detalle(stdscr, item, fila_inicio, filas_detalle, columnas):
    """Muestra todos los campos del item seleccionado, uno por línea."""
    stdscr.hline(fila_inicio - 1, 0, curses.ACS_HLINE, columnas)

    if item is None:
        stdscr.addstr(fila_inicio, 0, '(sin selección)')
        return

    campos = list(item.items())[:filas_detalle - 1]
    for i, (clave, valor) in enumerate(campos):
        texto = f'{clave}: {valor}'
        stdscr.addstr(fila_inicio + i, 0, texto[:columnas - 1])


def dibujar_resumen(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('resumen')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    _encabezado(stdscr, entrada, 'RESUMEN')
    stdscr.addstr(1, 0, f'{"PID":>7} {"ST":<2} {"CPU%":>6} {"RSS":>8}  COMANDO')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    top = sorted(entrada['datos'].values(), key=lambda x: x['cpu'], reverse=True)[:max_filas]

    for i, pr in enumerate(top):
        linea = (f'{pr["pid"]:>7} {pr["estado"]:<2} {pr["cpu"]:>6.1f} '
                 f'{pr["rss_kb"] / 1024:>7.1f}M  {pr["comando"]}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_memoria(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('memoria')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    _encabezado(stdscr, entrada, 'MEMORIA')
    stdscr.addstr(1, 0, f'{"PID":>7} {"RSS":>8} {"VMSIZE":>9} {"HEAP":>7} {"STACK":>7}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    top = sorted(entrada['datos'].values(), key=lambda x: x['vm_rss_kb'], reverse=True)[:max_filas]

    for i, pr in enumerate(top):
        heap = pr['segmentos'].get('heap', 0)
        stack = pr['segmentos'].get('stack', 0)
        linea = (f'{pr["pid"]:>7} {pr["vm_rss_kb"] / 1024:>7.1f}M {pr["vm_size_kb"] / 1024:>8.1f}M '
                 f'{heap:>6}K {stack:>6}K')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_fds(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('fds')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    _encabezado(stdscr, entrada, 'FILE DESCRIPTORS')
    stdscr.addstr(1, 0, f'{"PID":>7} {"FDS":>5}  TIPOS (primeros 5)')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    top = sorted(entrada['datos'].values(), key=lambda x: x['cantidad'], reverse=True)[:max_filas]

    for i, pr in enumerate(top):
        tipos = ', '.join(f['tipo'] for f in pr['fds'][:5])
        linea = f'{pr["pid"]:>7} {pr["cantidad"]:>5}  {tipos}'
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_threads(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('threads')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    # 'datos' acá es {pid: {tid: {...}}} -- lo aplanamos a una lista de threads.
    filas_threads = []
    for pid, threads in entrada['datos'].items():
        for t in threads.values():
            filas_threads.append({**t, 'pid': pid})

    edad = time.time() - entrada['ts']
    stdscr.addstr(0, 0, f'THREADS - {len(filas_threads)} threads - dato de hace {edad:.1f}s')
    stdscr.addstr(1, 0, f'{"PID":>7} {"TID":>7} {"ST":<2} {"CPU%":>6}  NOMBRE')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    top = sorted(filas_threads, key=lambda x: x['cpu'], reverse=True)[:max_filas]

    for i, t in enumerate(top):
        linea = f'{t["pid"]:>7} {t["tid"]:>7} {t["estado"]:<2} {t["cpu"]:>6.1f}  {t["nombre"]}'
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_senales(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('senales')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    _encabezado(stdscr, entrada, 'SEÑALES')
    stdscr.addstr(1, 0, f'{"PID":>7} {"BLOQ":>4} {"IGN":>4} {"HDLR":>4} {"PEND":>4}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    procesos = list(entrada['datos'].values())[:max_filas]

    for i, pr in enumerate(procesos):
        linea = (f'{pr["pid"]:>7} {len(pr["bloqueadas"]):>4} {len(pr["ignoradas"]):>4} '
                 f'{len(pr["con_handler"]):>4} {len(pr["pendientes_proceso"]):>4}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = procesos[seleccionado] if 0 <= seleccionado < len(procesos) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_scheduling(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('scheduling')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    _encabezado(stdscr, entrada, 'SCHEDULING')
    stdscr.addstr(1, 0, f'{"PID":>7} {"NICE":>5} {"PRI":>4} {"POLICY":<7} {"RTPRI":>5} {"VOL":>6} {"INVOL":>6}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)
    procesos = list(entrada['datos'].values())[:max_filas]

    for i, pr in enumerate(procesos):
        linea = (f'{pr["pid"]:>7} {pr["nice"]:>5} {pr["priority"]:>4} {pr["policy"]:<7} '
                 f'{pr["rt_priority"]:>5} {pr["voluntary_ctxt_switches"]:>6} '
                 f'{pr["nonvoluntary_ctxt_switches"]:>6}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = procesos[seleccionado] if 0 <= seleccionado < len(procesos) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()


def dibujar_sistema(stdscr, snapshot, seleccionado=0):
    entrada = snapshot.get('sistema')
    stdscr.erase()
    if entrada is None:
        return _sin_datos(stdscr)

    d = entrada['datos']
    edad = time.time() - entrada['ts']

    stdscr.addstr(0, 0, f'SISTEMA - dato de hace {edad:.1f}s')
    stdscr.addstr(2, 0, f'CPU:  user {d["cpu_pct"]["user"]:>5.1f}%  system {d["cpu_pct"]["system"]:>5.1f}%  '
                        f'idle {d["cpu_pct"]["idle"]:>5.1f}%  iowait {d["cpu_pct"]["iowait"]:>5.1f}%')
    stdscr.addstr(3, 0, f'Load average: {d["loadavg"]["1min"]:.2f} {d["loadavg"]["5min"]:.2f} '
                        f'{d["loadavg"]["15min"]:.2f}')
    stdscr.addstr(5, 0, f'Memoria total: {d["mem_total_kb"] / 1024:.0f} MB   '
                        f'libre: {d["mem_libre_kb"] / 1024:.0f} MB   '
                        f'buffers: {d["mem_buffers_kb"] / 1024:.0f} MB   '
                        f'cached: {d["mem_cached_kb"] / 1024:.0f} MB')
    stdscr.addstr(6, 0, f'Swap total: {d["swap_total_kb"] / 1024:.0f} MB   '
                        f'libre: {d["swap_libre_kb"] / 1024:.0f} MB')
    stdscr.addstr(8, 0, f'Procesos: {d["procesos_totales"]}   threads: {d["threads_totales"]}   '
                        f'zombies: {d["zombies"]}')
    stdscr.addstr(9, 0, 'Por estado: ' + '  '.join(f'{k}={v}' for k, v in d['procesos_por_estado'].items()))
    stdscr.addstr(11, 0, f'Uptime: {d["uptime_seg"] / 3600:.1f} horas')

    stdscr.refresh()


# Cada vista se define UNA vez, con sus dos teclas (número y letra)
# juntas. TECLAS_VISTA se arma expandiendo esa lista, para no repetir
# cada vista dos veces.
VISTAS = [
    ('resumen', ('1', 'r'), dibujar_resumen),
    ('memoria', ('2', 'm'), dibujar_memoria),
    ('fds', ('3', 'f'), dibujar_fds),
    ('threads', ('4', 't'), dibujar_threads),
    ('senales', ('5', 's'), dibujar_senales),
    ('scheduling', ('6', 'p'), dibujar_scheduling),
    ('sistema', ('7', 'g'), dibujar_sistema),
]

TECLAS_VISTA = {}
for _nombre, _teclas, _funcion in VISTAS:
    for _tecla in _teclas:
        TECLAS_VISTA[_tecla] = _funcion


def loop_display(stdscr, snapshot, corriendo):
    curses.curs_set(0)       # oculta el cursor
    stdscr.nodelay(True)     # getch() no bloquea
    stdscr.timeout(200)      # espera hasta 200ms por una tecla

    vista_activa = dibujar_resumen
    seleccionado = 0

    while corriendo.value:
        tecla = stdscr.getch()

        if tecla == ord('q'):
            corriendo.value = False
            break
        elif tecla == curses.KEY_UP:
            seleccionado = max(0, seleccionado - 1)
        elif tecla == curses.KEY_DOWN:
            seleccionado += 1
        elif tecla != -1:
            caracter = chr(tecla) if 0 <= tecla < 256 else ''
            if caracter in TECLAS_VISTA:
                vista_activa = TECLAS_VISTA[caracter]
                seleccionado = 0  # se resetea al cambiar de vista

        vista_activa(stdscr, snapshot, seleccionado)