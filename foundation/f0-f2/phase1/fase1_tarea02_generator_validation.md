# Fase 1 — Tarea 1.2

## Implementación y validación unitaria del generador

**Conclusión:** `GENERATOR_VALIDATED`  
**benchmark_id:** `afino_core_stationary_rednoise_v1`  
**benchmark_version:** `1.0.0`  
**Prerregistro:** `FROZEN_BEFORE_SYNTHETIC_GENERATION`  
**AFINO ejecutado:** no  
**Benchmark completo materializado:** no

---

## 1. Entorno y hashes

| Elemento | Valor |
|---|---|
| Python | `3.13.5` |
| NumPy | `2.3.5` |
| Plataforma | `Linux-6.12.13-x86_64-with-glibc2.41` |
| Script del generador | `743005e580f20be331408d9165522932a289d256cef0efbe4c4f24fcb38c54bd` |
| Script de tests | `6d4092d3be4cc705d0547bc5233bb92013615fe4da578681bbcefe9a407a396b` |
| Prerregistro F1.1 | `dd80346172290e014d73f78240b3e31f135bcc7e4f075963e7e20d8456de3401` |
| Grid F1.1 | `f3c4c77ef71b9c8f9218bcf5a773d8e31c9ffc858ea68a1216542970e43f0bad` |
| Baseline F0.15 | `4c0bf97f875b9beb2bd2d619b26fa77b083fb946a05d3ee48c32896046690dc7` |
| Manifiesto de bloques | `898a47f697b3de765f2b73b4bc01181f031c485df5875b0a88e6216591e7883d` |
| Diagnóstico de pendientes | `4c0b854bb981c333b9f889e950c9337d3effa19b22412a67a557ce4352cfd747` |
| Fixtures | `0cf7966f4447cd6188d39aa37e66d6818152440b560a6046cef7825a0dad5fbd` |

Los arrays canónicos se serializan como `float64` little-endian, contiguos y en orden C antes de calcular SHA-256.

---

## 2. Arquitectura de la implementación

`fase1_tarea02_synthetic_generator.py` carga la configuración normativa, valida el grid y expone funciones separadas para construir tiempo y flare, generar un bloque emparejado, materializar el nulo y materializar positivos. Cada bloque contiene tiempo, envolvente, ruido, fase y metadatos de las dos `SeedSequence`. No utiliza `numpy.random` global. Los arrays compartidos se marcan como no escribibles para impedir mutaciones accidentales durante la materialización.

`fase1_tarea02_test_generator.py` contiene una implementación de referencia corta e independiente. El archivo de tests realiza el preflight, genera únicamente los 480 bloques en memoria, ejecuta las comprobaciones y escribe los tres CSV, la auditoría y este informe.

---

## 3. Resultado de los 480 bloques

| Métrica | Resultado |
|---|---:|
| Bloques intentados | 480 |
| Bloques válidos | 480 |
| `GENERATION_FAILURE` | 0 |
| Redraws | 0 |
| Media dentro de tolerancia | 480/480 |
| Desviación dentro de tolerancia | 480/480 |

Todos los invariantes temporales, de finitud y de monotonía de la envolvente forman parte del estado `OK` del manifiesto.

---

## 4. Referencia independiente

| Casos | Comparaciones exactas | Superadas | Resultado |
|---:|---:|---:|---|
| 5 | 64 | 64 | `True` |

Se utilizó `np.array_equal` para tiempo, envolvente, ruido y flujos, y comparación exacta float64 para la fase. La referencia crea directamente `SeedSequence`, `PCG64`, los draws normales, Nyquist, `irfft` y la fase; no llama a funciones internas del generador.

---

## 5. Determinismo frente al orden

| Órdenes | Bloques por orden | Diferencias |
|---|---:|---:|
| Normativo, inverso y aleatorio | 480 | 0 |

La semilla del orden aleatorio de test fue `734921` y no participa en la generación científica.

---

## 6. Diseño emparejado

Se verificaron 4440 asociaciones condición–semilla frente a 4440 previstas. No se persistieron las 4.440 curvas. Los hashes de ruido y fase se resuelven desde un único bloque `(N, alpha, data_seed)`. Los cinco tests de materialización confirmaron la fórmula del residuo, el escalado 1:2:4 y la independencia respecto a solicitar primero el nulo o el positivo.

---

