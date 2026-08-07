# Fase 0 — Tarea 0.14

## Ejecución ciega de AFINO-public sobre la cohorte congelada

**Estado:** completada con auditoría íntegra  
**Categoría global:** `FULL_PRIMARY_COHORT_REPRODUCTION`  
**paper_reproduction_status:** `UNRESOLVED`  
**Llamadas intentadas:** 960  
**Decisiones:** 320  
**Invariantes P3:** 120/120  
**Tuning posterior:** no

---

## 1. Protocolo y hashes

| Elemento | Valor |
|---|---|
| Commit AFINO-public | `6aceac9518fc8056052807e666da9d0c8bebb010` |
| Script SHA-256 | `9cd7c7bfa3bc3dccab38910f49210876088036d567330081de0b29c68332fd01` |
| Cohorte F0.11 SHA-256 | `b48cdc09d37b2ea4c4faec430903f81b0f7b9e4f4b026510175881a2c766fb36` |
| Manifiesto F0.13 SHA-256 | `5046f335d375af85ce6f1b5d58f0336688f1b2225887793f727d76cf46c57323` |
| Auditoría F0.13 SHA-256 | `4014c9f6888b3bc01447571e84ef698365ff917fd8c7618c11dbd212e42d4c4f` |
| Entorno SHA-256 | `011f8ed9d7bd0f339792b2914142e94c4d30dcd4ed76d0cf96ace83fb34c079f` |
| Python | `3.13.13` |
| AFINO | `0.5` |
| Duración total | `533.592059 s` |

Se conservaron los modelos M0=`pow_const`, M1=`pow_const_gauss` y
M2=`bpow_const`; semillas 0–9; cutoff `1/40 Hz`; transformación
`(time_tbjd-time_tbjd[0])*86400`; bounds de M1 de F0.10; y defaults públicos de
M0/M2. La semilla se reinició antes de cada llamada individual.

---

## 2. Resumen de las 32 variantes

