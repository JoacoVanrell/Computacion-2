---- BORRADOR ----
"elegí curses porque necesito input de teclado no bloqueante para los keybindings, y rich no lo provee".
"""
La solución es una línea en el docker-compose.yml: pid: "host". Eso hace que el contenedor comparta el PID namespace del host, y ahí /proc te muestra todos los procesos de tu Ubuntu.
"""
¿cómo manejaste las race conditions?": Al leer /proc no verifico existencia antes de abrir (patrón TOCTOU): un proceso puede morir entre el chequeo y la lectura. Uso try/except FileNotFoundError y descarto el PID de ese ciclo.
Además de R/S/D/T/Z, muestro I (idle kernel thread, no cuenta para el load average) y t (traced) porque aparecen en sistemas reales.

Ciclo 0 todo en 0.0% — como estaba previsto. Sin lectura anterior no hay delta. Ese detalle va al README: la primera muestra siempre es basura y por eso el monitor arranca mostrando ceros.
en estado D. Ese es de los cinco que pide la consigna y es el más raro de los cinco. D = uninterruptible sleep: el proceso está esperando I/O y el kernel no lo despierta ni le entrega señales.