#!/usr/bin/env python3
"""Servicio web: responde con el contador que mantiene el worker en Redis."""
import json
import os
import platform
from http.server import BaseHTTPRequestHandler, HTTPServer

import redis

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        r.incr("visitas_web")
        cuerpo = {
            "contador_worker": int(r.get("contador") or 0),
            "visitas_web": int(r.get("visitas_web") or 0),
            "contenedor": platform.node(),        # hostname = ID del contenedor
        }
        datos = json.dumps(cuerpo, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)


if __name__ == "__main__":
    print("web escuchando en 0.0.0.0:8000")   # 0.0.0.0: si fuera 127.0.0.1 no se vería desde fuera del contenedor
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
