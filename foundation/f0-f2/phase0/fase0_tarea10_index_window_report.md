# Fase 0 — Tarea 0.10

## Reejecución del piloto con las ventanas reconstruidas por índices

**Estado:** completada  
**Categoría:** `SELECTION_REPRODUCED_UNDER_INDEX_WINDOW`  
**paper_reproduction_status:** `UNRESOLVED`  
**Llamadas intentadas:** 240  
**Llamadas válidas:** 240  
**Comparaciones F0.8–F0.10:** 240  
**Invariantes exactos:** 60/60  
**Tuning posterior:** no

---

## A. Protocolo

| Elemento | Valor |
|---|---|
| Commit AFINO-public | `6aceac9518fc8056052807e666da9d0c8bebb010` |
| AFINO | `0.5` |
| Python | `3.13.13` |
| NumPy | `2.5.1` |
| SciPy | `1.18.0` |
| Script | `fase0_tarea10_run_index_window_pilot.py` |
| SHA-256 del script | `07d3b54ec0fdc1225638339b73a06dae07dbd5367b724b5a32359fa47942cf31` |
| Manifiesto F0.9 | `fase0_tarea09_index_window_manifest.csv` |
| SHA-256 del manifiesto | `ba303fa13dda064e6d18d06e9d7e75f03039717a02f78b0590ffdcb7ca396149` |
| SHA-256 del entorno | `011f8ed9d7bd0f339792b2914142e94c4d30dcd4ed76d0cf96ace83fb34c079f` |
| Ventana | `tau0_nearest_cadence_indices` |
| Cambio científico respecto a F0.8 | Solo los archivos de entrada |
| Código AFINO modificado | No |
| Entradas modificadas durante la ejecución | No |

La auditoría verificó los hashes de los ocho CSV de F0.9 y confirmó que el
commit, modelos, semillas, cutoff, bounds, transformación temporal y ausencia
de preprocesamiento externo coinciden con F0.8.

La transformación temporal continuó siendo:

```python
time_seconds = (time_tbjd - time_tbjd[0]) * 86400.0
```

Se mantuvieron:

```python
low_frequency_cutoff = 1.0 / 40.0
optimizer_seeds = range(10)
```

y los bounds de M1:

```python
[
    (-10.0, 10.0),
    (-1.0, 6.0),
    (-20.0, 10.0),
    (-16.0, 5.0),
    (np.log(1.0 / 300.0), np.log(1.0 / 40.0)),
    (0.05, 0.25),
]
```

No se añadieron normalización externa, detrending, suavizado, interpolación ni
extensiones. Los documentos finales de F0.8 fueron incorporados después de su
ejecución original y quedaron registrados con sus hashes.

---

## B. Resumen por variante

El periodo indicado es el centro formal de M1. En variantes no seleccionadas no
constituye una detección QPP.

| Variante | N | Bins | M1 seleccionada | Periodo mediano (rango), s | ΔBIC₀,₁ mediano (rango) | ΔBIC₂,₁ mediano (rango) | Bounds | Warnings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Publicado · PDCSAP · all | 15 | 7 | 10/10 | 68.527671 (68.527351–68.527720) | 17.013182 (17.013182–17.013182) | 14.579592 (14.579590–14.579598) | 30/30 | 6 filas / 17 avisos |
| Publicado · SAP · all | 15 | 7 | 0/10 | 140.053719 (140.052712–140.059491) | -3.556218 (-3.556218–-3.556218) | -0.212744 (-0.213309–0.013239) | 23/30 | 5 filas / 12 avisos |
| Publicado · PDCSAP · q0 | 15 | 7 | 10/10 | 68.527671 (68.527351–68.527720) | 17.013182 (17.013182–17.013182) | 14.579592 (14.579590–14.579598) | 30/30 | 6 filas / 17 avisos |
| Publicado · SAP · q0 | 15 | 7 | 0/10 | 140.053719 (140.052712–140.059491) | -3.556218 (-3.556218–-3.556218) | -0.212744 (-0.213309–0.013239) | 23/30 | 5 filas / 12 avisos |
| No seleccionado · PDCSAP · all | 15 | 7 | 0/10 | 49.979714 (49.933573–49.980103) | -5.733566 (-5.733566–-5.733566) | -1.883365 (-1.886918–-1.882276) | 11/30 | 2 filas / 24 avisos |
| No seleccionado · SAP · all | 15 | 7 | 0/10 | 45.929139 (45.929022–45.929180) | -3.394286 (-3.394286–-3.394286) | 0.440466 (0.365929–0.488753) | 15/30 | 3 filas / 32 avisos |
| No seleccionado · PDCSAP · q0 | 14 | 6 | 0/10 | 77.173167 (72.118824–81.495468) | -5.362096 (-5.362097–-5.362096) | -1.784602 (-1.788396–-1.784308) | 8/30 | 0 filas / 0 avisos |
| No seleccionado · SAP · q0 | 14 | 6 | 0/10 | 53.019809 (51.804929–53.175238) | -4.095521 (-4.095522–-4.095521) | -0.618287 (-0.752828–-0.512002) | 7/30 | 2 filas / 22 avisos |

