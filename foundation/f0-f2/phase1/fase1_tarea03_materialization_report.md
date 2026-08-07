# Fase 1 — Tarea 1.3

## Materialización y congelación del dataset sintético núcleo

**Estado:** `DATASET_FROZEN_BEFORE_AFINO`  
**Series persistidas:** 4.440  
**AFINO ejecutado:** no  
**BIC, selección y periodos ajustados calculados:** no

---

## 1. Procedencia y hashes

El script verificó los artefactos normativos antes de importar el generador:

| Artefacto | SHA-256 |
|---|---|
| `fase1_tarea01_core_benchmark_preregistration.json` | `dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401` |
| `fase1_tarea01_core_design_grid.csv` | `f3c4c77ef71b9c8f9218bcf5a773d8e31c9ffc858ea68a1216542970e43f0bad` |
| `fase1_tarea02_synthetic_generator.py` | `743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd` |
| `fase1_tarea02_noise_block_manifest.csv` | `898a47f697b3de765f2b73b4bc01181f031c485df5875b0a88e6216591e7883d` |
| `fase1_tarea02_generator_fixtures.csv` | `0cf7966f4447cd6188d39aa37e66d6818152440b560a6046cef7825a0dad5fbd` |
| `fase1_tarea02_generator_validation_audit.json` | `3e4d588110dbe535038dc0e85ec08a60e47de946d438c05b121b379ee0c02f11` |

| Script | SHA-256 |
|---|---|
| `fase1_tarea03_materialize_core_benchmark.py` | `e1ff19421ee6a0d9938efebf7691fda3428a10893c37b5323710e2191933816d` |

El entorno exigido y observado fue Python `3.13.5` y NumPy `2.3.5`.

---

## 2. Formato binario

Los flujos se guardaron concatenados en `<f8` y sus offsets en `<i8`. Los cuatro vectores temporales —N=15, 30, 60 y 120— se almacenaron una sola vez, también en `<f8`, con offsets `<i8`. Todos los archivos usan el formato NPY sin pickle.

| Archivo | Bytes | SHA-256 físico |
|---|---:|---|
| `fase1_tarea03_core_flux_values.npy` | 2.116.928 | `f5fdd48f2951a1e055355d76b8b82c931fceea8cbb0688ca0099fe329594e60d` |
| `fase1_tarea03_core_series_offsets.npy` | 35.656 | `9169e4253cee3fb75b52e6ef61995efcdb71514720ba39c311eb9a085e901d85` |
| `fase1_tarea03_core_time_values.npy` | 1.928 | `730e97faa7b9bbcf03ea9b8c897790fd500c36fadb8f7c47608d9614fbba8513` |
| `fase1_tarea03_core_time_offsets.npy` | 168 | `c58d96df35b66a33ec3ffe37347f745af78cfd3eaa4e77762230206513f4c233` |

---

## 3. Conteos

| Magnitud | Resultado |
|---|---:|
| Condiciones | 111 |
| Series nulas | 480 |
| Series positivas | 3960 |
| Series totales | 4440 |
| Bloques emparejados | 480 |
| Valores de flujo | 264,600 |
| Vectores temporales | 4 |
| Valores temporales | 225 |
| Contenidos de flujo distintos | 4440 |

Cada condición aparece exactamente 40 veces. La primera serie es `S000001`, correspondiente a `C001_NULL_N015_A0`, semilla 0; la última es `S004440`, correspondiente a `C111`, semilla 39.

---

## 4. Correspondencia bloque–condición–serie

La regeneración previa produjo `480/480 block hash sets matched`. Dentro de cada bloque, todas las series comparten los hashes de ruido y fase; existe exactamente un nulo y el número de positivos coincide con los periodos admitidos multiplicados por las tres amplitudes. No se produjo redraw, retirada ni sustitución.

---

## 5. Fixtures

Las 23 fixtures congeladas en F1.2 se localizaron en el orden materializado y sus hashes canónicos de flujo coincidieron:

