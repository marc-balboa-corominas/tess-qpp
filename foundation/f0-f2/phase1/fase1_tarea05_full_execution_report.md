# Fase 1 — Tarea 1.5

## Ejecución reanudable del benchmark sintético núcleo

**Estado:** `FULL_BENCHMARK_EXECUTION_COMPLETE`  
**Runner:** `1.0.1`  
**AFINO commit:** `6aceac9518fc8056052807e666da9d0c8bebb010`  
**Plan:** `16317` trabajos  
**Pendientes:** `0`

## 1. Integridad y entorno

Los hashes físicos y lógicos de F1.3, el runner y el plan se verificaron antes
y después. AFINO permaneció en el commit y versión congelados, sin diferencias
tracked ni staged. Los archivos no versionados se registran en la auditoría.

## 2. Conteos de ejecución

| Concepto | Resultado |
|---|---:|
| Trabajos planificados | 16317 |
| Filas en checkpoint | 16317 |
| Filas exportadas | 16317 |
| Trabajos primarios | 13320 |
| Trabajos de estabilidad | 2997 |
| M0 | 5439 |
| M1 | 5439 |
| M2 | 5439 |

Estados retenidos:

```text
{"OK": 16317}
```

## 3. Reanudación e idempotencia

Invocaciones registradas: `10`.  
Primera invocación, filas preexistentes:
`0`.  
Total final confirmado:
`16317`.

No se importó el checkpoint ni los resultados del canary.

## 4. Decisiones estructurales

| Tipo | Filas |
|---|---:|
| Primarias | 4440 |
| Estabilidad | 999 |
| Total | 5439 |

Estados de decisión:

```text
{"VALID": 5439}
```

Las decisiones incompletas conservan `qpp_selected` vacío y la etiqueta
`unavailable_incomplete_numerical`.

## 5. Warnings, bounds y tiempo

```text
warning_calls_by_model:
{"M0": 0, "M1": 0, "M2": 2529}

warning_totals_by_model:
{"M0": 0, "M1": 0, "M2": 22352}

bound_hit_calls_by_model:
{"M0": 567, "M1": 3859, "M2": 2116}

total_runtime_seconds:
8798.912625100376
```

Estos conteos son controles operativos; no constituyen análisis científico.

## 6. Hashes de cierre

```text
checkpoint:
9751062964e3db79f116270c58461a859c75c570d28bfc988a72a1cb577a934b

results:
1ba98f4f0df406f36c17c75cf90d0773b09c3139eb2e11dc35d67ac42ac02775

decisions:
bf2b65aa42f40fa798910096ee62127556dc9cbe67445222df465b6a1352ab27

validator:
524ddd8ca09637f259cf12b9a2f285603afb2aaa97d98ff2ea191e8364f66a8e

environment:
5b416b49f0444a0df415b3b2d1ce13137c3a682a2695df8f2bd9033d9c16db63
```

## 7. Incidencias

No se registraron incidencias mecánicas.

## 8. Diagnóstico

La ejecución completa se realizó mediante el runner 1.0.1 y el plan congelado de 16.317 trabajos. El primer registro de invocación partió de cero filas y todas las reanudaciones conservaron una historia contigua de transacciones confirmadas. Al finalizar no quedó ningún trabajo pendiente. La validación comparó cada resultado del checkpoint y del CSV exportado con su fila normativa del plan, incluidos serie, condición, clase, semilla externa, modelo y hashes de flujo y tiempo. No aparecieron claves duplicadas ni discrepancias de metadatos o inputs. Los cuatro payloads binarios y sus hashes lógicos coincidieron antes y después, y el checkpoint canary permaneció separado e intacto. Los resultados con estado distinto de OK, si existen, se conservaron como resultados numéricos del benchmark y generaron decisiones INCOMPLETE_NUMERICAL; no se transformaron en no selecciones ni se redibujaron series. La tabla de decisiones contiene exactamente 4.440 tríos primarios y 999 de estabilidad. Esta tarea solo congela resultados brutos y resume integridad, estados, warnings, bounds y tiempo operativo. No calcula tasas por condición, efectos de factores, errores agregados de periodo, discordancia entre semillas ni conclusiones científicas sobre robustez. El repositorio AFINO conservó el commit predeclarado, sin cambios tracked o staged, y el runner, el plan y el dataset mantuvieron sus hashes normativos.

## 9. Conclusión

`FULL_BENCHMARK_EXECUTION_COMPLETE`