Las parejas `all/q0` del positivo son contenidos idénticos. Sus resultados
duplicados constituyen invariantes, no evidencias independientes.

---

## C. Comparación F0.8–F0.10

Los cambios se calculan como F0.10 menos F0.8 y se resumen mediante la mediana de
las diez semillas de M1.

| Variante | Cambio N | Cambio bins | Cambio mediano periodo (s) | Cambio mediano ΔBIC₀,₁ | Cambio mediano ΔBIC₂,₁ | Cambio de decisión |
|---|---:|---:|---:|---:|---:|---|
| Publicado · PDCSAP · all | 14→15 | 6→7 | -1.976365 | +12.227382 | +4.926674 | 0/10 → 10/10 |
| Publicado · SAP · all | 14→15 | 6→7 | +10.880066 | +0.413643 | +0.696391 | 0/10 → 0/10 |
| Publicado · PDCSAP · q0 | 14→15 | 6→7 | -1.976365 | +12.227382 | +4.926674 | 0/10 → 10/10 |
| Publicado · SAP · q0 | 14→15 | 6→7 | +10.880066 | +0.413643 | +0.696391 | 0/10 → 0/10 |
| No seleccionado · PDCSAP · all | 14→15 | 6→7 | -15.794572 | -0.426210 | -0.139569 | 0/10 → 0/10 |
| No seleccionado · SAP · all | 14→15 | 6→7 | -4.309537 | +0.171641 | +0.450664 | 0/10 → 0/10 |
| No seleccionado · PDCSAP · q0 | 13→14 | 6→6 | +5.665938 | -0.301877 | -0.222863 | 0/10 → 0/10 (diagnóstico irregular) |
| No seleccionado · SAP · q0 | 13→14 | 6→6 | +2.620981 | -0.466214 | -0.570040 | 0/10 → 0/10 (diagnóstico irregular) |

En el positivo PDCSAP, añadir la cadencia inicial cambia:

- muestras: **14→15**;
- bins después del cutoff: **6→7**;
- periodo formal: **−1,976365 s**;
- ΔBIC₀,₁: **+12,227382**;
- ΔBIC₂,₁: **+4,926674**;
- decisión: **0/10→10/10 selecciones**.

La comparación de las dos variantes `quality_zero_only` del evento no
seleccionado permanece clasificada como diagnóstica y no equivalente por
muestreo irregular.

---

## D. Comparación con el artículo

| Magnitud | Publicado | F0.10 PDCSAP | Diferencia |
|---|---:|---:|---:|
| Periodo | 68.52768338 s | 68.52767120 s | -0.00001218 s |
| ΔBIC₀,₁ | 17.01318061 | 17.01318246 | +1.84547364e-06 |
| ΔBIC₂,₁ | 14.57959220 | 14.57959176 | -4.37073375e-07 |
| Selección M1 | Sí | Sí, 10/10 semillas | Coincide |

La diferencia absoluta del periodo es
**0.00001218 s**, equivalente a
**0.00001777 %**.

