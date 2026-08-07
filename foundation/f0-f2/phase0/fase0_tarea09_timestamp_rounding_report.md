# Fase 0 — Tarea 0.9

## Auditoría del redondeo temporal y reconstrucción por índices de cadencia

**Estado:** completada con nuevas entradas congeladas  
**AFINO ejecutado:** no  
**Marcadores inspeccionados:** 6  
**Filas de auditoría vecinal:** 18  
**Ventana candidata:** `tau0_nearest_cadence_indices`

---

## 1. Preservación de artefactos anteriores

Se verificaron los hashes congelados de F0.7, los artefactos de ejecución de
F0.8, el manifiesto F0.6, los dos FAST-LC y el catálogo de flares. No se
modificó ni sobrescribió ninguno.

- Artefactos requeridos verificados: 19.
- Artefactos F0.8 opcionales presentes y verificados: 0.

---

## 2. Precisión temporal del catálogo

| Propiedad | Valor |
|---|---:|
| Decimales de los marcadores | 6 |
| Resolución decimal | 0,0864 s |
| Semiancho de redondeo | ±0,0432 s |
| Regla de compatibilidad | `abs(TIME_FITS - TIME_catalog) <= 0.5 × 10^-6 d` |

Los valores se leyeron directamente como cadenas del
`Flare_detections.csv` original. No se reutilizaron floats serializados por
pandas para decidir la asociación.

---

## 3. Asociación de marcadores

| Evento | Marcador | Tiempo catálogo | Fila FITS asociada | CADENCENO | TIME FITS | Offset (s) | Único en ±0,0432 s | Incluido literalmente en F0.7 |
|---|---|---:|---:|---:|---:|---:|---|---|
| published_qpp | start | 2505.134541 | 21400 | 5519580 | 2505.134540536650 | -0.040033 | Sí | No |
| published_qpp | peak | 2505.135235 | 21403 | 5519583 | 2505.135235051073 | +0.004413 | Sí | Sí |
| published_qpp | end | 2505.137782 | 21414 | 5519594 | 2505.137781603962 | -0.034218 | Sí | Sí |
| not_selected_qpp | start | 2535.256201 | 42133 | 5649693 | 2535.256200570454 | -0.037113 | Sí | No |
| not_selected_qpp | peak | 2535.256895 | 42136 | 5649696 | 2535.256895075590 | +0.006531 | Sí | Sí |
| not_selected_qpp | end | 2535.259442 | 42147 | 5649707 | 2535.259441594971 | -0.034994 | Sí | Sí |

El archivo `fase0_tarea09_timestamp_marker_audit.csv` contiene las 18 filas completas:
anterior, más cercana y posterior para cada evento y marcador.

---

## 4. Comparación de ventanas

### published_qpp

| Métrica | Límites literales F0.7 | Índices de cadencia |
|---|---:|---:|
| Índice inicial FITS | 21401 | 21400 |
| Índice final FITS | 21414 | 21414 |
| Número de muestras | 14 | 15 |
| Primera hora TBJD | 2505.134772041457 | 2505.134540536650 |
| Última hora TBJD | 2505.137781603962 | 2505.137781603962 |
| Cadencia mediana | 20.002015 s | 20.002015 s |
| Gap máximo | 20.002015 s | 20.002015 s |
| QUALITY no nulos | 0 | 0 |
| SAP finitos | 14 | 15 |
| PDCSAP finitos | 14 | 15 |

### not_selected_qpp

| Métrica | Límites literales F0.7 | Índices de cadencia |
|---|---:|---:|
| Índice inicial FITS | 42134 | 42133 |
| Índice final FITS | 42147 | 42147 |
| Número de muestras | 14 | 15 |
| Primera hora TBJD | 2535.256432072088 | 2535.256200570454 |
| Última hora TBJD | 2535.259441594971 | 2535.259441594971 |
| Cadencia mediana | 20.001761 s | 20.001751 s |
| Gap máximo | 20.001761 s | 20.001761 s |
| QUALITY no nulos | 1 | 1 |
| SAP finitos | 14 | 15 |
| PDCSAP finitos | 14 | 15 |

