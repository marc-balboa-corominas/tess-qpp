# F3A.2 — Materialización determinista de la cohorte y freeze del plan exacto

## 1. Provenance del catálogo BAIIW0001

F3A.2 parte exclusivamente de BAIIW0001, *Stationary quasi-periodic pulsations in 20-second cadence TESS flares*, tal como quedó fijado en F3A.1. La representación machine-readable utilizada procede del repositorio público del autor y queda ligada al commit `8a29c3d0ca1883f50769ec5850581201d99a6cc0`. `Flare_detections.csv` se conserva fuera de Git con SHA-256 `866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4`; `QPP_detections.csv` queda ligado a `4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e`. No se reconstruyeron filas para aproximar conteos publicados y no se sustituyó BAIIW0001 por otra fuente.

Existe una inconsistencia documental no bloqueante: el manuscrito reporta 61 QPP en 57 estrellas, mientras que la tabla machine-readable contiene 61 eventos en 56 TIC únicos. Las 61 filas QPP se preservan literalmente. La correspondencia con el parent universe demuestra 61 enlaces únicos y ninguna ambigüedad, por lo que la discrepancia de estrellas se registra como limitación de la fuente y no como motivo para editar los datos.

## 2. Reconstrucción del parent universe

El universo parental contiene exactamente 3.878 flares pertenecientes a 1.285 TIC. La identidad QPP se determina desde la tabla fuente antes de cualquier acceso a resultados F3A. Las 61 filas QPP se vinculan de forma determinista al parent universe mediante TIC y marcador inicial de la fuente. Para cada flare se construyó una identidad estable dependiente del checksum del catálogo, número de fila canónico, TIC, sector y marcador temporal. El índice resultante contiene 3.878 eventos fuente únicos.

La asignación fuente de sector se obtuvo mediante el calendario oficial TESS archivado con SHA-256 `e7c937a06e941f3ee7af150132f135ccb3c9636fda78d30cc0f8e343fd138768`. De las 3.878 filas, 3.872 admitieron cross-check directo contra intervalos de observación. Seis necesitaron únicamente la partición cronológica entre comienzos de sector; ninguna de esas seis terminó formando parte de la cohorte congelada.

## 3. Identidad de eventos

La cohorte no depende de disponibilidad posterior en MAST ni de una clasificación producida por F3A. Cada evento conserva el `source_event_identifier`, la clave canónica, TIC, sector y marcadores start/peak/end. Los diferentes flares de una misma estrella permanecen como eventos distintos y observaciones de un mismo TIC en sectores distintos tampoco se colapsan. No hay `phase3a_event_id` duplicados ni conflictos de identidad pendientes.

## 4. Matching de controles

Las 61 referencias `PUBLISHED_QPP_REFERENCE` se conservaron completas. Para cada una se seleccionó exactamente un control `PUBLISHED_NOT_SELECTED_REFERENCE`, sin reemplazo y sin utilizar información derivada de AFINO. La jerarquía congelada produjo 31 matches en el mismo TIC y sector, 22 en el mismo TIC en otro sector permitido y 8 dentro del mismo sector. No fue necesario utilizar el fallback global. El desempate se resolvió por mínima diferencia absoluta de log-duración y, cuando correspondía, por clave canónica lexicográficamente menor. No hubo referencias sin control ni controles reutilizados. El resultado final es una cohorte de 122 eventos.

## 5. Binding a TESS

La cohorte de 122 eventos corresponde a 87 pares TIC-sector únicos. El discovery MAST encontró un producto SPOC oficial de 20 segundos para los 87 pares. Cada producto se seleccionó con TIC y sector exactos y se registraron identificador, `dataURI`, versión de procesamiento y nombre físico. Los 87 FITS se almacenan fuera de Git. El manifest conserva el SHA-256 físico de cada FITS, calculado antes de abrir los arrays científicos. No existen relaciones evento-producto marcadas como `MISSING_PRODUCT`.

## 6. Mapping temporal

