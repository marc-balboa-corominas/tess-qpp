# F3A.3 — Validación canary/checkpointed del runner catalogue-scale

## 1. Función del canary

F3A.3 valida operativamente el runner que consumirá el plan F3A.2, sin autorizar todavía la ejecución científica completa. El canary fue congelado prospectivamente antes de la primera llamada AFINO y contiene 34 decisiones, equivalentes a 102 llamadas de modelo. Su selección depende únicamente de metadatos pre-ejecución y no de BIC, warnings, bounds, selección QPP, periodos o tiempos de ejecución.

## 2. Cobertura estructural

El subset contiene 30 decisiones PRIMARY y 4 STABILITY. Cubre los dos roles observacionales, las 13 ventanas y los seis perfiles de procesamiento. Las longitudes de entrada abarcan desde 15 hasta 222 cadencias. Las cuatro decisiones de estabilidad corresponden a seeds 1 y 9 de los anchors W00/P00 previamente fijados; la seed 0 de cada anchor ya pertenece a PRIMARY.

## 3. Integridad de payloads

Cada job consumió exclusivamente los arrays persistidos en F3A.2. Antes de ejecutar un modelo se verificaron `payload_id`, `variant_id`, offset, longitud y hashes físicos/lógicos. El checkpoint contiene 0 discrepancias de identidad. El runner no abrió FITS, no reaplicó QUALITY, no recalculó detrending, no regeneró variantes, no interpoló y no rellenó gaps.

## 4. Runner y checkpoint

El checkpoint SQLite utiliza `job_id` como clave primaria y una restricción adicional sobre `variant_id × external_optimizer_seed × model_id`. Cada llamada completada se confirma en una transacción independiente. El entorno ejecutado fue Python 3.13.13, NumPy 2.5.1, SciPy 1.18.0 y AFINO 0.5 en el commit `6aceac9518fc8056052807e666da9d0c8bebb010`. Los diffs tracked y staged del repositorio AFINO fueron cero.

## 5. Test de reanudación

Las cuatro invocaciones registradas siguieron exactamente la secuencia 37 + 41 + 24 + 0. La primera terminó deliberadamente en mitad de una decisión, porque 37 no es múltiplo de tres. La segunda conservó las 37 filas existentes y añadió 41; la tercera conservó 78 y añadió 24; la cuarta encontró los 102 jobs ya presentes y añadió cero. No existen `job_id` ni claves científicas duplicadas.

## 6. Contrato temporal

El diagnóstico temporal se realizó sobre las 34 decisiones, reutilizando sus payloads congelados. El criterio normativo es la implementación efectiva AFINO 0.5: `mean(diff(time_seconds))` y frecuencias estrictamente positivas de `np.fft.fftfreq`. Coincidieron 34/34 decisiones para la cadencia media y 34/34 para el conteo de bins positivos. El control histórico basado en mediana y `rfftfreq` se conserva únicamente como diagnóstico: produjo 0/34 y 13/34 coincidencias, sin intervenir en el pass/fail.

## 7. Replay exacto

Se reejecutaron fuera del checkpoint seis decisiones fijadas sin consultar outcomes: los dos anchors W00/P00 seed 0 y los cuatro anchors PRIMARY de longitud extrema. Esto produjo 18 llamadas independientes. Las comparaciones ignoran únicamente `runtime_seconds` y exigen igualdad de estado, warnings y diagnóstico de bounds, además de BIC y parámetros con tolerancia absoluta 5e-12 y tolerancia relativa cero. El número de discrepancias fue 0.

## 8. Warnings y bounds

Warnings y parámetros en bounds se conservan como diagnósticos operativos, no como criterios para rediseñar el canary. Los conteos agregados de warnings por modelo fueron M0=0, M1=0 y M2=159; los jobs con algún parámetro en bound fueron M0=8, M1=15 y M2=26. Ninguno de estos datos se utilizó para sustituir decisiones o modificar el plan.

## 9. Limitaciones

Este canary valida consumo de payloads, semántica checkpoint/resume, reproducibilidad numérica y contrato temporal en una muestra prospectiva de 102 jobs. No estima desempeño científico del catálogo, no mide tasas de selección, no compara resultados entre roles y no valida físicamente AFINO como detector de QPP. Los outputs canary tampoco autorizan tuning de ventanas, perfiles, thresholds o cohorte.

La cobertura del canary es deliberadamente operacional y no pretende representar la distribución completa de longitudes, estrellas, sectores o estados de admisibilidad del catálogo. Su función es someter el mismo mecanismo de ejecución a ventanas, perfiles, roles, longitudes y seeds prospectivamente elegidos, incluyendo una interrupción en mitad de un trío M0/M1/M2. Por ello, un pass demuestra que el runner respeta los bytes, identidades y reglas congeladas en los casos seleccionados; no demuestra que todas las llamadas restantes producirán el mismo patrón de warnings, bounds o tiempos de ejecución.

## 10. Qué permanece prohibido

La flag de autorización del plan completo no se utilizó y el número de jobs ejecutados fuera del canary es cero. Las otras 22.296 llamadas del plan F3A.2 permanecen sin ejecutar. No se ha realizado interpretación científica, comparación QPP/control, análisis de robustez ni interpretación de periodos. El único siguiente paso autorizable tras el freeze y revisión de esta tarea es F3A.4, ejecución completa checkpointed del plan ya congelado, todavía separada de su análisis científico.

`PHASE3A_RUNNER_VALIDATED_ON_FROZEN_CANARY`
