# Fase 0 — Tarea 0.7

## Congelación del primer conjunto de entrada real para AFINO-public

**Estado:** completada por el script de congelación  
**Series generadas:** 8  
**Ventana:** `tau0_published`  
**AFINO ejecutado:** no  
**Manifiesto SHA-256:** `38b9a47929fcde55ef94e197270c7782906f44080b0aead00b09dccded1e7c5d`

---

## A. Tabla resumen de las ocho series

| Serie | N usado | Flujo | Política QUALITY | Tiempo mínimo | Tiempo máximo | Cadencia mediana (s) | Máx. gap (s) | Observaciones |
|---|---:|---|---|---:|---:|---:|---:|---|
| `fase0_tarea07_published_qpp_sap_all.csv` | 14 | SAP_FLUX | finite_all | 2505.134772041 | 2505.137781604 | 20.002015 | 20.002015 | Fuente con warning de checksum heredado de F0.6. |
| `fase0_tarea07_published_qpp_sap_q0.csv` | 14 | SAP_FLUX | quality_zero_only | 2505.134772041 | 2505.137781604 | 20.002015 | 20.002015 | Idéntica a finite_all: todas las cadencias tienen QUALITY=0. Fuente con warning de checksum heredado de F0.6. |
| `fase0_tarea07_published_qpp_pdcsap_all.csv` | 14 | PDCSAP_FLUX | finite_all | 2505.134772041 | 2505.137781604 | 20.002015 | 20.002015 | Fuente con warning de checksum heredado de F0.6. |
| `fase0_tarea07_published_qpp_pdcsap_q0.csv` | 14 | PDCSAP_FLUX | quality_zero_only | 2505.134772041 | 2505.137781604 | 20.002015 | 20.002015 | Idéntica a finite_all: todas las cadencias tienen QUALITY=0. Fuente con warning de checksum heredado de F0.6. |
| `fase0_tarea07_notselected_sap_all.csv` | 14 | SAP_FLUX | finite_all | 2535.256432072 | 2535.259441595 | 20.001761 | 20.001761 | Conserva una cadencia con QUALITY=64. |
| `fase0_tarea07_notselected_sap_q0.csv` | 13 | SAP_FLUX | quality_zero_only | 2535.256432072 | 2535.259441595 | 20.001761 | 40.003503 | Elimina la cadencia QUALITY=64; mantiene su índice original sin renumerar. |
| `fase0_tarea07_notselected_pdcsap_all.csv` | 14 | PDCSAP_FLUX | finite_all | 2535.256432072 | 2535.259441595 | 20.001761 | 20.001761 | Conserva una cadencia con QUALITY=64. |
| `fase0_tarea07_notselected_pdcsap_q0.csv` | 13 | PDCSAP_FLUX | quality_zero_only | 2535.256432072 | 2535.259441595 | 20.001761 | 40.003503 | Elimina la cadencia QUALITY=64; mantiene su índice original sin renumerar. |

### Semántica de los recuentos

- `n_rows_original_window`: cadencias con `TIME` finito dentro de la ventana
  publicada inclusiva, antes de filtrar flujo o QUALITY.
- `n_finite_flux`: valores finitos del flujo elegido dentro de esa ventana,
  antes de aplicar la política QUALITY.
- `n_quality_zero` y `n_quality_nonzero`: recuentos en el CSV de salida.
- `fully_covered`: cobertura archivística de la ventana demostrada en F0.6;
  una eliminación causada por `quality_zero_only` se refleja en `max_gap_s`,
  pero no se reinterpreta como un gap del archivo fuente.

---

## B. Diferencias relevantes

### ¿Cuántas series cambian al pasar de `finite_all` a `quality_zero_only`?

Cambian **2 de las 4 comparaciones evento–flujo**:
not_selected_qpp / SAP_FLUX, not_selected_qpp / PDCSAP_FLUX. En la detección publicada, los CSV `all` y `q0` de cada
flujo son byte a byte idénticos y comparten SHA-256.

### ¿Dónde aparece `QUALITY != 0`?

El único valor no nulo aparece en el evento `not_selected_qpp` del sector 45:
una cadencia con `QUALITY=64`. Las variantes `finite_all` la conservan y las
variantes `quality_zero_only` la eliminan.

### ¿SAP y PDCSAP tienen el mismo número de muestras utilizables?

Sí. Para una misma combinación de evento y política, SAP y PDCSAP tienen el
mismo número de filas: 14 en todas las variantes `finite_all`, 14 en las
variantes `q0` del publicado y 13 en las variantes `q0` del no seleccionado.

### ¿Alguna variante queda con menos de 10 cadencias?

