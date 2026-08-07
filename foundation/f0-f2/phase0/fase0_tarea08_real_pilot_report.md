# Fase 0 — Tarea 0.8

## Ejecución piloto de AFINO-public sobre las ocho entradas congeladas

**Estado:** completada  
**Conclusión:** `PARTIAL_REPRODUCTION`  
**Fecha de ejecución:** 1 de agosto de 2026  
**Llamadas intentadas:** 240  
**Llamadas válidas:** 240  
**Excepciones:** 0  
**Tuning posterior:** no

---

## 1. Alcance

Esta actividad ejecuta M0, M1 y M2 sobre las ocho variantes predeclaradas de
F0.7. Es una reproducción piloto de dos eventos concretos. No estima
sensibilidad, especificidad, prevalencia ni tasa de falsos positivos.

---

## A. Entorno y protocolo

| Elemento | Valor |
|---|---|
| Commit AFINO-public | `6aceac9518fc8056052807e666da9d0c8bebb010` |
| AFINO | `0.5` |
| Python | `3.13.13` |
| NumPy | `2.5.1` |
| SciPy | `1.18.0` |
| Script | `fase0_tarea08_run_real_pilot.py` |
| SHA-256 del script | `bd43be5b76e61bb870795d52237c8598cc8f79d5c9df6006be44e52fe690c4c8` |
| SHA-256 del manifiesto F0.7 | `38b9a47929fcde55ef94e197270c7782906f44080b0aead00b09dccded1e7c5d` |
| SHA-256 del entorno | `011f8ed9d7bd0f339792b2914142e94c4d30dcd4ed76d0cf96ace83fb34c079f` |
| SHA-256 de resultados | `3e03b66459d4e01f6e4acf3daa4971428c2f8586735916f77d2169a22743f06b` |
| Código AFINO modificado | No |
| Archivos congelados modificados | No |
| Cambios Git versionados | Ninguno |
| Artefacto no versionado | `afino.egg-info/` |
| Duración interna | `91.502720 s` |
| Duración medida por PowerShell | `95.788922 s` |

### Transformación temporal

La única transformación externa fue, en memoria:

```python
time_seconds = (time_tbjd - time_tbjd[0]) * 86400.0
```

No se aplicaron normalización externa, detrending, suavizado, interpolación,
eliminación del perfil de flare ni extensión de ventana. `prep_series` realizó
su preprocesamiento interno habitual.

### Dominio espectral congelado

```python
low_frequency_cutoff = 1.0 / 40.0  # 0.025 Hz
```

Los bounds de M1 fueron:

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

M0 y M2 conservaron sus bounds públicos.

### Dependencias congeladas

```text
-e git+https://github.com/aringlis/afino_release_version.git@6aceac9518fc8056052807e666da9d0c8bebb010#egg=afino
astropy==8.0.1
astropy-iers-data==0.2026.7.27.0.56.29
colorama==0.4.6
contourpy==1.3.3
cycler==0.12.1
fonttools==4.63.0
iniconfig==2.3.0
kiwisolver==1.5.0
matplotlib==3.11.1
numpy==2.5.1
packaging==26.2
pillow==12.3.0
pluggy==1.6.0
pyerfa==2.0.1.5
Pygments==2.20.0
pyparsing==3.3.2
pytest==9.1.1
python-dateutil==2.9.0.post0
PyYAML==6.0.3
scipy==1.18.0
setuptools==83.0.0
six==1.17.0
wheel==0.47.0
```

---

## B. Resumen por variante

El periodo mostrado es el centro formal de M1 incluso cuando M1 no fue
seleccionado. No debe interpretarse por sí solo como una detección.

