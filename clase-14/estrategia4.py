#!/usr/bin/env python3
"""Servidor eco con socketserver."""
import socketserver

class EchoHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """Se llama una vez por conexión, en su propio thread."""
        for linea in self.rfile:            # framing por líneas, gratis
            self.wfile.write(linea)

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True              # equivale a SO_REUSEADDR
    daemon_threads = True

with Servidor(('0.0.0.0', 8080), EchoHandler) as srv:
    srv.serve_forever()