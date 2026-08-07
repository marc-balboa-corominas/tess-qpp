# Fase 0 — Tarea 0.15

## Cierre de la reproducción y especificación del baseline

**Baseline:** `afino_public_tess_reproduction_v1`  
**Estado:** `EMPIRICALLY_REPRODUCED_BASELINE`  
**paper_reproduction_status:** `UNRESOLVED`  
**Operaciones nuevas:** ninguna ejecución de AFINO, ninguna descarga y ninguna modificación de artefactos anteriores.

---

## A. Pregunta inicial

La fase de reproducción pretendía establecer si los resultados reales del catálogo TESS podían reconstruirse a partir de datos públicos y ejecutarse con el núcleo público de AFINO de forma suficientemente precisa como para recuperar la decisión de selección, el periodo y las diferencias BIC. La pregunta no era todavía medir sensibilidad o especificidad, ni demostrar que el repositorio público fuera documentalmente idéntico al pipeline privado de los autores. El criterio operativo era más limitado: identificar un protocolo reproducible, congelarlo antes de ampliar la muestra y comprobarlo fuera del caso utilizado para reconstruirlo.

---

## B. Cadena de evidencia

F0.1 fijó el catálogo y separó detecciones publicadas de eventos simplemente no seleccionados como QPP. F0.2 auditó el repositorio público y recuperó las fórmulas de M0, M1 y M2, la normalización interna, Hann, FFT, likelihood, optimizadores y BIC, además de identificar la ausencia de la capa TESS completa.

F0.5 demostró funcionalmente que el commit congelado distingue un nulo de una QPP sintética fuerte: 0/10 selecciones en el nulo y 10/10 en la señal de 80 s. F0.6–F0.9 reconstruyeron la procedencia catálogo–FITS–cadencia y mostraron que comparar literalmente los límites redondeados podía omitir una cadencia real.

F0.10 incorporó la cadencia inicial del caso de calibración mediante una ventana inclusiva por índices. Con PDCSAP, la decisión cambió de 0/10 a 10/10 y periodo y BIC coincidieron casi exactamente con el catálogo. F0.11 seleccionó cuatro pares nuevos sin mirar curvas ni resultados. F0.12 reconstruyó sus ocho ventanas en seis FAST-LC y asoció unívocamente los 24 marcadores. F0.13 congeló 32 combinaciones de flujo y QUALITY antes de ejecutar AFINO.

F0.14 intentó las 960 llamadas predeclaradas. Las cuatro detecciones primarias fueron `STABLE_REPRODUCTION`; los cuatro eventos emparejados fueron `STABLE_NOT_SELECTED`; los 120 invariantes de P3 fueron exactos. Sumados al caso de calibración, el protocolo reproduce cinco detecciones publicadas y conserva la no selección de cinco eventos emparejados pertenecientes a cinco TIC distintos.

### Registro mínimo de artefactos probatorios