---

## 5. Criterio de aceptación

- Una única cadencia compatible con ±0,0432 s para cada inicio, pico y final.
- Orden `start_index <= peak_index <= end_index`.
- Pico dentro de la ventana inclusiva.
- Diferencias con F0.7 limitadas a las cadencias de borde justificadas por
  redondeo decimal.
- Ninguna consulta a resultados AFINO para escoger índices.

**Criterio global satisfecho:** Sí.

---

## 6. Carácter post-piloto

Esta reconstrucción se formula después de F0.8, pero no se ha seleccionado para mejorar sus BIC. Está motivada por una discrepancia objetiva entre la precisión decimal de los marcadores publicados y la primera cadencia incluida mediante límites numéricos literales.

---

## 7. Entradas congeladas

Se generaron ocho variantes declaradas con `window_variant=tau0_nearest_cadence_indices`.

Todas conservan TIME en TBJD, flujo sin normalizar y el índice original dentro de la ventana por filas. Las variantes quality_zero_only no renumeran índices.

| Archivo | Evento | Flujo | Política | N original | N usado | Sampling | QUALITY != 0 | Gap máximo (s) |
|---|---|---|---|---:|---:|---|---:|---:|
| `fase0_tarea09_published_qpp_sap_all.csv` | published_qpp | SAP_FLUX | finite_all | 15 | 15 | `regular` | 0 | 20.002015 |
| `fase0_tarea09_published_qpp_sap_q0.csv` | published_qpp | SAP_FLUX | quality_zero_only | 15 | 15 | `regular` | 0 | 20.002015 |
| `fase0_tarea09_published_qpp_pdcsap_all.csv` | published_qpp | PDCSAP_FLUX | finite_all | 15 | 15 | `regular` | 0 | 20.002015 |
| `fase0_tarea09_published_qpp_pdcsap_q0.csv` | published_qpp | PDCSAP_FLUX | quality_zero_only | 15 | 15 | `regular` | 0 | 20.002015 |
| `fase0_tarea09_notselected_sap_all.csv` | not_selected_qpp | SAP_FLUX | finite_all | 15 | 15 | `regular` | 1 | 20.001761 |
| `fase0_tarea09_notselected_sap_q0.csv` | not_selected_qpp | SAP_FLUX | quality_zero_only | 15 | 14 | `diagnostic_irregular_sampling` | 0 | 40.003503 |
| `fase0_tarea09_notselected_pdcsap_all.csv` | not_selected_qpp | PDCSAP_FLUX | finite_all | 15 | 15 | `regular` | 1 | 20.001761 |
| `fase0_tarea09_notselected_pdcsap_q0.csv` | not_selected_qpp | PDCSAP_FLUX | quality_zero_only | 15 | 14 | `diagnostic_irregular_sampling` | 0 | 40.003503 |

---

