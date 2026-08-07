# Fase 1 — Tarea 1.12

## Ejecución completa reanudable del benchmark anidado

**Estado:** `FULL_NESTED_BENCHMARK_EXECUTION_COMPLETE`  
**Runner:** `afino_checkpointed` `1.1.0`  
**Plan:** `7938` llamadas  
**Pendientes:** `0`

## Cobertura e integridad

Se confirmaron las 7.938 claves del plan congelado: 6.480 resultados primarios
y 1.458 de estabilidad, con 2.646 filas para cada uno de los modelos M0, M1 y
M2. El checkpoint, el CSV exportado y el plan contienen los mismos `job_id`, la
misma clave `(series_id, external_optimizer_seed, model_id)`, los mismos
metadatos y los mismos hashes de flujo y tiempo. No quedaron trabajos
pendientes ni aparecieron duplicados o filas ajenas al plan.

Los estados retenidos fueron:

```text
{"OK": 7938}
```

Los resultados con error numérico, si existen, permanecen como filas
confirmadas y no fueron redibujados, eliminados ni convertidos manualmente en
no selecciones.

## Decisiones

Se recalcularon independientemente 2.646 decisiones: 2.160 primarias y 486 de
estabilidad. Los deltas BIC se compararon con tolerancia absoluta `5e-12` y
tolerancia relativa cero. Los estados fueron:

```text
{"VALID": 2646}
```

Un trío incompleto conserva `INCOMPLETE_NUMERICAL` y `qpp_selected` vacío.
Esta tarea no calculó tasas por condición, trayectorias, cruces de umbral,
errores agregados de periodo ni apoyo a la hipótesis temporal.

## Reanudación

La ejecución se dividió en siete lotes de 1.000 llamadas, un lote final de 938
y una invocación de exportación con cero llamadas nuevas. La primera invocación
partió de un checkpoint inexistente y no utilizó `--resume`; todas las
posteriores sí. La historia SQLite es contigua y la última invocación confirmó
idempotencia.

## Congelación

Los cuatro hashes físicos y lógicos de F1.10 coincidieron antes y después. El
runner 1.1.0 y el plan conservaron sus hashes normativos. El checkpoint canary
permaneció separado, sin escritura ni importación, y conservó su SHA-256. AFINO
permaneció en el commit y la versión congelados, sin diferencias tracked o
staged.

## Alcance

F1.12 congela exclusivamente los resultados brutos y los controles operativos:
estados, warnings, bounds, tiempos y reanudación. No se realizó interpretación
científica del efecto de extender las ventanas. Esa evaluación corresponde a
F1.13.

## Conclusión

`FULL_NESTED_BENCHMARK_EXECUTION_COMPLETE`
