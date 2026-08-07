# Fase 2 — Tarea 2.6 — Entregables para el mentor

## Decisión

`PHASE2_COMPLETE_ROBUSTNESS_MANUSCRIPT_VIABLE_CORRECTION_REQUIRES_PHASE3`

La Fase 2 queda cerrada documentalmente. La evidencia disponible sostiene un
manuscrito metodológico de reproducción y robustez con limitaciones explícitas.
No sostiene una corrección validada del procedimiento de selección.

## Estructura documental

- Claims trazables: 34
- Planos de evidencia: 7/7
- Claims sin fuente: 0
- Claims sin alcance: 0
- Claims sin interpretación prohibida: 0
- Limitaciones registradas: 18
- Claims de manuscrito evaluados: 17
- Requisitos de Ruta A: 7
- Requisitos de Ruta B: 9
- Palabras del informe: 1415

## Ruta recomendada

**Ruta A, inmediata:** manuscrito de reproducción y robustez. Debe conservar
la separación entre evidencia observacional, sintética, numérica y límites de
interpretación.

**Ruta B, futura:** desarrollo de una corrección. Requiere una regla definida
antes de la validación, ground truth sintético, criterios de éxito
prerregistrados y un benchmark held-out independiente.

Los diez eventos de F2 no pueden utilizarse simultáneamente para desarrollar
una regla y presentarla como validada.

## Puntos documentales congelados

- `inadmissibility ≠ non-selection`
- `observational role ≠ physical ground truth`
- `stable classification ≠ unique numerical optimum`
- `period robustness is conditional on retained selection`
- `SELECTION_GAINED = 0` respecto a W00/P00 no contradice transiciones locales
  0→1 porque las referencias de los contrastes son distintas.

## Claims

La matriz clasifica expresamente como prohibidos los claims de validación
observacional de AFINO, sensibilidad, especificidad, FPR observacional,
ground truth físico y unicidad del óptimo. La afirmación de corrección queda
como `REQUIRES_PHASE3`.

## Exclusiones

No se ejecutó AFINO, no se abrió FITS, no se regeneraron variantes, no se
calcularon estadísticas científicas nuevas, no se añadió ningún umbral y no
se autorizó candidate discovery.
