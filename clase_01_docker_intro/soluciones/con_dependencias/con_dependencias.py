#!/usr/bin/env python3
"""Clase 1 · Ej. 5: script con una dependencia externa (requests)."""
import requests

r = requests.get("https://httpbin.org/get", timeout=10)
print(f"Status: {r.status_code}")
print(f"Tu IP pública: {r.json()['origin']}")
