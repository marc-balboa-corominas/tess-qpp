# Fase 1 — Tarea 1.14

## Síntesis, cierre de Fase 1 y puerta de entrada a robustez observacional

**Decisión:** `PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS`

La Fase 1 se cierra con una separación explícita entre cuatro planos de
evidencia: reproducción observacional, ground truth sintético, diagnóstico
numérico e interpretación física no establecida. Esta separación es esencial
porque los resultados responden preguntas diferentes. La reproducción muestra
que un protocolo público congelado puede recuperar determinadas
clasificaciones publicadas. Los benchmarks sintéticos muestran cómo se
comporta ese protocolo cuando la presencia o ausencia de una componente
periódica es conocida por construcción. Los warnings, bounds y variaciones
entre seeds informan sobre estabilidad numérica. Ninguno de estos planos
demuestra por sí solo la existencia física de QPP en una observación real.

## Evidencia observacional reproducida

El baseline `afino_public_tess_reproduction_v1` reprodujo cinco detecciones QPP
publicadas y conservó como no seleccionados cinco eventos emparejados. En los
positivos, la doble regla BIC permaneció activa en las diez seeds externas; en
los controles, permaneció inactiva. El valor de esta evidencia es operativo:
existe un procedimiento identificable, congelado por hashes y reproducible
sobre diez observaciones conocidas. Esto basta para formular pruebas de
robustez sobre la misma cohorte.

El alcance sigue siendo limitado. No se reprodujeron las 61 detecciones del
catálogo ni los 3.817 eventos no seleccionados, y el adaptador TESS privado de
los autores continúa sin estar disponible. La política global de QUALITY, el
uso global de PDCSAP, la configuración privada completa del optimizador y la
convergencia formal tampoco están resueltos. La concordancia con el catálogo
no equivale a reconstrucción documental completa ni permite calcular
sensibilidad o especificidad.

Tampoco existe ground truth físico observacional. Las cinco detecciones son
eventos etiquetados por el catálogo y los cinco controles son eventos que ese
catálogo no seleccionó. La afirmación autorizada es que el baseline reproduce
esas clasificaciones. Continúa prohibido afirmar que los positivos contienen
QPP físicamente demostradas o que los controles prueban su ausencia.

## Ground truth sintético y dominio de funcionamiento

F1.1 congeló un generador con nulos y QPP estacionarias conocidas por
construcción. En el benchmark principal, M1 no fue seleccionado en ninguna de
las 480 realizaciones nulas. Este resultado se denomina `synthetic false
selection 0/480`; no es una tasa observacional de falsos positivos.

Las condiciones positivas mostraron una estratificación fuerte. De 99
condiciones, 78 quedaron en 0/40 y 21 tuvieron alguna selección. Todas las
condiciones positivas con N=15 y N=30 quedaron en 0/40. La selección se
concentró en ventanas más largas, amplitudes mayores y periodos más cortos.
Dentro de los estratos emparejados, aumentar amplitud nunca redujo la tasa,
pero el resultado no define una sensibilidad global: depende del generador,
del grid y del protocolo concretos.

F1.7 descompuso específicamente las ventanas cortas. En las 2.040 decisiones
con N=15 o N=30 fallaron simultáneamente las comparaciones frente a M0 y M2.
M0 fue el ganador BIC y la limitante del margen conjunto en todos los casos.
Aumentar la amplitud desplazó favorablemente Δ01 y el margen conjunto en los
45 contrastes, pero no produjo ningún cruce de umbral ni cambio de ganador.
Además, N=30 no quedó uniformemente más cerca del umbral que N=15: N=15 tuvo
un margen menos negativo en 17 de los 18 estratos comunes. Por tanto, la
dificultad de las ventanas cortas no se resume en “faltan bins”; el balance de
likelihood y penalización frente a M0 permaneció desfavorable.

## Aporte y límites del benchmark anidado

F1.8 prerregistró extensiones padre–prefijo para estudiar el efecto total de
observar una porción temporal mayor. El benchmark no aisló causalmente el
número de bins: al extender el prefijo también cambian la cola observada, los
momentos del ruido, la normalización interna, la ventana de Hann y la
cuadrícula FFT.

