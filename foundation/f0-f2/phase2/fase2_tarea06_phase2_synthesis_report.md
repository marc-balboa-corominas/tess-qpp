# Fase 2 — Tarea 2.6

## Síntesis de Fase 2 y decisión de ruta del manuscrito

**Decisión:** `PHASE2_COMPLETE_ROBUSTNESS_MANUSCRIPT_VIABLE_CORRECTION_REQUIRES_PHASE3`

## 1. Pregunta metodológica

La pregunta que puede responder la Fase 2 no es si AFINO es correcto en
general ni si las señales etiquetadas contienen QPP físicamente demostradas.
La pregunta defendible es más delimitada: una vez congelado un baseline
observacional efectivo que reproduce diez clasificaciones conocidas, ¿cómo
cambian esas clasificaciones cuando se perturban de manera prerregistrada la
ventana temporal y el procesamiento, y qué estabilidad numérica conserva la
implementación AFINO 0.5? Esta formulación mantiene separados cuatro planos:
reproducción de una clasificación publicada, comportamiento bajo ground truth
sintético, robustez interna de una cohorte observacional y diagnósticos
numéricos. La síntesis documental no añade umbrales, eventos ni estadísticas
científicas nuevas.

## 2. Evidencia reproducida

F1.14 autorizó pasar a robustez observacional con limitaciones y mantuvo
bloqueado el descubrimiento. El baseline efectivo había reproducido cinco
detecciones publicadas y conservado como no seleccionados cinco controles
emparejados. F2.1 congeló diez eventos, cinco parejas, trece ventanas, seis
perfiles y denominadores separados para análisis primario y estabilidad.
F2.2 materializó 780 variantes y congeló el plan exacto antes de AFINO. F2.3
validó el runner checkpointed: 84 resultados canary, reanudación 31+53+0,
idempotencia y seis replays exactos. F2.4 ejecutó las 2.784 llamadas previstas
y exportó 928 decisiones válidas sin trabajos pendientes. Por último, F2.5
representó las 780 variantes primarias, conservó las 46 variantes W00 con diez
seeds y cerró con `FROZEN_COHORT_ROBUSTNESS_CHARACTERIZED_WITH_LIMITATIONS`.

La reproducción tiene un alcance concreto. Demuestra que el protocolo público
congelado recupera las clasificaciones de estas diez observaciones y permite
evaluar su estabilidad interna. No demuestra que se haya reconstruido el
adaptador TESS privado ni el pipeline documental completo de los autores.

## 3. Resultados sintéticos relevantes de Fase 1

Los benchmarks sintéticos aportan contexto, pero no métricas observacionales.
En el nulo estacionario principal hubo `synthetic false selection 0/480`.
Entre 99 condiciones positivas, 21 tuvieron alguna selección y 78 ninguna,
con una dependencia fuerte de longitud, periodo, ruido y amplitud. En las
2.040 decisiones de ventanas cortas N=15 o N=30 fallaron simultáneamente las
comparaciones frente a M0 y M2, y M0 fue el ganador BIC. El benchmark anidado
mostró cruces ascendentes y descendentes: ampliar la porción temporal no
produjo una mejora monotónica. Además, la clasificación fue estable frente a
seed en los subconjuntos sintéticos, mientras M2 presentó múltiples soluciones
en gran parte de las condiciones.

Estos resultados justificaron estudiar ventana y optimizador en observaciones
reales. No autorizan llamar sensibilidad al porcentaje de condiciones
positivas seleccionadas ni FPR observacional al resultado del nulo. Tampoco
demuestran un efecto causal puro del número de bins, porque las extensiones
anidadas modifican simultáneamente cola, normalización, ventana de Hann y FFT.

## 4. Admisibilidad observacional

F2.2 y F2.5 coinciden en que 514 de las 780 variantes fueron elegibles y 266
inadmisibles: 142 por `IRREGULAR_SAMPLING`, 98 por `TOO_FEW_CADENCES` y 26 por
`PEAK_REMOVED_BY_QUALITY`. Esta separación es sustantiva, no meramente
administrativa. `inadmissibility ≠ non-selection`: una variante que no cumple
el contrato de entrada no proporciona una decisión negativa de AFINO y no
debe entrar en el denominador de selección entre elegibles.

La admisibilidad también limita comparaciones. Una celda con menos variantes
elegibles no puede compararse utilizando `selected/planned` como si las
inadmisibles fueran ceros. El manuscrito debe mostrar siempre variantes
previstas, elegibles e inadmisibles y conservar sus razones. Esta decisión
evita una apariencia artificial de estabilidad o de pérdida creada por
recodificación.

## 5. Robustez de clasificación

Entre las 780 variantes hubo 140 `SELECTED`, 374 `NOT_SELECTED` y 266
`INPUT_INADMISSIBLE`. Respecto al baseline global W00/P00 de cada evento,
F2.5 registró 140 selecciones retenidas, 136 pérdidas, 238 no selecciones
retenidas y cero ganancias. La lectura defendible es que las clasificaciones
publicadas reproducidas son sensibles a cambios de ventana y procesamiento,
mientras los controles emparejados elegibles permanecieron no seleccionados
en este diseño. Las pérdidas no son falsos negativos y los controles no son
verdaderos negativos, porque `observational role ≠ physical ground truth`.

