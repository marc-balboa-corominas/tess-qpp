# Fase 1 — Tarea 1.1

## Prerregistro del benchmark sintético núcleo

**benchmark_id:** `afino_core_stationary_rednoise_v1`  
**benchmark_version:** `1.0.0`  
**preregistration_status:** `FROZEN_BEFORE_SYNTHETIC_GENERATION`  
**Baseline enlazado:** `afino_public_tess_reproduction_v1`  
**Baseline SHA-256 verificado:** `4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7`  
**Curvas sintéticas generadas:** no  
**AFINO ejecutado:** no

---

## 1. Pregunta del módulo

Este módulo medirá con ground truth sintético conocido la frecuencia con la que
el baseline selecciona M1 en dos situaciones: una serie formada únicamente por
baseline, flare asimétrico y ruido gaussiano con pendiente espectral conocida,
y la misma serie con una QPP sinusoidal de frecuencia estacionaria. En los
positivos, la amplitud de la sinusoidal está modulada por la envolvente del
flare, pero no se añade amortiguamiento independiente ni deriva de periodo.

Los resultados describirán el comportamiento del algoritmo bajo este generador.
No serán sensibilidad, especificidad ni tasa de falsos positivos
observacionales.

---

## 2. Alcance y exclusiones

El grid estudia longitud de ventana, ciclos observados, amplitud QPP, pendiente
del ruido rojo y variabilidad por semilla externa del optimizador. Quedan fuera
de la versión 1.0.0: amortiguamiento adicional, deriva de periodo, flares
multipico, gaps, muestreo irregular, heteroscedasticidad, outliers, errores
fotométricos independientes y detrending alternativo.

Esos factores deberán incorporarse como módulos posteriores. Sus resultados no
podrán utilizarse para modificar retrospectivamente este grid.

---

## 3. Generador congelado

La cadencia es 20 s y el tiempo se define como:

```python
time = np.arange(N, dtype=float) * 20.0
duration_s = (N - 1) * 20.0
```

El flare tiene baseline unitario, exceso máximo 0,5, pico en
`round(0.20*(N-1))`, tiempo de subida `0.04*duration_s` y tiempo de caída
`0.30*duration_s`. Antes del pico crece exponencialmente y después decae
exponencialmente.

El nulo es:

```text
F_null(t) = 1 + E(t) + epsilon_alpha(t)
```

El positivo es:

```text
F_QPP(t) = 1 + E(t)
           + qpp_fraction * E(t)
             * sin(2*pi*(t-t_peak)/period_s + phi)
           + epsilon_alpha(t)
```

Las fracciones QPP son 0,01, 0,02 y 0,04. Con un pico de flare de 0,5, la
amplitud máxima posible de la componente es aproximadamente 0,005, 0,010 y
0,020.

| N | Duración (s) | Periodos admitidos |
|---:|---:|---|
| 15 | 280 | 50 s, 80 s |
| 30 | 580 | 50 s, 80 s, 140 s |
| 60 | 1.180 | 50 s, 80 s, 140 s |
| 120 | 2.380 | 50 s, 80 s, 140 s |

Solo se admite una combinación cuando `duration_s/period_s >= 3`.

---

## 4. Ruido, RNG y diseño emparejado

El ruido se sintetizará en Fourier con potencia proporcional a
`f**(-alpha)`, para `alpha = 0, 1, 2`, y se normalizará a media cero y desviación
muestral 0,005. El componente DC se fuerza a cero. Para N par, el coeficiente de
Nyquist se sustituye por una realización normal puramente real.

La especificación fija `SeedSequence`, el generador `PCG64` y el orden exacto
de draws. Para cada bloque `(N, alpha, data_seed)`:

```python
seed_sequence = np.random.SeedSequence(
    [20260802, N, alpha_code, data_seed]
)
noise_seed, phase_seed = seed_sequence.spawn(2)

rng_noise = np.random.Generator(np.random.PCG64(noise_seed))
rng_phase = np.random.Generator(np.random.PCG64(phase_seed))
phi = rng_phase.uniform(0.0, 2.0 * np.pi)
```

La misma realización de ruido y la misma fase se reutilizarán en el nulo, todos
los periodos admisibles y las tres amplitudes. La unidad de replicación
independiente es el bloque `(N, alpha, data_seed)`. Las series derivadas de un
mismo bloque son medidas repetidas; cualquier contraste entre condiciones debe
calcularse de forma emparejada antes de agregarse.

