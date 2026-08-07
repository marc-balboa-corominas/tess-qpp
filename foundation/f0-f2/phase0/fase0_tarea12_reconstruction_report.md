# Fase 0 — Tarea 0.12

## Reconstrucción archivística de la cohorte de validación

**Estado:** completada  
**Eventos intentados:** 8  
**RECONSTRUCTABLE:** 8  
**BLOCKED:** 0  
**FITS únicos descargados:** 6  
**Filas de auditoría de marcadores:** 72  
**AFINO ejecutado:** no  
**Variantes finales generadas:** no  
**Eventos sustituidos:** no

---

## 1. Procedencia y entorno

| Elemento | Valor |
|---|---|
| Cohorte F0.11 SHA-256 | `b48cdc09d37b2ea4c4faec430903f81b0f7b9e4f4b026510175881a2c766fb36` |
| QPP_detections.csv SHA-256 | `4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e` |
| Flare_detections.csv SHA-256 | `866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4` |
| Script SHA-256 | `96dc0b768655e44c6004bac54a1dabf90745e5d824ac6ab763e2d00e303cc30f` |
| Python | `3.13.13` |
| Astroquery | `0.4.11` |
| Astropy | `8.0.1` |
| Pandas | `3.0.5` |
| Sistema | `Windows-11-10.0.26200-SP0` |

Las consultas no usaron un filtro singleton `t_exptime=[20]`. Se consultaron
series temporales TESS por TIC y después se aplicó explícitamente:

```text
provenance_name == SPOC
19.5 <= t_exptime <= 20.5 s
productSubGroupDescription == FAST-LC
extension == fits
```

Los tiempos MAST `t_min/t_max`, expresados en MJD, solo se emplearon para
preseleccionar productos. La aceptación final se decidió con los `TIME` del
FITS y los marcadores originales de seis decimales.

---

## 2. Productos descargados

| TIC | Sector | Archivo | Bytes | SHA-256 | PROCVER | DATA_REL | Checksum |
|---|---|---|---|---|---|---|---|
| 24518895 | 32 | tess2020324010417-s0032-0000000024518895-0200-a_fast-lc.fits | 11269440 | a0ec7d514285e93be4dc17683eb7df1ef507f29126f70325e0de4042770c6d99 | spoc-5.0.21-20210107 | 48 | FAIL |
| 160619243 | 49 | tess2022057073128-s0049-0000000160619243-0221-a_fast-lc.fits | 11629440 | b6fdc4e7f35d6c3b42037fafe8f11fcd833caac4f2a1d18f877479e689f04b97 | spoc-5.0.64-20220407 | 71 | FAIL |
| 160619243 | 53 | tess2022164095748-s0053-0000000160619243-0226-a_fast-lc.fits | 10825920 | 383de5bc2c295e31fb9194cb712089f26229333c2c685e724659dc519f5cfe3b | spoc-5.0.72-20220608 | 77 | FAIL |
| 220433364 | 31 | tess2020294194027-s0031-0000000220433364-0198-a_fast-lc.fits | 11018880 | 1ec77983e442d64f17bda373c36a6098d7ca980fc1cae4618c827e322e54b811 | spoc-5.0.20-20201120 | 47 | FAIL |
| 220433364 | 39 | tess2021146024351-s0039-0000000220433364-0210-a_fast-lc.fits | 12107520 | 961d90423e4099701016b92febabebd81f3ae4c047188144f7d88293cbcac726 | spoc-5.0.35-20210626 | 56 | FAIL |
| 225953237 | 38 | tess2021118034608-s0038-0000000225953237-0209-a_fast-lc.fits | 11566080 | c92e5449dc07d57cccdaabc1a2c078a471d4798b29167881a5be156c45f042c4 | spoc-5.0.33-20210611 | 55 | FAIL |

Cada archivo se descargó una sola vez. El manifiesto conserva URI, identificador
MAST, tamaños publicado y local, cabeceras temporales, warnings y detalle de
checksum por HDU.

