import redis
import time

r = redis.Redis(host="redis", port=6379)

print("Worker iniciado, incrementando contador cada segundo...")
while True:
    r.incr("contador")
    print(f"Contador: {r.get('contador').decode()}")
    time.sleep(1)
