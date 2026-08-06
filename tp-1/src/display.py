"""
Display: TUI en curses. Corre en el proceso principal (no es un
Process aparte) porque necesita control exclusivo de la terminal.
"""
import curses
import time
import os
import json
import signal
import senales

INTERVALO_MIN = {
    'resumen': 0.5, 'memoria': 1.0, 'fds': 2.0, 'threads': 0.5,
    'senales': 5.0, 'scheduling': 5.0, 'sistema': 1.0,
}
INTERVALO_MAX = 30.0
PASO_INTERVALO = 0.5


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


def _aplicar_pin(lista, pid_pineado):
    """Si el pid pineado está en la lista, lo mueve al principio."""
    if pid_pineado is None:
        return lista
    pineado = next((x for x in lista if x['pid'] == pid_pineado), None)
    if pineado is None:
        return lista
    resto = [x for x in lista if x['pid'] != pid_pineado]
    return [pineado] + resto


def _pids_filtrados(snapshot, filtro_comando, filtro_usuario):
    """
    Devuelve un set de PIDs que matchean los filtros activos, o None si
    no hay ningún filtro (todos pasan). Usa 'resumen' como fuente de
    comando/usuario porque es la única vista que los tiene -- así el
    filtro funciona igual en las 7 vistas, aunque su propia data no
    tenga esos campos.
    """
    if not filtro_comando and not filtro_usuario:
        return None

    entrada = snapshot.get('resumen')
    if entrada is None:
        return set()

    resultado = set()
    for pid, pr in entrada['datos'].items():
        if filtro_comando and filtro_comando.lower() not in pr['comando'].lower():
            continue
        if filtro_usuario and filtro_usuario.lower() not in pr['usuario'].lower():
            continue
        resultado.add(pid)
    return resultado


def _pedir_texto(stdscr, prompt):
    """Pide una línea de texto al usuario, en la última fila de la pantalla."""
    filas, columnas = stdscr.getmaxyx()
    stdscr.addstr(filas - 1, 0, prompt)
    stdscr.clrtoeol()
    curses.echo()
    stdscr.nodelay(False)
    try:
        texto = stdscr.getstr(filas - 1, len(prompt)).decode('utf-8', errors='replace')
    finally:
        stdscr.nodelay(True)
        curses.noecho()
    return texto.strip()


