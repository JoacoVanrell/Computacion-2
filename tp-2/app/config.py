"""Configuración por variables de entorno: workers, maxsize, timeout por defecto."""
import os

# Timeout de una tarea, en segundos, cuando el cliente no manda uno.
TIMEOUT_DEFECTO = float(os.environ.get('TIMEOUT_DEFECTO', '30'))