La coincidencia es consistente con que el resultado catalogado se obtuviera a
partir de la ventana de 15 cadencias y PDCSAP bajo una configuración equivalente.
No constituye por sí sola una demostración del flujo y código exactos usados por
los autores.

---

## E. Diagnóstico

Añadir la cadencia inicial reproduce la selección del positivo únicamente con
PDCSAP. En las diez semillas, M1 supera simultáneamente ambos umbrales:
ΔBIC₀,₁≈17,013182 y ΔBIC₂,₁≈14,579592. El periodo mediano es
68,527671 s, a solo 0,000012 s del valor publicado. La coincidencia alcanza
también las diferencias BIC, con discrepancias medianas de aproximadamente
+1,85×10⁻⁶ y −4,37×10⁻⁷. Bajo este protocolo, la omisión de la cadencia inicial
explica por completo la falta de selección observada en F0.8 para PDCSAP.

El cambio no puede atribuirse aisladamente a un único componente. Pasar de 14 a
15 muestras modifica simultáneamente la media de normalización, la ventana de
Hann y la transformada. El efecto espectral observable es que las variantes
regulares pasan de seis a siete bins; además cambian su resolución y
frecuencias. Descomponer qué fracción del aumento de BIC procede de cada
mecanismo exigiría experimentos adicionales no incluidos en el protocolo
congelado.

SAP y PDCSAP siguen discrepando de forma decisiva. SAP no selecciona M1 en
ninguna semilla y desplaza el centro formal del positivo a unos 140,054 s.
Esto convierte la elección del producto de flujo en una cuestión central aún
abierta. El evento no seleccionado permanece sin selección en sus cuarenta
decisiones, tanto regulares como diagnósticas. Ninguna semilla cambia una
clasificación y los 60 invariantes de inputs idénticos se cumplen exactamente.

La estabilidad de la decisión no elimina las reservas numéricas. F0.10 registra
147 filas con algún parámetro en bound, frente a 115 en F0.8. Los warnings
disminuyen de 178 a 136 y continúan concentrados exclusivamente en M2. En la
solución positiva PDCSAP, M1 alcanza el límite inferior de `params[2]` en las
diez semillas; la convergencia formal continúa sin ser auditable.

Puede afirmarse que AFINO-public reproduce el evento publicado bajo la ventana
por índices, PDCSAP y la configuración congelada. No puede afirmarse todavía
que se haya reproducido globalmente el procedimiento del artículo, porque el
flujo original, la adaptación TESS y otros detalles no publicados siguen sin
confirmarse. Tampoco este caso individual valida rendimiento poblacional.

**Extensión:** 346 palabras.

---

## F. Bounds, warnings y estabilidad numérica

| Modelo | Llamadas | Filas en bound | Filas con warnings | Warnings totales |
|---|---:|---:|---:|---:|
| M0 | 80 | 26 | 0 | 0 |
| M1 | 80 | 68 | 0 | 0 |
| M2 | 80 | 53 | 29 | 136 |

Tipos de warning:

- `RuntimeWarning: overflow encountered in exp`: 111
- `RuntimeWarning: invalid value encountered in subtract`: 25

Comparación global:

| Métrica | F0.8 | F0.10 | Cambio |
|---|---:|---:|---:|
| Filas con algún bound | 115 | 147 | +32 |
| Filas con warnings | 44 | 29 | −15 |
| Warnings totales | 178 | 136 | −42 |
| Bounds de M2 | 78 | 53 | −25 |
| Warnings fuera de M2 | 0 | 0 | 0 |

En el positivo PDCSAP:

- M0 llega al límite superior de `params[1]` en 10/10 semillas.
- M1 llega al límite inferior de `params[2]` en 10/10 semillas.
- M2 llega a los límites de `params[1]` y `params[3]` en 10/10 semillas.
- El centro del bump de M1 no llega a los límites de 40 o 300 s.
- Los warnings proceden de M2, no del M1 seleccionado.

La convergencia formal sigue sin poder auditarse porque `main_analysis` no
devuelve ni comprueba `res.success` o `res.message`.

---

## G. Decisiones

### ¿Añadir la cadencia reproduce la selección?