| Variante | N | Bins | Decisiones válidas | Selecciones | Periodo M1 mediano (s) | ΔBIC₀,₁ mediano | ΔBIC₂,₁ mediano | Bounds | Warnings |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `P1_published_qpp_sap_all` | 27 | `[13]` | 10 | 10 | 55.742288 | 16.396258 | 19.913349 | 19 | 53 |
| `P1_published_qpp_sap_q0` | 25 | `[12]` | 10 | 0 | 65.348541 | -3.597228 | -0.629449 | 11 | 26 |
| `P1_published_qpp_pdcsap_all` | 27 | `[13]` | 10 | 10 | 56.058235 | 17.557964 | 19.987563 | 20 | 31 |
| `P1_published_qpp_pdcsap_q0` | 25 | `[12]` | 10 | 0 | 226.749361 | -3.436667 | -1.611092 | 18 | 49 |
| `P1_not_selected_qpp_sap_all` | 34 | `[16]` | 10 | 0 | 68.162172 | -2.129018 | 1.438087 | 20 | 21 |
| `P1_not_selected_qpp_sap_q0` | 33 | `[16]` | 10 | 0 | 70.883664 | -5.209028 | -1.368983 | 20 | 24 |
| `P1_not_selected_qpp_pdcsap_all` | 34 | `[16]` | 10 | 0 | 104.414795 | -5.844746 | -1.435880 | 8 | 38 |
| `P1_not_selected_qpp_pdcsap_q0` | 33 | `[16]` | 10 | 0 | 40.560994 | -5.163694 | -0.650692 | 18 | 14 |
| `P2_published_qpp_sap_all` | 152 | `[75]` | 10 | 10 | 73.241706 | 10.879828 | 13.883268 | 10 | 106 |
| `P2_published_qpp_sap_q0` | 139 | `[69]` | 10 | 0 | 70.849304 | -5.468512 | 0.894909 | 10 | 81 |
| `P2_published_qpp_pdcsap_all` | 152 | `[75]` | 10 | 10 | 73.209746 | 10.543011 | 12.719207 | 10 | 47 |
| `P2_published_qpp_pdcsap_q0` | 139 | `[69]` | 10 | 0 | 72.189592 | -6.778612 | -0.973648 | 20 | 126 |
| `P2_not_selected_qpp_sap_all` | 178 | `[88]` | 10 | 0 | 82.476394 | -4.770378 | 0.500833 | 10 | 127 |
| `P2_not_selected_qpp_sap_q0` | 166 | `[82]` | 10 | 0 | 86.669629 | -6.506215 | -0.842705 | 10 | 90 |
| `P2_not_selected_qpp_pdcsap_all` | 178 | `[88]` | 10 | 0 | 83.358910 | -4.491040 | 0.137787 | 10 | 142 |
| `P2_not_selected_qpp_pdcsap_q0` | 166 | `[82]` | 10 | 0 | 88.163408 | -6.403875 | -1.347356 | 10 | 92 |
| `P3_published_qpp_sap_all` | 19 | `[9]` | 10 | 0 | 40.000000 | 2.032075 | 5.440432 | 19 | 93 |
| `P3_published_qpp_sap_q0` | 19 | `[9]` | 10 | 0 | 40.000000 | 2.032075 | 5.440432 | 19 | 93 |
| `P3_published_qpp_pdcsap_all` | 19 | `[9]` | 10 | 10 | 44.031324 | 11.619056 | 14.451670 | 20 | 38 |
| `P3_published_qpp_pdcsap_q0` | 19 | `[9]` | 10 | 10 | 44.031324 | 11.619056 | 14.451670 | 20 | 38 |
| `P3_not_selected_qpp_sap_all` | 16 | `[7]` | 10 | 0 | 48.832129 | -5.202433 | -1.655920 | 14 | 0 |
| `P3_not_selected_qpp_sap_q0` | 16 | `[7]` | 10 | 0 | 48.832129 | -5.202433 | -1.655920 | 14 | 0 |
| `P3_not_selected_qpp_pdcsap_all` | 16 | `[7]` | 10 | 0 | 49.013925 | -5.192861 | -1.508101 | 15 | 24 |
| `P3_not_selected_qpp_pdcsap_q0` | 16 | `[7]` | 10 | 0 | 49.013925 | -5.192861 | -1.508101 | 15 | 24 |
| `P4_published_qpp_sap_all` | 42 | `[20]` | 10 | 0 | 59.499635 | 2.519421 | 6.736896 | 20 | 48 |
| `P4_published_qpp_sap_q0` | 41 | `[20]` | 10 | 0 | 60.673400 | 3.133460 | 7.420994 | 20 | 49 |
| `P4_published_qpp_pdcsap_all` | 42 | `[20]` | 10 | 10 | 60.053929 | 13.503810 | 17.706372 | 20 | 65 |
| `P4_published_qpp_pdcsap_q0` | 41 | `[20]` | 10 | 10 | 61.108581 | 12.824993 | 17.126507 | 20 | 40 |
| `P4_not_selected_qpp_sap_all` | 44 | `[21]` | 10 | 0 | 53.873181 | -7.826861 | -3.954170 | 19 | 40 |
| `P4_not_selected_qpp_sap_q0` | 42 | `[20]` | 10 | 0 | 54.796239 | -4.509716 | -0.758128 | 19 | 51 |
| `P4_not_selected_qpp_pdcsap_all` | 44 | `[21]` | 10 | 0 | 53.710980 | -7.779819 | -2.718635 | 19 | 39 |
| `P4_not_selected_qpp_pdcsap_q0` | 42 | `[20]` | 10 | 0 | 54.767414 | -4.519371 | 1.172432 | 20 | 66 |

---

## 3. Cohorte primaria

| Par | Rol | N | Válidas | Selecciones | Clasificación | Periodo publicado | Periodo mediano | ΔBIC₀,₁ publicado/mediano | ΔBIC₂,₁ publicado/mediano |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|
| P1 | `published_qpp` | 27 | 10 | 10 | `STABLE_REPRODUCTION` | 56.05823638 | 56.05823457 | 17.55796487/17.55796424 | 19.98756342/19.98756291 |
| P1 | `not_selected_qpp` | 34 | 10 | 0 | `STABLE_NOT_SELECTED` | — | 104.41479479 | —/-5.84474569 | —/-1.43587967 |
| P2 | `published_qpp` | 152 | 10 | 10 | `STABLE_REPRODUCTION` | 73.20971864 | 73.20974574 | 10.54301500/10.54301087 | 12.71921134/12.71920721 |
| P2 | `not_selected_qpp` | 178 | 10 | 0 | `STABLE_NOT_SELECTED` | — | 83.35891026 | —/-4.49104018 | —/0.13778673 |
| P3 | `published_qpp` | 19 | 10 | 10 | `STABLE_REPRODUCTION` | 44.03128221 | 44.03132380 | 11.61905655/11.61905570 | 14.45167103/14.45167032 |
| P3 | `not_selected_qpp` | 16 | 10 | 0 | `STABLE_NOT_SELECTED` | — | 49.01392542 | —/-5.19286140 | —/-1.50810141 |
| P4 | `published_qpp` | 42 | 10 | 10 | `STABLE_REPRODUCTION` | 60.05392234 | 60.05392866 | 13.50380923/13.50380958 | 17.70634440/17.70637199 |
| P4 | `not_selected_qpp` | 44 | 10 | 0 | `STABLE_NOT_SELECTED` | — | 53.71097961 | —/-7.77981902 | —/-2.71863489 |

