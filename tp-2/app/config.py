"""Configuración por variables de entorno: workers, maxsize, timeout por defecto."""
import os

# Timeout de una tarea, en segundos, cuando el cliente no manda uno.
TIMEOUT_DEFECTO = float(os.environ.get('TIMEOUT_DEFECTO', '30'))

# Cuántos workers consumen de la cola a la vez.
WORKERS = int(os.environ.get('WORKERS', '4'))

# Lugares en la cola. Si se llena, el POST responde 503.
MAXSIZE_COLA = int(os.environ.get('MAXSIZE_COLA', '100'))

# Procesos del pool para hashear. Por defecto, uno por núcleo.
PROCESOS = int(os.environ.get('PROCESOS', os.cpu_count()))

# 1 = hashear en el ProcessPoolExecutor (lo correcto).
# 0 = hashear dentro del event loop, para la medición 2.
USAR_EXECUTOR = os.environ.get('USAR_EXECUTOR', '1') == '1'

# 0 = descargar las URLs con gather (lo correcto).
# 1 = una atrás de la otra con for + await, para la medición 1.
DESCARGA_SECUENCIAL = os.environ.get('DESCARGA_SECUENCIAL', '0') == '1'

# Cuánto esperar, al apagar, a que terminen las tareas en curso.
# Tiene que ser MENOR que los 10 s que da Docker antes de matar el
# proceso, para que quede tiempo de escribir el JSON.
LIMITE_APAGADO = float(os.environ.get('LIMITE_APAGADO', '5'))

# Carpeta de los estado_<timestamp>.json (en Docker, un volumen).
DIR_ESTADOS = os.environ.get('DIR_ESTADOS', 'estados')
