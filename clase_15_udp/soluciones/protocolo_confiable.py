#!/usr/bin/env python3
"""Clase 15 · Ej. 3 (OBLIGATORIO): confiabilidad sobre UDP — reintentos, duplicados y números de secuencia.

    python3 protocolo_confiable.py                    # compara "ingenuo" vs "con seq" con 30% y 70% de pérdida
    python3 protocolo_confiable.py --perdida 0.6 --mensajes 50
    python3 protocolo_confiable.py --timeouts         # Parte B.6: timeout muy corto vs muy largo

La pérdida se simula en LOS DOS sentidos (pedido y respuesta), como en una red real:
  - si se pierde el PEDIDO, el servidor no hizo nada → reintentar está bien
  - si se pierde la RESPUESTA, el servidor YA hizo el trabajo → reintentar sin seq lo hace DOS veces
Además el servidor a veces responde TARDE (después del timeout del cliente): sin seq, el cliente
toma esa respuesta vieja como si fuera la del pedido actual → respuestas EQUIVOCADAS.
"""
import argparse
import random
import socket
import statistics
import struct
import threading
import time


def sendto_con_perdidas(sock, datos, destino, prob):
    if random.random() < prob:
        return len(datos)                       # "miente": dice que mandó
    return sock.sendto(datos, destino)


def empaquetar(seq, payload):
    return struct.pack("!I", seq) + payload     # 4 bytes de número de secuencia, orden de red


def desempaquetar(datos):
    (seq,) = struct.unpack("!I", datos[:4])
    return seq, datos[4:]


# ───────────────────────── servidor ─────────────────────────
class Servidor(threading.Thread):
    """Pone en mayúsculas. Cuenta cuántas veces hizo el TRABAJO REAL.
    con_seq=True → deduplica: si ve un (cliente, seq) repetido, reenvía la respuesta guardada sin trabajar."""
    def __init__(self, prob, con_seq, demora=0.15):
        super().__init__(daemon=True)
        self.demora = demora                    # probabilidad de responder TARDE (más que el timeout del cliente)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        self.prob, self.con_seq = prob, con_seq
        self.trabajos = 0
        self.respuestas = {}                    # (origen, seq) -> respuesta ya calculada
        self.fin = threading.Event()

    def run(self):
        while not self.fin.is_set():
            try:
                datos, origen = self.sock.recvfrom(65535)
            except TimeoutError:
                continue
            if random.random() < self.demora:
                time.sleep(0.08)                    # red lenta: esta respuesta llega después del timeout
            if self.con_seq:
                seq, payload = desempaquetar(datos)
                clave = (origen, seq)
                if clave not in self.respuestas:            # primera vez: trabajar
                    self.trabajos += 1
                    self.respuestas[clave] = empaquetar(seq, payload.upper())
                sendto_con_perdidas(self.sock, self.respuestas[clave], origen, self.prob)
            else:
                self.trabajos += 1                          # cada llegada = trabajo (aunque sea repetida)
                sendto_con_perdidas(self.sock, datos.upper(), origen, self.prob)


# ───────────────────────── cliente ─────────────────────────
def pedir_ingenuo(sock, payload, destino, prob, intentos=100, timeout=0.05):
    sock.settimeout(timeout)
    for n in range(1, intentos + 1):
        sendto_con_perdidas(sock, payload, destino, prob)
        try:
            resp, _ = sock.recvfrom(65535)
            return resp, n
        except TimeoutError:
            continue
    return None, intentos


def pedir_con_seq(sock, seq, payload, destino, prob, intentos=100, timeout=0.05):
    sock.settimeout(timeout)
    for n in range(1, intentos + 1):
        sendto_con_perdidas(sock, empaquetar(seq, payload), destino, prob)
        limite = time.monotonic() + timeout
        while (resto := limite - time.monotonic()) > 0:
            sock.settimeout(resto)
            try:
                datos, _ = sock.recvfrom(65535)
            except TimeoutError:
                break
            r_seq, r_payload = desempaquetar(datos)
            if r_seq == seq:                        # la que corresponde a ESTE pedido
                return r_payload, n
            # si no: respuesta DEMORADA de un pedido anterior → descartar y seguir esperando
    return None, intentos


def experimento(prob, n_msgs, con_seq, timeout=0.05):
    srv = Servidor(prob, con_seq)
    srv.start()
    destino = srv.sock.getsockname()
    intentos, perdidos, incorrectos = [], 0, 0
    t0 = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
        for i in range(n_msgs):
            payload = f"mensaje {i}".encode()
            if con_seq:
                resp, n = pedir_con_seq(c, i, payload, destino, prob, timeout=timeout)
            else:
                resp, n = pedir_ingenuo(c, payload, destino, prob, timeout=timeout)
            intentos.append(n)
            if resp is None:
                perdidos += 1
            elif resp != payload.upper():
                incorrectos += 1                    # ¡recibió la respuesta de OTRO pedido!
    dur = time.perf_counter() - t0
    time.sleep(0.1)
    srv.fin.set()
    return {"trabajos": srv.trabajos, "intentos": statistics.mean(intentos), "max": max(intentos),
            "perdidos": perdidos, "incorrectos": incorrectos, "seg": dur}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perdida", type=float, nargs="*", default=[0.3, 0.7])
    ap.add_argument("--mensajes", type=int, default=100)
    ap.add_argument("--timeouts", action="store_true")
    a = ap.parse_args()
    random.seed(1)

    if a.timeouts:
        for t in (0.01, 0.05, 0.3):
            r = experimento(0.3, 30, True, timeout=t)
            print(f"timeout {t:>5}s → {r['seg']:.2f}s para 30 mensajes · {r['intentos']:.1f} intentos prom")
        print("muy corto: reintenta antes de que la respuesta pueda llegar (tráfico y trabajo de más);"
              " muy largo: cada pérdida te cuesta esperar todo el timeout.")
        return

    for prob in a.perdida:
        print(f"\n=== pérdida {prob:.0%} en cada sentido · {a.mensajes} mensajes ===")
        for con_seq in (False, True):
            r = experimento(prob, a.mensajes, con_seq)
            nombre = "CON seq " if con_seq else "ingenuo "
            print(f"{nombre} trabajos del servidor: {r['trabajos']:>4} (debería ser {a.mensajes}) · "
                  f"intentos prom {r['intentos']:.2f} (máx {r['max']}) · sin respuesta {r['perdidos']} · "
                  f"respuestas EQUIVOCADAS {r['incorrectos']}")


if __name__ == "__main__":
    main()
