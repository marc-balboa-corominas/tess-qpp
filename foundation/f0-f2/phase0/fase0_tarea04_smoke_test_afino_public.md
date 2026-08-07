# Fase 0 — Tarea 0.4

## Instalación aislada y prueba mínima de AFINO-public

**Estado:** completada  
**Fecha de ejecución:** 31 de julio de 2026  
**Artefacto auditado:** `aringlis/afino_release_version`  
**Commit:** `6aceac9518fc8056052807e666da9d0c8bebb010`  
**Versión de paquete instalada:** `0.5`

---

## 1. Objetivo

Comprobar si el commit público fijado de AFINO puede clonarse, instalarse,
importarse y ejecutar sus tests y un análisis sintético mínimo en un entorno aislado,
sin modificar su código científico.

La prueba distingue entre:

1. clonación del repositorio;
2. instalación del paquete;
3. resolución de dependencias;
4. ejecución de tests;
5. importación del paquete y de sus módulos;
6. ejecución sintética mínima;
7. repetibilidad entre procesos independientes.

---

## A. Identificación

| Elemento | Resultado |
|---|---|
| Equipo | Ordenador personal |
| Sistema operativo | Microsoft Windows 11 Pro, versión `10.0.26200`, 64 bits |
| Arquitectura | AMD64 / 64 bits |
| RAM aproximada | 31,92 GB |
| Placa/modelo registrado | Gigabyte B550 AORUS ELITE V2 |
| Procesador | NO REGISTRADO |
| PowerShell | 5.1.26100.8972 |
| Git | 2.55.0.windows.3 |
| Python base | 3.13.13, distribución Miniforge/conda-forge |
| pip inicial | 26.0.1 |
| pip después de actualizar herramientas | 26.2 |
| Entorno | `venv` aislado en `afino_public_smoke_test/.venv` |
| Ruta del intérprete aislado | `afino_public_smoke_test/.venv/Scripts/python.exe` |
| Aislamiento comprobado | Sí: `sys.prefix != sys.base_prefix` |
| Fecha del commit | 2022-11-29T11:51:07-05:00 |
| Estado inicial de Git | `HEAD detached at 6aceac9`; árbol limpio |

### Comprobación del artefacto

```text
git rev-parse HEAD
6aceac9518fc8056052807e666da9d0c8bebb010

git status
HEAD detached at 6aceac9
nothing to commit, working tree clean
```

---

## B. Instalación

### B.1. Comandos principales

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
python -m pip freeze > fase0_tarea04_environment_initial.txt
python -m pip check
```

### B.2. Primer intento sin reparaciones

| Métrica | Resultado |
|---|---|
| Creación del `venv` | Correcta, código 0 |
| Actualización de herramientas | Correcta, código 0 |
| `pip install -e .` | Correcto, código 0 |
| Paquete instalado | `afino==0.5`, editable |
| Dependencias científicas instaladas automáticamente | Ninguna |
| `pip check` | Código 0; no detectó requisitos rotos |
| Modificación de código científico | No |
| Artefacto generado dentro del repositorio | `afino.egg-info/`, no versionado |

`pip check` no prueba que el entorno sea ejecutable en este caso: el paquete no
declara sus dependencias científicas como requisitos de instalación.

### B.3. Warnings observados

Durante la actualización de herramientas aparecieron avisos repetidos:

```text
WARNING: Cache entry deserialization failed, entry ignored
```

No impidieron la actualización. La instalación editable de AFINO terminó
correctamente.

### B.4. Dependencias iniciales

Contenido de `fase0_tarea04_fase0_tarea04_environment_initial.txt`:

```text
-e git+https://github.com/aringlis/afino_release_version.git@6aceac9518fc8056052807e666da9d0c8bebb010#egg=afino
packaging==26.2
setuptools==83.0.0
wheel==0.47.0
```

SHA-256 registrado durante la ejecución:

```text
2E42FCB89FC11B69FFF1DBB6A36EC61582C25D21FF4632B52BEB38CE8E09DD35
```

### B.5. Reparaciones ambientales mínimas

| Orden | Problema | Cambio mínimo | ¿Modifica código? | Resultado |
|---:|---|---|---|---|
| 1 | Pytest no estaba instalado | `python -m pip install pytest` | No | Pytest 9.1.1 instalado |
| 2 | La colección falló por ausencia de NumPy | `python -m pip install -r requirements.txt` | No | Instaladas las dependencias publicadas |
| 3 | Pytest heredó una configuración externa desde el directorio del usuario | Uso de `pytest_isolated.ini`, `--rootdir` y ruta explícita a `tests` | No | Ejecución aislada del repositorio |

El `requirements.txt` publicado contiene, sin restricciones de versión:

```text
numpy
scipy
matplotlib
astropy
```

No se instaló manualmente `seaborn`, no se cambió de Python y no se editó ningún
archivo científico.

### B.6. Versiones resueltas principales

| Paquete | Versión |
|---|---:|
| afino | 0.5, editable desde el commit auditado |
| numpy | 2.5.1 |
| scipy | 1.18.0 |
| matplotlib | 3.11.1 |
| astropy | 8.0.1 |
| pytest | 9.1.1 |
| pip | 26.2 |
| setuptools | 83.0.0 |
| wheel | 0.47.0 |

La lista completa se conserva en `fase0_tarea04_fase0_tarea04_environment_smoke_test_final.txt`.

---

## C. Tests

### C.1. Ejecución inicial, antes de instalar `requirements.txt`

| Métrica | Resultado |
|---|---:|
| Tests recogidos | 0 |
| Superados | 0 |
| Fallidos | 0 |
| Errores | 1 durante la colección |
| Warnings de pytest | 0 registrados |
| Código de salida | 2 |
| Duración reportada por pytest | 0,20 s |
| Duración externa | 0,662 s |

Primer error completo relevante:

```text
ImportError while importing test module 'tests/test_afino.py'
tests/test_afino.py:2: in <module>
    import numpy as np
