# Fase 1 — Tarea 1.10

## Materialización y congelación del dataset anidado

**Estado:** `NESTED_DATASET_FROZEN_BEFORE_AFINO`

Se materializaron exactamente **2,160 series** en el orden
normativo `NWS000001`–`NWS002160`, sin reordenarlas después de construir el
payload. Las 720 series nulas y las
1,440 positivas ocupan en conjunto
129,600 valores `float64`. Antes de escribirlos se
regeneraron mediante el generador congelado de F1.9 y coincidieron
120/120 bloques,
360/360 padres,
2160/2160 hijos y
6/6 tiempos.

Los cuatro arrays se escribieron sin pickle y se cerraron antes de recargarlos
con `np.load(..., allow_pickle=False)`. El ciclo completo de escritura y lectura
reprodujo exactamente 2160/2160 hashes de flujo y
6/6 hashes temporales. Los offsets comienzan en
cero, terminan en 129.600 y conservan la longitud declarada de cada serie. Los
seis tiempos persistidos suman 360 valores y permanecerán en segundos; el
futuro runner deberá leerlos directamente y no reconstruirlos.

Los padres no se duplicaron en un payload separado. Cada uno de los 360 padres
está representado por una única serie `N=120`. Usando exclusivamente los arrays
releídos, las 2,160/2160 comparaciones padre–hijo
fueron byte a byte exactas. También se conservaron las
1,800/1800 relaciones adyacentes: 600 nulas y
1.200 positivas. Por tanto, la estructura de medidas repetidas sobrevivió la
serialización.

Los hashes lógicos congelados son:

```text
canonical_flux_payload_sha256:
9847da04c1793247ab34b01c06b2e9d579715d3bf06c1ea0cb14ea9ebaab03f0

series_offsets_canonical_sha256:
a8f34927c914b8256334e3570ed31b8c5fbb8504b991db0de976105c0f5d3e06

time_values_canonical_sha256:
dfaa422bf7854de5f2a6e89a8db3f06ec9f3c0ccab7d60cd507b45325c3ea6cc

time_offsets_canonical_sha256:
7ab392ff65815e1dd36e8c48377f0c8969351b0e178210cd85f5711be77aa1a5

ordered_series_manifest_sha256:
cc9f44c710dade51e91fe0c2d30b193c621c7b9905764c6fe69fcf1c94c395a5
```

No se ejecutó ni interpretó AFINO; no se calcularon BIC, periodos ajustados ni
decisiones. No se eliminaron series, no se redibujaron padres y no se normalizó
ningún hijo. Los momentos variables del ruido de los prefijos continúan siendo una
propiedad intencionada del diseño, mientras que la unidad independiente permanece
el bloque `(alpha, data_seed)`. La unicidad de los 2.160 hashes de flujo se registra
como control de contenido y no se interpreta como independencia científica.

El manifiesto enlaza cada serie con su condición, bloque, padre `N=120`, vector
temporal, offsets y hashes canónicos. De este modo, cualquier futura ejecución
puede verificar los inputs antes de ajustar modelos y detenerse ante una sola
discrepancia. El dataset queda congelado antes de AFINO y preparado para construir
un plan y un runner que consuman exclusivamente estos arrays persistidos.

## Conclusión

`NESTED_DATASET_FROZEN_BEFORE_AFINO`
