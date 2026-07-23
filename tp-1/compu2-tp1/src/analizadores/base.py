"""
Loop genérico de analizador.
Cada analizador corre en su PROPIO proceso, con su propio intervalo.
"""
import time


def loop_analizador(nombre, funcion, snapshot, intervalo, corriendo):
    """
    nombre    : clave dentro del snapshot ('resumen', 'memoria', ...)
    funcion   : recolectar(previo) -> (datos, nuevo_previo)
    snapshot  : Manager().dict() compartido entre todos los procesos
    intervalo : Value('d') - segundos entre ciclos, ajustable en vivo
    corriendo : Value('b') - flag de apagado
    """
    previo = {}

    while corriendo.value:
        inicio = time.time()

        try:
            datos, previo = funcion(previo)
            # Asignación de la clave ENTERA, no mutación interna.
            snapshot[nombre] = {'ts': time.time(), 'datos': datos}
        except Exception as e:
            # Si un analizador explota, no debe tumbar el monitor entero.
            snapshot[nombre] = {'ts': time.time(), 'error': str(e), 'datos': {}}

        # Dormimos en tramos cortos en vez de un sleep largo: así el
        # proceso reacciona rápido al apagado y a cambios de intervalo.
        objetivo = inicio + intervalo.value
        while time.time() < objetivo and corriendo.value:
            time.sleep(0.1)