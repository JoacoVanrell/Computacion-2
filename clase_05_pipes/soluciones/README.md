# Clase 5 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu `mini_shell.py` en `../mi_trabajo/` estaba vacío; acá está resuelto.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `minish.py` | **Ej. 5 (obligatorio)**: shell con `>` + bonus `<`, `>>` + extras `2>` y pipelines `a \| b \| c` | `python3 minish.py` |
| `mi_tee.py` | Adicional: `tee` casero | `ls -la \| python3 mi_tee.py salida.txt` |
| `monitor_pipe.py` | Adicional: monitor en el medio de un pipeline | `cat /etc/services \| python3 monitor_pipe.py \| wc -l` |

## Verificación del obligatorio (salida real)

```
minish$ echo "hola mundo" > test.txt
minish$ cat test.txt
hola mundo
minish$ echo otra >> test.txt
minish$ wc -l < test.txt
2
minish$ ls /etc | grep -c conf
28
minish$ ls /noexiste 2> err.txt
[código 2]
minish$ echo "a | b"          ← entre comillas NO es un pipe
a | b
```

## Lo que tenés que poder explicar

1. **Cómo funciona `>`:** en el **hijo**, antes del `exec`: `fd = open(archivo)`, `dup2(fd, 1)`, `close(fd)`.
   El programa nuevo escribe en el fd 1 "como siempre" y no sabe que es un archivo.
2. **Por qué en el hijo y no en el padre:** si el padre hace `dup2(fd, 1)`, el *shell* pierde su stdout.
3. **`O_TRUNC` vs `O_APPEND`:** `>` vacía el archivo; `>>` escribe al final.
4. **Pipeline de N comandos:** N-1 pipes; el hijo `i` hace `dup2(pipe[i-1].lectura, 0)` y `dup2(pipe[i].escritura, 1)`.
5. **El bug clásico:** si algún proceso (¡incluido el padre!) deja abierto un extremo de **escritura**,
   el lector **nunca recibe EOF** y el pipeline se cuelga. Por eso cada hijo cierra *todos* los fds de los
   pipes después del `dup2`, y el padre cierra todos los suyos.
6. **Por qué el monitor imprime por stderr:** stdout es *el dato* que lee el siguiente comando; si
   mezclás estadísticas ahí, `wc -l` las cuenta.
7. **`mi_tee` con `| head`:** cuando `head` termina, nuestro `write` a stdout tira `BrokenPipeError`
   (SIGPIPE): no hay lectores. Lo atrapamos y salimos tranquilos.

## Ejercicio 7 (FIFO) — qué pasa y por qué
- `open(FIFO, 'w')` **bloquea** hasta que alguien lo abra para leer (y viceversa): es un punto de encuentro.
- El lector termina el `for` cuando el escritor **cierra** (EOF), igual que con un pipe anónimo.
- A diferencia de `pipe()`, el FIFO tiene **nombre en el filesystem**, por eso lo pueden usar procesos que no son parientes.
