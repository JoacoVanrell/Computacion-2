"""Servidor HTTP de prueba para las mediciones (servicio `lento` del compose).

    GET /demora/0.5   -> responde 200 a los 0.5 s, con ~1 KB de cuerpo

Es como el de la clase 20 (descargas_reales.py): una página "lejana" que
tarda siempre lo mismo, para que los números no dependan de internet.
ThreadingHTTPServer atiende cada pedido en su propio thread, así que muchas
descargas a la vez no se hacen fila acá.
"""
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUERTO = 9100


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'          # keep-alive

    def do_GET(self):
        if self.path.startswith('/demora/'):
            time.sleep(float(self.path.split('/')[2]))
            cuerpo = b'x' * 1256
            self.send_response(200)
        else:
            cuerpo = b'no existe'
            self.send_response(404)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 1024


if __name__ == '__main__':
    print(f'servidor lento escuchando en el puerto {PUERTO}')
    Servidor(('0.0.0.0', PUERTO), Handler).serve_forever()
