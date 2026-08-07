# Fase 0 — Tarea 0.8

## Erratum interpretativo

**Estado de F0.8:** ejecución aprobada  
**Naturaleza de la corrección:** interpretativa y metodológica  
**Artefactos originales:** conservados sin sobrescritura  
**Fecha:** 1 de agosto de 2026

---

## 1. Estados corregidos

La interpretación de F0.8 queda expresada mediante tres estados separados:

```text
selection_status:
NOT_REPRODUCED_UNDER_LITERAL_CATALOG_BOUNDS

period_feature_status:
APPROXIMATELY_RECOVERED_WITH_PDCSAP

paper_reproduction_status:
UNRESOLVED
```

La etiqueta `PARTIAL_REPRODUCTION` del informe original solo describe el
comportamiento observado bajo el protocolo literal ejecutado. No debe
interpretarse como una conclusión definitiva sobre la reproducibilidad del
procedimiento de Joshi et al.

---

## 2. Motivo de la corrección

Las ventanas de F0.7 se construyeron mediante desigualdades literales:

```python
time >= catalog_start
time <= catalog_end
```

Los tiempos publicados tienen seis decimales, con una resolución de:

```text
10^-6 d = 0.0864 s
```

En los dos eventos, la primera cadencia conservada aparece casi exactamente una
cadencia después del inicio publicado:

| Evento | Inicio publicado | Primera cadencia conservada | Separación |
|---|---:|---:|---:|
| Detección QPP publicada | 2505.134541 | 2505.134772041 | ≈ 19.962 s |
| Evento no seleccionado como QPP | 2535.256201 | 2535.256432072 | ≈ 19.965 s |

Este patrón es compatible con la posibilidad de que exista una cadencia
inmediatamente anterior cuyo tiempo real sea ligeramente menor que el valor
redondeado del catálogo, pero que represente la muestra inicial utilizada al
construir el evento publicado.

Todavía no se afirma que esa cadencia falte. La hipótesis debe comprobarse
directamente en los FITS, inspeccionando las muestras inmediatamente anteriores
y posteriores a los límites catalogados.

---

## 3. Consecuencia metodológica

Con ventanas de solo 13–14 muestras, añadir o retirar una cadencia modifica:

- la longitud de la serie;
- la cuadrícula de Fourier;
- la ventana de Hann;
- la normalización de la potencia;
- el número y la posición de los bins;
- la likelihood;
- los BIC.

Por tanto, el resultado de F0.8 no permite concluir todavía que AFINO-public no
reproduce la selección publicada. Solo permite concluir que la selección no se
reproduce bajo los límites literales de catálogo usados en F0.7.

---

## 4. Resultados que permanecen válidos

F0.8 conserva todo su valor como auditoría de ejecución:

- se intentaron 240 llamadas;
- las 240 produjeron resultados finitos;
- se ejecutaron las ocho variantes predeclaradas;
- no hubo tuning posterior;
- los invariantes de archivos idénticos se cumplieron;
- ninguna semilla cambió la decisión;
- el evento no seleccionado permaneció sin selección;
- PDCSAP produjo un centro formal de M1 cercano al periodo publicado;
- SAP produjo un resultado marcadamente distinto;
- M2 concentró los warnings y mostró una fuerte incidencia de bounds.

El valor de 70.504 s debe denominarse:

```text
centro formal de M1 no seleccionado
```

No debe denominarse QPP reproducida ni periodo QPP recuperado de forma
confirmatoria.

---

## 5. Defecto documental de `n_samples`

El campo:

```json
"n_samples": null
```

en `summary_by_variant` procede de:

```python
"n_samples": specification.get("n_samples")
```

La estructura estática `specification` no contiene ese campo. Los valores
correctos sí están presentes en:

- las 240 filas de `fase0_tarea08_real_pilot_results.csv`;
- la sección `inputs` de `fase0_tarea08_execution_audit.json`.

El defecto no afecta a cálculos, decisiones ni hashes de entrada. En el próximo
script, `n_samples` deberá obtenerse de la estructura de entrada cargada o de
las filas reales de resultados.

---

## 6. Regla para la siguiente tarea

Antes de volver a ejecutar AFINO debe realizarse una auditoría de bordes
temporales directamente sobre los FITS:

1. recuperar varias cadencias antes y después de cada inicio y final publicado;
2. registrar sus tiempos exactos;
3. calcular su distancia a los límites redondeados del catálogo;
4. comprobar si una cadencia inmediatamente anterior es compatible con el
   inicio original redondeado;
5. definir por adelantado las variantes de borde que se probarán;
6. congelar sus nombres y hashes antes de cualquier nueva ejecución.

No se interpolarán datos, no se compactarán tiempos y no se modificará ningún
artefacto de F0.7 o F0.8.

---

## 7. Relación con el informe original

Este erratum no reemplaza ni altera los archivos originales. Los complementa y
tiene precedencia sobre cualquier formulación del informe F0.8 que sugiera una
conclusión definitiva sobre la reproducibilidad del artículo.

La formulación vigente es:

> La selección publicada no fue reproducida bajo los límites literales del
> catálogo; la característica temporal se recuperó aproximadamente con PDCSAP;
> la reproducibilidad del procedimiento del artículo permanece sin resolver.
