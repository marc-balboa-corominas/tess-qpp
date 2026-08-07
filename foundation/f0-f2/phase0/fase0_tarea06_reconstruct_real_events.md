# Fase 0 — Tarea 0.6

## Reconstrucción de una detección QPP publicada y un evento no seleccionado en TESS

**Estado:** completada con una incidencia técnica abierta  
**Fecha de ejecución:** 31 de julio–1 de agosto de 2026  
**AFINO ejecutado:** no  
**Productos descargados:** dos SPOC FAST-LC  
**Eventos reconstruidos:** dos

---

## 1. Objetivo

Demostrar que una detección QPP publicada y una fulguración no seleccionada
como QPP pueden localizarse de forma determinista en los catálogos del estudio,
vincularse a productos oficiales TESS de 20 segundos y reconstruirse a partir
de sus intervalos temporales publicados.

La actividad evalúa procedencia archivística, cobertura temporal y contenido de
los FITS. No evalúa todavía la clasificación de AFINO.

---

## A. Entorno y procedencia

| Elemento | Valor |
|---|---|
| Python | `3.13.13` |
| astroquery | `0.4.11` |
| astropy | `8.0.1` |
| pandas | `3.0.5` |
| NumPy | `2.5.1` |
| Matplotlib | `3.11.1` |
| Entorno | `.venv_tess`, separado del entorno congelado de AFINO |
| Repositorio de catálogos | commit `8a29c3d0ca1883f50769ec5850581201d99a6cc0` |
| `Flare_detections.csv` | SHA-256 `866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4` |
| `QPP_detections.csv` | SHA-256 `4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e` |
| Script de descarga e inspección | SHA-256 `cc6454c3e29de6ad4e2b8c10989fe5b66787e307b99df842ce21a2712bd603cc` |

La primera comprobación de importaciones falló por el transporte de un bloque
multilínea mediante PowerShell. El entorno no se recreó ni se reinstaló; el
probe corregido terminó con código `0` y `pip check` no detectó dependencias
rotas.

---

## B. Selección determinista

### B.1. Detección QPP publicada

Se aplicó a `QPP_detections.csv`:

1. `Tau == 0`;
2. `Period (s) >= 60`;
3. `delta_min = min(BIC_M0_M1, BIC_M2_M1)`;
4. orden descendente por `delta_min`.

| Campo | Valor |
|---|---:|
| TIC | `67378184` |
| Inicio TBJD | `2505.134541` |
| Pico TBJD | `2505.135235` |
| Final TBJD | `2505.137782` |
| Duración | `0.003241067 d` = `4.66713648 min` |
| Periodo QPP | `68.52768338 s` |
| Amplitud | `1.398308222` |
| Energía | `9.42 × 10^30 erg` |
| ΔBIC M0–M1 | `17.01318061` |
| ΔBIC M2–M1 | `14.57959220` |
| Δmin | `14.57959220` |

El enlace con `Flare_detections.csv` mediante TIC e inicio redondeado a seis
decimales produjo exactamente una fila.

### B.2. Evento no seleccionado como QPP

Se excluyeron los 61 eventos presentes en `QPP_detections.csv`. Todas sus claves
TIC–inicio aparecieron una sola vez en el catálogo de flares. Entre los cuatro
eventos restantes del mismo TIC se escogió el de duración más próxima:

| Campo | Valor |
|---|---:|
| TIC | `67378184` |
| Inicio TBJD | `2535.256201` |
| Pico TBJD | `2535.256895` |
| Final TBJD | `2535.259442` |
| Duración | `0.003241025 d` = `4.667076 min` |
| Amplitud | `3.705017148` |
| Energía | `1.98 × 10^31 erg` |
| Diferencia de duración | `4.2 × 10^-8 d` ≈ `0.00363 s` |
| Matching | mismo TIC, duración más próxima |

Este evento se denomina **evento no seleccionado como QPP**. No se interpreta
como un negativo físico.

---

## C. Consulta MAST

La consulta inicial empleó `t_exptime=[20]`. En `astroquery 0.4.11`, el campo
continuo requiere un intervalo, por lo que ese filtro fue ignorado y la tabla de
observaciones incluyó también productos de 120 s. La incidencia se conservó.

El filtrado posterior por `provenance_name=SPOC`,
`productSubGroupDescription=FAST-LC` y extensión FITS produjo cinco productos
válidos de 20 s, en los sectores 44, 45, 46, 71 y 72. El script de descarga usó
explícitamente solo las filas con `t_exptime == 20.0`.

---

## D. Archivos MAST utilizados