F1.13 encontró dos synthetic false selections entre 720 decisiones nulas y
solo cuatro selecciones entre 1.440 decisiones positivas. El contraste
prerregistrado `C_support=ΔΔ01−ΔΔ21` fue negativo en 959 de 1.200
transiciones. En la mayoría de extensiones, la evidencia relativa frente a M2
aumentó más que la evidencia frente a M0; por ello, la parte principal de la
hipótesis de soporte temporal no quedó apoyada de forma dominante.

Sí aparecieron cruces conjuntos: cuatro ascendentes y dos descendentes. La
selección no fue monotónica. Dos trayectorias positivas se seleccionaron en
N=60 y revirtieron en N=90; otras dos aparecieron únicamente en N=120. Esto
aporta evidencia de sensibilidad a la ventana y justifica estudiar
perturbaciones temporales en las observaciones reales. No demuestra que
extender una observación mejore de forma general la clasificación.

La recuperación de periodo condicionada a selección quedó limitada a cuatro
casos, una observación por estrato seleccionado. Esa población es demasiado
pequeña para establecer una tendencia. El centro formal de M1 en ejecuciones
no seleccionadas debe permanecer separado del concepto de periodo recuperado.

## Estabilidad y no unicidad numérica

La clasificación no cambió entre seeds en las 111 condiciones del benchmark
principal ni en las 54 condiciones de estabilidad anidadas. Sin embargo, esta
estabilidad tiene límites. En F1.13, las 540 decisiones del subconjunto de
estabilidad fueron no selecciones; por tanto, no se probó estabilidad de
selecciones positivas anidadas. M2 superó el criterio de múltiples soluciones
en 97/111 condiciones del benchmark principal y en 38/54 condiciones
anidadas. Debe conservarse la formulación: `stable classification ≠ unique
numerical optimum`.

Los bounds de M1 y M2 y los warnings de M2 fueron frecuentes y variaron con la
longitud de la serie. Son diagnósticos que deben registrarse, no explicaciones
causales ni criterios post hoc para aceptar o descartar resultados.

## Puerta de entrada a la siguiente fase

Existe base suficiente para pasar a una fase de robustez observacional porque
hay diez observaciones ya congeladas, un baseline reproducible y riesgos
concretos identificados antes de ampliar la cohorte. No se requiere otro
benchmark sintético para decidir si esas diez clasificaciones sobreviven a
perturbaciones razonables. La decisión no valida AFINO y no autoriza
descubrimiento.

La siguiente fase deberá prerregistrar, como mínimo: perturbaciones de límites
temporales; PDCSAP frente a SAP; política QUALITY; gaps y muestreo irregular;
alternativas de detrending o representación espectral; seeds externas;
warnings y bounds por modelo; y separación entre robustez de clasificación y
periodo recuperado. Las variantes deberán aplicarse simétricamente a las cinco
detecciones y los cinco controles. Los outcomes serán conservación, pérdida o
cambio de la clasificación publicada bajo perturbaciones, no verdad física.

La búsqueda de nuevos candidatos permanece bloqueada. También continúan
prohibidas las afirmaciones de sensibilidad, especificidad, tasa observacional
de falsos positivos, ground truth físico y efecto causal puro del número de
bins. Una fase posterior podrá abordar descubrimiento únicamente tras un nuevo
prerregistro que defina población, selección, variantes, multiplicidad,
criterios de exclusión y separación entre confirmación y exploración.

## Conclusión

La Fase 1 ha cumplido su función: caracterizó el comportamiento del baseline
bajo ground truth sintético, identificó fallos de ventanas cortas, mostró
sensibilidad no monotónica a extensiones temporales y documentó límites
numéricos. La evidencia es suficiente para estudiar robustez de las diez
observaciones conocidas, pero insuficiente para presentar AFINO como validado
o para iniciar búsqueda de candidatos.

`PHASE1_COMPLETE_PROCEED_TO_OBSERVATIONAL_ROBUSTNESS_WITH_LIMITATIONS`