## 8. Hashes de los nuevos artefactos de datos

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea09_published_qpp_sap_all.csv` | `9549b87917198e1ab88a5018d62eb89ea90fa72c4bc986de4218d1a1bce996fd` |
| `fase0_tarea09_published_qpp_sap_q0.csv` | `9549b87917198e1ab88a5018d62eb89ea90fa72c4bc986de4218d1a1bce996fd` |
| `fase0_tarea09_published_qpp_pdcsap_all.csv` | `e55949806744c1bc2e5e85d9e09a2a26775abc862dcbc8f82e2f5e4dca52040f` |
| `fase0_tarea09_published_qpp_pdcsap_q0.csv` | `e55949806744c1bc2e5e85d9e09a2a26775abc862dcbc8f82e2f5e4dca52040f` |
| `fase0_tarea09_notselected_sap_all.csv` | `37aa5c2a866a303caeb48aaf51dacebe5757134ecaa56220599288fdfc4c3bab` |
| `fase0_tarea09_notselected_sap_q0.csv` | `9ca65fb1c134c7fe4d9c401e3d6361a798d544810377b4325275f4cb39c48475` |
| `fase0_tarea09_notselected_pdcsap_all.csv` | `08ab8a53a42ba3689d919038ae4e8f1b07df4e449b25a862ee6a51e42aa53e72` |
| `fase0_tarea09_notselected_pdcsap_q0.csv` | `5801c2687be7a8806323465f3ebde007e9b1fa53fbad9a0686f8903fe8577e98` |
| `fase0_tarea09_index_window_manifest.csv` | `ba303fa13dda064e6d18d06e9d7e75f03039717a02f78b0590ffdcb7ca396149` |
| `fase0_tarea09_timestamp_marker_audit.csv` | `4d4a72e995c5936b9f7608e7430ef3f26bc610013c43456edaf80e44b0fd02d0` |

El SHA-256 de este informe se imprime en la salida de consola después de
escribirlo; no se incluye dentro del propio archivo para evitar autorreferencia.

---

## 9. Erratum documental de F0.8

El valor `n_samples: null` de `summary_by_variant` en la auditoría F0.8 procede
de:

```python
"n_samples": specification.get("n_samples")
```

La lista estática `specification` no contenía ese campo. Los valores correctos
permanecen en las 240 filas del CSV de resultados y en la sección `inputs` del
JSON. La próxima ejecución debe obtener `n_samples` de la entrada cargada o de
las filas reales, no de la especificación estática.

---

## 10. Diagnóstico

La auditoría confirma que los seis marcadores publicados corresponden a
cadencias observadas concretas cuando se interpreta su precisión de seis
decimales. Para cada inicio, pico y final existe exactamente una cadencia dentro
de ±0,0432 s, y los índices asociados están ordenados. En los dos eventos, la cadencia vinculada al inicio es la inmediatamente anterior a la primera muestra conservada por F0.7. La muestra
de inicio afectada queda fuera del recorte literal cuando su TIME exacto es
ligeramente menor que el valor catalogado, aunque ambos se impriman igual a seis
decimales. Los dos finales coinciden con las últimas cadencias ya incluidas en F0.7.

La comparación de tamaños es: published_qpp: 14→15 muestras; not_selected_qpp: 14→15 muestras. Cada diferencia entre la ventana
literal y la reconstruida está limitada a una cadencia de borde asociada de
forma única a un marcador. Por ello puede explicarse mediante precisión decimal,
sin elegir índices usando resultados de AFINO ni probar ventanas alternativas.
Las variantes `finite_all` conservan SAP y PDCSAP finitos. Cualquier variante
`quality_zero_only` que retire una cadencia interna mantiene sus tiempos e
índices originales y se etiqueta según la regularidad realmente observada, no
como si la cuadrícula hubiera sido compactada.

El segundo conjunto queda congelado como
`tau0_nearest_cadence_indices`, sin reemplazar F0.7 ni F0.8. Su existencia no
invalida el piloto literal: lo conserva como sensibilidad a límites numéricos
publicados. Tampoco demuestra todavía qué ventana utilizaron los autores. Solo
establece que la asociación por índices es defendible y está determinada de
forma única por los seis marcadores. Una futura ejecución deberá procesar las
ocho nuevas variantes completas, sin cancelar combinaciones tras resultados
tempranos, sin adaptar bounds o cutoff y manteniendo separados los resultados
diagnósticos de muestreo irregular.

**Extensión:** 283 palabras.

---

## 11. Conclusión

La asociación por redondeo es defendible y determina de manera única un segundo conjunto de ocho variantes. F0.7 y F0.8 permanecen archivados como recorte y análisis literales.
