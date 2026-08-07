# Fase 0 — Tarea 0.5

## Prueba sintética mínima de selección de modelos

**Estado:** completada  
**Fecha de ejecución:** 31 de julio de 2026  
**Commit AFINO-public:** `6aceac9518fc8056052807e666da9d0c8bebb010`  
**Versión del paquete:** `0.5`  
**Resultado estructural:** 60/60 llamadas registradas, sin excepciones

---

## 1. Objetivo

Comprobar funcionalmente si AFINO-public:

1. favorece M1 al introducir una QPP estacionaria fuerte y conocida;
2. no favorece M1 en una serie idéntica sin QPP;
3. recupera aproximadamente el periodo inyectado;
4. mantiene la clasificación al variar únicamente la semilla que controla
   las inicializaciones internas.

Esta actividad es una prueba funcional controlada. No es una simulación física
realista, una estimación de completitud ni una medida de falsos positivos.

---

## A. Entorno

| Elemento | Valor |
|---|---|
| Sistema | Windows 11, 64 bits |
| Python | `3.13.13` |
| Ejecutable | `.venv/Scripts/python.exe` |
| AFINO | `0.5`, instalación editable |
| Commit | `6aceac9518fc8056052807e666da9d0c8bebb010` |
| Script | `fase0_tarea05_synthetic_model_selection.py` |
| SHA-256 del script | `4fbe868786fd96bf3c81862931f1e661a402f8cad727287d9c2c865ef0c02fd1` |
| SHA-256 del CSV | `0110eb02602542bd611882256128c5b27cc0ef6e50e37c7e8aea4e39f9df1097` |
| Modificaciones versionadas | Ninguna |
| Estado no versionado | `afino.egg-info/`, generado en F0.4 |
| Duración interna | 29,975 s |
| Duración total medida por PowerShell | 32,047 s |

### Dependencias fijadas

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

## B. Datos sintéticos

### B.1. Muestreo

```python
cadence = 20.0
duration = 1800.0
injected_period = 80.0
data_seed = 20260731

times = np.arange(0.0, duration + cadence, cadence)
```

Se generaron 91 muestras, desde 0 hasta 1800 s inclusive.

### B.2. Perfil de fulguración

Con:

```text
t_peak = 300 s
amplitude = 0.8
rise_tau = 60 s
decay_tau = 450 s
```

se utilizó:

\[
F_{\rm flare}(t)=
\begin{cases}
0.8\,\exp[(t-300)/60], & t\leq300,\\
0.8\,\exp[-(t-300)/450], & t>300.
\end{cases}
\]

### B.3. Ruido y datasets

```python
rng = np.random.default_rng(20260731)
noise = rng.normal(0.0, 0.005, size=times.size)

null_flux = 1.0 + flare_excess + noise

qpp_signal = 0.03 * np.sin(
    2.0 * np.pi * (times - 300.0) / 80.0
)
qpp_flux = null_flux + qpp_signal
```

Los dos datasets comparten exactamente tiempos, perfil de flare y realización
de ruido. La única diferencia introducida es `qpp_signal`.

### B.4. Hashes de los datos

| Array | SHA-256 |
|---|---|
| `times` | `75abfb714484735038e62dcf5af5ad93562f5fef7e0eb798bf471f64727e8c02` |
| `noise` | `0bd7b61281c21f1a7f6181a6375a8c548159cfc0cd52aca07d77f9fc2bb99e00` |
| `flare_excess` | `c8616bf3f7d28d349191932a390c88baca0c22ce4b7cb0e16acbdf9785b25374` |
| `null_flux` | `2fd1781330d6190729e0f2a4e3235a328335889253c8e9c5014a4bfd26ee84c6` |
| `qpp_flux` | `485fc30e4974f835cd8eb65653351cfe2730ba38d57a0d804834afe2f4f61c07` |

---

## C. Procedimiento

### C.1. Modelos

| Identificador científico | Nombre aceptado por el código |
|---|---|
| M0 | `pow_const` |
| M1 | `pow_const_gauss` |
| M2 | `bpow_const` |

Cada dataset se preparó mediante `AfinoSeries` y `prep_series`. No se modificaron
bounds, modelos, BIC, número interno de inicializaciones ni
`low_frequency_cutoff`.

### C.2. Semillas

Se realizaron diez ejecuciones por dataset. Antes de **cada llamada individual**
a un modelo se fijó:

```python
np.random.seed(seed)
```

con `seed = 0, 1, ..., 9`. Así, los datos permanecieron idénticos y la semilla
no fue consumida acumulativamente por el orden M0–M1–M2.

### C.3. Regla de selección

\[
\Delta{\rm BIC}_{0,1}={\rm BIC}_{M0}-{\rm BIC}_{M1},
\]

\[
\Delta{\rm BIC}_{2,1}={\rm BIC}_{M2}-{\rm BIC}_{M1}.
\]

Se marcó `QPP_SELECTED=True` únicamente cuando ambas diferencias fueron
estrictamente superiores a 10.

