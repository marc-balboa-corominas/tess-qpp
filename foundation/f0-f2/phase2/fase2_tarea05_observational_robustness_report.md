# Fase 2 — Tarea 2.5

## Análisis de robustez de la cohorte observacional congelada

**Conclusión:** `FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS`

### 1. Admisibilidad de los inputs

El análisis reconstruyó las 780 variantes primarias previstas: diez eventos,
trece ventanas y seis perfiles. De ellas, 514 fueron evaluadas por AFINO en
F2.4 y 266 permanecieron como `INPUT_INADMISSIBLE`. Estas últimas no se
convirtieron en no selecciones ni se retiraron de los denominadores
planificados. Las razones estructurales fueron 142 casos de
`IRREGULAR_SAMPLING`, 98 de `TOO_FEW_CADENCES` y 26 de
`PEAK_REMOVED_BY_QUALITY`. Entre las 514 decisiones evaluables hubo
140 selecciones,
374 no selecciones y
0 resultados numéricamente
incompletos. Por tanto, toda proporción de selección se calculó únicamente
entre inputs elegibles y conserva su denominador explícito.

### 2. Estabilidad de clasificación respecto al baseline

Las diez filas W00/P00 con seed 0 reprodujeron exactamente la clasificación
congelada F2.1. También coincidieron, con tolerancia absoluta de 5×10⁻¹², los
dos deltas BIC y el centro formal de M1; las etiquetas de periodo se
reconstruyeron desde `baseline_qpp_selected` y la regla prerregistrada, no
desde el rol observacional. La cohorte F2.1 no contiene BIC individuales de
M0, M1 y M2, por lo que esos tres valores actuales se registraron pero no se
presentaron como una comparación independiente congelada.

Respecto a cada baseline, hubo
140 variantes con selección
retenida, 136 pérdidas de selección,
238 no selecciones retenidas y
0 ganancias de selección. A ello
se añaden las 266 inadmisibles. Estos términos describen transiciones internas
de la cohorte, no aciertos, errores ni verdad física. Los resúmenes por
evento mantienen las 78 variantes previstas para cada observación y muestran
por separado cuántas fueron elegibles, inadmisibles, seleccionadas o no
seleccionadas. También identifican las ventanas y perfiles concretos en los
que la clasificación se apartó del baseline y conservan el rango de
`joint_margin`. Este nivel de presentación evita que un evento con muchas
variantes admisibles domine silenciosamente la descripción frente a otro con
más pérdidas por calidad o irregularidad temporal.

La tabla por pareja conserva igualmente dos bloques independientes, uno para
cada miembro. Solo añade conteos descriptivos de variantes homólogas en las
que ambos miembros fueron elegibles, ambos inadmisibles o solo uno de ellos
fue inadmisible. La coincidencia o diferencia entre clasificaciones de los
dos miembros no se interpreta como una medida de pareja correcta, porque los
roles observacionales no constituyen etiquetas físicas verdaderas.

### 3. Perturbaciones temporales

Los 720 contrastes compararon cada ventana no-W00 con W00 del mismo evento y
perfil. Fueron comparables como `BOTH_ELIGIBLE`
468 contrastes; en
0 la referencia era
inadmisible, en 84 lo era
la variante y en 168 lo eran
ambas. Entre los comparables se observaron
302 transiciones 0→0,
4 transiciones 0→1,
41 transiciones 1→0 y
121 transiciones 1→1. Estos 720 contrastes no
son replicaciones independientes: las ventanas son medidas repetidas dentro
de diez eventos. Los resúmenes por rol, perfil y ventana conservan cinco
eventos planificados por celda.

### 4. Perfiles de procesamiento

Los 780 contrastes prerregistrados cubrieron exactamente `FLUX_FINITE`,
`QUALITY_PDCSAP`, `QUALITY_SAP`, `DETREND_PDCSAP`, `DETREND_SAP` y
`FLUX_Q0`. Resultaron `BOTH_ELIGIBLE`
429 comparaciones; el resto
mantuvo por separado la inadmisibilidad de la referencia, de la variante o de
ambas. Entre los pares comparables hubo
292 transiciones 0→0,
1 transiciones 0→1,
44 transiciones 1→0 y
92 transiciones 1→1. No se añadieron
combinaciones de q0 con detrending ni perfiles no congelados. Las diferencias
son descriptivas y no atribuyen causalidad al producto de flujo, QUALITY o
detrending.

### 5. Estabilidad frente a seed externa

Las 46 variantes W00 elegibles se analizaron con seeds 0–9, para un total de
460 decisiones. No hubo discordancia de clasificación: 15 variantes fueron
seleccionadas con 10/10 seeds y 31 no fueron seleccionadas con 0/10 seeds.
Esto establece estabilidad de la decisión en este conjunto congelado, pero
no unicidad del resultado numérico. En los tres modelos, cada variante mostró
diez payloads de parámetros distintos entre las diez seeds. Por tanto,
`stable classification ≠ unique numerical optimum`: la multiplicidad de
parámetros se conserva como diagnóstico numérico, no como demostración de
óptimos físicos distintos.

### 6. Periodo recuperado y centro formal no seleccionado

La tabla de robustez del periodo contiene 140 filas en las que
el baseline estaba seleccionado, la variante también estaba seleccionada y
ambos periodos estaban disponibles. El cambio absoluto tuvo mediana de
0.244031 s, Q1 de
0.0331366 s, Q3 de
0.61861 s y máximo de
2.71469 s. Entre las 15 variantes W00
seleccionadas por las diez seeds, el rango del periodo recuperado tuvo mediana
de 0.000195585 s y máximo de
0.000736002 s.

Además, se conservaron 374 centros formales M1
de decisiones no seleccionadas con la etiqueta
`formal_m1_center_not_selected`. No se incluyeron como periodos recuperados
ni en la tabla ni en la figura de estabilidad del periodo.

### 7. Warnings y bounds

Los diagnósticos se resumieron por modelo, perfil y rol, y adicionalmente por
modelo y ventana. Se registraron número de llamadas, llamadas con warnings,
warnings totales y llamadas con parámetros en bounds. No se utilizó la
presencia de warnings o bounds para explicar transiciones de clasificación,
ni se estableció una relación causal. `convergence_status` permanece como
`NOT_AUDITABLE`, por lo que la estabilidad de clasificación no equivale a
convergencia demostrada.

### 8. Alcance observacional

El resultado caracteriza estabilidad interna en una cohorte de diez eventos
y cinco parejas congeladas. No estima sensibilidad, especificidad, tasa
observacional de falsos positivos, accuracy ni verdad física de QPP. El rol
`PUBLISHED_QPP_REPRODUCED` y el rol `MATCHED_NOT_SELECTED` describen la
construcción de la cohorte, no ground truth. No se ejecutó AFINO, no se abrió
ningún FITS, no se regeneraron variantes y no se repitió QUALITY, detrending,
interpolación o relleno de gaps. Tampoco se añadieron candidatos, eventos ni
umbrales de robustez.

`FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS`
