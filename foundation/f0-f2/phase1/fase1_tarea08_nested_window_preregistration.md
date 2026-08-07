# Fase 1 — Tarea 1.8

## Prerregistro del benchmark de extensión temporal anidada

**benchmark_id:** `afino_nested_window_support_v1`  
**benchmark_version:** `1.0.0`  
**preregistration_status:** `FROZEN_BEFORE_SERIES_GENERATION`  
**Series generadas:** no  
**AFINO ejecutado:** no

## 1. Hipótesis y alcance

F1.7 observó que, en las ventanas `N=15` y `N=30`, las dos comparaciones BIC
fallaban simultáneamente y que el margen conjunto estaba limitado por la
comparación de M1 frente a M0. Este benchmark congela una prueba dirigida de la
hipótesis siguiente:

> Al añadir cadencias reales de la misma realización subyacente, el aumento de
> soporte espectral modificará principalmente la evidencia de M1 frente a M0 y
> puede producir cruces conjuntos de los dos umbrales BIC.

La dirección no se presupone. Una ventana más larga puede mejorar, empeorar o
dejar sin cambios los márgenes. El módulo describirá las trayectorias observadas
sin imponer un porcentaje mínimo de contrastes favorables y sin convertir la
hipótesis en criterio de aprobación.

Fuentes normativas verificadas:

```text
fase1_tarea07_short_window_diagnostic_audit.json
c565716438d3990119aea48ed85ac8018fa4772d0cb1c952f33e02971ab0c2da

fase1_tarea02_synthetic_generator.py
743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd

fase1_tarea01_core_benchmark_preregistration.json
dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401
```

El generador de F1.2 solo se ha verificado mediante hash. No se ha importado ni
ejecutado durante F1.8.

## 2. Realizaciones padre

La unidad independiente es `(red_noise_alpha, data_seed)`, con:

```text
red_noise_alpha = 0.0, 1.0, 2.0
data_seed = 0..39
parent_n_samples = 120
cadence = 20 s
```

En la futura generación se invocará exactamente:

```python
generate_paired_block(
    n_samples=120,
    alpha=red_noise_alpha,
    data_seed=data_seed,
    specification=frozen_f1_1_specification,
)
```

Del bloque se reutilizarán únicamente `noise`, `phase_rad`,
`noise_seed_metadata` y `phase_seed_metadata`. La envolvente calculada por el
generador para `N=120` no se utilizará.

La semilla del bloque continuará siendo:

```python
np.random.SeedSequence([20260802, 120, alpha_code, data_seed])
```

El ruido queda normalizado una sola vez en el padre `N=120`, mediante el
generador validado. Los prefijos hijos no se recentran, no se reescalan y no se
reestandarizan. Por ello, su media y varianza realizadas pueden diferir de las
del padre completo.

Existen 120 bloques independientes de ruido y fase. Cada bloque produce tres
padres de flujo —un nulo y dos positivos—, para un total de 360 padres antes de
extraer ventanas.

## 3. Señal física padre

El tiempo se construirá una sola vez:

```python
time_s = np.arange(120, dtype=np.float64) * 20.0
```

La envolvente fija usa:

```text
baseline_flux = 1.0
flare_peak_excess = 0.5
peak_index = 3
t_peak = 60.0 s
reference_duration = 280.0 s
rise_tau = 11.2 s
decay_tau = 84.0 s
```

\[
E(t)=
\begin{cases}
0.5\exp((t-60)/11.2), & t\le 60,\\
0.5\exp(-(t-60)/84), & t>60.
\end{cases}
\]

El padre nulo será:

\[
F_{\rm null}(t)=1+E(t)+\epsilon(t).
\]

Los padres positivos serán:

\[
F_{\rm QPP}(t)=1+E(t)+0.04E(t)
\sin\left(2\pi\frac{t-60}{P}+\phi\right)+\epsilon(t),
\]

con `P=50 s` o `P=80 s`. La misma realización de ruido y la misma fase se
comparten entre el nulo y ambos periodos. La envolvente, el término periódico y
el ruido se combinan primero en el padre completo; nunca se recalculan dentro
de una ventana hija.

## 4. Ventanas anidadas

Las seis ventanas son prefijos exactos:

| N | Duración |
|---:|---:|
| 15 | 280 s |
| 30 | 580 s |
| 45 | 880 s |
| 60 | 1.180 s |
| 90 | 1.780 s |
| 120 | 2.380 s |

