# F3A.4 — Ejecución completa checkpointed del plan congelado

## 1. Propósito de F3A.4

F3A.4 completa materialmente el plan de ejecución congelado en F3A.2 utilizando el runner validado en F3A.3. Esta tarea produce un dataset de ejecución completo y auditado; no realiza interpretación científica. El universo operacional está fijado en 7.466 decisiones y 22.398 llamadas de modelo. Los 102 resultados del canary F3A.3 se reutilizaron byte-a-byte y las 22.296 llamadas restantes se ejecutaron sin modificar cohortes, variantes, payloads, seeds, modelos, bounds ni reglas de selección.

## 2. Freezes utilizados

El plan científico procede del commit F3A.2 `6bf9beca8fa8016495693575f8c86a2dec5fecb1` y el runner del freeze F3A.3 `0738b1cc132598119dcbbc27b4113c93ae9d2733`. El SHA-256 del runner ejecutado es `0de4b1b3745e7c7b237ff82680dd8f6cb8e2bf1288c58fd07d1624ca034558db` y el plan completo conserva SHA-256 `d190a4f5e70339b05fd42b2d0cda9c51dd180c10e885c27fdfa43323c8dc1c6f`. Los cuatro arrays externos de payloads permanecieron ligados a sus hashes F3A.2. El repositorio AFINO siguió en el commit `6aceac9518fc8056052807e666da9d0c8bebb010`, con diffs tracked y staged iguales a cero.

## 3. Bootstrap de los resultados canary

Se creó un checkpoint full independiente. Su inicialización se realizó contra el plan completo con autorización explícita y cero jobs nuevos. Después se importaron las 102 filas previamente validadas del checkpoint F3A.3. Cada fila demostró coincidencia de `job_id`, variante, seed, modelo, payload y hash lógico; además se preservó `result_core_sha256`. El audit de bootstrap contiene 102 filas y el número de discrepancias de result-core al compararlo posteriormente con el checkpoint completo es 0.

## 4. Autorización del plan completo

La autorización quedó registrada prospectivamente antes de cualquier nueva llamada full. Autoriza únicamente ejecutar el plan congelado; mantiene en `false` el análisis científico, la comparación baseline/referencia y el candidate discovery. Debido al guard histórico del runner F3A.3, la ejecución usó un worktree detached en el commit del canary como `repo-root`, mientras los bytes del runner procedieron del freeze F3A.3 y checkpoint/outputs permanecieron en el repositorio principal. No fue necesario modificar el runner.

## 5. Secuencia checkpoint/resume

Tras el bootstrap de 102 filas, las nuevas ejecuciones siguieron la secuencia congelada de siete chunks de 3.000 jobs, seguida por 1.296 jobs y una invocación final de cero jobs. El checkpoint registra también su inicialización previa de cero ejecuciones. La última invocación encontró 22.398 filas presentes y añadió cero, proporcionando la prueba de idempotencia del estado completo. No existen trabajos borrados, redibujados o sustituidos.

## 6. Completitud de 22.398 resultados

El checkpoint contiene exactamente 22.398 resultados y el CSV exportado contiene el mismo número. Los conteos por modelo son 7.466 M0, 7.466 M1 y 7.466 M2. Todos los resultados tienen estado `OK`. Las tres llamadas correspondientes a cada decisión permiten reconstruir exactamente 7.466 decisiones con estado `VALID`. Esta completitud se evalúa exclusivamente como propiedad estructural de la ejecución y no como evidencia a favor o en contra de ninguna clasificación física.

## 7. Integridad plan, checkpoint y CSV

La auditoría uno-a-uno produce 0 discrepancias entre plan y checkpoint, 0 entre checkpoint y CSV y 0 discrepancias de identidad de payload. El ensamblaje independiente de decisiones produce 0 discrepancias respecto de los BIC almacenados y la regla congelada. Los identificadores de job y las claves `variant × seed × model` permanecen únicos.

## 8. Contrato temporal

Para cada una de las 7.466 decisiones se reconstruyó el payload temporal sin abrir FITS. El criterio efectivo AFINO es la media de `diff(time_seconds)` y el número de frecuencias estrictamente positivas de `np.fft.fftfreq`. Las coincidencias normativas son 7466/7.466 para la cadencia y 7466/7.466 para los bins positivos. Mediana y `rfftfreq` se preservan solo como diagnósticos legacy y no intervienen en el gate.

## 9. Diagnósticos operacionales

Los únicos resúmenes agregados de F3A.4 son operacionales y se separan por modelo: número de llamadas, llamadas con warnings, warnings totales, llamadas con parámetros en bounds, tiempo total, mediana de runtime y conteos de `convergence_status`. No se calculan estos diagnósticos por rol observacional, ventana, perfil ni estado de selección, evitando anticipar la caracterización científica posterior.

## 10. Limitaciones

El pass de F3A.4 demuestra completitud, trazabilidad, integridad de payloads y coherencia de ejecución del plan congelado. No demuestra validez física de las clasificaciones ni compara comportamiento entre poblaciones. Tampoco autoriza ajustes posteriores basados en warnings, bounds o resultados. Cualquier interpretación de robustez, pérdidas, ganancias, sensibilidad a ventanas, procesamiento, seed o periodo queda fuera de esta fase.

## 11. Ausencia explícita de análisis científico

Durante F3A.4 no se abrieron FITS, no se regeneraron variantes, no se reaplicó QUALITY, no se recalculó detrending, no se interpoló ni se rellenaron gaps. No se eliminaron eventos ni jobs. No se calcularon fracciones de selección, comparaciones QPP/control, transiciones de baseline, efectos de ventana o preprocessing, ni estadísticas de periodo. El output final es exclusivamente el execution dataset completo que podrá utilizar la siguiente fase de análisis una vez congelado y archivado.

`PHASE3A_FULL_EXECUTION_VALIDATION_PASS`
