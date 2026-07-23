import multiprocessing
import os
import time

def tarea(nombre):
    print(f"[{nombre}] PID={os.getpid()}, padre={os.getppid()}")
    time.sleep(2)
    print(f"[{nombre}] terminó")

if __name__ == "__main__":
    p = multiprocessing.Process(target=tarea, args=("Worker",))
    p.start()
    p.join()
    print(f"[Main] hijo terminó con código {p.exitcode}")

"""
La diferencia clave es que fork() te da el mecanismo crudo — vos manejás todo. 
multiprocessing.Process te da una abstracción:solo definís qué hacer,no cómo crear/esperar el proceso."""