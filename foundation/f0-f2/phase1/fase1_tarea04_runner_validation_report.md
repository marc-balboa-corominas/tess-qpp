# Fase 1 — Tarea 1.4

## Congelación del plan y validación del runner reanudable

**Conclusión:** `RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK`  
**Runner implementation:** `1.0.1`  
**AFINO commit:** `6aceac9518fc8056052807e666da9d0c8bebb010`  
**AFINO:** `0.5`  
**Plan completo ejecutado:** no  
**Canary:** 48 llamadas  

## 1. Entorno y preflight

Se verificaron los hashes físicos y lógicos de F1.3 antes de cualquier llamada. Los tiempos persistidos se entregaron directamente en segundos relativos. El repositorio AFINO no contenía cambios tracked ni staged. El estado no versionado se conserva en la auditoría y puede incluir `afino.egg-info/`.

## 2. Plan normativo

| Bloque | Trabajos |
|---|---:|
| Primario | 13.320 |
| Estabilidad | 2.997 |
| **Plan completo** | **16.317** |
| Canary | 48 |

El plan completo conserva claves únicas `(series_id, external_optimizer_seed, model_id)` y no fue ejecutado durante F1.4.

## 3. Checkpoint y reanudación

| Pasada | Trabajos nuevos | Total confirmado |
|---|---:|---:|
| Primera (`--stop-after 17`) | 17 | 17 |
| Segunda | 31 | 48 |
| Tercera | 0 | 48 |

Duplicados: 0. Cada llamada confirmada corresponde a una transacción SQLite independiente.

## 4. Repetibilidad directa

Los seis replays predeclarados coincidieron exactamente: `6/6`. La comparación incluyó BIC, log-likelihood, parámetros, periodo formal de M1, rchi2, probabilidad, warnings y bounds.

## 5. Resultados canary

Se exportaron 48 filas de modelo y 16 decisiones únicamente para comprobar la infraestructura. No se presentan tasas de detección o selección y las decisiones canary no son elegibles para el análisis primario.

## 6. Hashes congelados

| Artefacto | SHA-256 |
|---|---|
| `fase1_tarea04_build_execution_plan.py` | `0980c0c8630106dc19627f50722ffe54c46b35d68809e6db6be651be537c79d3` |
| `fase1_tarea04_full_execution_plan.csv` | `ccc7b6232b921e6422097fa1fc2525ec7f559459994ba7dfb222dbb0abfecf03` |
| `fase1_tarea04_canary_plan.csv` | `5663ee0c5607db3764abe26f7e4e231a0b36d467714bb2f62778a3c414d47480` |
| `fase1_tarea04_run_afino_checkpointed_v2.py` | `2e35137655a6fd66cd53d76f9229024b4c74ace597c9df62479e48cefc3c84e7` |
| `fase1_tarea04_canary_checkpoint.sqlite` | `e353f3c87ed2453fbb15e8dd17d09b66591badbe0f5d6ac7313691191c8415f8` |
| `fase1_tarea04_canary_results.csv` | `02c8bb60851b79f11c353fc1f3394d46dc4a4529772813abc7bfd522d130378b` |
| `fase1_tarea04_canary_decisions.csv` | `518eb193c3158bd1aab668c05a0b5557988836d8646e01a8eae9505b5c60ba08` |
| `fase1_tarea04_environment.txt` | `5b416b49f0444a0df415b3b2d1ce13137c3a682a2695df8f2bd9033d9c16db63` |

## 7. Incidencias

No se registraron incidencias mecánicas. Los resultados científicos del canary no se utilizaron para alterar el protocolo.

## 8. Diagnóstico

La infraestructura reanudable se validó exclusivamente mediante el canary congelado de 48 llamadas. El plan completo de 16317 trabajos fue construido y auditado, pero no se ejecutó. Las entradas proceden de los cuatro payloads binarios de F1.3: sus hashes físicos y lógicos se verificaron antes de abrir el checkpoint, y cada trabajo volvió a comprobar los hashes de su flujo y su vector temporal. Los tiempos sintéticos se entregaron directamente en segundos relativos, sin aplicar la conversión observacional desde TBJD.

La primera pasada confirmó 17 trabajos y dejó 31 pendientes. La segunda añadió 31 trabajos, alcanzando las 48 filas. La tercera encontró todas las claves ya confirmadas y realizó 0 llamadas nuevas. SQLite impuso unicidad tanto sobre job_id como sobre la terna serie, semilla externa y modelo. Cada resultado, incluido un eventual estado de error, se confirmó en una transacción independiente; una interrupción anterior al commit no puede producir una fila falsamente terminada.

Las seis ejecuciones directas de replay coincidieron exactamente con sus resultados confirmados en BIC, log-likelihood, parámetros, centro formal de M1, rchi2, probabilidad, warnings y bounds. Esta igualdad valida la repetibilidad mecánica del runner para los dos extremos predeclarados del canary, no la convergencia formal del optimizador ni la unicidad global de sus soluciones. AFINO continúa etiquetado como NOT_AUDITABLE respecto a res.success y res.message.

Las 16 decisiones del canary se exportaron únicamente para comprobar agrupación, regla doble BIC y etiquetado del centro de M1. No se calcularon ni interpretaron tasas de detección o selección, y estos resultados no son elegibles para el análisis primario de F1.5. No se modificaron código AFINO, dataset, bounds, cutoff, semillas ni reglas después de observar el canary. El runner y ambos planes quedan congelados; F1.5 deberá usar un checkpoint nuevo y el plan completo, conservando este checkpoint canary por separado.

## 9. Conclusión

`RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK`
