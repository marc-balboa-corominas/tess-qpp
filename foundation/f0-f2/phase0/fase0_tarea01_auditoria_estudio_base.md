# Fase 0 — Tarea 0.1  
## Auditoría de reproducibilidad del estudio base

**Fecha de auditoría:** 2026-07-29  
**Fecha de revisión:** 2026-07-30  
**Estudio auditado:** *Stationary quasi-periodic pulsations in 20-second cadence TESS flares*  
**Texto metodológico auditado:** arXiv v1, 26 de junio de 2025.  
**Referencia bibliográfica final:** *Astronomy & Astrophysics*, volumen 700, A178, 2025.  
**Alcance:** artículo, repositorio público asociado y documentación oficial de MAST sobre productos TESS de 20 s.  
**No realizado:** programación del pipeline, descarga masiva de curvas de luz o consulta de fuentes externas adicionales.

---

## Ficha de actividad

* **Nombre de la actividad:** F0.1 — Auditoría de reproducibilidad del estudio base.
* **Objetivo científico:** reconstruir la cadena desde la selección de objetivos TESS hasta las conclusiones físicas y separar qué partes pueden reproducirse exactamente, parcialmente o no con los materiales públicos.
* **Pregunta concreta que debe responder:** ¿qué información pública permite reproducir la muestra, el detector de flares, AFINO y las conclusiones, y qué información falta?
* **Resultado o entregable esperado:** este documento Markdown con tabla de reproducibilidad, auditoría directa de ambos CSV, separación de capas de evidencia y diagnóstico final.
* **Duración disponible:** 2–4 horas.
* **Dependencias previas:** artículo publicado, repositorio público y documentación oficial de MAST.
* **Datos, código, artículos o herramientas disponibles:** artículo arXiv, `Flare_detections.csv`, `QPP_detections.csv` y documentación MAST.
* **Restricciones técnicas o metodológicas:** no programar el pipeline; no descargar masivamente curvas de luz; no completar vacíos mediante inferencias no documentadas.
* **Criterios para considerar la actividad terminada:** todas las filas respondidas, fuentes localizables, ausencias marcadas como `NO ESPECIFICADO`, CSV contados directamente, negativos y casos umbral evaluados, capas de evidencia separadas y al menos un bloqueo identificado.
* **Relación con el objetivo global del proyecto:** determina si el estudio base puede reproducirse antes de ejecutar AFINO o formular una contribución científica adicional.

---

## Fuentes consultadas

