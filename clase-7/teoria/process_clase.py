import multiprocessing
import time

class MiWorker(multiprocessing.Process):
    def __init__(self, nombre, duracion):
        super().__init__()
        self.nombre = nombre
        self.duracion = duracion

    def run(self):
        """Se ejecuta automáticamente al llamar start()"""
        print(f"[{self.nombre}] arranco")
        time.sleep(self.duracion)
        print(f"[{self.nombre}] termino")

if __name__ == "__main__":
    w = MiWorker("Worker-1", 2)
    w.start()
    w.join()