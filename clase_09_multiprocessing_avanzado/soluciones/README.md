# Clase 9 — Ejercicios resueltos

> Material de estudio armado con Claude. Tus pruebas de Pool están en `../mi_trabajo/`.

| Archivo | Ejercicio | Correr |
|---|---|---|
| `procesador_imagenes.py` | **Ej. 5 (obligatorio)**: blur 3×3 con `Pool.map`, speedup y verificación | `python3 procesador_imagenes.py --workers 4` |
| `mapreduce_archivo.py` | Ej. 6 + **extensión**: Map-Reduce sobre un archivo grande en chunks | `python3 mapreduce_archivo.py [archivo.txt]` |
| `pipeline_escalado.py` | Ej. 7 + respuesta a "¿cómo escalarías la etapa lenta?" | `python3 pipeline_escalado.py --lentos 4` |

## Resultados reales (mi máquina tiene solo 2 CPUs)

```
procesador_imagenes.py --size 400 --workers 2
  Secuencial: 0.28s
  Pool(1): 0.28s  speedup 1.00x  eficiencia 100%   resultado idéntico ✓
  Pool(2): 0.20s  speedup 1.44x  eficiencia  72%   resultado idéntico ✓

mapreduce_archivo.py (15.7 MB)   Secuencial 0.68s · Pool(2) 0.47s · speedup 1.46x

pipeline_escalado.py --lentos 1   20 resultados: 4.06s
pipeline_escalado.py --lentos 4   20 resultados: 1.12s   ← 3.6× más rápido escalando SOLO la etapa lenta
```
En tu notebook (más núcleos) el speedup debería ser mayor. Probá `--workers 1, 2, 4, 8` y anotá cuándo deja de mejorar.

## Lo que hay que saber explicar

**¿Por qué el speedup no es igual a la cantidad de workers?**
1. **Pickle:** cada imagen viaja del padre al worker serializada (y el resultado vuelve). Por eso el worker devuelve
   solo métricas y no la imagen filtrada entera.
2. Arrancar el `Pool` cuesta (crear procesos).
3. Si hay más workers que **núcleos**, se pelean por la CPU.
4. Lo que queda secuencial (crear imágenes, el reduce) no se acelera → **Ley de Amdahl**.

**¿Por qué `procesar_imagen` recibe una tupla?** `Pool.map` pasa **un solo argumento** por tarea. Para varios: `starmap`.

**Map-Reduce:**
- `imap_unordered` porque el orden no importa (sumar es conmutativo) y no espera al chunk más lento.
- `chunks()` es un **generador**: el archivo nunca se carga entero en memoria.
- `Counter + Counter` suma las cuentas → el reduce es trivial.
- Chunk muy chico = mucho overhead de pickle por tarea; chunk muy grande = mal reparto de trabajo.

**Pipeline — "¿qué pasa si una etapa es mucho más lenta?"** Se vuelve el **cuello de botella**: las etapas rápidas
terminan y quedan esperando, y la cola de entrada de la lenta crece (más memoria).
**"¿Cómo la escalarías?"** Poniendo **K procesos** leyendo de la misma cola. Hay que ajustar los centinelas:
la etapa anterior manda **K** `None`, y la siguiente espera **K** `None` antes de terminar.
Costo: se pierde el **orden** de salida (si importa, hay que numerar los items y reordenar al final).