| Etapa | Artefacto | SHA-256 | Función probatoria |
|---|---|---|---|
| F0.5 — baseline sintético | `fase0_tarea05_synthetic_model_selection.md` | `0bee6b63e1ee514527df16f8b36145966c3c0ee3b801dc19f97f3430bcf681ff` | Prueba funcional nulo/QPP. |
| F0.10 — calibración | `fase0_tarea10_index_window_results.csv` | `7b5f8a6f88e7cbd35df37b4ce2baee410f91fae56f6036c63edeab05a55941db` | Reproducción del primer positivo y su comparación. |
| F0.10 — informe | `fase0_tarea10_index_window_report.md` | `c2a10970f6e9bd12f91ee6ed95a79aef3eb0ea3fbfb7ca4dc0a05337be896d6e` | Interpretación y límites de la calibración. |
| F0.11 — cohorte | `fase0_tarea11_validation_cohort.csv` | `b48cdc09d37b2ea4c4faec430903f81b0f7b9e4f4b026510175881a2c766fb36` | Selección ciega de cuatro pares nuevos. |
| F0.12 — productos | `fase0_tarea12_product_manifest.csv` | `19b8cc1ad53c193a08e1f38405b196598a0fae96aec444ebfd087907e4fe3270` | Procedencia de seis FAST-LC. |
| F0.12 — eventos | `fase0_tarea12_event_reconstruction.csv` | `d168907f616ff14898f86b5e318914d0deba2d954b1dbe1d05353d242966c4c5` | Ocho ventanas reconstruibles. |
| F0.12 — marcadores | `fase0_tarea12_marker_audit.csv` | `c4c78041099214f913cc8e3a0f4e8e0d833e82ae523ecffec27faecac43fef4a` | Asociación de 24 marcadores. |
| F0.13 — manifiesto | `fase0_tarea13_validation_input_manifest.csv` | `5046f335d375af85ce6f1b5d58f0336688f1b2225887793f727d76cf46c57323` | Congelación de las 32 entradas. |
| F0.14 — resultados | `fase0_tarea14_validation_results.csv` | `e832059ace112013d3545ee768d013942ffdc2d752dc31f31ce8424546a2ba35` | 960 salidas por modelo. |
| F0.14 — decisiones | `fase0_tarea14_validation_decisions.csv` | `e427b8fcf9049cba1a91f33a98b04e7eebb71314576a07cca4156e64af0141d8` | 320 decisiones por variante y semilla. |
| F0.14 — resumen primario | `fase0_tarea14_primary_cohort_summary.csv` | `c02f42883ca0a82d1b98b139638442c8e17eaab8c8ec30003091999aad1e77fa` | Ocho clasificaciones primarias. |
| F0.14 — auditoría | `fase0_tarea14_execution_audit.json` | `7d77da2d862d8052b7b9a70897ff9f3b809c275217416b1aaf447447d480efa6` | Preflight, invariantes, bounds y warnings. |
| F0.14 — informe | `fase0_tarea14_validation_report.md` | `9f5afbc52fbfcb6ca1604ffe91295c035689b6d83e7507313648c8af4727113d` | Categoría global y límites. |

---

## C. Baseline efectivo

| Componente | Valor que pasa a Fase 1 | Clase de evidencia |
|---|---|---|
| AFINO | `aringlis/afino_release_version`, commit `6aceac9518fc8056052807e666da9d0c8bebb010`, versión `0.5`, sin modificaciones | `DIRECT_PUBLIC_CODE` |
| Entrada primaria | `PDCSAP_FLUX` | `EMPIRICALLY_IDENTIFIED` |
| Política QUALITY primaria | `finite_all` | `EMPIRICALLY_IDENTIFIED` |
| Ventana | `tau0_nearest_cadence_indices`, inicio y final inclusivos | `EMPIRICALLY_IDENTIFIED` |
| Asociación temporal | Cadencia única dentro de ±0,0432 s para cada marcador | `EMPIRICALLY_IDENTIFIED` |
| Tiempo | `(time_tbjd - time_tbjd[0]) * 86400` | `EMPIRICALLY_IDENTIFIED` |
| Preprocesamiento AFINO | Normalización por la media, ventana de Hann, FFT y rescalado público de potencia | `DIRECT_PUBLIC_CODE` |
| Dominio espectral | `low_frequency_cutoff = 1/40 Hz` | `EMPIRICALLY_IDENTIFIED` |
| Modelos | M0=`pow_const`, M1=`pow_const_gauss`, M2=`bpow_const` | `DIRECT_PUBLIC_CODE` |
| Centro M1 | Periodos entre 40 y 300 s | `EMPIRICALLY_IDENTIFIED` |
| Selección | ΔBIC₀,₁ > 10 y ΔBIC₂,₁ > 10 | `EMPIRICALLY_IDENTIFIED` |
| Validación | Semillas 0–9, reiniciadas antes de cada modelo | `EMPIRICALLY_IDENTIFIED` |
| Convergencia | `NOT_AUDITABLE` | `UNRESOLVED` |