No. El mínimo es **13 cadencias**.

### ¿Debe descartarse ya alguna serie?

No. Las ocho cumplen las reglas fijadas. El warning de checksum del sector 44
se conserva en las notas y afecta a las cuatro variantes publicadas, pero no
justifica eliminar selectivamente una combinación de flujo o calidad en esta
fase.

---

## C. Diagnóstico

La matriz piloto queda suficientemente congelada para una primera reproducción:
existen ocho archivos con nombres estables, hashes individuales, ventana
temporal idéntica a la publicada y reglas de inclusión definidas antes de
ejecutar AFINO. Las diferencias entre variantes proceden únicamente del flujo
elegido y de la política de calidad. No se han modificado los tiempos, las
unidades ni los valores de flujo, y los índices conservan su posición original
dentro de cada ventana.

Esta tarea no resuelve todavía qué flujo representa mejor el análisis del
artículo, si QUALITY=64 debe excluirse, cómo transformar las curvas para el
formato esperado por AFINO, ni si serán necesarias normalización, eliminación
del perfil de flare o extensiones temporales. Tampoco resuelve el aviso de
checksum del sector 44; se conserva como riesgo de procedencia, aunque el
archivo utilizado está fijado mediante SHA-256.

Como punto de partida operativo, PDCSAP_FLUX con `finite_all` parece la variante
más cercana a una futura reproducción piloto: utiliza el flujo ya corregido por
SPOC y evita introducir todavía una decisión adicional sobre quality flags.
Esto no implica que sea la combinación correcta ni que coincida con el
preprocesamiento del estudio. SAP y las variantes `quality_zero_only` deben
ejecutarse después como comparaciones predefinidas, no como ajustes elegidos
según el resultado. El conjunto queda así preparado para evaluar sensibilidad
a decisiones concretas sin alterar retrospectivamente las entradas.

**Extensión:** 222 palabras.

---

## D. Reglas congeladas

1. Ventana inclusiva exacta entre inicio y final publicados.
2. Sin extensiones temporales.
3. Sin conversión del tiempo TBJD.
4. Sin normalización o centrado del flujo.
5. Sin suavizado, interpolación ni detrending manual.
6. `finite_all`: flujo finito, sin excluir flags.
7. `quality_zero_only`: flujo finito y `QUALITY == 0`.
8. El índice de cadencia no se renumera tras el filtrado.
9. SAP y PDCSAP se guardan en archivos separados.
10. AFINO no se ejecuta durante F0.7.

---

## E. Archivos congelados

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea07_published_qpp_sap_all.csv` | `a2ba27fe6ec8e11e2e5c8c8a273585c86cd2325260d9b23769af9052a7c214e6` |
| `fase0_tarea07_published_qpp_sap_q0.csv` | `a2ba27fe6ec8e11e2e5c8c8a273585c86cd2325260d9b23769af9052a7c214e6` |
| `fase0_tarea07_published_qpp_pdcsap_all.csv` | `aeed2423e0f032ce2edfb599cbbfada7da704cd19f237950eaac9db96fc967bd` |
| `fase0_tarea07_published_qpp_pdcsap_q0.csv` | `aeed2423e0f032ce2edfb599cbbfada7da704cd19f237950eaac9db96fc967bd` |
| `fase0_tarea07_notselected_sap_all.csv` | `7921f8f3f1453266d2d41de2bc731f4db8f2d27fae7bf3756b635f5212875a46` |
| `fase0_tarea07_notselected_sap_q0.csv` | `f0be3b0569c302e9408f5f2d3ecb7b34a6c0f5bc5a15781d717a25cbbd5faee6` |
| `fase0_tarea07_notselected_pdcsap_all.csv` | `8f7f0a8e439afc7d1b8cc74b85ec61c7dab37af1196dff99686ea8a5ef1c5da8` |
| `fase0_tarea07_notselected_pdcsap_q0.csv` | `632d0de25ae989905f491205ed5ed5320b6a0da5e0d16d0810f5ebe765882df9` |

| `fase0_tarea07_pilot_input_manifest.csv` | `38b9a47929fcde55ef94e197270c7782906f44080b0aead00b09dccded1e7c5d` |

---

## F. Decisiones aún abiertas

- Flujo científico principal: SAP o PDCSAP.
- Política definitiva de QUALITY.
- Tratamiento específico de `QUALITY=64`.
- Transformación exacta requerida por AFINO-public.
- Normalización y detrending.
- Uso futuro de extensiones temporales.
- Correspondencia con el preprocesamiento no publicado del estudio.
- Resolución definitiva del warning de checksum del sector 44.

Ninguna de estas decisiones modifica los ocho archivos congelados.