E   ModuleNotFoundError: No module named 'numpy'
```

### C.2. Ejecución después de instalar las dependencias publicadas

| Métrica | Resultado |
|---|---:|
| Tests recogidos | 7 |
| Superados | 7 |
| Fallidos | 0 |
| Errores | 0 |
| Warnings de pytest | 0 registrados |
| Código de salida | 0 |
| Duración reportada por pytest | 8,84 s |
| Duración externa | 9,511 s |

Tests superados:

```text
tests/test_afino.py::test_afinoseries
tests/test_afino.py::test_prep_series
tests/test_afino.py::test_model_id_to_string
tests/test_afino.py::test_nothing
tests/test_afino.py::test_main_analysis
tests/test_afino.py::test_pow
tests/test_afino.py::test_pow_const
```

**Interpretación:** los tests publicados pasan en este entorno después de instalar
manualmente el `requirements.txt`. Esto demuestra ejecutabilidad básica, no
corrección científica completa ni equivalencia con la ejecución TESS.

---

## D. Importación

### D.1. Paquete

Comando conceptual ejecutado:

```powershell
python -c "import afino; print(afino.__file__)"
```

Resultado equivalente registrado por el probe:

```text
Estado: OK
Versión de metadatos: 0.5
Ruta: .../afino_release_version/afino/__init__.py
```

### D.2. Submódulos descubiertos

| Módulo | Resultado | Observación |
|---|---|---|
| `afino.afino_main_analysis2` | ERROR | `No module named 'rnspectralmodels3'` |
| `afino.afino_main_analysis3` | OK | Núcleo utilizado en la prueba mínima |
| `afino.afino_model_comparison` | OK | — |
| `afino.afino_model_fitting` | OK | — |
| `afino.afino_series` | OK | — |
| `afino.afino_spectral_models` | OK | — |
| `afino.afino_start` | OK | Emitió `SyntaxWarning` por `\s` en cadenas |
| `afino.afino_test_script` | ERROR | `No module named 'afino_start'` |
| `afino.afino_utils` | OK | — |

No se intentó reparar los dos módulos fallidos. El primer fallo requiere un módulo
no disponible o no declarado; el segundo deriva de una importación absoluta interna.
Corregirlos excedería una reparación ambiental mínima.

Warnings de importación en Python 3.13:

```text
afino_start.py:126: SyntaxWarning: invalid escape sequence '\s'
afino_start.py:236: SyntaxWarning: invalid escape sequence '\s'
afino_start.py:315: SyntaxWarning: invalid escape sequence '\s'
```

---

## E. Ejemplo sintético y repetibilidad

### E.1. Entrada

Se utilizó un script externo, fuera del repositorio, con:

```python
times = np.linspace(0.0, 100.0, 101)
flux = (
    1.0
    + 0.10 * np.sin(2.0 * np.pi * 0.08 * times)
    + 0.02 * np.cos(2.0 * np.pi * 0.03 * times)
)
result = main_analysis(prepared, model="pow_const")
```

La entrada fue idéntica en cinco procesos independientes y no se fijó una semilla.

### E.2. Resultado

| Métrica | Resultado |
|---|---:|
| Procesos intentados | 5 |
| Procesos completados | 5 |
| Resultados idénticos bit a bit | No |
| Rango de `lnlike` | 5.684341886080801e-14 |
| Rango de BIC | 1.13686837721616e-13 |
| Rango de `rchi2` | 3.75503181970771e-06 |
| Rango de probabilidad | 2.661999519658035e-116 |
| Rango máximo del parámetro variable | 1.896170154225274e-08 |

La no identidad exacta queda demostrada. Las diferencias de este caso son
numéricamente pequeñas y no cambiaron el modelo ni la estructura del resultado.
No debe extrapolarse esta estabilidad a los modelos QPP, a otros datos ni a casos
cercanos a un umbral BIC.

---

## F. Estado del repositorio tras la prueba

```text
?? afino.egg-info/
```

No se modificó ningún archivo versionado. `afino.egg-info/` fue generado por la
instalación editable y se conserva como artefacto observado.

---

## G. Diagnóstico final

El commit público puede clonarse, fijarse e instalarse en modo editable sin modificar
su código científico. Sin embargo, `pip install -e .` no produce por sí solo un entorno
ejecutable completo: instala `afino==0.5`, pero no las dependencias científicas porque
el paquete no las declara como requisitos de instalación. La primera colección de
pytest falló antes de ejecutar pruebas por ausencia de NumPy. La reparación ambiental
mínima consistió en instalar el `requirements.txt` publicado, que contiene NumPy,
SciPy, Matplotlib y Astropy sin versiones fijadas. Tras ello, los siete tests
publicados fueron recogidos y superados.

El paquete `afino` y el módulo principal auditado `afino_main_analysis3` pueden
importarse. No obstante, no todo el árbol de módulos es importable:
`afino_main_analysis2` requiere `rnspectralmodels3`, que no está disponible ni
declarado, y `afino_test_script` intenta importar `afino_start` como módulo de nivel
superior. No se corrigieron estos problemas porque implicarían alterar la estructura
del código o incorporar componentes no documentados, y no bloquean el núcleo cubierto
por los tests.

El ejemplo sintético externo terminó correctamente en cinco procesos independientes.
Los resultados no fueron idénticos bit a bit: el BIC varió aproximadamente
\(1.14\times10^{-13}\) y un parámetro \(1.90\times10^{-8}\). En este caso simple,
la solución es numéricamente muy estable, pero la ejecución no es estrictamente
determinista. Esta prueba no caracteriza todavía la variabilidad del modelo QPP ni de
casos con óptimos competidores.

El entorno final queda suficientemente registrado para repetir este smoke test
concreto mediante el commit, Python 3.13.13 y el `pip freeze` adjunto. No constituye
un entorno canónico multiplataforma ni reproduce el entorno de Joshi et al. Podemos
avanzar a experimentos sintéticos controlados con `afino_main_analysis3`; antes de
uso científico sistemático deberán fijarse versiones y diseñarse pruebas de
determinismo, sensibilidad y corrección numérica más exigentes.

**Extensión del diagnóstico:** 291 palabras.

---

## H. Archivos y evidencia

| Archivo | Contenido |
|---|---|
| `fase0_tarea04_paso02_clonado.log` | Clonación, commit y estado inicial |
| `fase0_tarea04_paso03_instalacion.log` | Creación del entorno e instalación inicial |
| `fase0_tarea04_fase0_tarea04_environment_initial.txt` | Entorno inmediatamente posterior a `pip install -e .` |
| `fase0_tarea04_paso04_pytest_initial.txt` | Primer fallo de colección |
| `fase0_tarea04_paso04b_requirements_install.txt` | Instalación de dependencias publicadas |
| `fase0_tarea04_paso04b_pytest.txt` | Siete tests superados |
| `pytest_isolated.ini` | Configuración externa usada para aislar pytest |
| `fase0_tarea04_paso05_probe.py` | Probe externo de importación y repetibilidad |
| `fase0_tarea04_paso05_import_results.json` | Resultado por módulo |
| `fase0_tarea04_paso05_determinism_results.json` | Cinco ejecuciones y rangos numéricos |
| `fase0_tarea04_paso05_probe_output.txt` | Salida completa del probe |
| `fase0_tarea04_fase0_tarea04_environment_smoke_test_final.txt` | Dependencias finales fijadas por `pip freeze` |
| `fase0_tarea04_paso05_hashes.txt` | Hashes generados durante la ejecución |
| `fase0_tarea04_paso05_resumen.txt` | Resumen final del probe |

---

## I. Resultado para el registro de actividad

### Registro de actividad

* **Fecha:** 2026-07-31
* **Actividad:** F0.4 — Instalación aislada y prueba mínima de AFINO-public
* **Objetivo:** comprobar la ejecutabilidad actual del commit público sin alterar su código científico.
* **Trabajo realizado:** clonación, fijación de commit, creación de `venv`, instalación editable, instalación de herramientas de test, ejecución inicial de pytest, instalación del `requirements.txt`, repetición aislada de tests, importación sistemática de módulos y cinco ejecuciones sintéticas independientes.
* **Métodos utilizados:** Git con `detached HEAD`, Python `venv`, pip editable, `pip freeze`, `pip check`, pytest con configuración externa aislada y probe externo en Python.
* **Datos o archivos empleados:** código público del commit auditado y una serie sintética determinista; no se utilizaron curvas TESS.
* **Parámetros y configuraciones:** Python 3.13.13; modelo `pow_const`; cinco procesos; sin semilla; entrada temporal de 101 muestras entre 0 y 100.
* **Resultados obtenidos:** instalación editable correcta; instalación inicial incompleta; siete tests superados tras instalar `requirements.txt`; paquete y siete de nueve submódulos importables; análisis sintético completado cinco veces; resultados no idénticos bit a bit pero muy próximos.
* **Comprobaciones realizadas:** hash del entorno inicial, commit exacto, estado Git, `pip check`, aislamiento del intérprete, tests, importación por módulo y rangos entre ejecuciones.
* **Errores o dificultades:** dependencia NumPy ausente tras la instalación editable; configuración pytest externa heredada; dos módulos no importables; tres `SyntaxWarning`; pequeños errores de sintaxis en los bloques PowerShell de inspección y `else`, sin efecto sobre los resultados científicos.
* **Decisiones tomadas y justificación:** instalar únicamente las dependencias publicadas; no añadir `seaborn`; no corregir imports internos; usar un archivo pytest externo; conservar separada la instrumentación del repositorio.
* **Limitaciones:** un solo sistema operativo e intérprete; tests escasos; ejemplo solo con `pow_const`; cinco repeticiones insuficientes para caracterizar no determinismo general; sin comparación con outputs históricos.
* **Preguntas abiertas:** compatibilidad con un entorno histórico; comportamiento de los modelos QPP; efecto de la semilla y de las inicializaciones; función de los dos módulos no importables; necesidad real de `seaborn` en rutas no probadas.
* **Archivos creados o modificados:** archivos de log, freezes, configuración pytest, probe externo y JSON de resultados; ningún archivo científico versionado modificado.
* **Estado de la actividad:** completada.
* **Siguiente acción recomendada:** diseñar una tarea separada de validación sintética controlada que compare modelos, inyecciones conocidas, sensibilidad a semillas y estabilidad de BIC, manteniendo intacto `AFINO-public`.

---

## J. Criterio de finalización

- [x] Commit exacto `6aceac9`.
- [x] Entorno aislado.
- [x] Primer intento sin reparaciones registrado.
- [x] Tests ejecutados o error inicial conservado.
- [x] Reparaciones ambientales documentadas.
- [x] Código científico sin modificar.
- [x] Dependencias iniciales y finales guardadas.
- [x] Importación del paquete comprobada.
- [x] Ejemplo sintético mínimo ejecutado.
- [x] Repetibilidad entre procesos evaluada.
- [x] Diagnóstico reproducible emitido.
