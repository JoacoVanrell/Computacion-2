#!/usr/bin/env python3
"""Worker en background: incrementa un contador en Redis cada INTERVALO segundos."""
import os
import time

import redis

r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379, decode_responses=True)
intervalo = float(os.getenv("INTERVALO", "1"))

# Redis puede tardar un poco en estar listo: depends_on solo ordena el ARRANQUE, no espera a que esté "sano"
for _ in range(30):
    try:
        r.ping()
        break
    except redis.ConnectionError:
        print("esperando a redis...")
        time.sleep(1)

while True:
    print(f"contador = {r.incr('contador')}")
    time.sleep(intervalo)