| Rol | Sector | ID MAST | Archivo | Tamaño | SHA-256 local |
|---|---:|---:|---|---:|---|
| Detección QPP publicada | 44 | `68724499` | `tess2021284114741-s0044-0000000067378184-0215-a_fast-lc.fits` | 10,512,000 B | `926e45c3ff6aeee9e9332d59c1b4f4456e89d62062483257e86d1f18d09c1aff` |
| Evento no seleccionado como QPP | 45 | `71234876` | `tess2021310001228-s0045-0000000067378184-0216-a_fast-lc.fits` | 10,883,520 B | `4ae5baf9ef29ec027704cb59d606a13565a68608cae97021dbc9c07c1dc92bea` |

### URI de MAST

- Detección QPP: `mast:TESS/product/tess2021284114741-s0044-0000000067378184-0215-a_fast-lc.fits`
- Evento no seleccionado: `mast:TESS/product/tess2021310001228-s0045-0000000067378184-0216-a_fast-lc.fits`

Ambas descargas terminaron con estado `COMPLETE`, y el tamaño local coincidió
con el publicado en la tabla de productos MAST.

---

## E. Referencia temporal

Los dos FITS contienen:

| Campo | Valor |
|---|---|
| `BJDREFI` | `2457000` |
| `BJDREFF` | `0.0` |
| `TIMESYS` | `TDB` |
| `TIMEREF` | `SOLARSYSTEM` |
| `TIMEUNIT` | `d` |

Los valores `TIME` se compararon directamente con los TBJD del catálogo. No se
convirtió el eje temporal del FITS.

---

## F. Auditoría de ventanas

| Métrica | Detección QPP publicada | Evento no seleccionado como QPP |
|---|---:|---:|
| TIC | 67378184 | 67378184 |
| Sector | 44 | 45 |
| Inicio publicado | 2505.134541 | 2535.256201 |
| Pico publicado | 2505.135235 | 2535.256895 |
| Final publicado | 2505.137782 | 2535.259442 |
| TIME mínimo del archivo | 2500.180335000 | 2525.502273800 |
| TIME máximo del archivo | 2524.442913990 | 2550.629217990 |
| Cadencias en el intervalo | 14 | 14 |
| Cadencia mediana | 20.002015 s | 20.001761 s |
| SAP finitos | 14 | 14 |
| PDCSAP finitos | 14 | 14 |
| `QUALITY == 0` | 14 | 13 |
| `QUALITY != 0` | 0 | 1 |
| Valores QUALITY no nulos | ninguno | `64`, una cadencia |
| Gap máximo | 20.002015 s | 20.001761 s |
| Intervalo completamente cubierto | Sí | Sí |

No hay NaN en SAP o PDCSAP dentro de las ventanas. Los gaps máximos equivalen a
una sola cadencia nominal, por lo que no se observa ninguna cadencia ausente
dentro de los intervalos.

En los archivos completos existen:

- sector 44: 104.805 filas, 98.454 TIME finitos y 6.351 no finitos;
- sector 45: 108.540 filas, 103.545 TIME finitos y 4.995 no finitos.

Estos TIME no finitos están fuera de las ventanas seleccionadas.

---

## G. Figuras sin procesamiento

- `fase0_tarea06_positive_raw.png`
- `fase0_tarea06_nonselected_raw.png`

Cada figura contiene SAP y PDCSAP sin normalización adicional, suavizado,
interpolación, detrending adicional ni filtrado de quality flags. Las líneas
verticales indican inicio, pico y final publicados. La cadencia con
`QUALITY=64` aparece marcada en el evento no seleccionado.

Las dos fulguraciones son visualmente identificables. SAP y PDCSAP muestran
escalas y formas de fondo claramente diferentes, de modo que la elección del
flujo no puede tratarse como indiferente.

---

## H. Incidencias

### H.1. Filtro `t_exptime`

`t_exptime=[20]` no restringió la tabla inicial de observaciones. La lista final
de productos no quedó contaminada porque se filtró explícitamente por FAST-LC,
y el paso de descarga utilizó únicamente las filas con exposición igual a 20 s.

### H.2. Checksum del sector 44

Al abrir el FITS del sector 44 con `checksum=True`, Astropy emitió:

```text
Checksum verification failed for HDU ('LIGHTCURVE', 1).
Checksum verification failed for HDU ('APERTURE', 1).
```

La descarga terminó como `COMPLETE`, el tamaño local coincidió con MAST y se
registró el SHA-256 local. El archivo pudo abrirse y sus columnas y ventanas se
leyeron con resultados finitos. Aun así, el aviso no debe omitirse: debe
verificarse o documentarse como incidencia de integridad antes de una
reproducción científica definitiva.

El sector 45 no emitió este aviso.

---

## I. Diagnóstico