Una realización no finita no se reemplazará por otra semilla.

---

## 5. Grid y conteos completos

El CSV normativo contiene 111 condiciones:

| Tipo | Condiciones | Semillas por condición | Series |
|---|---:|---:|---:|
| `NULL_FLARE_RED_NOISE` | 12 | 40 | 480 |
| `STATIONARY_QPP_PRESENT` | 99 | 40 | 3.960 |
| **Total** | **111** | **40** | **4.440** |

Las condiciones nulas tienen `period_s`, `qpp_fraction` y `minimum_cycles`
vacíos. No se emplean ceros ficticios.

Para el análisis principal se usará `external_optimizer_seed=0`:

```text
4.440 series × 3 modelos = 13.320 llamadas
```

En `data_seed=0` de cada condición se añadirán las semillas externas 1–9:

```text
111 condiciones × 9 semillas adicionales × 3 modelos = 2.997 llamadas
```

Total futuro congelado:

```text
16.317 llamadas individuales de modelo
```

Cada llamada conservará las 20 inicializaciones internas del código público.

---

## 6. Estimandos primarios y diagnósticos

Por condición se informarán conjuntamente:

```text
valid_run_rate = decisiones primarias válidas / 40
selection_rate = selecciones / decisiones primarias válidas
```

Los fallos no se imputarán como no selecciones. Si no existe ninguna decisión
válida, `selection_rate` quedará indefinida.

En nulos, `selection_rate` se denominará
`synthetic_false_selection_rate`. En positivos se denominará
`synthetic_detection_rate`.

Para los positivos se separarán:

* Error de periodo en ejecuciones seleccionadas.
* Error del centro formal de M1 en todas las ejecuciones válidas.

Un centro M1 no seleccionado llevará la etiqueta
`formal_m1_center_not_selected` y no se llamará periodo recuperado. Se
congelan como resúmenes la mediana del error firmado, la mediana del error
absoluto y el percentil 90 del error absoluto.

En la auditoría de estabilidad, la discordancia será la proporción de pares de
semillas válidas con decisiones distintas:

```text
2*n_selected*n_not_selected / (n_valid*(n_valid-1))
```

También se registrarán el rango BIC de M2, el flag
`M2_BIC_range > 0.001`, tasas de bounds y warnings por modelo y tasa de fallo
numérico.

---

## 7. Riesgos del generador

1. Las series cortas pueden representar pobremente la pendiente espectral
   nominal y ofrecer pocos bins a AFINO.
2. La estandarización fija la potencia total del ruido en cada realización y
   elimina variabilidad natural de amplitud entre semillas.
3. `alpha=2` puede concentrar gran parte de la potencia en los primeros bins.
4. Al escalar subida y caída con la duración, N modifica simultáneamente la
   ventana y las escalas temporales absolutas del flare.
5. La frecuencia QPP es estacionaria, pero su amplitud varía con la envolvente.
6. El emparejamiento induce dependencia deliberada entre amplitudes, periodos y
   el nulo.
7. La reproducción bit a bit dependerá de conservar PCG64, el orden de draws y
   el entorno NumPy que se registrará en F1.2.

Estos riesgos son características a auditar, no razones para retirar
realizaciones.

---

## 8. Regla de versionado

La versión 1.0.0 quedará inmutable tras su aprobación. Cualquier cambio en
fórmulas, grid, admisión por ciclos, RNG, orden de draws, semillas,
emparejamiento, ground truth, denominadores, estimandos, protocolo AFINO o
umbrales diagnósticos requerirá una nueva versión y nuevos hashes. No se
sobrescribirá este prerregistro.

Una corrección puramente tipográfica deberá publicarse como erratum separado y
demostrar que no cambia generación, ejecución ni interpretación.

---

## 9. Comprobación de cierre

```text
Baseline verificado: sí
Condiciones: 111
Nulos: 480
Positivos: 3.960
Series totales: 4.440
Llamadas primarias futuras: 13.320
Llamadas adicionales de estabilidad: 2.997
Llamadas futuras totales: 16.317
Curvas generadas: no
AFINO ejecutado: no
```

El siguiente paso permitido es **F1.2 — Implementación y validación unitaria del
generador sintético**, todavía sin ejecutar el benchmark completo.