```text
23/23 fixture flux hashes matched
```

---

## 6. Round-trip

Los cuatro arrays se cerraron y recargaron mediante `np.load(..., allow_pickle=False)`. Las 4.440 series se reconstruyeron desde los offsets, junto con su vector temporal referenciado. Resultado:

```text
4440/4440 persisted series round-trip exact
```

---

## 7. Hash lógico

| Payload canónico | SHA-256 |
|---|---|
| `canonical_flux_payload_sha256` | `f593637faabf57bdcd9c4bea66f161cbaace77ad09de682179d709b002167abe` |
| `series_offsets_canonical_sha256` | `b7ed6562c1d5a256309ca417744ed3f0520c79fb3d85b43a67383d9d4810817e` |
| `time_values_canonical_sha256` | `6809c6c9ecb0667c5eda35e62fccbd958dc5c619845f9da37e0713f5b1580537` |
| `time_offsets_canonical_sha256` | `28d9acdf22fdfaf6737337f20331e37a52710ec0d43c5b39251119b619a875a4` |

El manifiesto ordenado de series tiene SHA-256 físico `2020c849348c81235036443d3215395c602b80b00debe64fec692935dda778f4`. El manifiesto de tiempos tiene SHA-256 `ce7f2f465f7ee73c8de983a91a8415b1a9d75e3b65a5e94b553d42c94068a5e7`.

---

## 8. Incidencias

No hubo discrepancias de bloque, fallos de materialización, fixtures discordantes ni errores de round-trip. La dependencia bit a bit respecto de NumPy 2.3.5 se conserva como limitación documentada del dataset, no como fallo. El número de contenidos de flujo distintos se registra sin imponer unicidad.

---

## 9. Diagnóstico (313 palabras)

La materialización transforma el grid prerregistrado en un dataset binario cerrado sin introducir una nueva decisión científica. Antes de escribir las curvas definitivas se regeneraron los 480 bloques con NumPy 2.3.5 y se compararon, byte a byte mediante hashes canónicos, sus vectores de tiempo, envolventes, ruidos y fases con F1.2. Los 480 conjuntos coincidieron. Después se recorrieron las condiciones C001–C111 y, dentro de cada una, las semillas 0–39, asignando S000001–S004440 sin reordenación posterior. Los nulos conservaron vacíos los campos de periodo, fracción QPP y ciclos nominales.

Los 4.440 flujos se almacenaron como un único payload float64 little-endian, acompañado por offsets int64. Los cuatro tiempos posibles se persistieron por separado, de modo que la fase de AFINO deberá leerlos y no reconstruirlos. Cada serie quedó vinculada a su bloque emparejado mediante hashes de ruido y fase. En los 480 bloques apareció exactamente un nulo y el número previsto de positivos, determinado por los periodos admitidos y las tres amplitudes. No se redibujó, retiró ni sustituyó ninguna realización.

Las 23 fixtures de F1.2 coincidieron exactamente con sus flujos materializados. Tras guardar los cuatro archivos NPY, los arrays se liberaron, se recargaron con allow_pickle=False y se reconstruyeron las 4.440 series desde sus offsets. Todos los hashes de flujo y tiempo volvieron a coincidir. Se registran hashes físicos de los archivos y hashes lógicos de los payloads canónicos para distinguir cambios reales de datos de posibles diferencias futuras en las cabeceras NPY. El número observado de contenidos distintos se conserva como descripción y no como criterio de aprobación.

La limitación relevante es deliberada: el dataset queda ligado bit a bit a NumPy 2.3.5, PCG64 y la implementación validada en F1.2. Esta congelación elimina la regeneración cruzada entre entornos, pero no evalúa AFINO, BIC, periodos ajustados ni rendimiento. La siguiente fase debe consumir estos arrays exactamente como están.

---

## Conclusión

**DATASET_FROZEN_BEFORE_AFINO**
