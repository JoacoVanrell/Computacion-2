#!/usr/bin/env python3
"""Clase 20 · Ej. 4 (locks, o su ausencia) y Ej. 5 (timeouts y cancelación).

    python3 locks_y_cancelacion.py
"""
import asyncio
import sys
import threading
import time


# ─────────────────────────── Ej. 4.1 — sin await en el medio: no hace falta Lock ───────────────────────────
contador = 0


async def sumar():
    global contador
    contador += 1                     # leer-sumar-guardar sin ningún await → nadie puede meterse


def registrar():                      # una llamada cualquiera (un log, una validación…)
    pass


def sumar_en_thread(veces):
    global contador
    for _ in range(veces):
        v = contador                  # leer
        registrar()                   # ← el intérprete puede cambiar de thread acá (sin pedirte permiso)
        contador = v + 1              # guardar un valor que quizás quedó viejo


async def ej4_1():
    global contador
    print("=== 4.1 Contador compartido ===")
    contador = 0
    await asyncio.gather(*(sumar() for _ in range(1000)))
    print(f"  1000 corrutinas (+1 cada una):           contador = {contador}")

    contador = 0
    sys.setswitchinterval(1e-6)       # cambiar de thread muy seguido: hace visible la race de la clase 11
    hilos = [threading.Thread(target=sumar_en_thread, args=(10_000,)) for _ in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    sys.setswitchinterval(0.005)
    print(f"  10 threads × 10 000 (+1 cada vez):       contador = {contador}  ← esperado 100000: race condition")

    contador = 0

    async def sumar_10000():
        global contador
        for _ in range(10_000):
            v = contador
            registrar()                  # la misma llamada: en una corrutina NO es punto de cambio
            contador = v + 1
            if _ % 100 == 0:
                await asyncio.sleep(0)   # cede, pero FUERA de la sección crítica
    await asyncio.gather(*(sumar_10000() for _ in range(10)))
    print(f"  10 corrutinas × 10 000 (cediendo afuera): contador = {contador}")


# ─────────────────────────── Ej. 4.2 — await en el medio: SÍ hace falta Lock ───────────────────────────
async def ej4_2():
    print("\n=== 4.2 Transferencias (un await adentro de la sección crítica) ===")
    cuentas = {"A": 1000, "B": 0}

    async def transferir(origen, destino, monto):
        saldo = cuentas[origen]                  # leo
        await asyncio.sleep(0)                   # ← punto de suspensión: acá corre otra transferencia
        cuentas[origen] = saldo - monto          # escribo un saldo que quedó VIEJO
        cuentas[destino] += monto

    await asyncio.gather(*(transferir("A", "B", 1) for _ in range(100)))
    print(f"  sin Lock:  A = {cuentas['A']:4d}  B = {cuentas['B']:3d}  total = {sum(cuentas.values())}"
          f"   ← esperado A = 900: ¡se crearon {sum(cuentas.values()) - 1000} pesos de la nada!")

    cuentas = {"A": 1000, "B": 0}
    lock = asyncio.Lock()

    async def transferir_bien(origen, destino, monto):
        async with lock:                         # async with: tomar el lock puede tener que ESPERAR
            saldo = cuentas[origen]
            await asyncio.sleep(0)
            cuentas[origen] = saldo - monto
            cuentas[destino] += monto

    await asyncio.gather(*(transferir_bien("A", "B", 1) for _ in range(100)))
    print(f"  con Lock:  A = {cuentas['A']:4d}  B = {cuentas['B']:3d}  total = {sum(cuentas.values())}")


# ─────────────────────────── Ej. 5.1 — timeout ───────────────────────────
async def operacion_lenta(nombre):
    try:
        await asyncio.sleep(10)
        return "terminé"
    except asyncio.CancelledError:
        print(f"    [{nombre}] me llegó CancelledError → el timeout me CANCELÓ (no sigo corriendo de fondo)")
        raise


async def ej5_1():
    print("\n=== 5.1 Timeout ===")
    t0 = time.perf_counter()
    try:
        async with asyncio.timeout(0.5):
            await operacion_lenta("timeout()")
    except TimeoutError as e:
        print(f"  asyncio.timeout(0.5) → {type(e).__name__} a los {time.perf_counter() - t0:.2f}s")

    t0 = time.perf_counter()
    try:
        await asyncio.wait_for(operacion_lenta("wait_for()"), timeout=0.5)
    except TimeoutError as e:
        print(f"  asyncio.wait_for(…, 0.5) → {type(e).__name__} a los {time.perf_counter() - t0:.2f}s "
              f"(¿asyncio.TimeoutError is TimeoutError? {asyncio.TimeoutError is TimeoutError})")


# ─────────────────────────── Ej. 5.2 — cancelación ───────────────────────────
async def ej5_2_timeout_roto():
    """El timeout de 0,3 s envuelve una corrutina que se traga la cancelación: no corta nunca."""
    vueltas = 0

    async def mentirosa_finita():
        nonlocal vueltas
        while vueltas < 10:                      # para que la demo termine: 10 vueltas de 0,1 s
            vueltas += 1
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                pass                             # ✗ se la traga
        return "terminé igual"

    t0 = time.perf_counter()
    try:
        async with asyncio.timeout(0.3):
            r = await mentirosa_finita()
        print(f"     timeout(0.3) alrededor de la mentirosa: devolvió {r!r} a los {time.perf_counter() - t0:.2f}s "
              f"— el timeout NO cortó")
    except TimeoutError:
        print("     el timeout cortó")


async def ej5_2_base_exception():
    async def tarea():
        try:
            await asyncio.sleep(10)
        except Exception:                        # el "except distraído"
            print("    [tarea] el except Exception la atrapó")
            return "seguí"

    t = asyncio.create_task(tarea())
    await asyncio.sleep(0.05)
    t.cancel()
    try:
        await t
        print("  8) …")
    except asyncio.CancelledError:
        print(f"  8) `except Exception:` NO atrapó la cancelación (CancelledError hereda de "
              f"{asyncio.CancelledError.__mro__[1].__name__}) → la tarea se canceló bien")


async def main():
    await ej4_1()
    await ej4_2()
    await ej5_1()
    print("\n=== 5.2 Cancelación ===")
    await ej5_2_cancelar_cpu()
    await ej5_2_mentirosa()
    await ej5_2_timeout_roto()
    await ej5_2_base_exception()


async def ej5_2_cancelar_cpu():
    async def calcular(segundos):
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < segundos:
            pass                                 # CPU puro, sin await
        print(f"    [calcular] terminé de calcular a los {time.perf_counter() - inicio:.2f}s; ahora hago un await…")
        await asyncio.sleep(0)                   # recién acá se entrega el CancelledError
        print("    [calcular] esto nunca se imprime")

    inicio = time.perf_counter()
    tarea = asyncio.create_task(calcular(2))
    loop = asyncio.get_running_loop()
    # cancelo desde OTRO thread a los 0,2 s (desde una corrutina no podría: el loop está tomado por calcular)
    threading.Timer(0.2, lambda: (print("    [timer] cancel() pedido a los 0.20s"),
                                  loop.call_soon_threadsafe(tarea.cancel))).start()
    try:
        await tarea
    except asyncio.CancelledError:
        print(f"  6) se canceló recién a los {time.perf_counter() - inicio:.2f}s (en su primer await), no a los 0,2 s")


async def ej5_2_mentirosa():
    async def mentirosa(parar):
        while not parar.is_set():
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                print("    [mentirosa] me cancelaron… y sigo como si nada")   # ✗ sin raise

    parar = asyncio.Event()
    tarea = asyncio.create_task(mentirosa(parar))
    await asyncio.sleep(0.05)
    tarea.cancel()
    await asyncio.sleep(0.5)
    print(f"  7) 0,5 s después del cancel(): done()={tarea.done()}, cancelled()={tarea.cancelled()}"
          f" → sigue viva; quien hizo `await tarea` esperaría para siempre")
    parar.set()
    await tarea


if __name__ == "__main__":
    asyncio.run(main())
