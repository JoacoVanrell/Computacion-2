import threading
import time

def tarea(nombre, duracion):
    print(f"[{nombre}] Iniciando...")
    time.sleep(duracion)
    print(f"[{nombre}] Terminado!")

# Crear threads
t1 = threading.Thread(target=tarea, args=("Thread-1", 2))
t2 = threading.Thread(target=tarea, args=("Thread-2", 1))

# Demostrar que el objeto existe ANTES del start
print(f"[Antes de start] t1 existe: {t1}")
print(f"[Antes de start] t1.is_alive(): {t1.is_alive()}")
print(f"[Antes de start] t1.ident: {t1.ident}")
print(f"[Antes de start] hilos vivos: {threading.enumerate()}")

# Iniciar threads
t1.start()
t2.start()

# Demostrar que ahora sí están vivos
print(f"[Después de start] t1.is_alive(): {t1.is_alive()}")
print(f"[Después de start] t1.ident: {t1.ident}")
print(f"[Después de start] hilos vivos: {threading.enumerate()}")

print("[Main] Threads iniciados")

# Esperar a que terminen
t1.join()
t2.join()

print("[Main] Todos los threads terminaron")