# Clase 17 — Ejercicios resueltos

> Material de estudio armado con Claude.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `comparar_analisis.py` | **Ej. 3 (obligatorio)**: select/poll/epoll con factores, ACTIVOS alto y límite exacto de select | `python3 comparar_analisis.py` |
| `chat_selectors.py` | Ej. 6: chat de un solo hilo con framing correcto, `/nick`, `/lista`, buffers de salida | `python3 chat_selectors.py` + `nc` |
| `loop_con_pool.py` | Ej. 7: el costo del hilo único y cómo resolverlo **sin** dejar el event loop | `python3 loop_con_pool.py` |

## Ej. 3 — tabla de mi máquina (µs por llamada)

```
A) 3 activos
conexiones  fd máx  select     poll   epoll
       100     201     6.1      1.7     0.7
       500    1001    27.7      6.4     0.6
      1000    2001   FALLA     24.0     0.6
      2000    4001   FALLA    111.0     0.7
      5000   10001   FALLA    280.7     0.6
  conexiones ×50 → poll ×166 · epoll ×0.8

B) la MITAD activos
      5000   10001   FALLA    347.7   227.4
  conexiones ×50 → poll ×144 · epoll ×52

select() falla con UN solo socket de fd = 1024
```

**Respuestas**
2. **poll** pasó de 1,7 a 280 µs: **×166** para ×50 conexiones (crece con el total de conexiones: es O(n); en mi corrida, incluso algo más que lineal).
3. **epoll** quedó plano (~0,6 µs) aunque haya 5000 conexiones: solo devuelve los 3 listos.
4. **select falla desde 1000 conexiones**, pero lo que importa es el **número de fd**, no la cantidad: cada conexión del
   benchmark usa 2 fds (socketpair), así que con 1000 el fd máximo ya es 2001 > 1023. Con un solo socket de fd 1024 ya falla.
5. En un servidor web la mayoría de las conexiones están **ociosas** (keep-alive esperando la próxima petición, clientes
   lentos, usuarios leyendo la página): en cada instante muy pocas tienen datos.
6. `poll` recibe **toda** la lista en cada llamada, el kernel la copia y la **recorre entera** para ver quién está listo
   → O(n). `epoll` **registra una vez**: el kernel mantiene el conjunto y una lista de "listos" que se llena cuando llegan
   datos (por interrupción), y `poll()` solo te devuelve esa lista → O(listos).
7. Con la **mitad activos**, epoll también crece (×52): ahora hay 2500 listos para devolver. **La ventaja se achica**
   porque ya no hay "muchos ociosos"; epoll brilla cuando listos ≪ total.
8–9. Con **10–100 conexiones** los tres tardan microsegundos: no vale la pena complicarse. Con pocos clientes y lógica
   compleja, **threads** (clase 14) son más simples y alcanzan.

**10. Conclusión (nginx vs Apache):** Un Apache clásico usa **un thread (o proceso) por conexión**: con 5000 conexiones
son 5000 stacks y el scheduler repartiendo CPU entre threads que en su mayoría solo esperan. nginx usa **pocos procesos,
cada uno con un event loop sobre epoll**: vigilar 5000 conexiones le cuesta lo mismo que vigilar 100 (en mi máquina,
~0,6 µs por llamada contra 280 µs de `poll`), porque el kernel le entrega directamente las pocas que tienen datos.
Por eso nginx atiende muchas más conexiones con mucha menos memoria.

## Ej. 6 — chat (prueba real)
La línea `/nick x` llegó partida en **3 `recv()`** (`"/ni"`, `"ck"`, `" x\n"`) y se procesó bien gracias al buffer de entrada.
1. **No necesita lock** porque hay **un solo hilo**: mientras una función corre, nadie más toca `clientes`. (Con threads,
   dos podrían modificar la lista o escribirle al mismo socket a la vez.)
2. `difundir()` **encola** (buffer de salida + `EVENT_WRITE`) en vez de `sendall()`: si un cliente no lee y su buffer
   del kernel está lleno, `sendall()` **bloquearía todo el loop** → los demás quedarían congelados.
5. El chat original asume "1 recv = 1 línea". Falla cuando llegan **dos líneas juntas** o **una partida** (TCP es un flujo).
- Protección extra: si a alguien se le acumula > 1 MB sin leer, se lo desconecta (la memoria crecería sin límite).

## Ej. 7 — salida real
```
sin pool  PING respondido a los 1.03s · cálculo pesado a los 1.03s    ← el PING esperó al cálculo
con pool  PING respondido a los 0.05s · cálculo pesado a los 1.01s    ← el loop siguió libre
```
**Regla:** *nada que tarde puede correr en el hilo del event loop.* **Solución sin dejar el loop:** mandar el trabajo a un
**pool de procesos** (es CPU-bound) y cuando termina avisarle al loop por un **socketpair** registrado en el selector
(el *self-pipe* de la clase 6). Es exactamente lo que hace `asyncio` con `run_in_executor` (y lo que vas a necesitar en el TP2).
Con `server_threads.py` de la clase 14 no pasaba: el SO reparte el tiempo entre threads.

## Ej. 4 y 5 (respuestas cortas)
- Con `selectors` desaparecen la lista `vigilados` y el diccionario `fd → socket`: se guarda **cualquier dato** (`data=`) junto a cada socket.
- `DefaultSelector` en Linux = **`EpollSelector`**. `SelectSelector` anda igual con pocos clientes pero hereda el límite de 1024.
- `close()` sin `unregister()` → el selector queda con un fd muerto: excepciones o eventos fantasma (y si el número se reusa, confusión total).
- `EVENT_WRITE` permanente → un socket casi siempre está listo para escribir → `select()` vuelve al instante → **100 % de CPU**.
