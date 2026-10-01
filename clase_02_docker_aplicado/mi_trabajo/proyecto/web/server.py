import redis
import sys
import os
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler

r = redis.Redis(host="redis", port=6379)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        contador = r.get("contador")
        contador = contador.decode() if contador else "0"

        body = f"""Python:    {sys.version}
OS:        {platform.system()} {platform.release()}
CPUs:      {os.cpu_count()}
Contador:  {contador}
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format, *args):
        pass  # silencia logs del servidor

print("Servidor en http://localhost:8080")
HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
