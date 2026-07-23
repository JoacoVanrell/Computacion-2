import multiprocessing
import os
import time
import random

def worker(id):
    demora = round(random.uniform(0.5, 2.0), 2)
    print(f"[Worker-{id}] PID={os.getpid()} | arranca, va a esperar {demora}s")
    time.sleep(demora)
    print(f"[Worker-{id}] terminó tras {demora}s")

if __name__ == "__main__":
    procesos = []
    inicio = time.time()

    # Loop 1: lanzar todos
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        p.start()
        procesos.append(p)

    # Loop 2: esperar a todos
    for p in procesos:
        p.join()

    total = round(time.time() - inicio, 2)
    print(f"\n[Main] todos terminaron | tiempo total: {total}s")