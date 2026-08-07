# Fase 1 — Tarea 1.7

## Descomposición del fallo de selección en ventanas cortas

**Estado:** `SHORT_WINDOW_FAILURE_DIAGNOSTIC_COMPLETE`

## Población y auditoría

Se analizaron exclusivamente las 2.040 decisiones primarias con `N=15` o `N=30` y semilla externa cero: 1.800 positivos sintéticos y 240 nulos. Los 6.120 resultados de M0, M1 y M2 se vincularon sin tríos incompletos, duplicados, BIC no finitos ni discrepancias con las decisiones de F1.5. AFINO no se ejecutó y no se generaron curvas sintéticas nuevas.

## Cuello de botella de la regla doble

La clasificación es inequívoca: las 2.040 series pertenecen a `BOTH_COMPARISONS_FAILED`. No existe ningún caso en el que se supere solo la comparación frente a M0, solo la comparación frente a M2 o ambos umbrales. Además, M0 es el modelo con BIC mínimo en las 2.040 series; M1 no llega a ser ganador formal una sola vez. El término limitante inmediato es la comparación frente a M0: en todas las realizaciones, ΔBIC₀,₁ es menor que ΔBIC₂,₁ y, por tanto, `joint_margin` coincide con `margin_vs_m0`.

En positivos, la mediana de ΔBIC₀,₁ es -5.478 para N=15 y -7.454 para N=30; las medianas de ΔBIC₂,₁ son -1.912 y -2.467. La descomposición likelihood–BIC muestra mejoras positivas de likelihood en muchas series, pero insuficientes para compensar los restos observados de penalización BIC. Estos restos se describen empíricamente y no se interpretan como grados de libertad privados.

## Amplitud y proximidad a los umbrales

Aumentar `q` desplaza los márgenes aunque no produzca selección. Los 45 contrastes emparejados de amplitud presentan cambio mediano positivo en ΔBIC₀,₁ y en `joint_margin`; 40/45 también aumentan en ΔBIC₂,₁. No hubo cruces de umbral ni cambios de ganador BIC. Por tanto, la señal de mayor amplitud sí mueve la evidencia en la dirección prevista, pero el desplazamiento permanece lejos de la regla doble y no autoriza una categoría adicional de “casi detección”.

N=30 no se aproxima uniformemente más que N=15 en los periodos comunes. De los 18 estratos compartidos, N=15 tiene una mediana de `joint_margin` menos negativa en 17, mientras N=30 solo la mejora en 1. El mayor soporte de N=30 aporta más ganancia de likelihood en algunas condiciones, pero también presenta un resto de penalización BIC mayor; con estos datos no basta para cruzar ninguno de los umbrales.

## Periodo formal, bounds y soporte espectral

Los centros formales de M1 no equivalen a periodos recuperados. Para N=15, el error firmado mediano es 97.157 s y el error absoluto mediano 97.157 s. Para N=30, el error firmado mediano baja a 0.409 s, pero el error absoluto mediano sigue siendo 26.377 s. Esto indica que algunos centros se acercan al periodo inyectado, especialmente en N=30, pero existe dispersión sustancial y todos continúan etiquetados como `formal_m1_center_not_selected`.

M1 toca algún bound en 1001/1.800 positivos. El bound más frecuente es la anchura (827), seguido del centro (183) y la amplitud (114). La coexistencia de bounds con márgenes negativos documenta restricciones numéricas observables, pero no demuestra que sean la causa del fallo. M2 registra warnings, mientras M1 no, de acuerdo con F1.6.

Después del cutoff permanecen exactamente 7 bins para N=15 y 14 para N=30. Este soporte espectral reducido es compatible con la hipótesis de que la evidencia de likelihood no compensa la penalización de complejidad, pero la tarea no establece causalidad física.

## Hipótesis para el siguiente benchmark

En ventanas cortas, aumentar el soporte espectral manteniendo la misma señal y el mismo proceso de ruido debería elevar principalmente ΔBIC₀,₁, porque la mejora de likelihood de M1 observada aquí no compensa el resto de penalización frente a M0; si la hipótesis es correcta, el margen frente a M0 crecerá más que el margen frente a M2 y aparecerán cruces conjuntos de los dos umbrales.

Esta hipótesis es comprobable y no modifica la regla de selección ni define todavía un nuevo grid.
