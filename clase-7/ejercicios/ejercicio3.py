import multiprocessing
import os
import time
import random

def productor(q):
    print(f"[Productor] PID={os.getpid()} | arrancando")
    for i in range(10):
        item = f"item-{i}"
        time.sleep(random.uniform(0.1, 0.4))  # simula tiempo de generación
        q.put(item)
        print(f"[Productor] puso: {item}")
    
    q.put(None)  # señal de fin
    print(f"[Productor] terminó, mandó señal de fin")

def consumidor(q):
    print(f"[Consumidor] PID={os.getpid()} | arrancando")
    procesados = 0

    while True:
        item = q.get()         # bloquea hasta que haya algo
        if item is None:       # señal de fin
            break
        time.sleep(random.uniform(0.1, 0.3))  # simula procesamiento
        print(f"[Consumidor] procesó: {item}")
        procesados += 1

    print(f"[Consumidor] terminó | procesó {procesados} items")

if __name__ == "__main__":
    q = multiprocessing.Queue()

    p_prod = multiprocessing.Process(target=productor, args=(q,))
    p_cons = multiprocessing.Process(target=consumidor, args=(q,))

    inicio = time.time()

    p_prod.start()
    p_cons.start()

    p_prod.join()
    p_cons.join()

    total = round(time.time() - inicio, 2)
    print(f"\n[Main] todo terminó en {total}s")