---

## 4. Comparación numérica de los positivos primarios

Las diferencias son valores medidos menos publicados, salvo el periodo, que se
presenta como diferencia absoluta.

| Par | Selección | Δ periodo mediana (s) | Δ periodo mediana (%) | Δ(ΔBIC₀,₁) mediana | Δ(ΔBIC₂,₁) mediana |
|---|---|---:|---:|---:|---:|
| P1 | `STABLE_REPRODUCTION` | 0.00000266 | 0.00000474 | -0.00000063 | -0.00000051 |
| P2 | `STABLE_REPRODUCTION` | 0.00003491 | 0.00004768 | -0.00000413 | -0.00000413 |
| P3 | `STABLE_REPRODUCTION` | 0.00004720 | 0.00010721 | -0.00000085 | -0.00000071 |
| P4 | `STABLE_REPRODUCTION` | 0.00000649 | 0.00001081 | 0.00000035 | 0.00002759 |

No se aplica ninguna tolerancia posterior para declarar concordancia numérica.

---

## 5. SAP frente a PDCSAP

| Par | Rol | Comparaciones válidas | SAP seleccionada | PDCSAP seleccionada | Semillas con decisión distinta |
|---|---|---:|---:|---:|---:|
| P1 | `published_qpp` | 10/10 | 10/10 | 10/10 | 0/10 |
| P1 | `not_selected_qpp` | 10/10 | 0/10 | 0/10 | 0/10 |
| P2 | `published_qpp` | 10/10 | 10/10 | 10/10 | 0/10 |
| P2 | `not_selected_qpp` | 10/10 | 0/10 | 0/10 | 0/10 |
| P3 | `published_qpp` | 10/10 | 0/10 | 10/10 | 10/10 |
| P3 | `not_selected_qpp` | 10/10 | 0/10 | 0/10 | 0/10 |
| P4 | `published_qpp` | 10/10 | 0/10 | 10/10 | 10/10 |
| P4 | `not_selected_qpp` | 10/10 | 0/10 | 0/10 | 0/10 |

---

## 6. Efecto de QUALITY == 0

