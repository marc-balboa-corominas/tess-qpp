# Fase 2 — Tarea 2.1

## Prerregistro de robustez observacional sobre la cohorte congelada

**Estado:** `OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN`

La cohorte queda limitada a las diez observaciones cuya clasificación fue
congelada en F0.15: cinco eventos `PUBLISHED_QPP_REPRODUCED` y cinco
`MATCHED_NOT_SELECTED`. Existen cinco pares, cada uno formado por una
detección publicada reproducida y un evento emparejado no seleccionado. Los
identificadores, TIC, sectores, productos FITS, hashes, marcadores temporales,
índices inclusivos y resultados baseline se extrajeron de los artefactos
observacionales enlazados por F0.15. No se creó ningún evento, no se sustituyó
ningún caso problemático y no se inspeccionó todavía la elegibilidad de una
variante.

Las perturbaciones temporales se aplicarán simétricamente a los dos miembros
de cada par. Las trece ventanas incluyen el baseline, desplazamientos del
inicio o del final en una o dos cadencias, y extensiones o contracciones
simétricas. Todos los desplazamientos operan sobre los índices FITS inclusivos
congelados. El pico mantiene su índice original y debe permanecer dentro de la
ventana; un desplazamiento que lo excluya será inadmisible y no se corregirá
moviendo el otro límite. Esta simetría evita escoger ventanas distintas según
la clasificación previa del evento.

Los seis perfiles distinguen tres dimensiones. Se compararán PDCSAP y SAP;
`finite_all` y `q0_native`; y, para ambos productos bajo `finite_all`, una
transformación lineal `linear_residual_plus_one`. `finite_all` conserva tiempo
y flujo finitos sin filtrar por `QUALITY`. `q0_native` exige además
`QUALITY==0` y no interpola. La alternativa lineal sustrae una recta estimada
sobre las mismas cadencias y reescala el residuo alrededor de uno. Es una
prueba de sensibilidad al preprocesamiento, no un modelo físico del flare. No
se añadirán combinaciones q0 con detrending, filtros adicionales ni perfiles
elegidos después de observar resultados.

F2.2 resolverá la admisibilidad sin ejecutar AFINO. Una variante solo será
elegible si existe el producto, la ventana está dentro del FITS, conserva el
pico, mantiene al menos quince cadencias después de la política de calidad,
retiene el pico, tiene tiempos estrictamente crecientes, índices originales
consecutivos, ausencia de duplicados, desviación máxima de intervalos no
superior a 0,001 s y datos finitos. El detrending deberá producir escala,
tendencia y flujo transformado válidos. No se interpolarán gaps, no se
rellenarán cadencias y no se reindexará para ocultar irregularidad.

La inadmisibilidad no equivale a no selección. Las combinaciones inadmisibles
permanecerán en el grid con `decision_status=INPUT_INADMISSIBLE`, una razón
explícita y campos BIC y selección vacíos. Por tanto, el denominador de
retención de cada evento será únicamente el número de variantes primarias
elegibles. Las variantes inadmisibles se contarán por separado y no se
mezclarán con pérdidas de clasificación. No se fija un porcentaje mínimo de
robustez.

La clasificación y el periodo se analizarán como outcomes distintos. Para una
variante elegible se registrarán los dos deltas BIC, el margen conjunto, el
ganador BIC, la conservación de la clasificación baseline, warnings y bounds.
El desplazamiento de periodo frente al baseline solo se calculará cuando el
baseline y la variante estén seleccionados y ambos periodos existan. Una nueva
selección en un control podrá registrar el centro formal de M1, pero no se
denominará recuperación de un periodo verdadero.

El grid máximo contiene 780 decisiones primarias: diez eventos por trece
ventanas por seis perfiles con seed externa cero. La estabilidad añade 540
decisiones en W00: diez eventos por seis perfiles y seeds uno a nueve. El
máximo es de 1.320 decisiones y 3.960 llamadas de modelo. F2.2 congelará el
número exacto elegible antes de cualquier ejecución.

Esta fase no estimará sensibilidad, especificidad, tasa observacional de falsos
positivos ni ground truth físico. Los pares describirán cambios concordantes o
discordantes, no rendimiento poblacional. La búsqueda de candidatos permanece
bloqueada porque la autorización de F1.14 se limita a probar la robustez de las
diez clasificaciones conocidas. No se descargaron nuevos eventos, no se
materializaron curvas y no se ejecutó AFINO.

`OBSERVATIONAL_ROBUSTNESS_PREREGISTRATION_FROZEN`