## 7. Pendientes espectrales

| N | alpha | Bins positivos | Pendiente estimada | Esperada | Error absoluto | Orden | Tolerancia |
|---:|---:|---:|---:|---:|---:|---|---|
| 15 | 0.0 | 7 | 0.0097950080193126999 | -0 | 0.0097950080193126999 | True | True |
| 15 | 1.0 | 7 | -0.79609796466249105 | -1 | 0.20390203533750895 | True | True |
| 15 | 2.0 | 7 | -1.8200882490525934 | -2 | 0.17991175094740663 | True | True |
| 30 | 0.0 | 15 | -0.14696951518551507 | -0 | 0.14696951518551507 | True | True |
| 30 | 1.0 | 15 | -0.99727773661486341 | -1 | 0.0027222633851365918 | True | True |
| 30 | 2.0 | 15 | -2.0423527037371589 | -2 | 0.042352703737158937 | True | True |
| 60 | 0.0 | 30 | -0.022483645775005476 | -0 | 0.022483645775005476 | True | True |
| 60 | 1.0 | 30 | -0.93824051702514089 | -1 | 0.061759482974859115 | True | True |
| 60 | 2.0 | 30 | -1.9204855185672618 | -2 | 0.079514481432738204 | True | True |
| 120 | 0.0 | 60 | -0.024305957953237905 | -0 | 0.024305957953237905 | True | True |
| 120 | 1.0 | 60 | -1.0146164108588021 | -1 | 0.014616410858802054 | True | True |
| 120 | 2.0 | 60 | -1.973442256303767 | -2 | 0.026557743696232983 | True | True |

Resultado global: `True`. La pendiente se ajustó sobre el periodograma medio no normalizado de las cuarenta realizaciones, excluyendo frecuencia cero.

---

## 8. Fixtures congeladas

Se congelaron 23 filas: cinco nulos, trece positivos con `qpp_fraction=0.01` —uno por cada periodo admisible de los cinco bloques— y cinco positivos adicionales con `qpp_fraction=0.04` usando el menor periodo admisible de cada bloque. Cada fila conserva parámetros, metadatos de seeds y hashes de tiempo, flare, ruido, fase y flujo.

---

## 9. Incidencias

- No se observaron incidencias bloqueantes ni realizaciones inválidas.

---

## 10. Diagnóstico

La implementación se validó exclusivamente contra el prerregistro F1.1 y no contra resultados de AFINO. Se intentaron los 480 bloques independientes previstos, correspondientes a cuatro tamaños, tres pendientes y cuarenta semillas. Se obtuvieron 480 bloques válidos y 0 fallos. En cada bloque válido, tiempo, envolvente, ruido y fase fueron finitos; la media del ruido quedó dentro de ±1e-14 y su desviación muestral dentro de ±1e-14 de 0,005. No se sustituyó ni redibujó ninguna realización.

Los cinco casos de referencia coincidieron exactamente con una implementación literal independiente. La comparación incluyó tiempo, flare, ruido, fase, flujo nulo y todas las combinaciones positivas admisibles de esos bloques. La regeneración de los 480 bloques en orden inverso y en un orden aleatorio de test produjo los mismos hashes canónicos, por lo que el contenido no depende del orden de solicitud ni de un estado global de NumPy.

El emparejamiento se auditó sobre las 4.440 asociaciones condición–semilla sin persistir las curvas. Cada asociación de un mismo bloque reutiliza el hash del ruido y el hash float64 de la fase. En los cinco bloques de referencia, la resta positivo menos nulo reprodujo la fórmula periódica, y las fracciones 0,02 y 0,04 escalaron el residuo por factores dos y cuatro dentro de las tolerancias congeladas.

Las doce pendientes espectrales de conjunto cumplieron el error máximo de 0,35 y, para cada N, siguieron el orden alpha=0 > alpha=1 > alpha=2. Este resultado valida la familia generativa a nivel de conjunto, no la pendiente exacta de cada curva. Las fixtures fijan 23 salidas reconstruibles bajo NumPy 2.3.5. No se ejecutó AFINO ni se materializó el benchmark completo.

**Palabras del diagnóstico:** 280.

---

## 11. Cierre

```text
GENERATOR_VALIDATED
```

La implementación queda preparada para F1.3 sin ejecutar todavía AFINO ni persistir el conjunto completo de 4.440 series.