| Variante | Sampling | Llamadas válidas | M1 seleccionada | Periodo mediano (s) | Rango periodo (s) | Rango ΔBIC₀,₁ | Rango ΔBIC₂,₁ | Bounds / warnings |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Publicado · PDCSAP · all | `regular` | 30/30 | 0/10 | 70.504035 | 70.503591–70.504100 | 4.785800 a 4.785800 | 9.652918 a 9.652918 | 14 filas en bound; 10 filas / 37 avisos |
| Publicado · SAP · all | `regular` | 30/30 | 0/10 | 129.173619 | 117.209100–147.905230 | -4.496011 a -3.969861 | -1.330257 a -0.805111 | 11 filas en bound; 5 filas / 11 avisos |
| Publicado · PDCSAP · q0 | `regular` | 30/30 | 0/10 | 70.504035 | 70.503591–70.504100 | 4.785800 a 4.785800 | 9.652918 a 9.652918 | 14 filas en bound; 10 filas / 37 avisos |
| Publicado · SAP · q0 | `regular` | 30/30 | 0/10 | 129.173619 | 117.209100–147.905230 | -4.496011 a -3.969861 | -1.330257 a -0.805111 | 11 filas en bound; 5 filas / 11 avisos |
| No seleccionado · PDCSAP · all | `regular` | 30/30 | 0/10 | 65.774439 | 64.895523–204.752590 | -5.350250 a -5.307356 | -1.786726 a -1.723837 | 12 filas en bound; 3 filas / 17 avisos |
| No seleccionado · SAP · all | `regular` | 30/30 | 0/10 | 50.238676 | 50.087707–50.250796 | -3.565927 a -3.565926 | -0.010200 a -0.010168 | 22 filas en bound; 3 filas / 14 avisos |
| No seleccionado · PDCSAP · q0 | `diagnostic_irregular_sampling` | 30/30 | 0/10 | 71.507193 | 66.138564–71.507467 | -5.101599 a -5.060220 | -1.627292 a -1.560914 | 11 filas en bound; 2 filas / 19 avisos |
| No seleccionado · SAP · q0 | `diagnostic_irregular_sampling` | 30/30 | 0/10 | 50.432373 | 49.955357–50.505141 | -3.629308 a -3.629307 | -0.050539 a -0.047928 | 20 filas en bound; 6 filas / 32 avisos |

Todas las variantes conservaron seis frecuencias positivas después del cutoff.
Las series regulares tienen un `dt` efectivo cercano a 20,002 s. Las dos
variantes diagnósticas irregulares conservan un gap de 40,004 s y AFINO les
asigna un `dt` efectivo de 21,669 s.

---

## C. Comparación con el resultado publicado

Referencia publicada:

- periodo: **68,52768338 s**;
- ΔBIC₀,₁: **17,01318061**;
- ΔBIC₂,₁: **14,57959220**.

| Variante positiva | ¿Reproduce selección? | Periodo mediano | Diferencia con 68,528 s | ΔBIC₀,₁ mediano frente a publicado | ΔBIC₂,₁ mediano frente a publicado |
|---|---|---:|---:|---:|---:|
| Publicado · PDCSAP · all | No, 0/10 | 70.504035 s | 1.976352 s (2.884 %) | 4.785800 frente a 17.013181 (-12.227381) | 9.652918 frente a 14.579592 (-4.926674) |
| Publicado · SAP · all | No, 0/10 | 129.173619 s | 60.645935 s (88.498 %) | -3.969861 frente a 17.013181 (-20.983042) | -0.909514 frente a 14.579592 (-15.489106) |
| Publicado · PDCSAP · q0 | No, 0/10 | 70.504035 s | 1.976352 s (2.884 %) | 4.785800 frente a 17.013181 (-12.227381) | 9.652918 frente a 14.579592 (-4.926674) |
| Publicado · SAP · q0 | No, 0/10 | 129.173619 s | 60.645935 s (88.498 %) | -3.969861 frente a 17.013181 (-20.983042) | -0.909514 frente a 14.579592 (-15.489106) |

La variante primaria recupera un periodo próximo, pero no reproduce la
selección porque ninguno de sus dos márgenes BIC supera estrictamente 10.

---

## D. Comparación de decisiones

### ¿SAP y PDCSAP producen la misma clasificación?

Sí: ninguna variante positiva selecciona M1. No obstante, los resultados
numéricos difieren intensamente. PDCSAP sitúa el centro formal cerca de 70,5 s,
mientras que SAP lo sitúa alrededor de 129,2 s y produce diferencias BIC
negativas.

### ¿La política de calidad altera la clasificación?

No. En el positivo, `all` y `q0` son inputs idénticos y sus resultados coinciden
exactamente. En el evento no seleccionado, retirar `QUALITY=64` tampoco cambia
la decisión, pero altera el muestreo, el `dt` efectivo, los periodos formales y
los BIC; esas variantes son únicamente diagnósticas.

