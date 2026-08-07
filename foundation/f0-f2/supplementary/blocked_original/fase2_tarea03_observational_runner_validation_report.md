# Fase 2 — Tarea 2.3

## Validación canary del runner observacional checkpointed

**Conclusión:** `OBSERVATIONAL_RUNNER_VALIDATION_BLOCKED`  
**Runner:** `afino_checkpointed` `1.2.0`  
**AFINO:** `6aceac9518fc8056052807e666da9d0c8bebb010` / `0.5`  
**Plan completo ejecutado:** no

El canary contiene 84 trabajos y es un subconjunto literal del plan exacto
F2.2: conserva cada `job_id`, todos los campos científicos y el `job_order`
original, añadiendo únicamente `canary_order`. Sus 16 variantes únicas
producen 28 decisiones: 16 primarias y 12 de estabilidad, con 28 filas para
cada uno de M0, M1 y M2.

La pareja P3 en W00 cubre P00–P05 para ambos miembros y para las seeds 0 y 1.
Por tanto, el canary incluye PDCSAP, SAP, `finite_all`, `q0_native`, ausencia
de detrending y `linear_residual_plus_one`, además de las dos clases
observacionales y de decisiones primarias y de estabilidad. Las cuatro
decisiones P2 en WX2 incorporan una ventana perturbada, inputs más largos y
detrending fuera del baseline.

El runner cargó exclusivamente los cuatro payloads F2.2 mediante
`np.load(..., allow_pickle=False)`. Para cada trabajo utilizó directamente
los slices persistidos de tiempo y flujo. Los índices FITS solo se emplearon
para comprobar hashes y consecutividad. No se abrió ningún FITS, no se
reaplicó QUALITY, no se repitió detrending y no se reconstruyeron,
normalizaron, interpolaron o rellenaron curvas.

La interrupción ocurrió después de 31 transacciones confirmadas, dejando 53
trabajos pendientes y una decisión con trío incompleto. La segunda pasada
conservó las 31 filas y añadió exactamente 53. La tercera encontró 84
resultados existentes, ejecutó cero llamadas nuevas y exportó desde SQLite.
No aparecieron `job_id` ni claves científicas duplicadas.

El contrato temporal se calculó independientemente desde cada tiempo
persistido. Para los resultados OK, `afino_effective_dt_s` coincidió con la
mediana de los intervalos con tolerancia absoluta de 5×10⁻¹² s, y el número
de bins tras el cutoff coincidió con el conteo derivado de las frecuencias
FFT y el límite congelado de 1/40 Hz. SQLite y los dos CSV coincidieron, y los
deltas BIC se recalcularon sin discrepancias.

Los seis replays externos al checkpoint —M0, M1 y M2 para F2D000471 y
F2D000461— coincidieron exactamente en estado, BIC, log-likelihood,
parámetros, periodo formal de M1, rchi2, probabilidad, warnings, bounds,
cadencia efectiva, bins y error.

El diff frente al runner 1.1.0 clasificó los cambios únicamente como
`dataset_contract`, `observational_metadata`, `output_naming`, `job_counts`
y `plan_kind_validation`. La importación y llamadas AFINO, modelos, bounds,
cutoff, reinicio de semillas, warnings, diagnóstico de bounds, serialización,
regla doble BIC, transacción por llamada y lógica base de replay permanecieron
intactos.

Los resultados canary no son elegibles para analizar robustez ni para ajustar
perfiles, ventanas, umbrales o cohorte. El plan completo de 2.784 llamadas
permanece sin ejecutar.

`OBSERVATIONAL_RUNNER_VALIDATION_BLOCKED`