La única operación admitida es:

```python
child = parent[:n_samples]
```

Debe verificarse byte a byte, sobre payload `float64`, que cada hijo coincide
con el prefijo correspondiente. No se permite reconstruir la señal, volver a
muestrear, cambiar la cadencia ni normalizar por separado.

Las ventanas de un mismo padre son medidas repetidas. No se contabilizarán como
seis realizaciones independientes.

## 5. Grid y conteos

El grid normativo contiene 54 condiciones:

```text
6 tamaños × 3 pendientes × 3 tipos = 54
```

Por cada `(N, alpha)` se incluyen un nulo, un positivo `P=50 s` y un positivo
`P=80 s`, todos con 40 semillas de datos.

| Componente | Conteo |
|---|---:|
| Condiciones nulas | 18 |
| Condiciones positivas | 36 |
| Series nulas | 720 |
| Series positivas | 1.440 |
| Series totales | 2.160 |
| Llamadas primarias futuras | 6.480 |
| Llamadas de estabilidad futuras | 1.458 |
| Llamadas futuras totales | 7.938 |

Las celdas `period_s` y `qpp_fraction` de los nulos permanecen vacías.

Artefacto normativo:

```text
fase1_tarea08_nested_window_design_grid.csv
7c1a1fb9724dfe195fec1337e4f0af906e3dd8f1c754ab0abc7f3bc2cc1e8dcd
```

## 6. Ejecución futura

La ejecución primaria usará `external_optimizer_seed=0`. Para `data_seed=0` de
cada condición se añadirán las semillas externas `1..9`. Cada serie y semilla
se evaluará con M0, M1 y M2 mediante el protocolo AFINO ya congelado:

```text
AFINO commit: 6aceac9518fc8056052807e666da9d0c8bebb010
package: 0.5
cutoff: 1/40 Hz
regla: ΔBIC0,1 > 10 y ΔBIC2,1 > 10
20 inicializaciones internas por llamada
```

No se permitirá parada adaptativa, retirada de realizaciones difíciles ni
ajuste posterior del protocolo.

## 7. Estimandos

Por condición se informarán:

```text
selection_rate
median_delta_bic_0_1
median_delta_bic_2_1
median_joint_margin
bic_winner_distribution
formal_m1_period_error
```

Las trayectorias positivas se emparejarán dentro de
`(alpha, period, data_seed)` en los pasos:

```text
15→30, 30→45, 45→60, 60→90, 90→120
```

Hay 240 trayectorias positivas y 1.200 transiciones adyacentes. En cada una se
registrarán cambios de ambos deltas, del margen conjunto, cruces de cada umbral,
cruces conjuntos y cambios del ganador formal de BIC.

El contraste direccional queda congelado como:

```python
support_hypothesis_contrast = (
    paired_change_delta_bic_0_1
    - paired_change_delta_bic_2_1
)
```

La hipótesis recibe apoyo descriptivo en una transición cuando este contraste
es positivo y aumenta el margen frente a M0. No se fija un porcentaje mínimo,
no se realizarán pruebas post hoc y este contraste no sustituye la regla doble
de selección.

## 8. Límites

Extender el prefijo añade principalmente cola del flare y ruido. Al mismo
tiempo cambian la normalización interna de AFINO, la ventana de Hann, las
frecuencias FFT y el número de bins. Por tanto, el benchmark identifica el
efecto total de ampliar una observación anidada; no aísla un efecto matemático
puro del número de bins.

La varianza realizada de los prefijos no queda fijada exactamente en `0,005`.
El módulo no estudia damping, gaps, muestreo irregular ni cambios de cadencia.
Sus resultados solo serán aplicables a este generador sintético, estos dos
periodos, esta amplitud y el protocolo congelado.

## 9. Versionado y cierre

La versión `1.0.0` será inmutable después de su aprobación. Cualquier cambio en
la señal padre, ventanas, cadencia, RNG, normalización, grid, semillas,
emparejamiento, protocolo AFINO o estimandos requerirá una versión nueva y
nuevos hashes.

```text
Condiciones: 54
Series nulas: 720
Series positivas: 1.440
Series totales: 2.160
Llamadas futuras: 7.938
Señal construida una vez a nivel del padre: sí
Prefijos exactos: sí
Reestandarización por N: no
Series generadas: no
AFINO ejecutado: no
```

El siguiente paso permitido será implementar y validar la generación anidada,
sin modificar este prerregistro.