### ¿El positivo se reproduce en alguna variante?

No en términos de selección: **0/40 decisiones positivas** seleccionan M1.
PDCSAP sí recupera un centro formal próximo al periodo publicado.

### ¿El evento no seleccionado permanece sin seleccionar?

Sí: **0/40 decisiones** seleccionan M1.

### ¿Alguna semilla cambia la decisión?

No. Las 80 decisiones variante–semilla son `False`.

### ¿Se cumplen los invariantes de inputs idénticos?

Sí:

- SAP `all` frente a SAP `q0`: 30/30 comparaciones exactas.
- PDCSAP `all` frente a PDCSAP `q0`: 30/30 comparaciones exactas.

Se compararon BIC, parámetros, periodo, likelihood, `rchi2`, probabilidad y
decisión.

### ¿Qué resultados son únicamente diagnósticos?

- `notselected_pdcsap_q0`
- `notselected_sap_q0`

Ambos están etiquetados como `diagnostic_irregular_sampling` y
`diagnostic_only`.

### ¿Aparecen bounds o warnings?

Sí.

| Modelo | Llamadas | Filas en bound | Filas con warnings | Warnings totales |
|---|---:|---:|---:|---:|
| M0 | 80 | 22 | 0 | 0 |
| M1 | 80 | 15 | 0 | 0 |
| M2 | 80 | 78 | 44 | 178 |

Tipos de warning:

- `RuntimeWarning: overflow encountered in exp`: 155
- `RuntimeWarning: invalid value encountered in subtract`: 20
- `RuntimeWarning: overflow encountered in multiply`: 3

Los warnings aparecen exclusivamente en M2. Ninguna llamada terminó con error,
pero `main_analysis` no permite comprobar formalmente `res.success`.

No se registró ningún hit del parámetro central de M1 (`params[4]`) en los
límites de 40 o 300 s. Los bounds observados afectan a otros parámetros de M0,
M1 y, sobre todo, M2.

---

## E. Diagnóstico

La ejecución completa no reproduce la decisión QPP publicada, pero sí recupera
parte de la señal metodológica esperada; por ello la categoría final es
PARTIAL_REPRODUCTION. Las 240 llamadas terminaron sin excepciones y ninguna
semilla seleccionó M1 en ninguna variante. En el positivo primario,
PDCSAP_FLUX con `finite_all`, el centro formal de M1 es muy estable:
70,504035 s de mediana, solo 1,976352 s o 2,884 % por encima de los
68,527683 s publicados. Sin embargo, M1 no supera el criterio congelado:
ΔBIC₀,₁ es aproximadamente 4,786 y ΔBIC₂,₁ aproximadamente 9,653, frente al
requisito estricto de que ambos sean mayores que 10. El segundo margen queda
cerca del umbral, pero el primero no; no debe describirse como selección
reproducida.

SAP y PDCSAP producen la misma clasificación, pero no resultados
intercambiables. En SAP, el periodo formal del positivo se desplaza a una
mediana de 129,174 s y ambas diferencias BIC son negativas. El evento no
seleccionado permanece sin seleccionar en sus cuarenta decisiones
variante–semilla, lo que concuerda con su estado catalogado, aunque los
periodos de un M1 no favorecido no deben interpretarse como detecciones.

Las semillas no cambian ninguna clasificación. Los invariantes de las parejas
idénticas se cumplen exactamente en las 60 comparaciones modelo–semilla, lo
que valida el reinicio del estado aleatorio y la ausencia de mutación entre
llamadas. Las dos variantes `quality_zero_only` del evento no seleccionado son
solo diagnósticas: contienen 13 muestras, un gap de 40,004 s y AFINO les asigna
un `dt` efectivo de 21,669 s. Sus BIC no son comparables a los regulares como
si únicamente se hubiera retirado un valor de flujo.

No hay un bloqueo numérico, pero la inferencia es frágil. Solo quedan seis bins
de frecuencia, 115 de 240 ajustes alcanzan al menos un bound y M2 concentra
los 178 warnings registrados. Además, la convergencia formal continúa sin ser
auditable. El piloto demuestra que el flujo y el tratamiento del muestreo
influyen fuertemente, pero no autoriza tuning posterior ni conclusiones sobre
rendimiento poblacional.

