#!/usr/bin/env python3
"""Clase 6 · Ej. 5 (OBLIGATORIO): servidor que responde a señales.

    python3 servidor_signals.py [--config config.json] [--log server.log]

    kill -HUP  <pid>   recargar configuración (relee el JSON)
    kill -USR1 <pid>   mostrar estadísticas
    kill -USR2 <pid>   rotar el log (server.log → server.log.<timestamp>)
    kill <pid>  / Ctrl+C   shutdown limpio

Diferencia con el esqueleto del profe: los manejadores NO hacen el trabajo, solo
anotan qué señal llegó (patrón del FLAG). El trabajo real (print, abrir archivos,
renombrar logs) se hace en el loop principal, que es un lugar seguro.
¿Por qué? Una señal puede interrumpir el programa en CUALQUIER línea, incluso en
medio de un print o de una escritura al log: hacer lo mismo desde el handler puede
corromper buffers (no son funciones async-signal-safe).
"""
import argparse
import json
import os
import signal
import time


class Servidor:
    def __init__(self, ruta_config, ruta_log):
        self.ruta_config = ruta_config
        self.ruta_log = ruta_log
        self.pendientes = set()               # señales que llegaron y falta procesar
        self.ejecutando = True
        self.config = {"max_conexiones": 100, "timeout": 30}
        self.stats = {"requests": 0, "errores": 0, "inicio": time.time()}
        self.log = open(self.ruta_log, "a")
        self._cargar_config()
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGUSR1, signal.SIGUSR2):
            signal.signal(sig, self._anotar)

    # ── el handler: lo MÍNIMO posible ──
    def _anotar(self, sig, frame):
        self.pendientes.add(sig)

    # ── el trabajo real, llamado desde el loop principal ──
    def _procesar_senales(self):
        while self.pendientes:
            sig = self.pendientes.pop()
            nombre = signal.Signals(sig).name
            if sig in (signal.SIGTERM, signal.SIGINT):
                self._registrar(f"[{nombre}] shutdown solicitado")
                self.ejecutando = False
            elif sig == signal.SIGHUP:
                self._cargar_config()
                self._registrar(f"[SIGHUP] config recargada: {self.config}")
            elif sig == signal.SIGUSR1:
                uptime = time.time() - self.stats["inicio"]
                self._registrar(f"[SIGUSR1] uptime={uptime:.1f}s requests={self.stats['requests']} "
                                f"errores={self.stats['errores']} config={self.config}")
            elif sig == signal.SIGUSR2:
                self._rotar_log()

    def _registrar(self, msg):
        linea = f"{time.strftime('%H:%M:%S')} {msg}"
        print(linea, flush=True)
        self.log.write(linea + "\n")
        self.log.flush()

    def _cargar_config(self):
        try:
            with open(self.ruta_config) as f:
                self.config.update(json.load(f))
        except FileNotFoundError:
            pass                                    # sin archivo: quedan los valores por defecto
        except json.JSONDecodeError as e:
            print(f"config inválida, me quedo con la anterior: {e}")

    def _rotar_log(self):
        destino = f"{self.ruta_log}.{int(time.time())}"
        self.log.close()
        os.rename(self.ruta_log, destino)            # rename es atómico y no copia datos (inodo)
        self.log = open(self.ruta_log, "a")          # archivo nuevo, vacío
        self._registrar(f"[SIGUSR2] log rotado → {destino}")

    def procesar_request(self):
        self.stats["requests"] += 1
        time.sleep(0.1)                              # "trabajo"
        if self.stats["requests"] % 10 == 0:
            self.stats["errores"] += 1

    def run(self):
        pid = os.getpid()
        print(f"Servidor iniciado (PID {pid})\n  kill -HUP {pid} | kill -USR1 {pid} | kill -USR2 {pid} | kill {pid}")
        while self.ejecutando:
            self.procesar_request()
            self._procesar_senales()
        self._registrar(f"cleanup… requests procesadas: {self.stats['requests']}")
        self.log.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.json")
    p.add_argument("--log", default="server.log")
    a = p.parse_args()
    Servidor(a.config, a.log).run()