### C.4. Recuperación del periodo

Para M1:

\[
P=\frac{1}{\exp(a_4)}=
\frac{1}{\exp(\mathrm{params}[4])}.
\]

---

## D. Tabla de decisiones

| Dataset | Ejecuciones válidas M0–M1–M2 | M1 seleccionada | Periodo mediano (s) | Rango del periodo (s) | Rango ΔBIC₀,₁ | Rango ΔBIC₂,₁ |
|---|---:|---:|---:|---:|---:|---:|
| Null | 10/10 | 0/10 | 51.435644* | 51.434985–73.408662* | -10.502606 a -9.072544 | -3.417833 a -1.987762 |
| QPP 80 s | 10/10 | 10/10 | 81.241062 | 81.240975–81.241124 | 112.744805 a 112.744805 | 69.116217 a 69.116261 |

\* El periodo formal del nulo se registra por completitud, pero no representa una
QPP detectada. Las semillas 3 y 7 encontraron una solución próxima a 73,41 s;
las restantes, una solución próxima a 51,44 s. Ninguna superó el criterio BIC.

### Recuperación del periodo positivo

- Periodo inyectado: **80,000 s**.
- Periodo mediano recuperado: **81.241062 s**.
- Error absoluto: **1.241062 s**.
- Error relativo: **1.551 %**.
- Amplitud total del rango entre semillas: **0.000148257 s**.

---

## E. Diagnósticos por modelo

| Dataset | Modelo | Llamadas | BIC mediano | rχ² mediano | Probabilidad mediana | Tiempo mediano (s) |
|---|---|---:|---:|---:|---:|---:|
| Null | M0 (`pow_const`) | 10 | -466.366528 | 0.490449 | 0.907463 | 0.239 |
| Null | M1 (`pow_const_gauss`) | 10 | -457.293984 | 0.496918 | 0.893227 | 0.524 |
| Null | M2 (`bpow_const`) | 10 | -459.281755 | 0.473358 | 0.911568 | 0.506 |
| QPP_80s | M0 (`pow_const`) | 10 | -309.848073 | 12.1808 | 8.10386e-23 | 0.310 |
| QPP_80s | M1 (`pow_const_gauss`) | 10 | -422.592878 | 0.51264 | 0.882576 | 0.625 |
| QPP_80s | M2 (`bpow_const`) | 10 | -353.476660 | 4.19552 | 6.06517e-06 | 0.734 |

Los valores de `rchi2` y `probability` se registran como salidas del código, pero
no se incorporan al criterio de selección de esta tarea.

### E.1. Warnings

| Dataset | Modelo | Filas con warnings | Warnings registrados | Tipos principales |
|---|---|---:|---:|---|
| Null | M0 | 0/10 | 0 | Ninguno |
| Null | M1 | 0/10 | 0 | Ninguno |
| Null | M2 | 6/10 | 65 | `overflow encountered in exp` × 50; `invalid value encountered in subtract` × 15 |
| QPP_80s | M0 | 0/10 | 0 | Ninguno |
| QPP_80s | M1 | 0/10 | 0 | Ninguno |
| QPP_80s | M2 | 8/10 | 94 | `overflow encountered in exp` × 66; `invalid value encountered in subtract` × 25; `divide by zero encountered in log` × 1; `divide by zero encountered in divide` × 1; `invalid value encountered in scalar subtract` × 1 |

Los warnings de M2 se produjeron durante evaluaciones intermedias del optimizador.
Las filas finales contienen parámetros y métricas finitas, pero el estado formal
de convergencia no es auditable porque `main_analysis` no conserva
`res.success` ni `res.message`.

### E.2. Soluciones en bounds

| Dataset | Modelo | Filas en algún bound | Bound observado |
|---|---|---:|---|
| Null | M0 | 0/10 | Ninguno |
| Null | M1 | 10/10 | `params[5]`, anchura del bump, límite inferior `0.05` |
| Null | M2 | 0/10 | Ninguno |
| QPP_80s | M0 | 10/10 | `params[2]`, ln del fondo constante, límite inferior `-20` |
| QPP_80s | M1 | 10/10 | `params[5]`, anchura del bump, límite inferior `0.05` |
| QPP_80s | M2 | 10/10 | `params[3]`, índice de alta frecuencia, límite superior `9` |

El bound de anchura de M1 es especialmente relevante: tanto en el nulo como en
el positivo, el ajuste escogió el bump más estrecho permitido. En el positivo
esto es compatible con la señal sinusoidal estacionaria y deliberadamente fácil,
pero impide interpretar esta prueba como validación de bumps QPP con anchura
física realista.

---

## F. Diagnóstico

AFINO-public supera esta prueba funcional mínima. Para el dataset positivo,
M1 fue seleccionado en las diez semillas: ΔBIC₀,₁ permaneció entre
112.744805 y 112.744805, y ΔBIC₂,₁ entre
69.116217 y 69.116261. Ambos márgenes están muy por
encima del umbral estricto de 10. Para el nulo, M1 no fue seleccionado en
ninguna semilla; las dos diferencias fueron siempre negativas, por lo que
M0 y M2 obtuvieron BIC menores que M1. La clasificación no cambió al variar
la semilla de inicialización.

