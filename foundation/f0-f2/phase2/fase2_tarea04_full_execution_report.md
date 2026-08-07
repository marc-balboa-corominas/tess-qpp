# Fase 2 — Tarea 2.4

## Ejecución completa del plan observacional exacto

**Estado de ejecución:** `FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE`  
**Validación temporal:** `AFINO_0_5_CONTRACT_CONFIRMED_WITH_DOCUMENTED_PREREGISTERED_CHECK_MISMATCH`  
**Runner:** `afino_checkpointed` `1.2.0`

### Completitud de ejecución

Se ejecutaron exactamente las 2.784 llamadas del plan F2.2: 928 para M0,
928 para M1 y 928 para M2. El checkpoint contiene 2.784 filas, el CSV exporta
2.784 resultados y la tabla de decisiones contiene 928 filas, distribuidas
en 514 decisiones primarias y 414 de estabilidad. No queda ningún trabajo
pendiente. Todos los estados, incluidos posibles errores numéricos, se
conservaron sin eliminar ni repetir selectivamente trabajos.

### Integridad plan–resultado

El validador independiente comparó literalmente los 2.784 `job_id` y sus
metadatos entre el plan, SQLite y el CSV. También verificó las claves
`variant_id`–seed–modelo, los offsets, tamaños, hashes de tiempo y flujo,
metadatos observacionales, warnings, bounds y outputs numéricos. No aparecieron
duplicados, discrepancias plan–resultado ni diferencias SQLite–CSV. Las 928
decisiones se recalcularon desde los tres BIC con tolerancia absoluta de
5×10⁻¹² y tolerancia relativa cero, sin discrepancias.

### Reanudación e idempotencia

El checkpoint era nuevo y contenía cero filas antes de comenzar. Las cinco
invocaciones añadieron exactamente 700, 700, 700, 684 y 0 trabajos. Los
totales acumulados fueron 700, 1.400, 2.100, 2.784 y 2.784. La quinta pasada
no ejecutó llamadas nuevas y exportó desde el checkpoint. La lógica de una
transacción SQLite independiente por llamada coincide byte a byte con el
runner congelado F1.11.

### Contrato temporal solicitado

El control prerregistrado basado en `median(diff(time))` y
`numpy.fft.rfftfreq` se mantuvo sin modificar para conservar trazabilidad.
Coincidió en 12 de 928 decisiones para la
cadencia y en 740 de 928 para el número
de bins. Sus desacuerdos se documentan, pero no se convierten en fallos del
runner porque no representan la convención utilizada por AFINO 0.5.

### Contrato temporal observado de AFINO 0.5

La validación separada calculó `mean(diff(time))` y las frecuencias
estrictamente positivas de `numpy.fft.fftfreq`. Este contrato coincidió en
928/928 decisiones para la cadencia efectiva y en 928/928 para los bins tras
el cutoff. Los tres modelos coincidieron entre sí en cadencia y conteo de bins
en 928/928 decisiones.

### Diagnósticos operativos

Los conteos de estado, warnings, bounds, tiempos totales y medianos y
`convergence_status` se registraron únicamente por modelo. No se calcularon
tasas de selección, retención, ganancias, pérdidas ni comparaciones por clase,
producto, perfil, ventana o periodo.

### Interpretaciones científicas aplazadas

Los payloads F2.2, el plan completo, el runner y el checkpoint canary F2.3
permanecieron intactos. No se abrió ningún FITS, no se repitió preprocesamiento
y no se interpretaron resultados científicos. El análisis prerregistrado de
robustez queda reservado para F2.5. Esta tarea solo establece que la ejecución
fue completa, reanudable, idempotente y estructuralmente coherente con los
artefactos congelados; no evalúa el significado físico de ninguna selección.

`FULL_OBSERVATIONAL_PLAN_EXECUTION_COMPLETE`