| Par | Rol | Flujo | Input all=q0 | Estado q0 | Marcadores q0 | Comparaciones válidas | Cambios de decisión |
|---|---|---|---|---|---|---:|---:|
| P1 | `published_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 10/10 |
| P1 | `published_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 10/10 |
| P1 | `not_selected_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P1 | `not_selected_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P2 | `published_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `peak_marker_removed` | 10/10 | 10/10 |
| P2 | `published_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `peak_marker_removed` | 10/10 | 10/10 |
| P2 | `not_selected_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P2 | `not_selected_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P3 | `published_qpp` | `SAP_FLUX` | True | `regular` | `all_markers_retained` | 10/10 | 0/10 |
| P3 | `published_qpp` | `PDCSAP_FLUX` | True | `regular` | `all_markers_retained` | 10/10 | 0/10 |
| P3 | `not_selected_qpp` | `SAP_FLUX` | True | `regular` | `all_markers_retained` | 10/10 | 0/10 |
| P3 | `not_selected_qpp` | `PDCSAP_FLUX` | True | `regular` | `all_markers_retained` | 10/10 | 0/10 |
| P4 | `published_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P4 | `published_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P4 | `not_selected_qpp` | `SAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |
| P4 | `not_selected_qpp` | `PDCSAP_FLUX` | False | `diagnostic_irregular_sampling` | `all_markers_retained` | 10/10 | 0/10 |

Las doce variantes irregulares conservan `diagnostic_only` y quedan excluidas
de la categoría global y de cualquier estimación de rendimiento.

---

## 7. Invariantes de P3

- Comparaciones esperadas: 120.
- Comparaciones superadas: 120.
- Resultado global: `True`.

Las cuatro parejas all/q0 idénticas se compararon por semilla y modelo en BIC,
likelihood, parámetros, periodo, rchi2, probabilidad, decisión, warnings y hits
de bounds.

---

## 8. Bins, bounds y warnings

| Modelo | Llamadas | Estados | Filas en bound | Filas con warnings | Warnings totales |
|---|---:|---|---:|---:|---:|
| M0 | 320 | `{'OK': 320}` | 0 | 0 | 0 |
| M1 | 320 | `{'OK': 320}` | 222 | 0 | 0 |
| M2 | 320 | `{'OK': 320}` | 295 | 194 | 1775 |

La convergencia formal permanece `NOT_AUDITABLE`.

---

## 9. Diagnóstico

La ejecución ciega intentó las 960 llamadas predeclaradas sobre los 32 archivos
congelados, sin detenerse por resultados intermedios. Se obtuvieron
960 llamadas válidas y 0 errores. La
conclusión primaria se restringe a PDCSAP, `finite_all`, muestreo regular y los
tres marcadores retenidos. En ese conjunto, 4 de los
cuatro positivos alcanzan `STABLE_REPRODUCTION` y 4 de los
cuatro eventos emparejados alcanzan `STABLE_NOT_SELECTED`. Hay
0 estados primarios dependientes de la semilla. La
categoría resultante es `FULL_PRIMARY_COHORT_REPRODUCTION`; describe únicamente la concordancia de
estos ocho eventos y no una tasa de detección poblacional.

La comparación con el catálogo se mantiene separada de la selección. Para cada
positivo se registran el centro formal de M1 y las diferencias exactas de
periodo y BIC en las diez semillas, sin introducir una tolerancia posterior. Si
M1 no supera ambos umbrales, su periodo se conserva como
`formal_m1_center_not_selected` y no se presenta como QPP reproducida. Esto
permite distinguir una clasificación coincidente de una proximidad numérica
que, por sí sola, no decide el modelo.

SAP y PDCSAP difieren en 20 de
80 comparaciones válidas emparejadas de decisiones
`finite_all`. Esta cifra documenta sensibilidad al producto de flujo, pero no
identifica cuál usaron los autores fuera de la hipótesis primaria. El filtrado
q0 cambia 40 decisiones entre 160 comparaciones
all/q0 válidas; 40 de esos cambios pertenecen a
variantes diagnósticas. Esas series no entran en la categoría
global. En particular, P2 positivo q0 sigue excluido de cualquier afirmación de
reproducción porque elimina la cadencia del pico y genera muestreo irregular,
aunque su ajuste pudiera parecer favorable.

Los cuatro pares idénticos de P3 produjeron
120/120 comparaciones
exactas por semilla y modelo. Así se comprueba que el reinicio independiente de
la semilla conserva BIC, likelihood, parámetros, periodo, warnings y bounds
para contenidos idénticos. Las variantes proporcionan bins después del cutoff
en el conjunto [7, 9, 12, 13, 16, 20, 21, 69, 75, 82, 88]. Se registraron 517 filas con algún parámetro
en bound y 1775 warnings. Estas incidencias forman parte de la
salida congelada y no se corrigieron tras observarlas.

La convergencia permanece `NOT_AUDITABLE`: AFINO-public devuelve soluciones
finitas, pero `main_analysis` no expone `res.success` ni `res.message`. Los
fallos CHECKSUM de LIGHTCURVE y APERTURE continúan como procedencia heredada de
F0.12, no como ajustes de esta fase. Ningún resultado se utilizó para cambiar
ventanas, políticas de calidad, bounds, semillas o el orden interpretativo
predeclarado. `paper_reproduction_status` permanece `UNRESOLVED`, porque aún
faltan las extensiones 1τ–3τ, la selección completa de 61 detecciones y los
3.817 eventos no seleccionados.

**Extensión:** 414 palabras.

---

## 10. Categoría y límites

```text
cohort_category:
FULL_PRIMARY_COHORT_REPRODUCTION

paper_reproduction_status:
UNRESOLVED
```

La conclusión primaria utiliza exclusivamente las ocho variantes PDCSAP
`finite_all`. Las demás son sensibilidades predeclaradas o diagnósticos. Cuatro
positivos y cuatro eventos emparejados no constituyen una estimación
poblacional.
