# Fase 1 — Tarea 1.6

## Auditoría y análisis prerregistrado del benchmark núcleo

**Estado:** `CORE_BENCHMARK_ANALYSIS_COMPLETE`

## 1. Alcance e integridad

El análisis utilizó exclusivamente los resultados completos congelados en F1.5. Se compararon las 16.317 filas del CSV con SQLite, incluidos identificadores, metadatos, estados, likelihood, BIC y parámetros. Se recalcularon las 5.439 decisiones con tolerancia absoluta de `5e-12` y tolerancia relativa cero. No hubo discrepancias, duplicados ni decisiones inválidas. El checkpoint, los resultados y las decisiones conservaron sus hashes antes y después. AFINO no se ejecutó y no se incorporó el canary.

Los términos de este informe son deliberadamente sintéticos: `synthetic false selection` y `synthetic detection` describen únicamente este generador y este protocolo. El rendimiento observacional no se estima y la verdad física de QPP no queda establecida.

## 2. Selección sintética en nulos

M1 no fue seleccionado en ninguna de las 480 realizaciones nulas primarias: **0/480**. Cada una de las doce condiciones tuvo 0/40 selecciones. Los intervalos de Wilson son descriptivos y no constituyen una corrección por multiplicidad ni una prueba de hipótesis.

| N | alpha | Seleccionadas | Tasa sintética | Wilson 95% |
|---:|---:|---:|---:|---:|
| 15 | 0 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 15 | 1 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 15 | 2 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 30 | 0 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 30 | 1 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 30 | 2 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 60 | 0 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 60 | 1 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 60 | 2 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 120 | 0 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 120 | 1 | 0/40 | 0.0% | [0.0%, 8.8%] |
| 120 | 2 | 0/40 | 0.0% | [0.0%, 8.8%] |

Este resultado es una tasa de selección sintética bajo el nulo construido; no es una tasa observacional de falsos positivos.

## 3. Detección sintética en positivos

Las 99 condiciones positivas abarcaron tasas entre **0.0%** y **100.0%**, con mediana por condición de **0.0%**. Hubo 78 condiciones con 0/40 y 21 con al menos una selección. No se asigna una categoría de éxito o fracaso porque F1.1 no fijó un umbral global.

En el extremo inferior, todas las condiciones con N=15 y N=30 quedaron en 0/40. Con N=60 solo aparecieron selecciones para P=50 s y q=0.04: 2/40 con alpha=0, 7/40 con alpha=1 y 20/40 con alpha=2. Con N=120 apareció el dominio de mayor selección: los periodos de 50 y 80 s alcanzaron 40/40 en varias combinaciones de amplitud y pendiente, mientras que P=140 s solo produjo selecciones con q=0.04, desde 7/40 hasta 27/40 según alpha. Las comparaciones de N y alpha son descriptivas y totalmente estratificadas; no son contrastes emparejados porque usan bloques de ruido distintos.

| Condición en el extremo superior | N | P (s) | alpha | q | Seleccionadas | Tasa |
|---|---:|---:|---:|---:|---:|---:|
| C087_QPP_N120_P050_A0_Q040 | 120 | 50 | 0 | 0.04 | 40/40 | 100.0% |
| C090_QPP_N120_P050_A1_Q040 | 120 | 50 | 1 | 0.04 | 40/40 | 100.0% |
| C092_QPP_N120_P050_A2_Q020 | 120 | 50 | 2 | 0.02 | 40/40 | 100.0% |
| C093_QPP_N120_P050_A2_Q040 | 120 | 50 | 2 | 0.04 | 40/40 | 100.0% |
| C096_QPP_N120_P080_A0_Q040 | 120 | 80 | 0 | 0.04 | 40/40 | 100.0% |
| C099_QPP_N120_P080_A1_Q040 | 120 | 80 | 1 | 0.04 | 40/40 | 100.0% |
| C101_QPP_N120_P080_A2_Q020 | 120 | 80 | 2 | 0.02 | 40/40 | 100.0% |
| C102_QPP_N120_P080_A2_Q040 | 120 | 80 | 2 | 0.04 | 40/40 | 100.0% |