El valor `SELECTION_GAINED = 0` respecto a W00/P00 no contradice las cuatro
transiciones temporales 0→1 ni la transición de procesamiento 0→1. Las
referencias son diferentes. La comparación global enfrenta cada variante con
W00/P00. El contraste de ventanas enfrenta una ventana con W00 del mismo
perfil. El contraste de procesamiento enfrenta el perfil derecho con el
perfil izquierdo en el mismo evento y ventana. Una variante puede pasar de
0 a 1 respecto a una referencia local que ya difiere del baseline global sin
crear una ganancia respecto a W00/P00.

## 6. Seed, warnings y bounds

Las 46 variantes W00 elegibles mantuvieron su clasificación entre seeds 0–9:
15 fueron seleccionadas 10/10 veces y 31 no seleccionadas 0/10. No hubo
discordancia de decisión. Sin embargo, cada variante mostró múltiples
payloads de parámetros en los tres modelos. La formulación que debe
mantenerse es `stable classification ≠ unique numerical optimum`. La
estabilidad binaria no prueba que el optimizador alcance un único punto ni
que las soluciones tengan una interpretación física distinta.

Los diagnósticos operativos tampoco son accesorios. M1 alcanzó bounds en
632 de 928 llamadas. M2 produjo warnings en 555 llamadas, 4.690 warnings
totales y bounds en 827 llamadas. `convergence_status` permaneció
`NOT_AUDITABLE` en las 2.784 llamadas. Estos hechos deben figurar en métodos,
resultados o limitaciones, pero no permiten atribuir causalidad entre un
warning, un bound y un cambio de clasificación.

## 7. Periodo

La tabla de robustez del periodo contiene 140 filas en las que el baseline y
la variante permanecieron seleccionados y ambos periodos estaban disponibles.
Dentro de esa población condicionada, el cambio absoluto mediano fue
0,244031 s y el máximo 2,714694 s. Esta evidencia permite describir
estabilidad del periodo cuando la selección sobrevive, no robustez global del
periodo. `period robustness is conditional on retained selection`.

Los 374 centros formales M1 de decisiones no seleccionadas se conservaron como
`formal_m1_center_not_selected`. Son outputs auditables del modelo, pero no
periodos recuperados. No compensan las 136 pérdidas de clasificación ni las
266 variantes inadmisibles y deben permanecer fuera de las figuras y
resúmenes de periodo recuperado.

## 8. Limitaciones

La cohorte contiene solo diez eventos y cinco parejas. Ventanas, perfiles y
seeds son medidas repetidas dentro de eventos. No existe ground truth
observacional o físico independiente, y los perfiles se limitan a los
prerregistrados. F2.1 no congeló BIC individuales del baseline. El control
temporal externo mediana/rfftfreq no coincidió con la convención efectiva
media/fftfreq positivo de AFINO 0.5. La convergencia no es auditable; M1 y M2
presentan bounds frecuentes; M2 acumula warnings; y la multiplicidad de
parámetros impide afirmar unicidad numérica.

La evidencia corresponde a una única versión y commit de AFINO. El
descubrimiento de candidatos permaneció bloqueado. El adaptador TESS privado
y la política completa de los autores siguen sin reconstruirse. Finalmente,
los diez eventos F2 ya han sido observados: pueden motivar una corrección,
pero no funcionar simultáneamente como datos de desarrollo y validación.

## 9. Claims defendibles

Son defendibles: reproducción del baseline observacional efectivo en las diez
observaciones; dependencia de las clasificaciones publicadas respecto a
ventana y procesamiento; permanencia no seleccionada de los controles
elegibles dentro del diseño; estabilidad de clasificación frente a seed en
W00; estabilidad condicionada del periodo; y presencia de limitaciones
numéricas documentadas. También es defendible integrar los resultados
sintéticos de Fase 1 como caracterización del dominio probado, siempre
separados del rendimiento observacional.

No son defendibles: validación observacional de AFINO, sensibilidad,
especificidad, FPR observacional, ground truth físico, unicidad del óptimo o
causalidad de warnings y bounds. Tampoco es defendible afirmar que las cinco
detecciones fueron seleccionadas bajo todas las variantes. El manuscrito debe
formular las pérdidas como transiciones internas y las inadmisibles como
inputs sin decisión.

## 10. Decisión: manuscrito de robustez o corrección futura

La ruta inmediata recomendada es la Ruta A: un manuscrito metodológico de
reproducción y robustez con arquitectura de claims, métodos reproducibles,
tablas con denominadores, discusión extensa de limitaciones y código y datos
derivados auditables. La base documental y científica necesaria ya existe.

La Ruta B, una corrección del procedimiento, permanece abierta pero no
establecida. Exige definir una regla antes de ver los datos de validación,
prerregistrar criterios de éxito, construir ground truth sintético apropiado,
comparar con el baseline congelado, controlar complejidad y multiplicidad y
separar clasificación de periodo. Sobre todo, requiere un benchmark held-out
independiente. Está prohibido ajustar una regla sobre F2.5 y presentar los
mismos diez eventos como validación confirmatoria. La Fase 2 queda cerrada:
el artículo de robustez es viable con limitaciones; la afirmación de
corrección requiere Fase 3.

`PHASE2_COMPLETE_ROBUSTNESS_MANUSCRIPT_VIABLE_CORRECTION_REQUIRES_PHASE3`