1. [Artículo en arXiv, versión HTML v1](https://arxiv.org/html/2506.22131v1), fechado el 26 de junio de 2025 y auditado como texto metodológico de referencia, especialmente §§2, 3.1, 3.4, 4.1, 4.2, 5 y “Data availability”. Referencia bibliográfica final: *Astronomy & Astrophysics*, 700, A178 (2025).
2. [Repositorio público asociado](https://github.com/aadishj19/QPPs-in-TESS-flares), archivos `Flare_detections.csv` y `QPP_detections.csv`.
3. [MAST — TESS Data Product Overview](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview), apartados de productos fotométricos, misión extendida y quality flags.

---

## Criterio de clasificación

* **Sí:** la especificación y los insumos públicos permiten repetir la operación sin decisiones sustantivas no documentadas.
* **Parcial:** puede construirse una implementación razonable o repetirse una parte, pero faltan decisiones capaces de cambiar el resultado.
* **No:** falta el insumo, código, configuración o resultado necesario.

Cuando el estudio no proporciona un dato, se indica literalmente `NO ESPECIFICADO`.

---


## Particularidades de los productos TESS de 20 s relevantes para la auditoría

Según la documentación oficial de MAST:

* los datos rápidos se distribuyen como archivos de píxeles `_fast-tp.fits` y curvas de luz `_fast-lc.fits`;
* los archivos de curva de luz incluyen SAP_FLUX, PDCSAP_FLUX, vectores de posición y quality flags;
* no se distribuyen archivos CBV independientes asociados a las curvas rápidas de 20 s;
* no se generan productos de Data Validation para los datos de 20 s.

Por tanto, conocer únicamente que se descargaron “datos de 20 s” no fija el producto, la serie de flujo ni la máscara de calidad usada. Esta ambigüedad afecta directamente a la reconstrucción del preprocesamiento y del detector de flares.

---

## 1. Tabla de reproducibilidad

| Elemento | Especificación exacta del artículo | Fuente exacta | ¿Reproducible públicamente? | Ambigüedad o información faltante |
|---|---|---|---|---|
| Población inicial de objetivos | Todos los objetos observados por TESS a cadencia de 20 s en los sectores 27–80; 66.527 objetos únicos analizados. | Artículo §2, párrafo que comienza “Since TESS cycle-3…” | Parcial | No se publica la lista de TIC, los nombres de archivos, la fecha de consulta ni el procedimiento exacto de deduplicación. |
| Sectores TESS utilizados | Sectores 27 a 80, inclusivos. | Artículo resumen, §2 y §5. | Sí | No se proporciona una tabla objeto–sector; un mismo TIC puede aparecer en varios sectores. |
| Producto TESS descargado | Datos TESS de 20 s descargados en masa mediante scripts cURL de MAST. Producto exacto: `NO ESPECIFICADO`. | Artículo §2; MAST “Target Pixel Files” y “Light Curve Files”. | Parcial | MAST distribuye `_fast-tp.fits` y `_fast-lc.fits`; el artículo no identifica cuál se descargó ni los nombres de producto. |
| Serie de flujo utilizada: SAP, PDCSAP u otra | `NO ESPECIFICADO`. El texto habla de “normalized flux” y de la curva original normalizada. | Artículo §§3.1–3.2; MAST “Light Curve Files”, SAP_FLUX y PDCSAP_FLUX. | No | La elección SAP/PDCSAP afecta tendencias, amplitudes, ruido y detecciones. |
| Tratamiento de quality flags | `NO ESPECIFICADO`. | Artículo: sin política declarada; MAST “Cadence Quality Flags”. | No | No se sabe qué bits fueron rechazados, conservados o corregidos, ni cómo se trataron valores NULL. |
| Preprocesamiento previo a ARIMA | Se usa una curva de flujo normalizada. Fórmula de normalización y tratamiento de huecos: `NO ESPECIFICADO`. | Artículo §3.1, Fig. 1 y nota al pie 3. | Parcial | No se especifican normalización, segmentación por sector, eliminación de NaN, manejo de gaps, outliers ni stitching. |
| Selección del modelo ARIMA | `auto_arima()` de `pmdarima`; búsqueda \(p\in[0,3]\), \(d\in[0,2]\), \(q\in[0,3]\); selección por AIC mínimo. | Artículo §3.1.1, Ecs. (1)–(2). | Parcial | Versión, argumentos completos, búsqueda stepwise/exhaustiva, estacionalidad, intercepto, pruebas de estacionariedad, solver y tolerancias: `NO ESPECIFICADO`. |
| Criterios iniciales de detección de flare | Residuales positivos por encima de \(3\sigma\); agrupación de puntos continuos o “near-continuous”; mínimo de ocho puntos consecutivos. | Artículo §3.1.2. | Parcial | Definición exacta de \(\sigma\), tolerancia de “near-continuous” y reglas de unión/separación de eventos: `NO ESPECIFICADO`. |
| Criterios morfológicos de aceptación | Aumento antes del pico y descenso después; desviación estándar de 50 puntos antes y después \(\leq 60\%\) de la amplitud; rechazo si \(0.5< t_\mathrm{rise}/t_\mathrm{decay}<2\); rechazo si duración \(>4\) h. | Artículo §3.1.2, Fig. 2 y desigualdad de simetría. | Parcial | No se publica código ni tratamiento de empates, ruido no monotónico, bordes de segmento o ventanas incompletas. |
| Definición de inicio, pico y final | Inicio: instante más temprano antes del pico donde comienza un ascenso monotónico. Final: cuando el flujo cae por debajo del half-maximum. Pico: `NO ESPECIFICADO` formalmente. | Artículo §3.1.2; Tabla 1. | Parcial | No se define si half-maximum se calcula sobre flujo absoluto o exceso sobre baseline; tampoco la regla exacta del pico en mesetas o múltiples máximos. |
| Número final de flares | 3.878 flares en 1.285 estrellas. | Artículo §3.4, Tabla 1 y §5; `Flare_detections.csv`. | Sí | El catálogo final puede contarse, pero no regenerarse exactamente sin el pipeline. |
| Criterio para considerar un flare analizable por AFINO | El artículo afirma que se analizaron los 3.878 flares. Criterios adicionales de elegibilidad, número mínimo de puntos o política ante fallos: `NO ESPECIFICADO`. | Artículo §4.2. | Parcial | No se informa si todos produjeron un ajuste válido en todas las extensiones ni cómo se gestionaron optimizaciones fallidas. |
| Ventana temporal analizada | Intervalo completo del flare desde inicio hasta final como un único segmento, no fases impulsiva y de decaimiento por separado. | Artículo §4.2, párrafo anterior a Tabla 2. | Sí | Para eventos extendidos, la tabla usa un final ampliado; debe distinguirse del final original. |
| Extensiones de la ventana | \(\tau=(t_\mathrm{end}-t_\mathrm{start})/2\); se prueban extensiones de \(1\tau\), \(2\tau\) y \(3\tau\) al final original. El CSV también contiene `Tau=0`. | Artículo §4.1, Ecs. (13)–(14); `QPP_detections.csv`. | Parcial | No se especifica el criterio de selección entre las cuatro ventanas ni si se corrigió la multiplicidad de pruebas. |
| Preprocesamiento de AFINO | Normalización de la serie por su media, aplicación de una ventana de Hann y cálculo del espectro de potencia de Fourier. | Artículo §4.1. | Parcial | Convención de FFT/PSD, normalización espectral, tratamiento de gaps y frecuencias descartadas: `NO ESPECIFICADO`. |
| Definición de los modelos M0, M1 y M2 | M0: ley de potencia simple; M1: ley de potencia más bump gaussiano en espacio log–log; M2: ley de potencia quebrada. | Artículo §4.1; Fig. 6. | Parcial | Funciones completas, parametrización, priors/bounds, likelihood y número exacto de parámetros: `NO ESPECIFICADO` en el artículo auditado. |
| Rango de periodos o frecuencias | Búsqueda de periodos cortos hasta 300 s; límite inferior efectivo de 40 s por Nyquist para cadencia de 20 s. | Artículo §4.1. | Parcial | El texto denomina \(f_p\) a una cantidad restringida en segundos, una inconsistencia dimensional. No se publican límites internos exactos del ajuste. |
| Umbral de decisión QPP | El modelo preferido debe superar a cada alternativa con \(\Delta\mathrm{BIC}=\mathrm{BIC}_j-\mathrm{BIC}_i>10\). Para QPP, el modelo relevante es M1. | Artículo §4.1, Eq. (12). | Parcial | Cuatro filas publicadas presentan `BIC_M2_M1<10`; la tabla y la regla declarada no son plenamente consistentes sin aclaración. |
| Uso del \(\chi^2\) reducido | Se utiliza para validar la consistencia entre modelo y datos; el CSV publica `rchi2_M0`, `rchi2_M1` y `rchi2_M2`. | Artículo §4.1; `QPP_detections.csv`. | Parcial | Umbral, regla de aceptación o papel frente al BIC: `NO ESPECIFICADO`. |
| Número final de QPP | 61 firmas QPP-like en 57 estrellas; periodos 42–193 s. | Artículo §4.2, Tabla 2 y §5; `QPP_detections.csv`. | Sí | Son detecciones del modelo, no ground truth físico. |
| Disponibilidad de positivos | 61 registros positivos con TIC, tiempos, periodo, errores, BIC resumido, \(\chi^2\), extensión y propiedades del flare. | `QPP_detections.csv`. | Sí | Solo se publican los positivos seleccionados. |
| Disponibilidad de negativos | `NO ESPECIFICADO` / no publicados como resultados AFINO auditables. | Repositorio: solo `Flare_detections.csv` y `QPP_detections.csv`. | No | Los 3.817 eventos restantes son no seleccionados como QPP por la ejecución reportada, pero no constituyen negativos auditables porque no se publican sus BIC, ajustes, extensiones temporales ni estados de ejecución. |
| Disponibilidad de casos cercanos al umbral | Sí entre los positivos: 22 registros tienen el menor de los dos \(\Delta\mathrm{BIC}\) a \(\pm2\) de 10; cuatro están por debajo de 10. Casos rechazados cercanos: `NO ESPECIFICADO`. | Cálculo directo sobre `QPP_detections.csv`. | Parcial | La definición “cercano” (\(\pm2\)) es una convención de esta auditoría, no del artículo. |
| Código del detector de flares | `NO ESPECIFICADO` / no publicado en el repositorio auditado. | Repositorio raíz. | No | El repositorio contiene únicamente los dos CSV. |
| Código/configuración exacta de AFINO | `NO ESPECIFICADO` / no publicado en el repositorio auditado. | Repositorio raíz; artículo §4.1. | No | Faltan implementación, configuración, parámetros, semillas, optimizador y logs. |
| Versiones de dependencias | Se nombran `pmdarima` y Lightkurve, pero versiones y entorno: `NO ESPECIFICADO`. | Artículo §§3.1.1 y 3.3; repositorio. | No | No hay `requirements.txt`, `environment.yml`, lockfile, contenedor ni release. |
| Licencia de código y tablas | `NO ESPECIFICADO`. No hay archivo de licencia visible. | Repositorio raíz. | No | No existe código publicado y los términos de reutilización de las tablas no están explicitados. |

---

## 2. Auditoría directa de los archivos públicos

### 2.1 Procedimiento de conteo

Los CSV se descargaron directamente de la rama `main` y se analizaron como CSV con cabecera.

| Archivo | Líneas totales | Filas de datos | Columnas | SHA-256 |
|---|---:|---:|---:|---|
| `Flare_detections.csv` | 3.879 | 3.878 | 9 | `866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4` |
| `QPP_detections.csv` | 62 | 61 | 22 | `4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e` |

### 2.2 `Flare_detections.csv`

**Columnas exactas:**

```text
TIC_ID
T_eff (K)
Start_time (TBJD)
End_time (TBJD)
Peak_time (TBJD)
Amplitude
Duration (days)
Flare_energy (erg)
ED (s)
```

| Comprobación | Resultado |
|---|---|
| Identificador que vincula el flare con TESS | `TIC_ID`. |
| ¿Contiene sector? | No. |
| ¿Contiene tiempos suficientes para localizar el evento? | Parcialmente sí: TIC y tiempos de inicio, fin y pico en TBJD permiten localizar el intervalo, pero faltan sector, product ID y filename. |
| ¿Contiene resultados de los tres modelos AFINO? | No. |
| ¿Contiene solo el modelo ganador? | No contiene resultados AFINO. |
| ¿Contiene eventos negativos? | No como negativos AFINO auditables. Los 3.817 eventos que no aparecen en `QPP_detections.csv` son no seleccionados por la ejecución reportada, pero la tabla no permite distinguir un resultado negativo válido, un fallo de optimización, un caso cercano al umbral o un evento no analizable. |
| ¿Contiene casos con \(\Delta\mathrm{BIC}\) cercano a 10? | No hay columnas BIC. |
| ¿Permite reconstruir qué extensión temporal ganó? | No. |

**Observación de trazabilidad:** las 61 filas QPP pueden vincularse al catálogo de flares por `TIC_ID` y `Start_Time`; el tiempo final publicado en la tabla QPP incluye la extensión, mientras que `Duration (days)` conserva aproximadamente la duración original.

**Terminología adoptada para los 3.817 eventos restantes:**

* **No selección publicada:** el evento no aparece entre los 61 seleccionados como QPP. Esto es lo único que puede afirmarse directamente.
* **Resultado negativo válido:** requeriría conocer que todos los modelos y extensiones se ejecutaron correctamente y no superaron el criterio. No está publicado.
* **Fallo de optimización:** no puede descartarse porque no se publican estados, excepciones ni logs.
* **Caso cercano al umbral:** no puede identificarse entre los no seleccionados porque sus BIC no están publicados.
* **Evento no analizable:** no puede distinguirse de las categorías anteriores porque no se publica una bandera de elegibilidad o ejecución.

### 2.3 `QPP_detections.csv`

**Columnas exactas:**

```text
TIC_ID
Start_Time (TBJD)
End_Time (TBJD)
Tau
Time_Extension (days)
Best_Model_BIC
Power_Law_Index
rchi2_M0
rchi2_M1
rchi2_M2
Period (s)
Err_P
Error_P (s)
BIC_M2_M1
BIC_M0_M1
T_eff (K)
Amplitude
Flare_energy (erg)
ED (s)
Duration (days)
Duration (mins)
Prot (d)
```

| Comprobación | Resultado |
|---|---|
| Identificador que vincula el flare con TESS | `TIC_ID`, junto con `Start_Time (TBJD)`. |
| ¿Contiene sector? | No. |
| ¿Contiene tiempos suficientes para redescargar/localizar el evento? | Parcialmente sí: TIC e intervalo TBJD permiten localizarlo; faltan sector y product ID. |
| ¿Contiene resultados de los tres modelos? | Parcial. Contiene \(\chi^2_\nu\) para M0, M1 y M2; publica `Best_Model_BIC` y las diferencias `BIC_M2_M1` y `BIC_M0_M1`, no tres columnas BIC independientes. |
| ¿Contiene solo el ganador? | Contiene solo detecciones QPP-like, por lo que el ganador implícito es M1; no existe una columna explícita con el nombre del modelo ganador. |
| ¿Contiene eventos negativos? | No. Las 61 filas son positivos publicados; la tabla no contiene resultados de los eventos no seleccionados. |
| ¿Contiene casos con \(\Delta\mathrm{BIC}\) cercano a 10? | Sí. Definiendo cercanía como \(|\min(\Delta\mathrm{BIC})-10|\leq2\), hay 22 positivos. |
| ¿Existe información para reconstruir qué extensión ganó? | Sí para los positivos: `Tau` toma 0, 1, 2 o 3 y `Time_Extension (days)` cuantifica la extensión. No se publica la comparación con extensiones perdedoras. |

**Distribución de la extensión ganadora publicada:**

| `Tau` | Número de positivos |
|---:|---:|
| 0 | 10 |
| 1 | 17 |
| 2 | 19 |
| 3 | 15 |

### 2.4 Control directo del umbral BIC

El artículo exige que M1 supere a **ambos** modelos con \(\Delta\mathrm{BIC}>10\). En el CSV:

* `BIC_M0_M1` tiene mínimo 10,147.
* `BIC_M2_M1` tiene mínimo 7,525.
* Cuatro registros tienen `BIC_M2_M1<10`.

| TIC_ID | Start_Time (TBJD) | Tau | BIC_M2_M1 | BIC_M0_M1 | Period (s) |
|---:|---:|---:|---:|---:|---:|
| 425933644 | 2097.667076 | 2 | 7.525482 | 12.270597 | 80.249348 |
| 167551757 | 2227.328669 | 1 | 7.711377 | 10.289503 | 64.617531 |
| 153977353 | 2442.896749 | 0 | 7.866370 | 10.235110 | 80.406699 |
| 348898049 | 2203.079285 | 0 | 8.868562 | 13.397946 | 89.467254 |

Esto no permite concluir por sí solo que las cuatro detecciones sean incorrectas. Sí demuestra una inconsistencia entre la interpretación literal de Eq. (12) y los valores publicados, o bien una definición de las columnas/criterio de selección que no está documentada completamente.


### 2.5 Conservación del procedimiento de conteo y hashes

Para no depender del historial del chat, esta revisión fija el siguiente script como procedimiento de referencia para regenerar los conteos publicados. No forma parte del pipeline científico: únicamente audita los dos CSV ya descargados.

**Ruta recomendada en el futuro repositorio:**

```text
scripts/audit/fase0_tarea01_auditar_csv.py
```

**Control de versiones:** sí. Debe guardarse junto con los hashes de entrada o con una referencia al commit del repositorio externo del que se descargaron las tablas.

```python
#!/usr/bin/env python3
"""Audita los CSV públicos del estudio base de QPP en TESS.

Calcula:
- líneas físicas, filas de datos y columnas;
- SHA-256 de cada archivo;
- distribución de Tau;
- positivos cercanos al umbral BIC;
- filas con BIC_M2_M1 < 10.

Uso:
    python scripts/audit/fase0_tarea01_auditar_csv.py data/raw/study_base
"""

from __future__ import annotations

import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path

BIC_THRESHOLD = 10.0
NEAR_THRESHOLD_MARGIN = 2.0
FILES = ("Flare_detections.csv", "QPP_detections.csv")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} no contiene cabecera CSV")
        return list(reader.fieldnames), list(reader)


def physical_line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in handle)


def as_float(row: dict[str, str], column: str) -> float:
    try:
        return float(row[column])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Valor inválido en columna {column!r}: {row}") from exc


def main() -> None:
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    loaded: dict[str, list[dict[str, str]]] = {}
    for filename in FILES:
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"No se encuentra {path}")

        fieldnames, rows = read_rows(path)
        loaded[filename] = rows
        print(f"Archivo: {filename}")
        print(f"  Líneas totales: {physical_line_count(path)}")
        print(f"  Filas de datos: {len(rows)}")
        print(f"  Columnas: {len(fieldnames)}")
        print(f"  SHA-256: {sha256_file(path)}")

    qpp_rows = loaded["QPP_detections.csv"]

    tau_distribution = Counter(
        int(as_float(row, "Tau")) for row in qpp_rows
    )
    print("Distribución de Tau:")
    for tau in sorted(tau_distribution):
        print(f"  Tau={tau}: {tau_distribution[tau]}")

    near_threshold = []
    bic_m2_m1_below_10 = []

    for row in qpp_rows:
        bic_m2_m1 = as_float(row, "BIC_M2_M1")
        bic_m0_m1 = as_float(row, "BIC_M0_M1")
        limiting_delta_bic = min(bic_m2_m1, bic_m0_m1)

        if abs(limiting_delta_bic - BIC_THRESHOLD) <= NEAR_THRESHOLD_MARGIN:
            near_threshold.append(row)
        if bic_m2_m1 < BIC_THRESHOLD:
            bic_m2_m1_below_10.append(row)

    print(
        "Casos próximos al umbral "
        f"(|min(ΔBIC)-{BIC_THRESHOLD}| <= {NEAR_THRESHOLD_MARGIN}): "
        f"{len(near_threshold)}"
    )
    print(f"Filas con BIC_M2_M1 < {BIC_THRESHOLD}: {len(bic_m2_m1_below_10)}")

    columns_to_report = (
        "TIC_ID",
        "Start_Time (TBJD)",
        "Tau",
        "BIC_M2_M1",
        "BIC_M0_M1",
        "Period (s)",
    )
    for row in bic_m2_m1_below_10:
        print("  " + ", ".join(f"{column}={row[column]}" for column in columns_to_report))


if __name__ == "__main__":
    main()
```

La convención de proximidad al umbral queda fijada como

\[
\left|\min\!\left(\Delta\mathrm{BIC}_{M2-M1},\Delta\mathrm{BIC}_{M0-M1}\right)-10\right|\leq 2.
\]

Cualquier cambio futuro de esta definición debe registrarse como una decisión metodológica nueva, no sobrescribirse silenciosamente.

---

## 3. Capas de evidencia

| Conclusión del artículo | Evidencia observacional usada | ¿Existe validación con ground truth sintético? | Interpretación física propuesta | Posible efecto de selección |
|---|---|---|---|---|
| Prevalencia aproximada de QPP | 61 firmas QPP-like entre 3.878 flares, aproximadamente 1,6%. | No se presenta una campaña de injection–recovery o ground truth sintético sobre esta muestra. La Fig. 2 usa un flare simulado como ilustración, no como validación completa. | Existencia de QPP estacionarias en una fracción de flares estelares. | Muestra GI no representativa; detector de flares conservador; mínimo de 160 s; corte de 4 h; AFINO conservador, estacionario y monoperiódico; resultados completos de los eventos no seleccionados no publicados. |
| Periodos entre aproximadamente 42 y 193 s | Periodos estimados para las 61 detecciones M1 publicadas. | No. | Posibles oscilaciones MHD u oscilatory reconnection; potencial uso sismológico. | Límite de Nyquist de 40 s, búsqueda limitada a 300 s, sesgo hacia señales estacionarias y con varios ciclos en la ventana. |
| Predominio de periodos cortos | Mediana 60,8 s y mayoría de detecciones por debajo de 80 s. | No. | Las QPP ópticas estelares pueden incluir una población de periodos subminuto o de pocos minutos. | El intervalo de búsqueda, la cadencia, el número de ciclos y la respuesta conservadora de AFINO favorecen periodos cortos frente a QPP largas o rápidamente amortiguadas. |
| Relación periodo–duración | En el conjunto completo no hay correlación Pearson; después de inspección visual y K-means se selecciona una rama con correlación positiva y regresión log–log; se repite para \(P>60\) s. | No. | Posible scaling físico común entre duración del flare y escala temporal de la QPP. | Selección post hoc de una rama, elección de \(K\), agrupación de clusters, corte a 60 s, ventana de análisis dependiente de la duración y errores de periodo cercanos al Nyquist. |
| Analogía entre QPP solares y estelares | Comparación de la pendiente estelar publicada y relaciones periodo–duración descritas en estudios solares citados por el artículo. | No en este estudio. | Procesos o leyes de escala análogos en flares solares y estelares. | Instrumentos, bandas, cadencias, muestras y métodos de detección diferentes; la comparación se apoya en una rama seleccionada, no en toda la muestra. |

### Distinción obligatoria

* **Ground truth sintético:** una señal conocida se inyecta y se evalúa recuperación, falsos positivos y sesgo paramétrico. No se publica esta validación para el pipeline completo del estudio.
* **Evidencia observacional:** M1 es favorecido estadísticamente en una curva real según los resultados publicados.
* **Interpretación física:** la periodicidad se atribuye tentativamente a procesos del plasma, ondas MHD o reconexión oscilatoria.

Una selección estadística de M1 no identifica por sí misma el mecanismo físico ni demuestra que la señal sea astrofísica.

---

## 4. Diagnóstico final

La muestra inicial puede reconstruirse **solo parcialmente**. El artículo define la selección como todos los objetos observados a 20 s en los sectores 27–80 y fija 66.527 objetos únicos, pero no publica la lista de TIC, los productos descargados ni la regla de deduplicación. MAST conserva los datos originales, por lo que puede obtenerse una muestra equivalente, pero no demostrar todavía que sea idéntica fila por fila.

El detector de fulguraciones no puede reconstruirse exactamente. Se publican `auto_arima`, los rangos de \(p,d,q\), el criterio AIC, el umbral de \(3\sigma\), el mínimo de ocho puntos y varios filtros morfológicos. Faltan el código, los parámetros restantes, la definición de puntos “casi continuos”, la normalización, el tratamiento de huecos y la selección SAP/PDCSAP y de quality flags. Estas decisiones pueden cambiar los residuos y el catálogo final.

AFINO puede reproducirse conceptualmente, no como ejecución exacta. Se especifican la normalización por la media, la ventana de Hann, tres modelos, \(\Delta\mathrm{BIC}>10\), el intervalo aproximado 40–300 s y las extensiones \(0\)–\(3\tau\). No se publican las funciones y límites completos, optimizador, inicialización, versiones ni política de selección de la extensión. Además, cuatro positivos tienen `BIC_M2_M1 < 10`, incompatible con una lectura literal de la ecuación (12) si esa columna representa \(\mathrm{BIC}_{M2}-\mathrm{BIC}_{M1}\).

Disponemos de 61 positivos y sus métricas resumidas. Los 3.817 eventos restantes son no seleccionados como QPP por la ejecución reportada, pero no constituyen negativos auditables: faltan sus BIC, ajustes, extensiones y estados de ejecución. No puede distinguirse entre resultado negativo válido, fallo de optimización, caso cercano al umbral o evento no analizable. Hay positivos próximos al umbral, pero no se publican rechazados próximos. El mayor bloqueo es la ausencia del pipeline ejecutable y de resultados completos para todos los eventos.

La relación periodo–duración es la primera conclusión física más adecuada para auditar porque la tabla contiene ambas variables. Sin embargo, su procedimiento tampoco es exactamente reproducible: faltan el espacio lineal o logarítmico de K-means, el escalado, el criterio para \(K=4\), la inicialización, la semilla, la pertenencia a clusters y la configuración completa de la regresión bayesiana. La identificación visual de una rama, la agrupación de clusters y la repetición con \(K=2\) tras excluir \(P<60\) s son decisiones potencialmente post hoc. Reconstruir el catálogo, repetir estadísticos y comprobar los 61 casos sería reproducción. Las inyecciones sintéticas, pruebas de sensibilidad, métodos alternativos y publicación de resultados completos podrían constituir investigación posterior, sin afirmar todavía novedad.

---

## 5. Resultado para el registro de actividad

### Registro de actividad

* **Fecha:** 2026-07-29
* **Actividad:** F0.1 — Auditoría de reproducibilidad del estudio base.
* **Objetivo:** reconstruir la cadena metodológica y clasificar su reproducibilidad pública.
* **Trabajo realizado:** lectura dirigida del artículo, revisión del repositorio, revisión de documentación MAST y auditoría directa de ambos CSV.
* **Métodos utilizados:** extracción de especificaciones, conteo directo de filas/columnas, verificación de nombres de campos, enlace TIC–tiempos, análisis de extensiones y comprobación de diferencias BIC.
* **Datos o archivos empleados:** `Flare_detections.csv`, `QPP_detections.csv`, artículo arXiv y documentación MAST.
* **Parámetros y configuraciones:** cercanía al umbral definida para esta auditoría como \(|\min(\Delta\mathrm{BIC})-10|\leq2\).
* **Resultados obtenidos:** 3.878 flares, 61 positivos QPP y 3.817 eventos no seleccionados cuyo estado no permite clasificarlos como negativos auditables; 22 positivos cercanos al umbral y cuatro filas con `BIC_M2_M1<10`.
* **Comprobaciones realizadas:** conteo de 3.879 y 62 líneas incluyendo cabecera; 9 y 22 columnas; hashes SHA-256; distribución `Tau`; consistencia aproximada entre duración original y extensión.
* **Errores o dificultades:** el repositorio no contiene código, entorno, release ni licencia; la semántica exacta de los BIC y la regla de extensión no están completamente documentadas.
* **Decisiones tomadas y justificación:** clasificar como “Parcial” cualquier componente que exija decisiones no publicadas capaces de cambiar las detecciones.
* **Limitaciones:** no se ejecutó el pipeline ni se descargaron curvas de luz; no se auditaron referencias externas a las tres fuentes autorizadas.
* **Preguntas abiertas:** elección SAP/PDCSAP; quality mask; parámetros completos de `auto_arima`; criterio de extensión; explicación de cuatro \(\Delta\mathrm{BIC}<10\); resultados completos y estados de ejecución de los 3.817 eventos no seleccionados. No están especificados el espacio exacto usado en K-means —lineal o logarítmico—, el escalado de variables, el criterio que determinó \(K=4\), la inicialización, la semilla, la pertenencia de cada evento a los clusters, ni los priors y configuración completa de la regresión bayesiana. El artículo indica que primero se identificó visualmente una rama, después se aplicó K-means con \(K=4\), se agruparon dos pares de clusters y se ajustó únicamente una de las ramas. También repitió el proceso con \(K=2\) tras excluir periodos inferiores a 60 segundos. Es una conclusión potencialmente sensible a decisiones post hoc.
* **Archivos creados o modificados:** `fase0_tarea01_auditoria_estudio_base.md`, que incorpora el script de auditoría destinado a guardarse posteriormente como `scripts/audit/fase0_tarea01_auditar_csv.py`.
* **Estado de la actividad:** completada con bloqueos documentados.
* **Siguiente acción recomendada:** revisión fila por fila del documento y, después, solicitud estructurada a los autores o diseño de una reproducción parcial claramente versionada.