Sí, para el positivo PDCSAP regular y en las diez semillas. SAP sigue sin
seleccionarse.

### ¿El periodo se acerca al publicado?

Sí. Pasa de una mediana de aproximadamente 70,504035 s en F0.8 a
68,527671 s en F0.10.

### ¿SAP y PDCSAP siguen discrepando?

Sí. PDCSAP reproduce selección, periodo y diferencias BIC. SAP no selecciona
M1 y sitúa el centro formal cerca de 140 s.

### ¿Cambia el evento no seleccionado?

No cambia de clasificación. Permanece sin selección en todas sus variantes y
semillas.

### ¿Las semillas alteran alguna clasificación?

No. Todas las decisiones son estables.

### ¿Se cumplen los invariantes?

Sí. SAP `all/q0` y PDCSAP `all/q0` coinciden exactamente para las diez semillas
y tres modelos: 60/60 comparaciones.

---

## H. Categoría final

### `SELECTION_REPRODUCED_UNDER_INDEX_WINDOW`

La categoría se adopta porque una variante positiva regular reproduce de manera
estable la doble condición BIC y el periodo publicado:

```text
event_role: published_qpp
flux_type: PDCSAP_FLUX
quality_policy: finite_all
window_variant: tau0_nearest_cadence_indices
selection_count: 10/10
```

La variante PDCSAP `quality_zero_only` obtiene el mismo resultado porque su
contenido es byte a byte idéntico; no es una confirmación independiente.

El estado general continúa siendo:

```text
paper_reproduction_status:
UNRESOLVED
```

Siguen pendientes el flujo realmente utilizado, la adaptación TESS no
publicada, la configuración completa de los autores, la convergencia formal y
la validación sobre una muestra mayor.

---

## I. Incidencias documentales

1. El primer intento de F0.10 no ejecutó AFINO porque el script aún no estaba
   presente en la ruta prevista. Fue un fallo de transporte, no científico.
2. La ejecución válida posterior terminó con código `0`.
3. El defecto `n_samples: null` de F0.8 quedó corregido: el resumen F0.10
   registra correctamente 15 muestras en las variantes regulares y 14 en las
   diagnósticas.
4. `afino.egg-info/` continúa como artefacto Git no versionado; no existen
   cambios versionados ni preparados.
5. F0.7, F0.8 y F0.9 permanecen inalterados.

---

## J. Hashes de evidencia

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea10_index_window_results.csv` | `7b5f8a6f88e7cbd35df37b4ce2baee410f91fae56f6036c63edeab05a55941db` |
| `fase0_tarea10_f08_f10_comparison.csv` | `330d87511925b456b7326c7330ca400df2b7b31eb0ab6c94c900baf1cb8a5da9` |
| `fase0_tarea10_execution_audit.json` | `f06ad189a8e0ff67f64399fa8279f6bde0007c9b01fe73cc02f59c6d07f5b50e` |
| `fase0_tarea10_execution_log.txt` | `1aa7759eb7cb13ab12b58eb030f47e57411c68a1fad6f7ed75d32ff7b0c659f5` |
| `fase0_tarea10_environment.txt` | `011f8ed9d7bd0f339792b2914142e94c4d30dcd4ed76d0cf96ace83fb34c079f` |
| `fase0_tarea10_console_output.txt` | `f6642ce1061016e3e5c3e9bc716918a34d0ea910ea4bf742b662e4f131b391d3` |
| `fase0_tarea10_run_index_window_pilot.py` | `07d3b54ec0fdc1225638339b73a06dae07dbd5367b724b5a32359fa47942cf31` |

---

## K. Resumen para mentor

La reejecución con la cadencia inicial recuperada reproduce exactamente el
positivo publicado cuando se usa PDCSAP. El periodo mediano es 68,527671 s y
las diferencias BIC son 17,013182 y 14,579592, prácticamente idénticas a las
publicadas. La selección es estable en 10/10 semillas. SAP sigue sin reproducir
el resultado, y el evento no seleccionado permanece sin selección. La
coincidencia resuelve la discrepancia del recorte literal, pero no demuestra
todavía la reproducibilidad integral del artículo ni su rendimiento
poblacional.