El periodo del positivo se recuperó de forma estable: mediana
81.241062 s, intervalo
81.240975–81.241124 s. El sesgo respecto a los
80 s inyectados es de 1.241062 s (1.551 %),
pequeño para esta prueba deliberadamente fácil. En el nulo, el periodo
formal de M1 no tiene interpretación como detección. Además, cambió entre
dos soluciones aproximadas, alrededor de 51,44 s y 73,41 s, aunque la
decisión siguió siendo negativa. Esto muestra que la inicialización puede
alterar parámetros de un modelo no favorecido sin alterar necesariamente
la clasificación.

Las 60 llamadas devolvieron resultados finitos y no hubo excepciones. No
puede afirmarse, sin embargo, que todos los optimizadores convergieran:
`main_analysis` no expone ni comprueba `res.success`. M2 produjo numerosos
`RuntimeWarning` durante evaluaciones intermedias, principalmente overflow
en exponenciales y diferencias numéricas inválidas. También aparecieron
soluciones en bounds. En particular, la anchura de M1 quedó en su límite
inferior en los veinte ajustes. Para la QPP sinusoidal pura esto es
coherente con un pico espectral muy estrecho, pero limita la interpretación
como validación de QPP físicamente anchas o transitorias.

La tarea permite avanzar a simulaciones más realistas porque confirma la
ruta completa M0–M1–M2, el cálculo de BIC y la recuperación del periodo en
un caso controlado. No permite estimar sensibilidad, especificidad ni tasa
de falsos positivos. La siguiente etapa debe variar amplitud, periodo,
duración, ruido y evolución temporal, manteniendo predefinidos los
experimentos y auditando los warnings y la incidencia de bounds.

**Extensión del diagnóstico:** 328 palabras.

---

## G. Respuestas directas

| Pregunta | Respuesta |
|---|---|
| ¿Selecciona M1 para el caso positivo? | Sí, 10/10 semillas. |
| ¿Rechaza M1 para el nulo? | Sí, 10/10 semillas. |
| ¿Recupera aproximadamente 80 s? | Sí: mediana 81,241 s, error relativo 1,551 %. |
| ¿Alguna semilla cambia la clasificación? | No. |
| ¿Los tres modelos convergen en todas las ejecuciones? | Las 60 llamadas terminan, pero la convergencia formal no es auditable. |
| ¿Aparecen resultados en bounds? | Sí; 40 de las 60 filas tienen al menos un parámetro exactamente en un bound. |
| ¿Puede pasarse a simulaciones más realistas? | Sí, conservando como riesgos los bounds, warnings de M2 y ausencia de estados del optimizador. |

---

## H. Limitaciones

1. Una sola realización de ruido blanco.
2. Una QPP sinusoidal, estacionaria, fuerte y presente durante toda la serie.
3. Un único periodo y una única amplitud.
4. Sin ruido rojo ni evolución del periodo, amplitud o fase.
5. Sin variación de duración, cadencia o morfología del flare.
6. Sin auditoría formal de convergencia de SciPy.
7. Los bounds condicionan varios ajustes.
8. No permite calcular tasas de detección ni falsos positivos.

---

## I. Registro de actividad

- **Fecha:** 2026-07-31.
- **Actividad:** F0.5 — Prueba sintética mínima de selección de modelos.
- **Objetivo:** verificar la ruta completa M0–M1–M2 en un caso positivo y uno nulo.
- **Métodos:** dos datasets emparejados, diez semillas de optimización y tres
  modelos por semilla.
- **Intentos realizados:** 60.
- **Resultados válidos:** 60.
- **Excepciones:** 0.
- **Clasificación del nulo:** M1 no seleccionada en 10/10.
- **Clasificación del positivo:** M1 seleccionada en 10/10.
- **Periodo positivo:** 81,241 s de mediana frente a 80 s inyectados.
- **Estabilidad:** clasificación estable; parámetros del nulo no completamente
  estables.
- **Incidencias:** warnings numéricos en M2 y soluciones en bounds.
- **Código AFINO modificado:** no.
- **Estado:** completada.

## J. Resumen para mentor

AFINO-public supera el control funcional más sencillo propuesto: reconoce de
forma robusta una QPP estacionaria fuerte de 80 s frente a modelos de continuo,
no selecciona M1 en el nulo emparejado y recupera el periodo con un sesgo de
aproximadamente 1,55 %. La conclusión se mantiene en diez semillas. El resultado
es alentador, pero no constituye todavía validación científica: M1 utiliza la
anchura mínima permitida, M2 produce warnings numéricos y el código no expone el
estado de convergencia. El paso metodológico siguiente debe ser una matriz de
inyecciones predefinida, no un ajuste manual de amplitud para obtener el
comportamiento deseado.