**Extensión:** 336 palabras.

---

## F. Conclusión categórica

### `PARTIAL_REPRODUCTION`

Se adopta esta categoría porque:

1. la selección QPP publicada no se reproduce en ninguna variante;
2. la variante primaria recupera un centro formal cercano al periodo publicado;
3. el evento no seleccionado permanece sin seleccionar;
4. los resultados son estables frente a las semillas;
5. no existe un bloqueo de ejecución, pero sí limitaciones numéricas y
   estructurales importantes.

No se adopta `REPRODUCTION_SIGNAL_FOUND`, porque el criterio BIC congelado no se
cumple. Tampoco se adopta `NUMERICAL_BLOCK`, porque las 240 llamadas devolvieron
resultados finitos. `NO_REPRODUCTION_WITH_FROZEN_PROTOCOL` sería demasiado
fuerte porque parte de la información temporal y el comportamiento del evento
de comparación sí se recuperan.

---

## G. Incidencias y limitaciones

1. Solo hay seis bins de frecuencia por ajuste.
2. Las ventanas contienen únicamente 13–14 muestras.
3. M2 alcanza bounds en 78 de sus 80 llamadas.
4. Se registraron 178 warnings en 44 llamadas, todos en M2.
5. La convergencia formal no puede auditarse.
6. Las dos series irregulares no son candidatos científicos válidos para una
   FFT uniforme.
7. El periodo de un M1 no seleccionado no constituye una detección.
8. El resumen por variante del JSON de auditoría contiene `n_samples: null`
   por una omisión de serialización; las 240 filas del CSV y la sección
   `inputs` del propio JSON registran correctamente 13 o 14 muestras. Este
   defecto documental no cambia cálculos ni decisiones.
9. El warning de checksum heredado del FAST-LC del sector 44 permanece abierto.
10. La adaptación exacta de Joshi et al. sigue sin estar disponible.

---

## H. Hashes de evidencia

| Archivo | SHA-256 |
|---|---|
| `fase0_tarea08_real_pilot_results.csv` | `3e03b66459d4e01f6e4acf3daa4971428c2f8586735916f77d2169a22743f06b` |
| `fase0_tarea08_execution_audit.json` | `16fa96a7e1ace531a2f4bcb4e8904dd4fb5a7350ac4a5d5ec1f11146d620695e` |
| `fase0_tarea08_execution_log.txt` | `d10452e0af753ed477cb181680ba24160953687322403d67da63edce42e363cc` |
| `fase0_tarea08_environment.txt` | `011f8ed9d7bd0f339792b2914142e94c4d30dcd4ed76d0cf96ace83fb34c079f` |
| `fase0_tarea08_console_output.txt` | `ee537ecf5dca96ea81a372da293c5de118c7c5ecd97b51b5fdb0c22b7e5f2c02` |
| `fase0_tarea08_run_real_pilot.py` | `bd43be5b76e61bb870795d52237c8598cc8f79d5c9df6006be44e52fe690c4c8` |

---

## I. Registro de actividad

- Ocho variantes ejecutadas sin omisiones.
- Diez semillas por variante y modelo.
- Tres modelos por decisión.
- 240 llamadas intentadas y válidas.
- 80 decisiones variante–semilla.
- 0 selecciones M1.
- 0 excepciones.
- 60/60 invariantes exactos superados.
- 115/240 filas con al menos un parámetro en bound.
- 44/240 filas con warnings; 178 warnings totales.
- Sin tuning posterior.
- Estado: completada como `PARTIAL_REPRODUCTION`.

## J. Resumen para mentor

El piloto no reproduce la selección QPP del catálogo bajo el protocolo
congelado. La variante primaria PDCSAP recupera un centro formal de 70,504 s,
próximo a los 68,528 s publicados, pero sus márgenes BIC son 4,786 y 9,653, por
debajo del requisito doble de 10. SAP produce una solución muy distinta. El
evento no seleccionado permanece sin seleccionar y ninguna semilla cambia las
decisiones. Los controles de inputs idénticos se cumplen exactamente. Los
resultados deben interpretarse con cautela por el reducido número de bins, la
alta incidencia de bounds y los warnings de M2.
