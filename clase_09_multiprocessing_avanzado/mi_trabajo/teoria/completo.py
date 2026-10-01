from multiprocessing import Pool
import time
import random
import os

def procesar(x):
    """Tarea con duración variable."""
    time.sleep(random.uniform(0.1, 1.0))
    print(f"[{os.getpid()}] procesó {x}")
    return x ** 2

def sumar(a, b):
    print(f"[{os.getpid()}] sumó {a} + {b}")
    return a + b

if __name__ == "__main__":
    print(f"[{os.getpid()}] main arranca")
    with Pool(4) as pool:
        # map: todos al final, en orden
        #print("=== map ===")
        #print(pool.map(procesar, range(5)))

        # imap_unordered: a medida que terminan
        #print("\n=== imap_unordered ===")
        #for r in pool.imap_unordered(procesar, range(5)):
        #    print(f"  llegó: {r}")

        # apply_async: tareas individuales con control fino
        print("\n=== apply_async ===")
        f1 = pool.apply_async(procesar, (10,))
        f2 = pool.apply_async(procesar, (10,))
        
        while not (f1.ready() and f2.ready()):
            
            if f1.ready():
                print(f"  El resultado de f1: {f1.get()}")
            if f2.ready():
                print(f"  El resultado de f2: {f2.get()}")



        # starmap: función con múltiples argumentos
        #print("\n=== starmap ===")
        #print(pool.starmap(sumar, [(1, 2), (3, 4), (5, 6)]))