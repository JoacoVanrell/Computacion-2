# Clase 7 — Ejercicios resueltos

> Material de estudio armado con Claude. Tu `obligatorio.py` en `../mi_trabajo/` estaba vacío; acá está resuelto.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `obligatorio_value_array.py` | **Ej. 5 (obligatorio)**: race con `Value` + tarea con `Array('d')` y bonus de la suma | `python3 obligatorio_value_array.py` |
| `banco.py` | Ejercicio de síntesis: banco con race y versión segura + log | `python3 banco.py` / `python3 banco.py --seguro` |
| `mmap_regiones.py` | Ej. 3.2: varios hijos en regiones separadas de un `mmap` anónimo | `python3 mmap_regiones.py` |

## Salida real

```
[A SIN lock] esperado 400000, obtenido 149638, perdidos 250362     ← ¡se perdieron más de la mitad!
[A CON lock] esperado 400000, obtenido 400000, perdidos 0
[B] errores en el array: 0   (cada proceso escribe SU porción → no hay race)
[B SIN lock] suma esperada 45.548651, obtenida 45.548651

banco.py --n 20000          Total: 8404 (esperado 5000) ✗ diferencia 3404   ← apareció plata
banco.py --n 20000 --seguro Total: 5000 (esperado 5000) ✓
```

## Lo que hay que entender

1. **¿Por qué `contador.value += 1` pierde incrementos?** Son 3 pasos: *leer* → *sumar* → *escribir*.
   Si dos procesos leen el mismo valor (ej. 41) antes de que alguno escriba, los dos escriben 42: se perdió uno.
2. **¿Por qué el `Array` de la parte B no tiene errores?** Cada proceso escribe índices **distintos**.
   Una race necesita que dos procesos toquen **el mismo dato** y al menos uno escriba.
3. **¿Y la suma "SIN lock" de la parte B salió bien?** Con solo 100 sumas la ventana de choque es chiquita
   y casi nunca se nota… **pero el código igual es incorrecto**. Que no falle en tu prueba no lo hace seguro.
4. **Mejor patrón para la suma:** cada proceso acumula en una variable **local** y suma al `Value` **una sola vez**
   dentro del lock. Menos tiempo con el lock tomado = menos espera.
5. **Banco:** el `if saldo >= monto` y las dos escrituras tienen que estar **juntos** en la sección crítica.
   Si solo protegés las escrituras, dos cajeros pueden pasar el `if` con el mismo saldo y dejarlo negativo.
6. **`Array(..., lock=False)`:** por defecto `Value`/`Array` vienen con un lock **interno** que protege *cada*
   lectura/escritura individual, pero **no** el `+=` (que son dos operaciones). Lo desactivé para que la race se vea bien;
   para protegerlo de verdad se usa `with x.get_lock():` o un `Lock()` propio.
7. **mmap anónimo + fork:** `mmap(-1, n)` es memoria sin archivo; el hijo la hereda **compartida**
   (no copy-on-write), por eso lo que escribe el hijo lo ve el padre.

## Tarea 4 del banco: ¿cómo lo resolverías?
Con un `Lock` alrededor de la transferencia completa (lo hace `--seguro`). Variante más fina: un lock **por cuenta**
(más paralelismo), pero entonces hay que tomarlos **siempre en el mismo orden** (ej. el índice menor primero)
para no caer en un **deadlock** → clase 11.
