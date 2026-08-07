# Fase 1 — Tarea 1.11

## Congelación del plan y validación del runner anidado reanudable

**Conclusión:** `NESTED_RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK`  
**Runner:** `afino_checkpointed` `1.1.0`  
**AFINO:** `6aceac9518fc8056052807e666da9d0c8bebb010` / `0.5`  
**Benchmark completo ejecutado:** no

## Plan e inputs

El plan normativo contiene exactamente 7.938 trabajos: 6.480 primarios y 1.458 de estabilidad. M0, M1 y M2 tienen 2.646 filas cada uno y las claves `(series_id, external_optimizer_seed, model_id)` son únicas. Antes y después del canary coincidieron los hashes físicos de F1.8 y F1.10 y los cuatro hashes lógicos del dataset. El runner leyó exclusivamente los cuatro arrays `.npy` con `allow_pickle=False`; entregó a AFINO los vectores temporales persistidos directamente en segundos, sin reconstrucción ni conversión TBJD.

## Adaptación del runner

La versión 1.1.0 se comparó con el runner 1.0.1. Los cambios quedaron clasificados como `dataset_contract`, `metadata`, `output_naming` y `job_counts`. La importación de AFINO, los tres modelos, los bounds, el cutoff de 1/40 Hz, el reinicio de la semilla, la captura de warnings, el diagnóstico de bounds, la regla doble BIC y la transacción SQLite por llamada permanecieron sin cambios. Las comprobaciones automáticas del núcleo científico fueron todas satisfactorias.

## Canary y reanudación

El canary resolvió doce series: seis prefijos del padre nulo con alpha 0 y seis del padre positivo P=80 s, q=0,04 y alpha 2. Se verificaron 12/12 hashes de flujo, 12/12 hashes temporales, 12/12 enlaces con la serie N=120 y las diez relaciones adyacentes. La primera pasada confirmó 23 llamadas y dejó 49 pendientes; la segunda añadió 49 y alcanzó 72; la tercera añadió cero. No aparecieron duplicados.

Los 72 resultados fueron OK y produjeron 24 decisiones VALID. Para N=15, 30, 45, 60, 90 y 120 quedaron respectivamente 7, 14, 22, 29, 44 y 59 bins tras el cutoff, coherentes con la lectura directa de tiempos en segundos. Los seis replays predeclarados coincidieron exactamente en estado, BIC, likelihood, parámetros, periodo formal, rchi2, probabilidad, warnings, bounds y error.

## Alcance y cierre

Los resultados canary no son elegibles para el análisis científico y no se utilizaron para ajustar el protocolo. No se ejecutó ninguna fila fuera del plan canary ni se modificaron AFINO, el dataset, el prerregistro o el runner 1.0.1. El runner 1.1.0 y los dos planes quedan congelados para F1.12.

## Conclusión

`NESTED_RUNNER_VALIDATED_BEFORE_FULL_BENCHMARK`
