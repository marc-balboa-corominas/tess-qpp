# Fase 0 — Tarea 0.11

## Selección y congelación de una cohorte pequeña de validación

**Estado:** completada  
**Detecciones QPP nuevas:** 4  
**Eventos no seleccionados como QPP:** 4  
**FITS descargados:** no  
**AFINO ejecutado:** no  
**Inspección visual utilizada:** no

---

## 1. Catálogos y calibración excluida

| Archivo | SHA-256 |
|---|---|
| `QPP_detections.csv` | `4f9d6c07fc722917fa432989b2d7c20b9b8da7cef4227a44187b55b6ddcfbe8e` |
| `Flare_detections.csv` | `866c7ebf0d2d3a6f024b55bd112e7d91491518dfd18a57b26a3f999c5d66faa4` |

El caso de calibración quedó excluido antes de ordenar candidatas:

```text
TIC: 67378184
start_tbjd: 2505.134541
role: calibration_event
```

El conjunto elegible contiene **7** eventos después de exigir
`Tau == 0`, ambas diferencias BIC estrictamente superiores a 10, periodo entre
40 y 300 s, exclusión del caso de calibración y exclusión completa de claves
TIC/inicio duplicadas.

---

## 2. Regla completa de selección

1. `P1 — highest_margin`: mayor `delta_min`; desempate por TIC e inicio
   ascendentes.
2. `P2 — near_threshold`: menor `delta_min` estrictamente superior a 10 entre
   las restantes; mismos desempates.
3. `P3 — shortest_period`: menor periodo entre las restantes; mismos
   desempates.
4. `P4 — longest_period`: mayor periodo entre las restantes; mismos
   desempates.

Para cada positivo se excluyeron todos los eventos presentes en
`QPP_detections.csv`. Se escogió primero un evento no utilizado del mismo TIC,
ordenado por diferencia absoluta de duración, diferencia absoluta de amplitud
e inicio. Si no existía, se aplicó globalmente duración, amplitud, TIC e inicio.

---

## 3. Cuatro positivos congelados

| Pareja | Criterio | TIC | Inicio TBJD | Periodo (s) | ΔBIC₀,₁ | ΔBIC₂,₁ | Δmin |
|---|---|---:|---:|---:|---:|---:|---:|
| P1 | `highest_margin` | 24518895 | 2198.799707 | 56.05823638 | 17.55796487 | 19.98756342 | 17.55796487 |
| P2 | `near_threshold` | 220433364 | 2166.070869 | 73.20971864 | 10.54301500 | 12.71921134 | 10.54301500 |
| P3 | `shortest_period` | 225953237 | 2345.223856 | 44.03128221 | 11.61905655 | 14.45167103 | 11.61905655 |
| P4 | `longest_period` | 160619243 | 2662.677869 | 60.05392234 | 13.50380923 | 17.70634440 | 13.50380923 |

---

## 4. Cuatro emparejamientos

| Pareja | Positivo TIC/inicio | Evento emparejado TIC/inicio | Método | Δ duración (d) | Δ amplitud |
|---|---|---|---|---:|---:|
| P1 | 24518895 / 2198.799707 | 24518895 / 2180.577182 | `same_tic_duration_match` | 0.001620572 | 0.265542156 |
| P2 | 220433364 / 2166.070869 | 220433364 / 2361.784182 | `same_tic_duration_match` | 0.006019113 | 0.079261227 |
| P3 | 225953237 / 2345.223856 | 225953237 / 2349.891231 | `same_tic_duration_match` | 0.000694497 | 0.181675311 |
| P4 | 160619243 / 2662.677869 | 160619243 / 2753.995580 | `same_tic_duration_match` | 0.000463094 | 0.068518781 |

---

## 5. Cobertura conseguida

| Métrica | Resultado |
|---|---:|
| Periodo mínimo | 44.03128221 s |
| Periodo máximo | 73.20971864 s |
| Δmin mínimo | 10.54301500 |
| Δmin máximo | 17.55796487 |
| TIC distintos entre positivos | 4 |
| TIC distintos en la cohorte completa | 4 |
| Matches del mismo TIC | 4/4 |
| Matches globales | 0/4 |

---

## 6. Diagnóstico

La cohorte contiene cuatro detecciones QPP nuevas y cuatro eventos no
seleccionados como QPP, fijados sin inspeccionar curvas ni ejecutar AFINO. La
selección cubre deliberadamente cuatro regímenes: el mayor margen BIC, el caso
más próximo al umbral doble, el periodo más corto y el periodo más largo entre
las filas elegibles restantes. El rango resultante de periodos es
44.031–73.210 s y el de Δmin es
10.543–17.558; por tanto, la muestra incluye tanto
un caso fuerte como una detección marginal y extremos temporales dentro del
dominio congelado de 40–300 s.

4 de los cuatro eventos de comparación proceden del mismo TIC
que su positivo. En esos casos se priorizaron, por este orden, duración,
amplitud e inicio temporal. Cuando no existió un candidato del mismo TIC sin
reutilizar, el emparejamiento global aplicó duración, amplitud, TIC e inicio.
Ningún evento de comparación se empleó dos veces. La cohorte reúne
4 TIC distintos entre los positivos y 4 al
considerar los ocho eventos.

La dependencia práctica más evidente para la reconstrucción posterior será la
disponibilidad de productos TESS que cubran cada ventana y la asociación única
de los marcadores redondeados con cadencias FITS. Esas condiciones no se han
comprobado todavía porque esta tarea prohíbe consultar MAST o descargar datos.
La selección queda, no obstante, completamente reproducible a partir de los
dos catálogos congelados, sus hashes y las reglas de ordenación. No se usaron
resultados previos de AFINO, morfología visual ni expectativas sobre qué caso
será más fácil de reproducir.

**Extensión:** 252 palabras.

---

## 7. Congelación

| Artefacto | SHA-256 |
|---|---|
| `fase0_tarea11_validation_cohort.csv` | `b48cdc09d37b2ea4c4faec430903f81b0f7b9e4f4b026510175881a2c766fb36` |
| `fase0_tarea11_select_validation_cohort.py` | `2a0e03f02207e949a8cc81be2e307d40b7d715e490147e668e6abb9a37652dd1` |

Los campos QPP de los eventos no seleccionados se mantienen vacíos. No se
consultaron curvas, MAST, FITS ni resultados de AFINO para resolver ninguna
decisión.
