import multiprocessing
import time
import random

def worker(id):
    print(f"[Worker-{id}] arranca")
    time.sleep(random.uniform(0.5, 2))
    print(f"[Worker-{id}] termina")

if __name__ == "__main__":
    procesos = []
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        p.start()
        procesos.append(p)

    for p in procesos:
        p.join()

    print("[Main] todos terminaron")