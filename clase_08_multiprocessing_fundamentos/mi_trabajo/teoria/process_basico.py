import multiprocessing
import os
import time

def tarea(nombre):
    print(f"[{nombre}] PID={os.getpid()}, parent={os.getppid()}")
    time.sleep(2)
    print(f"[{nombre}] termino")

if __name__ == "__main__":
    p = multiprocessing.Process(target=tarea, args=("Worker",))
    p.start()         # arranca el proceso
    p.join()          # espera a que termine
    print(f"[Main] PID={os.getpid()}, hijo terminó con exitcode={p.exitcode}")