El mapping entre los marcadores TBJD de BAIIW0001 y `TIME` nativo se aceptó solo después de verificar las cabeceras temporales del FITS. Start, peak y end se asignaron independientemente a la cadencia nativa más próxima, con la fila de índice menor como desempate exacto. Los 122 eventos tienen `TIME_MAPPING_VALID`; no hay mappings no resueltos ni ventanas base fuera de rango. W00 conserva start y end inclusivos y contiene el peak congelado.

## 7. Admisibilidad

La evaluación de entrada reutiliza literalmente el contrato F2: `finite_all`, `q0_native`, ausencia de interpolación o gap filling, un mínimo de 15 cadencias, peak retenido, tiempo estrictamente creciente, índices FITS nativos consecutivos, ausencia de duplicados y desviación máxima respecto de la cadencia mediana de `1e-3 s`. El detrending `linear_residual_plus_one` usa la misma construcción matricial y la misma condición de escala finita y no nula.

De las 9.516 combinaciones planificadas, 6.422 son `ELIGIBLE_FOR_AFINO` y 3.094 son `INPUT_INADMISSIBLE`. Las causas registradas son: 1.824 `IRREGULAR_SAMPLING`, 844 `TOO_FEW_CADENCES`, 282 `PEAK_REMOVED_BY_QUALITY`, 138 `PEAK_OUTSIDE_WINDOW` y 6 `WINDOW_OUT_OF_RANGE`. Estos estados describen disponibilidad y admisibilidad de entrada; no son clasificaciones QPP ni resultados físicos.

## 8. Materialización de las 78 celdas

Cada uno de los 122 eventos posee exactamente las 78 combinaciones primarias del diseño congelado, correspondientes a 13 ventanas y 6 perfiles. No se añadió ninguna celda secundaria ni se modificó una perturbación tras inspeccionar los datos. Los identificadores de variante son únicos y la matriz total contiene exactamente 9.516 filas, incluidas las variantes inadmisibles, que permanecen visibles en el manifest.

## 9. Payloads

Cada variante elegible se convirtió en un payload exacto formado por tiempo relativo en segundos, flux procesado e índices FITS nativos. Los arrays concatenados `time_seconds.npy`, `flux.npy`, `native_index.npy` y `offsets.npy` se guardan fuera de Git y quedan ligados mediante sus SHA-256 físicos. El manifest registra para cada payload sus hashes lógicos de tiempo, flux e índice y un hash lógico combinado. Las 6.422 reconstrucciones desde los arrays congelados reprodujeron exactamente el contenido materializado: `payload_roundtrip_mismatches = 0`.

## 10. Plan exacto de ejecución

Las 6.422 variantes primarias elegibles generan 6.422 decisiones primarias con seed 0. W00/P00 es elegible en 116 eventos; para cada uno se añaden las seeds 1–9, produciendo 1.044 decisiones adicionales de estabilidad. El plan contiene así 7.466 decisiones ejecutables. Cada decisión se descompone prospectivamente en M0 `pow_const`, M1 `pow_const_gauss` y M2 `bpow_const`, resultando en 22.398 llamadas: 7.466 por modelo. El cutoff queda congelado en 0,025 Hz y el commit AFINO futuro en `6aceac9518fc8056052807e666da9d0c8bebb010`. Todas las filas permanecen `NOT_EXECUTED`.

## 11. Limitaciones

La inconsistencia 57/56 de la fuente se mantiene explícita y no altera los 61 eventos QPP machine-readable. La inadmisibilidad de una variante tampoco autoriza reemplazar eventos, ajustar boundaries, rellenar gaps o cambiar denominadores de manera silenciosa. Las dependencias entre múltiples flares de una misma estrella se preservan para la interpretación posterior y no se presentan aquí como observaciones estadísticamente independientes.

## 12. Estado antes de F3A.3

F3A.2 termina antes de observar una sola clasificación producida por AFINO. No se han calculado BIC de F3A, decisiones QPP, periodos recuperados ni resultados científicos. El objetivo de esta tarea es exclusivamente fijar la cadena evento fuente → producto TESS → cadencias → variante → payload → futura llamada de modelo. Tras el freeze y revisión de este paquete, el siguiente paso es F3A.3: validar de forma canary y checkpointed el runner catalogue-scale contra este plan exacto antes de autorizar una ejecución completa.