Los dos eventos se localizaron de manera inequívoca. El TIC por sí solo no
habría bastado, porque TIC 67378184 dispone de productos FAST-LC en cinco
sectores, pero la combinación de TIC e intervalo TBJD produjo un único archivo
que cubre cada evento. La detección QPP publicada está en el sector 44, dentro
de `tess2021284114741-s0044-0000000067378184-0215-a_fast-lc.fits`; el evento no
seleccionado como QPP está en el sector 45, dentro de
`tess2021310001228-s0045-0000000067378184-0216-a_fast-lc.fits`. Los valores
`TIME` de ambos FITS contienen directamente los tiempos publicados, con
`BJDREFI=2457000`, `TIMESYS=TDB` y unidades de días, por lo que no fue necesario
transformar el eje temporal para reconstruir las ventanas.

SAP_FLUX, PDCSAP_FLUX y QUALITY están disponibles en ambos productos. Cada
intervalo contiene 14 cadencias, todas con SAP y PDCSAP finitos. La cadencia
mediana es aproximadamente 20,002 s y el gap máximo coincide con una cadencia,
de modo que no se detectan huecos internos. La detección QPP tiene las 14
cadencias con `QUALITY=0`. El evento no seleccionado contiene una cadencia con
`QUALITY=64`, visible también en la figura, pero no se eliminó. Fuera de las
ventanas existen filas con TIME no finito en ambos archivos; esto no afecta a
los intervalos reconstruidos.

No existe un bloqueo archivístico para ejecutar posteriormente AFINO: los
eventos son visibles, están completamente cubiertos y tienen los flujos
necesarios. Sin embargo, aún no debe iniciarse una reproducción científica. Hay
que fijar previamente si se utilizará SAP o PDCSAP, qué quality mask se aplicará,
cómo se tratará la cadencia marcada con 64, qué extensión temporal se analizará
y qué normalización o detrending corresponde a la adaptación del artículo.
Además, Astropy emitió un aviso de fallo de checksum para las extensiones
LIGHTCURVE y APERTURE del archivo del sector 44. El tamaño coincide con MAST y
su SHA-256 local está registrado, pero el aviso debe verificarse o mantenerse
como incidencia de integridad antes del análisis definitivo.

**Extensión:** 324 palabras.

---

## J. Decisiones que permanecen abiertas

1. SAP frente a PDCSAP.
2. Quality mask y tratamiento de `QUALITY=64`.
3. Ventana temporal exacta que se pasará a AFINO.
4. Normalización de flujo.
5. Detrending o eliminación del perfil de flare.
6. Tratamiento de TIME no finitos fuera del intervalo.
7. Verificación del warning de checksum del sector 44.
8. Correspondencia exacta con el preprocesamiento no publicado de Joshi et al.

No se adopta todavía ninguna de estas decisiones.

---

## K. Criterio de finalización

| Requisito | Estado |
|---|---|
| Selección determinista | Cumplido |
| Uso de “evento no seleccionado como QPP” | Cumplido |
| Eventos vinculados a productos concretos de MAST | Cumplido |
| Hash local de ambos FITS | Cumplido |
| Inspección de SAP, PDCSAP y QUALITY | Cumplido |
| Cobertura temporal comprobada | Cumplido |
| Dos figuras sin procesamiento | Cumplido |
| AFINO no ejecutado | Cumplido |
| Flujo y quality mask aún no decididos | Cumplido |
| Incidencias conservadas | Cumplido |

**Conclusión:** F0.6 queda completada. La trazabilidad archivística y temporal
está demostrada. El warning de checksum del sector 44 permanece como riesgo
técnico abierto, no como resultado corregido o descartado.

---

## L. Hashes de entregables

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea06_events_manifest.csv` | `081b85cbd2706bc0186404273858233b85403885ba663071f0522e0845142987` |
| `fase0_tarea06_positive_raw.png` | `cc02c7078bacbdbcbd10964ae294df2ce9ff0bab9324652d3e9f2fb35b49f133` |
| `fase0_tarea06_nonselected_raw.png` | `b175a8a7831ca88d0c592c2a645dce0913b6c6c76270c2e8dbb35e8df63f3f1e` |
| `fase0_tarea06_fits_inspection_audit.json` | `7c19cf136d0e800313e1261fe18aa1984c7630c87f8e917e33ab82257c2dec0a` |
| `fase0_tarea06_fits_inspection_report.txt` | `9c225c575530d1d6ba090690a561f56b09a1fcddf6941f8e1facb976c0ae2389` |

## M. Resumen para mentor

La tarea demuestra que TIC y tiempos publicados permiten reconstruir de forma
trazable dos eventos reales del catálogo. Ambos pertenecen al mismo TIC, están
en sectores consecutivos y tienen una duración prácticamente idéntica. Cada
intervalo contiene 14 cadencias de aproximadamente 20 s, sin gaps ni valores no
finitos en SAP o PDCSAP. El evento no seleccionado presenta una cadencia con
`QUALITY=64`. No existe un bloqueo archivístico para continuar, pero antes de
ejecutar AFINO deben fijarse el flujo, la máscara de calidad, la ventana y el
preprocesamiento. También debe conservarse y revisar el warning de checksum del
producto del sector 44.