def dibujar_resumen(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                     pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('resumen')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    _encabezado(stdscr, entrada, 'RESUMEN')
    stdscr.addstr(1, 0, f'{"PID":>7} {"ST":<2} {"CPU%":>6} {"RSS":>8}  COMANDO')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    valores = [p for p in entrada['datos'].values()
               if pids_filtrados is None or p['pid'] in pids_filtrados]

    if criterio_orden == 'pid':
        valores.sort(key=lambda x: x['pid'])
    elif criterio_orden == 'rss':
        valores.sort(key=lambda x: x['rss_kb'], reverse=True)
    else:
        valores.sort(key=lambda x: x['cpu'], reverse=True)

    valores = _aplicar_pin(valores, pid_pineado)
    top = valores[:max_filas]

    for i, pr in enumerate(top):
        linea = (f'{pr["pid"]:>7} {pr["estado"]:<2} {pr["cpu"]:>6.1f} '
                 f'{pr["rss_kb"] / 1024:>7.1f}M  {pr["comando"]}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return top


def dibujar_memoria(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                     pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('memoria')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    _encabezado(stdscr, entrada, 'MEMORIA')
    stdscr.addstr(1, 0, f'{"PID":>7} {"RSS":>8} {"VMSIZE":>9} {"HEAP":>7} {"STACK":>7}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    valores = [p for p in entrada['datos'].values()
               if pids_filtrados is None or p['pid'] in pids_filtrados]

    # Memoria no tiene CPU%: 'cpu' y 'rss' apuntan a lo mismo (vm_rss_kb).
    if criterio_orden == 'pid':
        valores.sort(key=lambda x: x['pid'])
    else:
        valores.sort(key=lambda x: x['vm_rss_kb'], reverse=True)

    valores = _aplicar_pin(valores, pid_pineado)
    top = valores[:max_filas]

    for i, pr in enumerate(top):
        heap = pr['segmentos'].get('heap', 0)
        stack = pr['segmentos'].get('stack', 0)
        linea = (f'{pr["pid"]:>7} {pr["vm_rss_kb"] / 1024:>7.1f}M {pr["vm_size_kb"] / 1024:>8.1f}M '
                 f'{heap:>6}K {stack:>6}K')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return top


def dibujar_fds(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                 pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('fds')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    _encabezado(stdscr, entrada, 'FILE DESCRIPTORS' + (' [VERBOSE]' if verbose else ''))
    limite_tipos = 20 if verbose else 5
    stdscr.addstr(1, 0, f'{"PID":>7} {"FDS":>5}  TIPOS (primeros {limite_tipos})')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    valores = [p for p in entrada['datos'].values()
               if pids_filtrados is None or p['pid'] in pids_filtrados]

    # FDs no tiene CPU% ni RSS: 'pid' ordena por pid, cualquier otro
    # criterio deja el orden natural (cantidad de FDs, descendente).
    if criterio_orden == 'pid':
        valores.sort(key=lambda x: x['pid'])
    else:
        valores.sort(key=lambda x: x['cantidad'], reverse=True)

    valores = _aplicar_pin(valores, pid_pineado)
    top = valores[:max_filas]

    for i, pr in enumerate(top):
        tipos = ', '.join(f['tipo'] for f in pr['fds'][:limite_tipos])
        linea = f'{pr["pid"]:>7} {pr["cantidad"]:>5}  {tipos}'
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return top


def dibujar_threads(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                     pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('threads')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    # 'datos' acá es {pid: {tid: {...}}} -- lo aplanamos a una lista de threads.
    filas_threads = []
    for pid, threads in entrada['datos'].items():
        if pids_filtrados is not None and pid not in pids_filtrados:
            continue
        for t in threads.values():
            filas_threads.append({**t, 'pid': pid})

    edad = time.time() - entrada['ts']
    stdscr.addstr(0, 0, f'THREADS - {len(filas_threads)} threads - dato de hace {edad:.1f}s')
    stdscr.addstr(1, 0, f'{"PID":>7} {"TID":>7} {"ST":<2} {"CPU%":>6}  NOMBRE')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    if criterio_orden == 'pid':
        filas_threads.sort(key=lambda x: x['pid'])
    else:
        filas_threads.sort(key=lambda x: x['cpu'], reverse=True)

    filas_threads = _aplicar_pin(filas_threads, pid_pineado)
    top = filas_threads[:max_filas]

    for i, t in enumerate(top):
        linea = f'{t["pid"]:>7} {t["tid"]:>7} {t["estado"]:<2} {t["cpu"]:>6.1f}  {t["nombre"]}'
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = top[seleccionado] if 0 <= seleccionado < len(top) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return top


def dibujar_senales(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                     pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('senales')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    _encabezado(stdscr, entrada, 'SEÑALES')
    stdscr.addstr(1, 0, f'{"PID":>7} {"BLOQ":>4} {"IGN":>4} {"HDLR":>4} {"PEND":>4}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    valores = [p for p in entrada['datos'].values()
               if pids_filtrados is None or p['pid'] in pids_filtrados]

    # Señales no tiene CPU% ni RSS: solo 'pid' cambia el orden acá,
    # el resto deja el orden natural del snapshot.
    if criterio_orden == 'pid':
        valores.sort(key=lambda x: x['pid'])

    valores = _aplicar_pin(valores, pid_pineado)
    procesos = valores[:max_filas]

    for i, pr in enumerate(procesos):
        linea = (f'{pr["pid"]:>7} {len(pr["bloqueadas"]):>4} {len(pr["ignoradas"]):>4} '
                 f'{len(pr["con_handler"]):>4} {len(pr["pendientes_proceso"]):>4}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = procesos[seleccionado] if 0 <= seleccionado < len(procesos) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return procesos


def dibujar_scheduling(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                        pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('scheduling')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    _encabezado(stdscr, entrada, 'SCHEDULING')
    stdscr.addstr(1, 0, f'{"PID":>7} {"NICE":>5} {"PRI":>4} {"POLICY":<7} {"RTPRI":>5} {"VOL":>6} {"INVOL":>6}')

    columnas, max_filas, fila_detalle, filas_detalle = _layout(stdscr)

    valores = [p for p in entrada['datos'].values()
               if pids_filtrados is None or p['pid'] in pids_filtrados]

    # Mismo caso que señales: sin CPU%/RSS propios.
    if criterio_orden == 'pid':
        valores.sort(key=lambda x: x['pid'])

    valores = _aplicar_pin(valores, pid_pineado)
    procesos = valores[:max_filas]

    for i, pr in enumerate(procesos):
        linea = (f'{pr["pid"]:>7} {pr["nice"]:>5} {pr["priority"]:>4} {pr["policy"]:<7} '
                 f'{pr["rt_priority"]:>5} {pr["voluntary_ctxt_switches"]:>6} '
                 f'{pr["nonvoluntary_ctxt_switches"]:>6}')
        _fila(stdscr, 2 + i, linea[:columnas - 1], i == seleccionado)

    item = procesos[seleccionado] if 0 <= seleccionado < len(procesos) else None
    _panel_detalle(stdscr, item, fila_detalle, filas_detalle, columnas)

    stdscr.refresh()
    return procesos


def dibujar_sistema(stdscr, snapshot, seleccionado=0, criterio_orden='cpu',
                     pids_filtrados=None, pid_pineado=None, verbose=False):
    entrada = snapshot.get('sistema')
    stdscr.erase()
    if entrada is None:
        _sin_datos(stdscr)
        return []

    d = entrada['datos']
    edad = time.time() - entrada['ts']
    filas, columnas = stdscr.getmaxyx()

    def linea(fila, col, texto):
        # A diferencia de las otras vistas, acá las filas son fijas
        # (no una lista recortada a max_filas), así que hay que chequear
        # a mano que entren en la pantalla antes de escribir.
        if fila < filas - 1:
            stdscr.addstr(fila, col, texto[:columnas - 1 - col])

    linea(0, 0, f'SISTEMA - dato de hace {edad:.1f}s')
    linea(2, 0, f'CPU:  user {d["cpu_pct"]["user"]:>5.1f}%  system {d["cpu_pct"]["system"]:>5.1f}%  '
                f'idle {d["cpu_pct"]["idle"]:>5.1f}%  iowait {d["cpu_pct"]["iowait"]:>5.1f}%')
    linea(3, 0, f'Load average: {d["loadavg"]["1min"]:.2f} {d["loadavg"]["5min"]:.2f} '
                f'{d["loadavg"]["15min"]:.2f}')
    linea(5, 0, f'Memoria total: {d["mem_total_kb"] / 1024:.0f} MB   '
                f'libre: {d["mem_libre_kb"] / 1024:.0f} MB   '
                f'buffers: {d["mem_buffers_kb"] / 1024:.0f} MB   '
                f'cached: {d["mem_cached_kb"] / 1024:.0f} MB')
    linea(6, 0, f'Swap total: {d["swap_total_kb"] / 1024:.0f} MB   '
                f'libre: {d["swap_libre_kb"] / 1024:.0f} MB')
    linea(8, 0, f'Procesos: {d["procesos_totales"]}   threads: {d["threads_totales"]}   '
                f'zombies: {d["zombies"]}')
    linea(9, 0, 'Por estado: ' + '  '.join(f'{k}={v}' for k, v in d['procesos_por_estado'].items()))
    linea(11, 0, f'Uptime: {d["uptime_seg"] / 3600:.1f} horas')

    # Top 3 CPU/memoria: se calculan acá, no en analizadores/sistema.py,
    # porque el Display ya lee el snapshot completo (ver README).
    fila = 13
    entrada_resumen = snapshot.get('resumen')
    if entrada_resumen is not None:
        top_cpu = sorted(entrada_resumen['datos'].values(),
                          key=lambda x: x['cpu'], reverse=True)[:3]
        linea(fila, 0, 'Top 3 CPU:')
        for i, pr in enumerate(top_cpu):
            linea(fila + 1 + i, 2, f'{pr["pid"]:>7} {pr["cpu"]:>6.1f}%  {pr["comando"][:50]}')
        fila += 5

    entrada_memoria = snapshot.get('memoria')
    if entrada_memoria is not None:
        top_mem = sorted(entrada_memoria['datos'].values(),
                          key=lambda x: x['vm_rss_kb'], reverse=True)[:3]
        linea(fila, 0, 'Top 3 memoria (RSS):')
        for i, pr in enumerate(top_mem):
            linea(fila + 1 + i, 2, f'{pr["pid"]:>7} {pr["vm_rss_kb"] / 1024:>7.1f}M')

    stdscr.refresh()
    return []


def dibujar_ayuda(stdscr):
    stdscr.erase()
    lineas = [
        'AYUDA - keybindings',
        '',
        '1-7 o r/m/f/t/s/p/g   cambiar de vista',
        'flechas arriba/abajo  navegar la lista',
        'Enter                 pin/despin del proceso seleccionado',
        '/                     filtrar por comando',
        'u                     filtrar por usuario',
        'c                     alternar orden (CPU / RSS / PID)',
        '+ / -                 ajustar intervalo de la vista activa',
        'q                     salir',
        'h o ?                 esta ayuda (cualquier tecla para volver)',
    ]
    for i, linea in enumerate(lineas):
        stdscr.addstr(i, 0, linea)
    stdscr.refresh()


# Cada vista se define UNA vez, con sus dos teclas (número y letra)
# juntas. TECLAS_VISTA se arma expandiendo esa lista, para no repetir
# cada vista dos veces. Guarda (nombre, función): el nombre hace falta
# para saber a qué Value de intervalo le pega +/-.
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
        TECLAS_VISTA[_tecla] = (_nombre, _funcion)


def _atender_senales(fd_senales, snapshot, intervalos, estado):
    """
    Consulta el self-pipe y aplica lo que corresponda. 'estado' es un
    dict mutable con 'filtro_comando'/'filtro_usuario'/'criterio_orden'/
    'verbose', para poder modificarlo desde acá sin variables globales.
    """
    for sig in senales.leer_pendientes(fd_senales):
        if sig in (signal.SIGINT, signal.SIGTERM):
            estado['corriendo'] = False

        elif sig == signal.SIGHUP:
            # Recarga intervalos por vista y filtros default desde config.json.
            try:
                with open('config.json') as f:
                    cfg = json.load(f)
                for nombre, valor in cfg.get('intervalos', {}).items():
                    if nombre in intervalos:
                        intervalos[nombre].value = valor
                estado['filtro_comando'] = cfg.get('filtro_comando') or ''
                estado['filtro_usuario'] = cfg.get('filtro_usuario') or ''
                estado['criterio_orden'] = cfg.get('orden', 'cpu')
            except (OSError, json.JSONDecodeError, ValueError):
                pass  # config.json roto o ausente: seguimos con lo que había

        elif sig == signal.SIGUSR1:
            # Dump del snapshot completo a dumps/dump_<timestamp>.json.
            try:
                os.makedirs('dumps', exist_ok=True)
                ruta = f'dumps/dump_{int(time.time())}.json'
                with open(ruta, 'w') as f:
                    json.dump(dict(snapshot), f, indent=2, default=str)
            except OSError:
                pass

        elif sig == signal.SIGUSR2:
            estado['verbose'] = not estado['verbose']


def loop_display(stdscr, snapshot, corriendo, intervalos, fd_senales):
    curses.curs_set(0)       # oculta el cursor
    stdscr.nodelay(True)     # getch() no bloquea
    stdscr.timeout(200)      # espera hasta 200ms por una tecla

    nombre_activo, vista_activa = 'resumen', dibujar_resumen
    seleccionado = 0
    pid_pineado = None
    lista_actual = []
    mostrando_ayuda = False

    # Estado que las señales pueden modificar desde afuera del loop de teclas.
    estado = {'corriendo': True, 'criterio_orden': 'cpu', 'filtro_comando': '',
              'filtro_usuario': '', 'verbose': False}

    while corriendo.value:
        _atender_senales(fd_senales, snapshot, intervalos, estado)
        if not estado['corriendo']:
            corriendo.value = False
            break

        tecla = stdscr.getch()

        if tecla == ord('q'):
            corriendo.value = False
            break
        elif mostrando_ayuda:
            # Con la ayuda en pantalla, cualquier tecla (menos q) vuelve.
            if tecla != -1:
                mostrando_ayuda = False
            continue
        elif tecla in (ord('h'), ord('?')):
            mostrando_ayuda = True
            dibujar_ayuda(stdscr)
            continue
        elif tecla == curses.KEY_UP:
            seleccionado = max(0, seleccionado - 1)
        elif tecla == curses.KEY_DOWN:
            seleccionado += 1
        elif tecla in (10, 13, curses.KEY_ENTER):
            if 0 <= seleccionado < len(lista_actual):
                pid = lista_actual[seleccionado]['pid']
                pid_pineado = None if pid_pineado == pid else pid
                seleccionado = 0  # el pineado siempre queda en la fila 0
        elif tecla == ord('c'):
            ciclo = ['cpu', 'rss', 'pid']
            actual = estado['criterio_orden']
            estado['criterio_orden'] = ciclo[(ciclo.index(actual) + 1) % len(ciclo)]
        elif tecla == ord('+'):
            v = intervalos[nombre_activo]
            v.value = min(INTERVALO_MAX, v.value + PASO_INTERVALO)
        elif tecla == ord('-'):
            v = intervalos[nombre_activo]
            v.value = max(INTERVALO_MIN[nombre_activo], v.value - PASO_INTERVALO)
        elif tecla == ord('/'):
            estado['filtro_comando'] = _pedir_texto(stdscr, 'Filtrar por comando: ')
        elif tecla == ord('u'):
            estado['filtro_usuario'] = _pedir_texto(stdscr, 'Filtrar por usuario: ')
        elif tecla != -1:
            caracter = chr(tecla) if 0 <= tecla < 256 else ''
            if caracter in TECLAS_VISTA:
                nombre_activo, vista_activa = TECLAS_VISTA[caracter]
                seleccionado = 0

        pids_filtrados = _pids_filtrados(snapshot, estado['filtro_comando'], estado['filtro_usuario'])
        lista_actual = vista_activa(stdscr, snapshot, seleccionado, estado['criterio_orden'],
                                     pids_filtrados, pid_pineado, estado['verbose'])