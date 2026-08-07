# Fase 2 — Tarea 2.2

## Materialización de variantes y congelación del plan exacto

**Estado:** `OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO`

Se localizaron los diez productos FITS asociados a la cohorte congelada y
cada archivo coincidió con el SHA-256 registrado en F2.1. La tabla
`LIGHTCURVE` fue legible en todos los casos y se registraron el número de
filas y la presencia de `TIME`, `QUALITY`, `SAP_FLUX` y `PDCSAP_FLUX`.
Hubo 10 filas de auditoría con fallos históricos de
`CHECKSUM` o `DATASUM`; estos avisos se conservaron como metadatos porque el
hash físico coincidió y la tabla fue utilizable. No se descargó ningún FITS.

Se resolvieron las 780 combinaciones primarias en el orden exacto del grid
F2.1 y se asignaron los identificadores `F2V000001` a `F2V000780` sin
reordenar por evento, clase, ventana, perfil o elegibilidad. Resultaron
514 variantes `ELIGIBLE_FOR_AFINO` y
266 inadmisibles. Las razones técnicas
observadas fueron: IRREGULAR_SAMPLING=142, PEAK_REMOVED_BY_QUALITY=26, TOO_FEW_CADENCES=98. Cada variante recibió una única categoría
según la precedencia congelada. Las inadmisibles permanecen en el manifiesto
con `INPUT_INADMISSIBLE`, sin BIC, sin selección y sin payload.

Las diez variantes baseline `W00/P00` fueron elegibles. Sus números de
muestras, hashes lógicos de tiempo y flujo, y primeros y últimos índices FITS
coincidieron exactamente con los CSV baseline físicamente congelados por
F0.9/F0.10 y F0.13/F0.14. La comparación no ejecutó AFINO y no recalculó una
clasificación.

Solo las variantes elegibles se escribieron en los cuatro payloads
contiguos. Los tiempos y flujos se persistieron como `<f8`; los índices FITS y
offsets como `<i8`. Tras cerrar y recargar los `.npy` con
`allow_pickle=False`, coincidieron 514/514
hashes de tiempo, 514/514 hashes de flujo y
514/514 hashes de índices. Desde los arrays
releídos también se confirmó `time[0]==0`, crecimiento temporal estricto,
índices consecutivos, regularidad dentro de 0,001 s y valores finitos.

El grid resuelto conserva las 1.320 decisiones máximas. Las
514 decisiones primarias elegibles usan su propia
variante. En la estabilidad, las seeds 1–9 heredaron únicamente la
elegibilidad del mismo evento y perfil en `W00`; por ello existen
46 variantes W00-perfil elegibles y
414 decisiones de estabilidad ejecutables. El plan
exacto congela 928 decisiones y
2784 llamadas: 928 para cada uno de M0, M1 y M2.
No se forzó el máximo teórico de 3.960 llamadas.

No se interpoló, rellenó ni reindexó ninguna curva. Los perfiles P00–P03 no
fueron normalizados, recentrados o reescalados. El detrending P04/P05 utilizó
literalmente la fórmula prerregistrada y sus fallos, cuando existieron,
permanecieron como inadmisibilidad. No se añadió ninguna ventana, perfil,
evento o umbral.

F2.2 resolvió exclusivamente la elegibilidad técnica y congeló inputs y
trabajos futuros. No se importó ni ejecutó AFINO, no se observaron resultados
de clasificación QPP y no se comparó científicamente la elegibilidad entre las
dos clases observacionales. La búsqueda de candidatos continúa bloqueada.

Los conteos de elegibilidad documentan qué inputs satisfacen el contrato
prerregistrado de muestreo, calidad y preprocesamiento. No describen una
diferencia física entre detecciones publicadas y controles, ni permiten
calcular sensibilidad, especificidad o una tasa observacional de falsos
positivos. La interpretación científica de las clasificaciones permanecerá
aplazada hasta que el plan exacto sea validado mediante canary y ejecutado con
checkpointing en tareas posteriores.

`OBSERVATIONAL_VARIANTS_AND_EXACT_PLAN_FROZEN_BEFORE_AFINO`
