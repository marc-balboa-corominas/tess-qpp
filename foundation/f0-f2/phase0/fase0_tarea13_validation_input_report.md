# Fase 0 — Tarea 0.13

## Congelación de las 32 entradas de la cohorte de validación

**Estado:** completada  
**Variantes declaradas:** 32  
**Contenidos SHA-256 distintos:** 28  
**AFINO ejecutado:** no  
**Ventana:** `tau0_nearest_cadence_indices`

---

## 1. Procedencia y preflight

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea11_validation_cohort.csv` | `b48cdc09d37b2ea4c4faec430903f81b0f7b9e4f4b026510175881a2c766fb36` |
| `fase0_tarea12_product_manifest.csv` | `19b8cc1ad53c193a08e1f38405b196598a0fae96aec444ebfd087907e4fe3270` |
| `fase0_tarea12_event_reconstruction.csv` | `d168907f616ff14898f86b5e318914d0deba2d954b1dbe1d05353d242966c4c5` |
| `fase0_tarea13_freeze_validation_inputs.py` | `48ffcbe5228cab7606ad3caae4d8d8337cee9667b4954a82a128b8a71ab9ff62` |
| `fase0_tarea13_validation_input_manifest.csv` | `5046f335d375af85ce6f1b5d58f0336688f1b2225887793f727d76cf46c57323` |

Se verificaron además los seis FITS antes de leer ninguna ventana:

| FITS | SHA-256 |
|---|---|
| `tess2020294194027-s0031-0000000220433364-0198-a_fast-lc.fits` | `1ec77983e442d64f17bda373c36a6098d7ca980fc1cae4618c827e322e54b811` |
| `tess2020324010417-s0032-0000000024518895-0200-a_fast-lc.fits` | `a0ec7d514285e93be4dc17683eb7df1ef507f29126f70325e0de4042770c6d99` |
| `tess2021118034608-s0038-0000000225953237-0209-a_fast-lc.fits` | `c92e5449dc07d57cccdaabc1a2c078a471d4798b29167881a5be156c45f042c4` |
| `tess2021146024351-s0039-0000000220433364-0210-a_fast-lc.fits` | `961d90423e4099701016b92febabebd81f3ae4c047188144f7d88293cbcac726` |
| `tess2022057073128-s0049-0000000160619243-0221-a_fast-lc.fits` | `b6fdc4e7f35d6c3b42037fafe8f11fcd833caac4f2a1d18f877479e689f04b97` |
| `tess2022164095748-s0053-0000000160619243-0226-a_fast-lc.fits` | `383de5bc2c295e31fb9194cb712089f26229333c2c685e724659dc519f5cfe3b` |

No se consultó MAST ni se descargaron archivos nuevos.

---

## 2. Reglas aplicadas

- `finite_all`: TIME finito y flujo seleccionado finito, sin excluir QUALITY.
- `quality_zero_only`: condición anterior y `QUALITY == 0`.
- Ventana inclusiva desde `start_fits_index` hasta `end_fits_index` de F0.12.
- Sin interpolación, compactación temporal, renumeración, extensión o sustitución.
- Regularidad: desviación máxima respecto a la cadencia mediana ≤ 0,001 s.
- `scientific_candidate`: muestreo regular y los tres marcadores retenidos.
- Cualquier pérdida de marcador o irregularidad: `diagnostic_only`.

---

## 3. Matriz de 32 variantes

| Variante | N original→usado | Gap máx. (s) | Regular | Marcadores | Sampling | Alcance | Rol |
|---|---:|---:|---|---|---|---|---|
| `P1_published_qpp_sap_all` | 27→27 | 19.999750 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P1_published_qpp_sap_q0` | 27→25 | 39.999499 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P1_published_qpp_pdcsap_all` | 27→27 | 19.999750 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_reproduction` |
| `P1_published_qpp_pdcsap_q0` | 27→25 | 39.999499 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P1_not_selected_qpp_sap_all` | 34→34 | 20.000353 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P1_not_selected_qpp_sap_q0` | 34→33 | 40.000666 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P1_not_selected_qpp_pdcsap_all` | 34→34 | 20.000353 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_not_selected_comparison` |
| `P1_not_selected_qpp_pdcsap_q0` | 34→33 | 40.000666 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P2_published_qpp_sap_all` | 152→152 | 19.999941 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P2_published_qpp_sap_q0` | 152→139 | 59.999803 | False | `peak_marker_removed` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P2_published_qpp_pdcsap_all` | 152→152 | 19.999941 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_reproduction` |
| `P2_published_qpp_pdcsap_q0` | 152→139 | 59.999803 | False | `peak_marker_removed` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P2_not_selected_qpp_sap_all` | 178→178 | 20.000242 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P2_not_selected_qpp_sap_q0` | 178→166 | 40.000465 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P2_not_selected_qpp_pdcsap_all` | 178→178 | 20.000242 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_not_selected_comparison` |
| `P2_not_selected_qpp_pdcsap_q0` | 178→166 | 40.000465 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P3_published_qpp_sap_all` | 19→19 | 20.000233 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P3_published_qpp_sap_q0` | 19→19 | 20.000233 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P3_published_qpp_pdcsap_all` | 19→19 | 20.000233 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_reproduction` |
| `P3_published_qpp_pdcsap_q0` | 19→19 | 20.000233 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P3_not_selected_qpp_sap_all` | 16→16 | 19.999991 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P3_not_selected_qpp_sap_q0` | 16→16 | 19.999991 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P3_not_selected_qpp_pdcsap_all` | 16→16 | 19.999991 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_not_selected_comparison` |
| `P3_not_selected_qpp_pdcsap_q0` | 16→16 | 19.999991 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P4_published_qpp_sap_all` | 42→42 | 19.999579 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P4_published_qpp_sap_q0` | 42→41 | 39.999152 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P4_published_qpp_pdcsap_all` | 42→42 | 19.999579 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_reproduction` |
| `P4_published_qpp_pdcsap_q0` | 42→41 | 39.999152 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P4_not_selected_qpp_sap_all` | 44→44 | 19.999860 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `predeclared_sensitivity` |
| `P4_not_selected_qpp_sap_q0` | 44→42 | 39.999720 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |
| `P4_not_selected_qpp_pdcsap_all` | 44→44 | 19.999860 | True | `all_markers_retained` | `regular` | `scientific_candidate` | `primary_not_selected_comparison` |
| `P4_not_selected_qpp_pdcsap_q0` | 44→42 | 39.999720 | False | `all_markers_retained` | `diagnostic_irregular_sampling` | `diagnostic_only` | `predeclared_sensitivity` |

Conteos:

```json
sampling_status = {"diagnostic_irregular_sampling": 12, "regular": 20}
marker_status = {"all_markers_retained": 30, "peak_marker_removed": 2}
interpretation_scope = {"diagnostic_only": 12, "scientific_candidate": 20}
```

---

## 4. Parejas all/q0 idénticas

- `P3 / published_qpp / SAP_FLUX`
- `P3 / published_qpp / PDCSAP_FLUX`
- `P3 / not_selected_qpp / SAP_FLUX`
- `P3 / not_selected_qpp / PDCSAP_FLUX`

Estas igualdades representan contenidos duplicados, no observaciones
independientes.

---

## 5. Invariantes obligatorios de P3

| Par | Evento | Flujo | Hash all | Hash q0 | Bytes | Contenido | Resultado |
|---|---|---|---|---|---|---|---|
| P3 | published_qpp | SAP_FLUX | `290f965697b2fca58de15312db01f872eff2d36bd8582754d9850bee9ce4ad96` | `290f965697b2fca58de15312db01f872eff2d36bd8582754d9850bee9ce4ad96` | True | True | PASS |
| P3 | published_qpp | PDCSAP_FLUX | `7c0c3556d3b458c4703407fdf64b4a846b111e5a91299df86e2bb3232f3ae55d` | `7c0c3556d3b458c4703407fdf64b4a846b111e5a91299df86e2bb3232f3ae55d` | True | True | PASS |
| P3 | not_selected_qpp | SAP_FLUX | `d9cc5de6f0cc393bcc81465f426d2f8db4306ed468d07df0d3aa75fb1b89c74f` | `d9cc5de6f0cc393bcc81465f426d2f8db4306ed468d07df0d3aa75fb1b89c74f` | True | True | PASS |
| P3 | not_selected_qpp | PDCSAP_FLUX | `90103d690adfba408870a24cfdb864436249b3b91215db56db40d72a7ecf26ba` | `90103d690adfba408870a24cfdb864436249b3b91215db56db40d72a7ecf26ba` | True | True | PASS |

Los cuatro invariantes comparan hash, bytes y contenido CSV.

---

## 6. Pico del positivo P2

Las dos variantes q0 del positivo P2 registran:

```text
marker_status = peak_marker_removed
interpretation_scope = diagnostic_only
```

La muestra asociada al pico catalogado tiene `QUALITY=64`. Se elimina sin
sustitución, interpolación ni ampliación de la ventana. Los índices FITS,
CADENCENO y `cadence_index_within_original_window` conservan sus valores
originales y muestran explícitamente el hueco.

---

## 7. Incidencia de checksum heredada

Los seis productos mantienen:

```text
CHECKSUM_VERIFICATION_FAILURE_LIGHTCURVE_AND_APERTURE
PRIMARY: valid
LIGHTCURVE: invalid
APERTURE: invalid
```

La incidencia no se corrigió ni se usó para modificar eventos. Los hashes y
tamaños coinciden con F0.12 y las columnas leídas son finitas dentro de las
ventanas.

---

## 8. Diagnóstico


La matriz queda congelada con 32 variantes obtenidas exclusivamente de los
índices inclusivos reconstruidos en F0.12. Después de aplicar cada política de
calidad, 20 variantes conservan muestreo regular y
12 quedan como `diagnostic_irregular_sampling`. En total,
2 variantes pierden al menos uno de los tres marcadores; por
ello 20 se clasifican como `scientific_candidate` y
12 como `diagnostic_only`. Esta clasificación se realizó antes
de consultar cualquier salida de AFINO.

El caso metodológicamente más importante es el positivo P2. Sus variantes q0,
tanto SAP como PDCSAP, eliminan la cadencia FITS asociada al pico publicado
porque esa muestra tiene `QUALITY=64`. Ambas conservan los índices y tiempos
originales, registran `peak_marker_removed` y no se interpretarán como
candidatos principales aunque posteriormente produjeran métricas favorables.
No se sustituyó el pico, no se extendió la ventana y no se interpoló el hueco.

Se compararon las dieciséis parejas all/q0. 4 son idénticas
byte a byte y en contenido: P3 published_qpp SAP_FLUX, P3 published_qpp PDCSAP_FLUX, P3 not_selected_qpp SAP_FLUX, P3 not_selected_qpp PDCSAP_FLUX. Los cuatro invariantes predeclarados de P3 se cumplen exactamente,
como era obligatorio al no existir flags dentro de sus dos ventanas. El número
mínimo de muestras conservadas es 16, observado en
P3_not_selected_qpp_sap_all, P3_not_selected_qpp_sap_q0, P3_not_selected_qpp_pdcsap_all, P3_not_selected_qpp_pdcsap_q0. Ninguna entrada queda vacía ni por debajo del mínimo
estructural de 2 muestras fijado para esta tarea;
esto permite congelarla, sin anticipar todavía la adecuación científica de sus
bins espectrales.

Los seis FITS mantienen la incidencia heredada
`CHECKSUM_VERIFICATION_FAILURE_LIGHTCURVE_AND_APERTURE`. Sus hashes y tamaños coinciden con F0.12, y todas las
muestras utilizadas tienen TIME y flujo finitos. La matriz se generó sin
normalización, detrending, suavizado, interpolación, extensión temporal,
sustitución de eventos o ejecución de AFINO. Por tanto, las 32 entradas quedan
definidas antes de observar cualquier resultado de selección de modelos.

**Extensión:** 288 palabras.

---

## 9. Cierre metodológico

Las 32 entradas quedan congeladas antes de ejecutar AFINO. `PDCSAP_FLUX +
finite_all` queda predeclarada como variante primaria según el rol del evento,
pero ninguna de las restantes combinaciones puede omitirse en la ejecución
posterior.