---

## 3. Clasificación de los ocho eventos

| Par | Rol | TIC | Sector | Archivo | N | QUALITY≠0 | Regular | Estado | Bloqueo |
|---|---|---|---|---|---|---|---|---|---|
| P1 | published_qpp | 24518895 | 32 | tess2020324010417-s0032-0000000024518895-0200-a_fast-lc.fits | 27 | 2 | True | RECONSTRUCTABLE | — |
| P1 | not_selected_qpp | 24518895 | 32 | tess2020324010417-s0032-0000000024518895-0200-a_fast-lc.fits | 34 | 1 | True | RECONSTRUCTABLE | — |
| P2 | published_qpp | 220433364 | 31 | tess2020294194027-s0031-0000000220433364-0198-a_fast-lc.fits | 152 | 13 | True | RECONSTRUCTABLE | — |
| P2 | not_selected_qpp | 220433364 | 39 | tess2021146024351-s0039-0000000220433364-0210-a_fast-lc.fits | 178 | 12 | True | RECONSTRUCTABLE | — |
| P3 | published_qpp | 225953237 | 38 | tess2021118034608-s0038-0000000225953237-0209-a_fast-lc.fits | 19 | 0 | True | RECONSTRUCTABLE | — |
| P3 | not_selected_qpp | 225953237 | 38 | tess2021118034608-s0038-0000000225953237-0209-a_fast-lc.fits | 16 | 0 | True | RECONSTRUCTABLE | — |
| P4 | published_qpp | 160619243 | 49 | tess2022057073128-s0049-0000000160619243-0221-a_fast-lc.fits | 42 | 1 | True | RECONSTRUCTABLE | — |
| P4 | not_selected_qpp | 160619243 | 53 | tess2022164095748-s0053-0000000160619243-0226-a_fast-lc.fits | 44 | 2 | True | RECONSTRUCTABLE | — |

`regular_sampling=True` exige que todos los intervalos difieran de la mediana en
como máximo `0.001 s`. La regularidad se registra, pero no forma
parte del criterio mínimo de asociación archivística.

---

## 4. Cadencias asociadas a los marcadores

| Par | Rol | Marcador | Fila FITS | CADENCENO | Offset (s) | QUALITY |
|---|---|---|---|---|---|---|
| P1 | published_qpp | start | 106175 | 4196191 | -0.012784421456 | 0 |
| P1 | published_qpp | peak | 106179 | 4196195 | -0.020185457600 | 0 |
| P1 | published_qpp | end | 106201 | 4196217 | 0.025428063017 | 0 |
| P1 | not_selected_qpp | start | 27454 | 4117470 | -0.016005480415 | 0 |
| P1 | not_selected_qpp | peak | 27457 | 4117473 | 0.023373826227 | 0 |
| P1 | not_selected_qpp | end | 27487 | 4117503 | -0.014793935053 | 0 |
| P2 | published_qpp | start | 93148 | 4054817 | -0.017717616424 | 0 |
| P2 | published_qpp | peak | 93153 | 4054822 | 0.017137060807 | 64 |
| P2 | published_qpp | end | 93299 | 4054968 | 0.032854675896 | 0 |
| P2 | not_selected_qpp | start | 91 | 4900310 | -0.025017713078 | 0 |
| P2 | not_selected_qpp | peak | 96 | 4900315 | 0.011343820796 | 0 |
| P2 | not_selected_qpp | end | 268 | 4900487 | 0.035328434918 | 0 |
| P3 | published_qpp | start | 49120 | 4828739 | 0.025680729727 | 0 |
| P3 | published_qpp | peak | 49122 | 4828741 | 0.022945767610 | 0 |
| P3 | published_qpp | end | 49138 | 4828757 | 0.001066031386 | 0 |
| P3 | not_selected_qpp | start | 69283 | 4848902 | -0.030985402324 | 0 |
| P3 | not_selected_qpp | peak | 69286 | 4848905 | 0.007347685641 | 0 |
| P3 | not_selected_qpp | end | 69298 | 4848917 | -0.012119805336 | 0 |
| P4 | published_qpp | start | 108914 | 6200164 | 0.036196432448 | 0 |
| P4 | published_qpp | peak | 108920 | 6200170 | 0.024058285648 | 0 |
| P4 | published_qpp | end | 108955 | 6200205 | -0.003544257217 | 0 |
| P4 | not_selected_qpp | start | 43229 | 6594664 | -0.006515585736 | 0 |
| P4 | not_selected_qpp | peak | 43232 | 6594667 | 0.031463733528 | 0 |
| P4 | not_selected_qpp | end | 43272 | 6594707 | -0.038155244065 | 0 |

