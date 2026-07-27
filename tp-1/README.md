---- BORRADOR ----
"elegí curses porque necesito input de teclado no bloqueante para los keybindings, y rich no lo provee".
"""
La solución es una línea en el docker-compose.yml: pid: "host". Eso hace que el contenedor comparta el PID namespace del host, y ahí /proc te muestra todos los procesos de tu Ubuntu.
"""
¿cómo manejaste las race conditions?": Al leer /proc no verifico existencia antes de abrir (patrón TOCTOU): un proceso puede morir entre el chequeo y la lectura. Uso try/except FileNotFoundError y descarto el PID de ese ciclo.
Además de R/S/D/T/Z, muestro I (idle kernel thread, no cuenta para el load average) y t (traced) porque aparecen en sistemas reales.

Ciclo 0 todo en 0.0% — como estaba previsto. Sin lectura anterior no hay delta. Ese detalle va al README: la primera muestra siempre es basura y por eso el monitor arranca mostrando ceros.
en estado D. Ese es de los cinco que pide la consigna y es el más raro de los cinco. D = uninterruptible sleep: el proceso está esperando I/O y el kernel no lo despierta ni le entrega señales.

un thread comparte el mismo PID que su proceso; solo un proceso nuevo tiene PID propio.

Memoria normal (COW): cuando el proceso hijo nace por fork, el kernel marca las páginas de memoria del padre como copy-on-write — ambos procesos apuntan a las mismas páginas físicas, pero en cuanto cualquiera de los dos escribe, el kernel copia esa página y a partir de ahí cada uno tiene su propia versión. Por eso una variable Python común diverge: escribís en el padre, el hijo se queda con la copia vieja.

Value('d') (memoria compartida real): multiprocessing.Value no crea una variable Python en el heap normal. Internamente pide memoria con mmap usando la bandera MAP_SHARED — un mapeo que el sistema operativo trata distinto a propósito: nunca se copia. Cuando el padre hace fork(), el hijo hereda ese mismo mapeo apuntando a las mismas páginas físicas de RAM, y esas páginas quedan marcadas para que cualquier escritura de cualquiera de los dos procesos se vea reflejada en el otro inmediatamente, sin copia de por medio. Es la única excepción a COW en todo este esquema.

(Dato extra para el README: por eso Value/Array traen un Lock asociado por default — como la memoria es realmente compartida, dos procesos escribiendo al mismo tiempo es una race condition de verdad, igual que con threads.)

¿Por qué Value "cruza" la frontera entre procesos a pesar de COW?
No guarda la información como una variable normal" es cierto pero es la conclusión, no la razón. Si te preguntan "¿por qué?", tenés que poder decir: porque Value pide memoria con mmap en modo MAP_SHARED, y ese tipo de mapeo el kernel nunca lo copia en el fork() — a diferencia de la memoria normal (COW), que sí se copia en cuanto alguien escribe. Practicá decir esa cadena completa: mmap → MAP_SHARED → no hay copia → por eso el hijo ve los cambios del padre.
¿Por qué mutar snapshot['resumen']['datos'][pid] = x no le llega al Manager, pero snapshot['resumen'] = {...} sí?
No se lo comunica al servidor" es la conclusión. La razón específica: snapshot[nombre] no te da el objeto real, te da una copia que llegó por pickle a través de una llamada IPC al proceso servidor del Manager. Mutás esa copia local, y como nunca volvés a llamar a snapshot[nombre] = ..., el proxy nunca dispara el mensaje que le avisaría al servidor.

¿Por qué Queue es la herramienta correcta para que 7 analizadores le manden datos a 1 agregador?
Una pila es LIFO (el último que entra es el primero que sale — como pensarías la pila de platos). Vos mismo dijiste antes, correctamente, que Queue es FIFO (el primero que entra es el primero que sale). Es una cola, no una pila. Es un error común pero en la corrección oral te lo van a marcar.

salieron 110 procesos en vez de los 332 que vimos con memoria — eso es porque /proc/<pid>/fd/ de procesos de otros usuarios te tira PermissionError (no podés ver los FDs ajenos sin privilegios), y ese try/except los está salteando en silencio.