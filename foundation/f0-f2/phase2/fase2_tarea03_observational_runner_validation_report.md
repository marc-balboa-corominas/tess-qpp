# Fase 2 — Tarea 2.3

## Validación canary del runner observacional checkpointed

**Conclusión:** `OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION`  
**Runner:** `afino_checkpointed` `1.2.0`  
**Plan completo ejecutado:** no  
**AFINO reejecutado durante la corrección:** no

El canary es un subconjunto literal del plan exacto F2.2. Conserva los 84
`job_id`, todos los campos del plan y el `job_order` original, añadiendo solo
`canary_order`. Contiene 16 variantes, 16 decisiones primarias y 12 de
estabilidad, con 28 filas para cada uno de M0, M1 y M2. La pareja P3 en W00
cubre P00–P05, PDCSAP, SAP, `finite_all`, `q0_native`, perfiles sin detrending
y con `linear_residual_plus_one`, ambas clases observacionales y seeds 0 y 1.
Las cuatro decisiones P2 en WX2 añaden una ventana perturbada y detrending
fuera del baseline.

El runner leyó exclusivamente los cuatro payloads persistidos mediante
`np.load(..., allow_pickle=False)`. Usó directamente los slices de tiempo y
flujo; los índices FITS sirvieron solo para auditoría. No abrió FITS, no
reaplicó QUALITY, no regeneró variantes, no repitió detrending, no
renormalizó, interpoló ni rellenó datos.

La interrupción y reanudación funcionaron como estaba previsto. La primera
pasada confirmó 31 transacciones y dejó 53 trabajos pendientes, cortando un
trío después de M0. La segunda conservó esas 31 filas y añadió exactamente 53.
La tercera encontró 84 existentes, ejecutó cero llamadas nuevas y exportó
desde SQLite. Se obtuvieron 84 resultados `OK`, 28 decisiones `VALID`, cero
duplicados y coincidencia completa entre SQLite y los CSV. Los seis replays
externos al checkpoint coincidieron exactamente.

El audit inicial quedó bloqueado por una discrepancia en el contrato temporal
externo. La tarea había pedido comparar `afino_effective_dt_s` con la mediana
de `diff(time)` y contar bins con `rfftfreq`. El canary demuestra de forma
uniforme que AFINO 0.5 usa la media aritmética de los intervalos, equivalente a
`(time[-1]-time[0])/(N-1)`. Los 84 resultados coincidieron exactamente con
esa media. La diferencia máxima respecto a la mediana fue de aproximadamente
13,4 microsegundos.

Además, la frecuencia positiva de AFINO excluye el bin de Nyquist cuando N es
par. El validador inicial lo incluyó y produjo seis discrepancias de un bin en
las dos variantes largas P2. Recalculando independientemente con
`fftfreq(...)[frequencies > 0]`, la cadencia efectiva y el número de bins
coinciden en 84/84 resultados. Esta corrección no modifica AFINO, checkpoint,
BIC, parámetros, decisiones, payloads ni plan.

El núcleo científico frente a F1.11 permanece intacto: importación y llamadas
AFINO, modelos, cutoff, bounds, reinicio de semillas, warnings, diagnóstico de
bounds, serialización, regla doble BIC, transacción por llamada y replay. La
limitación se conserva explícitamente porque el criterio solicitado de mediana
no es el utilizado por la implementación congelada. Los resultados canary no
son elegibles para analizar robustez ni para ajustar el protocolo, y el plan
completo de 2.784 llamadas permanece sin ejecutar.

`OBSERVATIONAL_RUNNER_VALIDATED_WITH_DOCUMENTED_LIMITATION`
