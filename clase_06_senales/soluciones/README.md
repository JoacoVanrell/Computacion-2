# Clase 6 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu `servidor_signals.py` en `../mi_trabajo/` estaba vacío; acá está resuelto.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `servidor_signals.py` | **Ej. 5 (obligatorio)**: servidor con HUP / USR1 / USR2 / TERM | `python3 servidor_signals.py` y en otra terminal `kill -USR1 <pid>` |
| `supervisor.py` | Ej. 6: supervisor que reinicia workers que mueren | `python3 supervisor.py --workers 3` y `kill -9 <pid worker>` |
| `timeout_alarm.py` | Ej. 4: timeout con `SIGALRM` como context manager | `python3 timeout_alarm.py` |

## Prueba real del obligatorio

```
Servidor iniciado (PID 773)
[SIGUSR1] uptime=0.6s requests=6 errores=0 config={'max_conexiones': 7, ...}
[SIGHUP]  config recargada: {'max_conexiones': 50, ...}      ← releyó config.json
[SIGUSR2] log rotado → server.log.1790897583                  ← quedó server.log nuevo + el viejo
[SIGTERM] shutdown solicitado
cleanup… requests procesadas: 15
```

## Mejoras respecto del esqueleto (y por qué) — buenas para la defensa

1. **Patrón flag:** los handlers solo hacen `self.pendientes.add(sig)`. El trabajo (print, abrir archivos,
   renombrar) se hace en el loop principal. Una señal puede llegar *en medio* de un `print` o un `write`;
   repetir esas operaciones dentro del handler puede corromper buffers (no son *async-signal-safe*).
2. **SIGHUP relee de verdad** un `config.json` (y si está roto, conserva la config anterior).
3. **SIGUSR2 rota de verdad:** cierra el log, `os.rename` (atómico, solo cambia el nombre → inodo) y abre uno nuevo.
4. En el **supervisor**, al llegar SIGCHLD se hace `waitpid(-1, WNOHANG)` **en bucle**: si mueren dos hijos
   casi juntos, puede llegar **una sola** SIGCHLD (las señales estándar **no se encolan**).
5. Los workers **ignoran SIGINT**: cuando apretás Ctrl+C la terminal manda SIGINT a **todo el grupo de procesos**;
   así el único que decide es el supervisor, que después manda SIGTERM ordenado a cada worker.
6. `setitimer` en vez de `alarm` porque acepta decimales, y siempre se **cancela en el `finally`**.

## Respuestas cortas (ejercicios 1–3)
- `kill -l` lista las señales; `kill <pid>` sin número manda **SIGTERM (15)**.
- `kill -9` no se puede capturar ni ignorar: el proceso **no puede hacer limpieza**. Por eso primero se usa SIGTERM.
- `signal.pause()` duerme hasta que llegue una señal (sin gastar CPU).
- Si el padre manda la señal **antes** de que el hijo registre su handler, el hijo muere con la acción por
  defecto (para SIGUSR1 = terminar). Por eso en el ejemplo hay un `sleep(1)` (en serio se sincroniza con un pipe).