La amplitud mostró un patrón no decreciente en los **33/33** estratos completos (N, P, alpha). Solo 4/33 aumentaron estrictamente en los tres pasos, porque muchas tasas permanecieron empatadas en cero o saturadas. Entre los 99 contrastes emparejados de amplitud, 28 tuvieron diferencia positiva, 71 diferencia cero y 0 negativa. Por tanto, no se observó una reversión de la tasa al aumentar q dentro de los bloques compartidos.

Para periodo, la diferencia se definió como periodo largo menos periodo corto. De los 90 contrastes, 25 fueron negativos, 65 cero y 0 positivos. En las regiones donde existió detección, los periodos más cortos fueron iguales o más favorables. La figura 2 conserva la estratificación completa y evita una tasa marginal ingenua por N; N=15 no incluye P=140 s.

## 4. Periodo seleccionado y centro formal de M1

M1 fue seleccionado en 488 de las 3.960 ejecuciones positivas primarias. Entre esas selecciones, el error firmado mediano fue **0.449 s**, el error absoluto mediano **0.821 s**, el percentil 90 del error absoluto **2.382 s** y el error relativo firmado mediano **0.767%**.

Al considerar el centro formal de M1 en todas las ejecuciones positivas válidas, incluidas las no seleccionadas, el error firmado mediano fue **0.838 s**, el absoluto mediano **7.802 s** y su percentil 90 **138.443 s**. En las 3472 ejecuciones no seleccionadas, el error absoluto mediano fue 13.579 s. La diferencia es grande: el centro de M1 está mucho mejor localizado cuando el modelo supera ambos umbrales BIC. Fuera de esa selección se conserva la etiqueta `formal_m1_center_not_selected`; no se denomina periodo recuperado.

## 5. Semilla del optimizador y multiplicidad de M2

Ninguna de las 111 condiciones cambió su decisión binaria entre las semillas externas 0–9. En consecuencia, `optimizer_seed_decision_discordance` fue cero en todas las condiciones. Esta estabilidad de clasificación no implica unicidad numérica: **97/111** condiciones superaron el criterio prerregistrado `M2_BIC_range > 0.001`.

| Mayores rangos de BIC de M2 | Rango | Semillas seleccionadas |
|---|---:|---:|
| C089_QPP_N120_P050_A1_Q020 | 4.542837 | 10/10 |
| C090_QPP_N120_P050_A1_Q040 | 3.798537 | 10/10 |
| C078_QPP_N060_P140_A0_Q040 | 3.394931 | 0/10 |

El indicador de M2 señala multiplicidad según el criterio operativo de BIC; no establece por sí solo soluciones físicas distintas.

## 6. Bounds, warnings y fallos numéricos

No hubo fallos numéricos: las 16.317 llamadas fueron `OK` y las 5.439 decisiones `VALID`. En las 4.440 llamadas primarias por modelo, M0 tuvo 471 bounds (10.6%), M1 3135 (70.6%) y M2 1747 (39.3%). Los warnings se concentraron exclusivamente en M2: 2106 llamadas primarias (47.4%) y 423 de estabilidad (42.3%).

Por tamaño, los bounds primarios de M1 aumentaron desde 48.1% en N=15 hasta 89.9% en N=120. Los warnings primarios de M2 fueron más frecuentes en N=60 (71.2%) y N=120 (68.7%). Estos diagnósticos deben acompañar la interpretación de BIC y periodos, pero no invalidan automáticamente una llamada `OK`.

## 7. Dominio de funcionamiento y límites

Dentro de este generador, la selección sintética fue nula en los doce nulos y se concentró en positivos con ventanas largas, amplitudes mayores y periodos más cortos. La amplitud fue no decreciente en todos los estratos emparejados, mientras que ampliar el periodo nunca mejoró la tasa en los contrastes observados. La decisión fue estable frente a la semilla externa, aunque M2 mostró variación de BIC en la mayoría de condiciones y los bounds de M1 fueron frecuentes.

Estas conclusiones son válidas únicamente para flares sintéticos con QPP estacionaria, ruido rojo generado por el procedimiento congelado, cadencia de 20 s, grid y protocolo AFINO prerregistrados. No estiman desempeño en curvas TESS reales, no prueban la presencia física de QPP y no autorizan extrapolaciones a otras envolventes, damping, gaps, detrending o distribuciones de ruido.

## Conclusión

`CORE_BENCHMARK_ANALYSIS_COMPLETE`
