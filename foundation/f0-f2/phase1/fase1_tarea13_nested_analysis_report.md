# Fase 1 — Tarea 1.13

## Análisis prerregistrado del efecto de extensión de ventanas anidadas

**Conclusión:** `NESTED_SUPPORT_HYPOTHESIS_MIXED`

El análisis utilizó exclusivamente las 2.160 decisiones primarias válidas de
F1.12, con `external_optimizer_seed=0`: 720 nulas y 1.440 positivas. Las
decisiones de estabilidad y el canary quedaron fuera de las tasas primarias.
Se reconstruyeron 360 trayectorias mediante la pareja normativa
`(parent_id, block_id)`, todas con N=15, 30, 45, 60, 90 y 120, y 1.800
transiciones adyacentes. No se ejecutó AFINO, no se regeneraron curvas y los
hashes de F1.8 y F1.12 permanecieron invariantes.

## Evidencia frente a M0 y M2

En positivos, la mediana de Δ01 fue -5,449 en N=15, -6,337 en N=30,
-6,487 en N=45, -6,131 en N=60, -6,337 en N=90 y -5,598 en N=120.
La mediana de Δ21 evolucionó de -1,891 a -1,491, -1,039, -0,304,
-0,038 y 1,205. Por tanto, la evidencia relativa frente a M2 aumentó con
mayor claridad que la evidencia frente a M0. M0 limitó el margen conjunto en
1435 de las 1.440 decisiones positivas; M2 lo
limitó en solo 5.

El contraste C_support se calculó en las 1.200 transiciones positivas. Su
mediana fue -0,745, con Q1
-1,162, Q3
-0,168, mínimo
-3,975 y máximo
6,278. Fue positivo en
241 transiciones, cero en
0 y negativo en
959. Las medianas por transición fueron:
15→30 -1,286,
30→45 -0,694,
45→60 -0,383,
60→90 -0,607
y 90→120 -0,619.
Los dos periodos mostraron medianas casi iguales, ambas negativas. Con alpha=2
los contrastes tardíos fueron menos negativos y 60→90 tuvo mediana ligeramente
positiva, pero no apareció un patrón uniforme entre todos los estratos.

## Cruces, secuencias y reversiones

Sí aparecieron cruces conjuntos, aunque fueron escasos. En positivos hubo
4 transiciones False→True y
2 True→False. Los cruces
individuales fueron 6 ascendentes y
3 descendentes frente a M0, y
15 ascendentes y
9 descendentes frente a M2. Las
trayectorias no fueron monotónicas: 236/240 positivas siguieron `000000`,
dos siguieron `000100` y dos `000001`. Las dos selecciones de N=60 se
revirtieron en N=90; las dos de N=120 aparecieron únicamente en la última
ventana. No hubo una trayectoria positiva que permaneciera seleccionada desde
N=60 o N=90 hasta el final.

## Nulo sintético

Bajo el nulo hubo cero synthetic false selections en N=15, N=30 y N=45;
una en N=60, cero en N=90 y una en N=120. Dos de las 120 trayectorias nulas
fueron seleccionadas alguna vez. Sus secuencias fueron 118 veces `000000`,
una vez `000100` y una vez `000001`. Se registraron
2 transiciones nulas False→True y
1 True→False. Estas cifras describen
exclusivamente synthetic false selection en el generador congelado y no una
tasa observacional de falsos positivos.

## Periodo formal y selección

Solo cuatro decisiones positivas fueron seleccionadas: una por cada combinación
N=60/P=50, N=60/P=80, N=120/P=50 y N=120/P=80. Sus errores firmados fueron,
respectivamente, +17,251 s, -12,154 s, +11,108 s y -18,625 s. Al existir una
sola observación por estrato, no puede inferirse una tendencia robusta del
periodo condicionado a selección. En las 1.440 ejecuciones válidas, el centro
formal de M1 se mantuvo separado de la recuperación seleccionada. La mediana
del error absoluto fue menor en N=30 —3,857 s para P=50 y 12,490 s para P=80—
y aumentó en N=120 hasta 40,952 s y 29,303 s. Tampoco aquí la extensión produjo
una mejora monotónica.

## Optimizador y diagnósticos

Las 54 condiciones de estabilidad contuvieron exactamente diez seeds externas.
Ninguna cambió la decisión: `selected_seed_count=0` en las 54 y discordancia
cero. Sin embargo, M2 presentó `m2_multiple_solution_flag` en
38/54 condiciones. Debe conservarse la distinción
`stable classification ≠ unique numerical optimum`.

En llamadas primarias, M0 y M1 no emitieron warnings. Los warnings de M2
afectaron al 12,8 % de llamadas en N=15 y al 93,1 % en N=120. Los bounds de
M1 afectaron entre el 48,6 % y el 65,0 % según N; los de M2 aumentaron hasta
81,1 % en N=120. Estos diagnósticos se presentan como controles descriptivos,
no como explicación causal de los cambios de selección.

## Interpretación

La hipótesis queda **mixta**. Está apoyada la parte que anticipaba la posible
aparición de cruces conjuntos y reversiones al extender prefijos. No está
apoyada, como tendencia dominante, la proposición de que aumentaría
principalmente la evidencia de M1 frente a M0: C_support fue negativo en
959/1.200 transiciones y Δ21 mejoró más que
Δ01. Además, el benchmark identifica el efecto total de extender la
observación. No permite atribuirlo causalmente al número de bins, porque
también cambian la cola observada, los momentos del ruido del prefijo, la
normalización interna, la ventana de Hann y la cuadrícula FFT.

`NESTED_SUPPORT_HYPOTHESIS_MIXED`
