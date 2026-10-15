"""Configuración por variables de entorno: workers, maxsize, timeout por defecto."""
import os

# Timeout de una tarea, en segundos, cuando el cliente no manda uno.
TIMEOUT_DEFECTO = float(os.environ.get('TIMEOUT_DEFECTO', '30'))

# Cuántos workers consumen de la cola a la vez.
WORKERS = int(os.environ.get('WORKERS', '4'))

# Lugares en la cola. Si se llena, el POST responde 503.
MAXSIZE_COLA = int(os.environ.get('MAXSIZE_COLA', '100'))