La especificación JSON es la fuente normativa del baseline. La matriz CSV asigna una clase de evidencia a cada componente y evita transformar una coincidencia numérica en confirmación documental del método de los autores.

---

## D. Qué está reproducido

Se han reproducido cinco detecciones QPP publicadas y cinco eventos emparejados no seleccionados como QPP, sin contar variantes all/q0 idénticas como nuevos eventos. En los cinco positivos, PDCSAP `finite_all` con la ventana inclusiva por índices recupera establemente la doble decisión BIC en 10/10 semillas. En los cuatro positivos nuevos, las diferencias absolutas de periodo son inferiores a 5×10⁻⁵ s; las diferencias medianas de ΔBIC₀,₁ y ΔBIC₂,₁ son del orden de 10⁻⁶–10⁻⁵.

También está reproducida la estabilidad de clasificación frente a las diez semillas utilizadas. Esto no implica que todos los parámetros sean únicos: M2 encuentra soluciones alternativas en P1, P3 y P4, pero sin cambiar el resultado de selección. La afirmación válida es, por tanto, que el baseline reproduce la decisión y presenta concordancia numérica estrecha con el catálogo para los eventos examinados.

---

## E. Qué no está reproducido

No se han reproducido las 61 detecciones del catálogo, los 3.817 eventos no seleccionados, las extensiones 1τ, 2τ y 3τ, ni el detector original de flares. Tampoco se ha recuperado el cálculo de las incertidumbres publicadas del periodo.

Continúan desconocidos la adaptación TESS privada, la política global de QUALITY, la configuración exacta completa de optimización, el uso global de PDCSAP y la correspondencia documental entre el commit público y el código ejecutado por los autores. La convergencia formal no puede auditarse porque `main_analysis` no conserva `res.success` ni `res.message`. Finalmente, la cohorte no proporciona sensibilidad, especificidad, tasa de falsos seleccionados ni ground truth físico independiente.

---

## F. Riesgos prioritarios

1. **Multiplicidad de soluciones de M2.** P1, P3 y P4 muestran soluciones alternativas dependientes de la semilla. Una clasificación estable no demuestra un óptimo numérico único.
2. **Bounds frecuentes.** En F0.14, M1 toca bounds en 222/320 llamadas y M2 en 295/320.
3. **Sensibilidad a una sola cadencia.** En calibración, pasar de 14 a 15 muestras cambió la selección de 0/10 a 10/10.
4. **Dependencia SAP/PDCSAP.** SAP reproduce dos de cuatro positivos nuevos; PDCSAP reproduce los cuatro.
5. **Muestreo irregular tras filtrar QUALITY.** Doce variantes q0 contienen gaps; P2 pierde específicamente la cadencia del pico.
6. **Pocos bins en ventanas cortas.** Las comparaciones primarias alcanzan solo siete bins después del cutoff.
7. **Ausencia de ground truth observacional.** Las etiquetas provienen del propio catálogo y no equivalen a verdad física independiente.
8. **CHECKSUM no válido en extensiones FITS.** Los seis productos presentan fallo de verificación en LIGHTCURVE y APERTURE, aunque tamaños, hashes locales, legibilidad y columnas analizadas fueron coherentes.

Estos riesgos no contradicen la reproducción lograda. Definen las variables que deberá controlar el benchmark sintético: ruido rojo, amortiguamiento, deriva del periodo, morfología compleja, duración, gaps, número de bins, cercanía a bounds y competencia inestable con M2.

---

## G. Decisión

La Fase 0 ha cumplido su objetivo operativo. Existe un baseline único, reproducido en cinco detecciones y cinco comparaciones, congelado mediante hashes y separado explícitamente del método completo —todavía desconocido— de los autores. No hay una contradicción objetiva que justifique detener el proyecto o supeditar el siguiente paso a una respuesta externa.

La Fase 1 deberá prerregistrar el benchmark antes de generar resultados y no podrá modificar retrospectivamente este baseline para mejorar su rendimiento.

**GO_TO_PHASE_1**