Para cada marcador de un evento reconstruible existe exactamente una cadencia
dentro de ±0,0432 s. El CSV de auditoría conserva además la anterior, la más
próxima y la posterior, con un objetivo de nueve filas por evento
reconstruible.

---

## 5. Incidencias

- Consultas MAST con error: 0.
- Descargas con error: 0.
- Productos no legibles: 0.
- Productos con checksum FAIL: 6.
- Ventanas irregulares reconstruibles: 0.
- Cadencias QUALITY distinto de cero: 31.

Las incidencias no provocaron sustituciones ni ampliaciones de tolerancia.

---

## 6. Diagnóstico

La auditoría intentó reconstruir los ocho eventos fijados en F0.11 sin consultar
resultados de AFINO ni generar entradas de análisis. Se realizaron consultas
independientes para los cuatro TIC y se filtraron explícitamente observaciones
TESS con procedencia SPOC y exposiciones entre 19.5 y
20.5 s. Los productos se eligieron primero por cobertura MAST y
se aceptaron únicamente cuando el contenido del FITS proporcionó una sola
asociación para inicio, pico y final dentro de ±0,0432 s. Los ocho eventos quedaron RECONSTRUCTABLE sin sustituir ninguno.

La cohorte utiliza 6 FAST-LC únicos descargados. Cuando dos
eventos comparten producto, el archivo aparece una sola vez en el manifiesto y
ambas reconstrucciones apuntan al mismo SHA-256. Las ventanas inclusivas se
mantuvieron completas: no se eliminaron flags QUALITY y no se aplicaron
normalización, detrending, suavizado ni interpolación. Entre los eventos
reconstruibles se registraron 31 cadencias con QUALITY distinto
de cero y 0 ventanas clasificadas como irregulares mediante la
tolerancia conservadora de 0.001 s respecto a la cadencia
mediana. Estas propiedades no alteraron la selección de eventos ni provocaron
una decisión sobre SAP frente a PDCSAP.

Los checksums se registraron como metadato de procedencia; 6
productos presentaron resultado FAIL. Un warning de checksum no se usó por sí
solo para sustituir o desplazar una ventana cuando el archivo continuó siendo
legible, pero queda señalado para la interpretación posterior. La dependencia
más importante antes de ejecutar AFINO es la longitud efectiva de cada ventana,
el número de flags y cualquier irregularidad temporal, porque todos pueden
cambiar la cuadrícula espectral al filtrar QUALITY. Esta tarea solo establece
la trazabilidad catálogo–producto–cadencia. No demuestra todavía que la
reproducción de F0.10 se generalice, ni confirma globalmente PDCSAP como flujo
original.

**Extensión:** 287 palabras.

---

## 7. Cierre metodológico

Esta actividad no decide SAP frente a PDCSAP ni aplica filtros de calidad. No se
han creado las 32 variantes posteriores. Los eventos `BLOCKED`, si existen,
permanecen congelados y no pueden reemplazarse. Los eventos
`RECONSTRUCTABLE` quedan preparados únicamente para una fase posterior de
congelación de entradas.
