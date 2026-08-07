# Fase 0 — Tarea 0.2

## Auditoría de la implementación pública de AFINO

**Fecha de auditoría:** 2026-07-30  
**Repositorio auditado:** [`aringlis/afino_release_version`](https://github.com/aringlis/afino_release_version)  
**Commit fijado:** [`6aceac9518fc8056052807e666da9d0c8bebb010`](https://github.com/aringlis/afino_release_version/commit/6aceac9518fc8056052807e666da9d0c8bebb010)  
**Tag/release observado:** [`v1.0`](https://github.com/aringlis/afino_release_version/releases/tag/v1.0), apuntando al commit anterior  
**Versión declarada dentro de `setup.py`:** `0.5`  
**Texto TESS auditado:** Joshi et al. (2025), arXiv v1, 27 de junio de 2025  
**Referencia bibliográfica final:** *Astronomy & Astrophysics*, **700**, A178 (2025)

> Alcance: auditoría estática del código, documentación y artículos primarios. No se instalaron dependencias, no se ejecutó AFINO, no se descargaron curvas TESS y no se escribió una implementación alternativa.

---

## Ficha de actividad

* **Nombre de la actividad:** F0.2 — Auditoría de la implementación pública de AFINO.
* **Objetivo científico:** determinar qué nivel de reproducción permite el software público y separar el AFINO original, el paquete público actual y la adaptación TESS.
* **Pregunta concreta que debe responder:** ¿el artefacto público permite reproducir exactamente la ejecución de Joshi et al. (2025), reproducir fielmente su metodología o solo reconstruirla conceptualmente?
* **Resultado o entregable esperado:** tabla del artefacto, matriz de correspondencia, clasificación única y preguntas para los autores.
* **Duración disponible:** 2–4 horas.
* **Dependencias previas:** F0.1 aprobada.
* **Datos, código, artículos o herramientas disponibles:** repositorio y documentación de AFINO; Inglis et al. (2015, 2016); Broomhall et al. (2019); Joshi et al. (2025).
* **Restricciones técnicas o metodológicas:** solo fuentes primarias; sin datos TESS, instalación ni reimplementación.
* **Criterios para considerar la actividad terminada:** commit y licencia fijados; fórmulas auditadas; adaptación TESS separada; nivel de reproducción clasificado; máximo cinco preguntas no redundantes.
* **Relación con el objetivo global del proyecto:** fija el baseline metodológico antes de estudiar completitud, falsos positivos y dependencia respecto al método.

---

## 1. Distinción histórica imprescindible

La expresión «AFINO» no designa un único artefacto inmutable:

1. **Inglis et al. (2015):** formulación inicial bayesiana. Compara dos modelos, usa PyMC/MCMC para obtener distribuciones posteriores y realiza comprobaciones predictivas posteriores con estadísticos adicionales.
2. **Inglis et al. (2016):** adaptación escalable para una muestra grande. Introduce tres modelos \(S_0,S_1,S_2\), máxima verosimilitud con SciPy, 20 inicializaciones aleatorias, BIC y una estadística \(\chi^2\)-like.
3. **Broomhall et al. (2019):** aplica y evalúa la versión de tres modelos en un benchmark sintético; distingue una versión completa y otra relajada.
4. **Paquete público auditado:** implementación Python genérica, declarada experimental, cuya estructura se aproxima principalmente a Inglis et al. (2016), pero no constituye por sí sola el código de ningún estudio concreto.
5. **Joshi et al. (2025):** adaptación a TESS que añade como mínimo el dominio de periodos de 40–300 s y cuatro ventanas temporales \(0,1,2,3\tau\). Esa capa de orquestación no aparece en el paquete público auditado.

Por tanto:

\[
\text{AFINO 2015}
\neq
\text{AFINO 2016}
\neq
\text{paquete público}
\neq
\text{ejecución TESS de 2025}.
\]

---

## 2. Artefacto de software

| Elemento | Resultado | Fuente exacta | Consecuencia para la reproducción |
|---|---|---|---|
| URL del repositorio | `https://github.com/aringlis/afino_release_version` | [`README.md`, repositorio raíz](https://github.com/aringlis/afino_release_version) | Proporciona un baseline público identificable, pero no demuestra que Joshi et al. lo utilizaran. |
| Commit exacto auditado | `6aceac9518fc8056052807e666da9d0c8bebb010` | [Página del commit](https://github.com/aringlis/afino_release_version/commit/6aceac9518fc8056052807e666da9d0c8bebb010); [patch](https://github.com/aringlis/afino_release_version/commit/6aceac9518fc8056052807e666da9d0c8bebb010.patch) | Toda afirmación sobre el código queda ligada a un estado inmutable. No consta que sea el commit usado en 2025. |
| Fecha del commit | 2022-11-29 11:51:07 −05:00 | Cabecera `Date` del [patch del commit](https://github.com/aringlis/afino_release_version/commit/6aceac9518fc8056052807e666da9d0c8bebb010.patch) | El código público fijado precede al estudio TESS; pudieron existir modificaciones privadas posteriores. |
| Tags o releases | Tag `v1.0` y release «Version 1.0», ambos apuntando a `6aceac9`. El paquete interno continúa declarando versión `0.5`. | [Tags](https://github.com/aringlis/afino_release_version/tags); [release `v1.0`](https://github.com/aringlis/afino_release_version/releases/tag/v1.0); [`setup.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/setup.py) | Existe una release fijable, pero la discrepancia `v1.0`/`0.5` impide tratar el número de versión como identificación inequívoca del software. |
| Licencia | BSD 2-Clause License. | [`LICENSE`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/LICENSE) | Permite reutilización y modificación con atribución y aviso de licencia; no garantiza validez científica ni equivalencia con la ejecución TESS. |
| Lenguaje y versión esperada | Python. Versión única esperada: **NO DISPONIBLE.** `setup.py` no declara `python_requires`; la CI enumera Python 3.6, 3.7, 3.8, 3.9 y 3.11. | [`setup.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/setup.py); [`.github/workflows/pythonpackage.yml`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/.github/workflows/pythonpackage.yml) | No existe una versión única de Python prescrita. La reproducibilidad binaria y numérica depende del entorno elegido. |
| Dependencias declaradas | `numpy`, `scipy`, `matplotlib`, `astropy`. Versiones fijadas: **NO DISPONIBLE.** `seaborn` es importado al generar figuras, pero no está declarado. | [`requirements.txt`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/requirements.txt); [`afino_start.py`, función de figura](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_start.py#L63-L70) | Una instalación actual puede resolver versiones distintas o fallar al crear figuras. No puede reconstruirse el entorno numérico original. |
| Archivo de entorno o lockfile | **NO DISPONIBLE.** Solo existe `requirements.txt` sin versiones; no hay `environment.yml`, lockfile ni contenedor. | Árbol del [commit auditado](https://github.com/aringlis/afino_release_version/tree/6aceac9518fc8056052807e666da9d0c8bebb010) | No es posible recrear exactamente el entorno ni excluir cambios de comportamiento de NumPy/SciPy. |
| Tests automáticos | Sí: `tests/test_afino.py` y workflow de GitHub Actions. Son pruebas unitarias básicas; no hay prueba end-to-end contra resultados científicos de referencia. Usan datos aleatorios sin semilla. | [`tests/test_afino.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/tests/test_afino.py); [workflow](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/.github/workflows/pythonpackage.yml) | Verifican parcialmente estructura y funciones simples, no la estabilidad de BIC, periodos, clasificación ni comportamiento frente a casos límite. |
| Datos de ejemplo | Ejemplo sintético de seno más ruido en la guía. `afino_test_script.py` referencia `test_data/flare566801.fits`; ese dataset FITS es **NO DISPONIBLE** en el árbol público auditado. | [`docs/user_guide.rst`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/docs/user_guide.rst#L13-L25); [`afino_test_script.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_test_script.py) | El ejemplo sintético permite una prueba informal, pero no hay un dataset de regresión distribuido que conecte código y resultados publicados. |
| Documentación de uso | README, documentación Sphinx/ReadTheDocs «AFINO 0.5», guía de usuario y referencia de API. Se advierte que es una herramienta experimental y que el repositorio está en desarrollo. | [README](https://github.com/aringlis/afino_release_version#readme); [ReadTheDocs](https://afino-release-version.readthedocs.io/en/latest/); [`docs/user_guide.rst`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/docs/user_guide.rst) | Es suficiente para comprender la interfaz general, no para reconstruir todas las decisiones científicas ni la adaptación TESS. |
| Outputs generados | Diccionario por modelo con `lnlike`, `model`, `BIC`, espectro ajustado, frecuencias, potencia, parámetros, `rchi2`, probabilidad e ID; guardado JSON o Pickle y figura PDF. Los datos se guardan siempre en `~/afino_repository/saves/`; `savedir` solo se aplica a la figura, pese a que la guía sugiere que permite cambiar las ubicaciones. | [`afino_main_analysis3.py`, retorno](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_main_analysis3.py#L107-L120); [`afino_utils.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_utils.py#L73-L125); [`afino_start.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_start.py#L63-L140) | Los outputs contienen ajustes brutos útiles, pero no un estado de clasificación TESS, trazas de optimización, incertidumbre del periodo ni resultados de las cuatro ventanas. Existe además una discrepancia documentación/código sobre rutas. |
| Estado de mantenimiento | El README lo define como «work in progress» y la documentación como herramienta científica experimental. El commit auditado es de 2022 y solo modifica la matriz de CI; el último cambio sustantivo visible inmediatamente anterior es también de 2022. | [README](https://github.com/aringlis/afino_release_version#readme); [documentación](https://afino-release-version.readthedocs.io/en/latest/); [commit auditado](https://github.com/aringlis/afino_release_version/commit/6aceac9518fc8056052807e666da9d0c8bebb010) | El repositorio es utilizable como referencia histórica, pero no debe asumirse mantenimiento activo ni correspondencia con el pipeline de 2025. |

### Diagnóstico del artefacto

El repositorio es un artefacto científico real y no una mera descripción: contiene modelos, likelihood, optimización, BIC, bondad de ajuste, tests y documentación. Sin embargo, carece de un entorno congelado, de datos de regresión, de una prueba científica end-to-end y de la capa TESS. La release observada no cambia el hecho de que el contenido al que apunta está fijado en un commit de 2022 y que el paquete se identifica internamente como `0.5`.

---

## 3. Fórmulas recuperadas

### 3.1 Papers originales

La versión de tres modelos de Inglis et al. (2016), Ecs. (2)–(4), utiliza:

\[
S_0(f)=A_0f^{-\alpha_0}+C_0,
\]

\[
S_1(f)=A_1f^{-\alpha_1}
+B\exp\left[-\frac{(\ln f-\ln f_p)^2}{2\sigma^2}\right]+C_1,
\]

\[
S_2(f)=
\begin{cases}
A_2 f^{-\alpha_b}+C_2, & f<f_{\rm break},\\
A_2 f_{\rm break}^{-\alpha_b+\alpha_a}f^{-\alpha_a}+C_2,
& f\ge f_{\rm break}.
\end{cases}
\]

Inglis et al. (2015) solo compara el equivalente de \(S_0\) con \(S_0\) más una gaussiana en log-frecuencia, mediante MCMC/PyMC. La tercera alternativa de ley de potencia rota pertenece a la evolución de 2016.

### 3.2 Código público fijado

En el commit auditado:

\[
M_0(f)=
e^{a_0}\left(\frac{f}{f_{\min}}\right)^{-a_1}+e^{a_2},
\]

\[
M_1(f)=M_0(f)+
\frac{e^{a_3}}{\sqrt{2\pi a_5^2}}
\exp\left[-\frac{1}{2}
\left(\frac{\ln f-a_4}{a_5}\right)^2\right],
\]

\[
M_2(f)=
\begin{cases}
e^{a_0}f^{-a_1}+e^{a_4}, & f<a_2,\\
e^{a_0}a_2^{-a_1+a_3}f^{-a_3}+e^{a_4},
& f\ge a_2.
\end{cases}
\]

Fuentes: [`afino_spectral_models.py`](https://github.com/aringlis/afino_release_version/blob/6aceac9518fc8056052807e666da9d0c8bebb010/afino/afino_spectral_models.py), funciones `pow`, `bpow`, `pow_const`, `NormalBump2` y `pow_const_gauss`.

La familia funcional de \(M_0\) puede transformarse algebraicamente en una ley de potencia más constante, pero la normalización por \(f_{\min}\) cambia la parametrización y, con bounds finitos sobre \(a_0\), puede cambiar el espacio de soluciones admisible. En \(M_1\), la normalización de la gaussiana también puede absorberse en una amplitud libre en ausencia de límites, pero no es estrictamente equivalente bajo los bounds publicados del código.

### 3.3 Joshi et al. (2025)

Joshi et al. nombran los tres modelos, pero no vuelven a publicar sus fórmulas completas. Remiten a Inglis et al. (2015, 2016) y Broomhall et al. (2019). Por tanto, las fórmulas exactas realmente ejecutadas en TESS no son recuperables únicamente del artículo TESS.

---

## 4. Matriz de correspondencia metodológica

**Convención de la columna Estado:** resume la correspondencia conjunta entre los papers originales, el paquete público y la ejecución TESS. `IGUAL` exige evidencia explícita en las tres capas; `MODIFICADO` exige una diferencia observable; `NO IMPLEMENTADO` exige ausencia comprobada en el código público; y `DESCONOCIDO` se usa cuando la documentación de Joshi et al. no permite establecer la equivalencia. La coincidencia nominal de un modelo no se considera evidencia de igualdad.

| Componente | Papers originales | Código público | Joshi et al. 2025 | Estado | Impacto |
|---|---|---|---|---|---|
| Formato de entrada | Series temporales de flare; los papers realizan preparación instrumental previa. | `analyse_series(times, flux)` recibe dos arrays NumPy. | Segmentos de curvas TESS; columna de flujo exacta y wrapper no publicados. | DESCONOCIDO | No puede reproducirse la interfaz entre productos TESS y AFINO. |
| Muestreo uniforme | La FFT se formula para frecuencias \(f_j=j/(N\Delta T)\); en 2016 se rebina a cadencia uniforme cuando procede. | Calcula una cadencia media \((t_{\rm final}-t_0)/(N-1)\); almacena diferencias, pero no valida uniformidad. | Cadencia nominal de 20 s; tratamiento de irregularidades no descrito. | DESCONOCIDO | Gaps o cadencias irregulares pueden desplazar frecuencias y violar el modelo estadístico del periodograma. |
| Tratamiento de gaps/NaN | Preparación dependiente del instrumento; no hay una regla genérica única de AFINO. | No se observa filtrado, interpolación ni rechazo explícito de NaN/gaps antes de la FFT. | **NO ESPECIFICADO.** | DESCONOCIDO | Puede alterar completamente la PSD, la convergencia y la población analizable. |
| Normalización temporal | \((I-\bar I)/\bar I\), sin detrending; Inglis 2015 §3.2 e Inglis 2016 Ec. (1). | Implementa exactamente `((data-mean)/mean)*hanning`. | Declara normalización por la media. | IGUAL | El núcleo de preprocesamiento temporal es recuperable, salvo elección previa de flujo y muestras. |
| Ventana de Hann | Hann/Hanning después de normalizar. | `np.hanning(N)`. | Declara Hann. | IGUAL | Correspondencia directa; siguen sin fijarse versión de NumPy ni manejo de extremos/gaps. |
| Definición de la PSD | Potencias de Fourier exponencialmente distribuidas; la convención absoluta de FFT no queda completamente especificada en los papers. | Usa \(\lvert\mathrm{FFT}(x)\rvert^2\) y conserva frecuencias positivas; no incluye factor explícito de cadencia o longitud. | Solo indica «Fourier power spectrum». | DESCONOCIDO | No puede probarse igualdad de normalización espectral absoluta. |
| Normalización de la PSD | No se documenta la doble normalización concreta del paquete. | Divide la potencia positiva por su media y después por la desviación estándar de esa potencia normalizada. | **NO ESPECIFICADO.** | MODIFICADO | Las amplitudes libres absorben parte del reescalado, pero bounds y likelihood pueden hacer que no sea completamente inocuo. |
| Fórmula completa de M0 | \(A_0f^{-\alpha_0}+C_0\). | \(e^{a_0}(f/f_{\min})^{-a_1}+e^{a_2}\). | Lo denomina ley de potencia; la figura/cadena metodológica presupone constante. No da fórmula. | MODIFICADO | Misma familia sin bounds, pero parametrización y límites sobre amplitud no son idénticos. |
| Fórmula completa de M1 | \(A_1f^{-\alpha_1}+B\exp[-(\ln f-\ln f_p)^2/(2\sigma^2)]+C_1\). | M0 más gaussiana normalizada en \(\ln f\). | Ley de potencia con bump gaussiano; fórmula completa no publicada. | MODIFICADO | La familia es cercana, pero la normalización del bump interactúa con los bounds de amplitud. |
| Fórmula completa de M2 | Ley de potencia rota continua más \(C_2\). | Ley de potencia rota continua más \(e^{a_4}\). | Broken power law; fórmula completa no publicada. | DESCONOCIDO | El código coincide funcionalmente con Inglis 2016, pero el nombre usado por Joshi et al. no demuestra que ejecutara esta fórmula y parametrización exactas. |
| Término de ruido blanco/constante | \(C_0,C_1,C_2\) explícitos y físicamente interpretados como transición a ruido blanco/Poisson. | Constante positiva exponenciada en M0, M1 y M2. | No se explicita en el texto abreviado; las figuras y referencias remiten a la versión con constante. | DESCONOCIDO | La coincidencia entre papers y código no demuestra que la adaptación TESS conservara exactamente este término y sus bounds. |
| Likelihood | Producto exponencial \(\prod_j S_j^{-1}\exp(-I_j/S_j)\); Inglis 2015 Ec. (3), Inglis 2016 Ec. (6). | `-sum(log(model))-sum(data/model)`. | Declara máxima verosimilitud y remite a los papers, pero no publica la expresión ejecutada. | DESCONOCIDO | Papers y código público coinciden, pero no puede probarse que el wrapper TESS utilizara exactamente esta implementación y convención. |
| Optimizador | 2015: PyMC/MCMC. 2016 y Broomhall: máxima verosimilitud con SciPy; algoritmos concretos no publicados. | Ejecuta L-BFGS-B y SLSQP y retiene el mayor log-likelihood. | Máxima verosimilitud; algoritmo **NO ESPECIFICADO**. | DESCONOCIDO | Diferentes optimizadores y versiones pueden producir soluciones locales distintas. |
| Inicialización | 2016: 20 ajustes con guesses aleatorios; distribución y semilla no publicadas. | 20 inicializaciones aleatorias con distribuciones codificadas; sin semilla ni registro del estado RNG. | **NO ESPECIFICADO.** | DESCONOCIDO | La ejecución no es determinista y casos cercanos al umbral pueden cambiar entre corridas. |
| Bounds o priors | 2015 publica priors uniformes; 2016 fija \(1<P<300\) s y \(0.05<\sigma<0.25\). | Bounds hardcoded; M1 usa por defecto \(a_4\in[-5.7,-1.5]\), \(a_5\in[0.05,0.25]\), con opción de sobrescritura. M2 tiene otros bounds. | Dominio efectivo 40–300 s, pero límites completos de todos los parámetros **NO ESPECIFICADOS**. | MODIFICADO | Los bounds deciden qué máximos son accesibles; la configuración TESS exacta no puede reconstruirse. |
| Número de parámetros por modelo | Por las ecuaciones: M0 = 3, M1 = 6, M2 = 5. | Los vectores contienen 3, 6 y 5 parámetros, pero el código pasa `k=2,5,4` al BIC y usa esos mismos valores al calcular grados de libertad. | **NO ESPECIFICADO.** | MODIFICADO | El desplazamiento común de una unidad deja invariantes las diferencias BIC entre estos tres modelos, pero cambia BIC absolutos, grados de libertad y probabilidades de ajuste. |
| Cálculo del BIC | \(\mathrm{BIC}=-2\ln L+k\ln n\), con \(k\) igual al número de parámetros libres y \(n=N/2\). | Implementa la fórmula, pero recibe `k=2,5,4` para modelos con 3,6,5 parámetros. | Usa diferencias BIC y umbral 10; no publica código. | MODIFICADO | Las \(\Delta\mathrm{BIC}\) entre M0/M1/M2 no cambian por el offset común; otros usos del BIC sí. Debe aclararse si la ejecución TESS conservó este comportamiento. |
| Umbral de selección | Inglis 2016: el ganador debe superar por más de 10 a todos los demás; además, un ajuste con \(p<0.01\) no es adecuado. | Calcula BIC y diferencias mediante helper, pero la ruta genérica no clasifica automáticamente con \(\Delta\mathrm{BIC}>10\) ni aplica el umbral de bondad de ajuste. | Ec. (12): \(\mathrm{BIC}_j-\mathrm{BIC}_i>10\) para todos los modelos alternativos. | NO IMPLEMENTADO | La lógica que convierte ajustes en «QPP seleccionada» está fuera del paquete público. |
| Cálculo del periodo | \(P=1/f_p\). | En la figura calcula `period = 1/exp(params[4])`. | Reporta periodos del bump de M1. | IGUAL | El estimador puntual es recuperable si el ajuste y los parámetros coinciden. |
| Error del periodo | 2015 permite distribuciones posteriores; la versión 2016 no define en la sección metodológica una regla única equivalente al campo TESS. | No devuelve incertidumbre de \(P\); devuelve centro y anchura del bump, que no son automáticamente el error del periodo. | Publica `Error_P (s)` en el CSV, pero el cálculo no está especificado. | NO IMPLEMENTADO | No puede reproducirse la incertidumbre publicada ni usarla rigurosamente en análisis posteriores. |
| \(\chi^2\) reducido | Inglis 2016 usa la estadística de Nita et al. y considera inadecuado \(p<0.01\). | Implementa estadística y probabilidad aproximada, pero usa grados de libertad basados en `2,5,4`; no aplica automáticamente \(p>0.01\) como filtro. | Afirma usar \(\chi^2_\nu\) para validar, sin umbral ni regla de decisión. | MODIFICADO | No puede saberse qué eventos fueron descartados por mal ajuste; los valores publicados pueden depender del conteo de grados de libertad. |
| Restricción 40–300 s | 2016 usa 1–300 s; el límite inferior depende de la cadencia instrumental. | El default de M1 no impone 40–300 s y permite sobrescribir el bound del centro. Además, `low_frequency_cutoff` presenta una contradicción entre documentación e implementación: el comentario indica que deberían conservarse frecuencias superiores al umbral, pero el código selecciona `frequencies < low_frequency_cutoff`, por lo que actúa efectivamente como un límite superior de frecuencia. | Impone 40 s por Nyquist y 300 s como máximo. No consta cómo se configuró `low_frequency_cutoff`. | MODIFICADO | El intervalo 40–300 s equivale a aproximadamente 0,00333–0,025 Hz. El parámetro podría haberse usado para excluir frecuencias superiores a 0,025 Hz, mientras que el bound del centro gaussiano limitaría los periodos superiores a 300 s, pero esa configuración exacta no está publicada. Cambia directamente el espacio de búsqueda y la prevalencia detectada. |
| Ventanas \(0,1,2,3\tau\) | No forman parte del procedimiento original descrito en 2015/2016 ni del núcleo resumido en Broomhall. | No hay un orquestador que construya y procese esas cuatro ventanas. | Añade 1, 2 y 3 \(\tau\) al final original, además de la ventana base. | NO IMPLEMENTADO | Es una modificación TESS sustantiva y potencial fuente de selección adicional. |
| Elección entre ventanas | **NO ESPECIFICADO** en AFINO original porque no usa esta estrategia. | **NO IMPLEMENTADO.** | Se probaron cuatro ventanas, pero no se describe cómo se resolvieron resultados múltiples o discordantes. | NO IMPLEMENTADO | No puede reconstruirse por qué una fila tiene un `Tau` concreto ni qué ocurría si varias ventanas daban detección. |
| Corrección por múltiples ventanas | No aplicable a la versión original de una sola ventana. | **NO IMPLEMENTADO.** | **NO ESPECIFICADO.** | NO IMPLEMENTADO | Probar cuatro ventanas aumenta las oportunidades de selección; la tasa efectiva de falsos positivos no puede deducirse del umbral por ajuste individual. |

---

## 5. Hallazgos críticos

### 5.1 Lo que sí puede recuperarse

* Preprocesamiento central \((I-\bar I)/\bar I\) y ventana de Hann.
* Tres familias espectrales de la versión 2016.
* Likelihood exponencial para potencias de Fourier.
* Ajuste de máxima verosimilitud con múltiples inicios.
* BIC, \(\chi^2\)-like y outputs por modelo.
* Estimador puntual \(P=1/f_p\).

### 5.2 Lo que bloquea una reproducción exacta o fiel del catálogo TESS

* Ausencia de una referencia explícita de Joshi et al. a repositorio, commit y entorno.
* Capa TESS no publicada: entrada, flux, quality flags, gaps/NaN y construcción de ventanas.
* Bounds completos y semilla no publicados.
* Regla de consolidación entre \(0,1,2,3\tau\) no publicada.
* Falta de corrección o evaluación explícita del efecto de cuatro ventanas.
* Lógica de selección final no implementada en la ruta pública genérica.
* Método de `Error_P (s)` no recuperable.
* Resultados completos y estados de optimización de los 3.817 eventos no seleccionados no publicados.
* Discrepancia no resuelta entre el número real de parámetros y los valores `k=2,5,4` usados para BIC y grados de libertad. No puede clasificarse todavía como error: podría ser una decisión deliberada, una convención heredada o un defecto de implementación. No debe corregirse antes de consultar a los autores.
* Cuatro filas publicadas con `BIC_M2_M1 < 10`, incompatibles con la lectura literal de la Ec. (12) salvo que la semántica de la columna o la regla aplicada sea distinta.

### 5.3 Baseline recomendado para fases posteriores

El baseline público debe fijarse como:

```text
aringlis/afino_release_version
tag: v1.0
commit: 6aceac9518fc8056052807e666da9d0c8bebb010
```

Debe denominarse **«baseline público AFINO v1.0/6aceac9»**, no «código de Joshi et al.». El núcleo público puede reproducirse a nivel de código fijando ese commit; lo que solo puede reconstruirse conceptualmente es la ejecución completa de Joshi et al., porque faltan la capa TESS, su configuración y la lógica de selección final.

Para las fases posteriores deberán mantenerse tres líneas explícitamente separadas:

1. **`AFINO-public`:** commit `6aceac9` sin cambios, conservado como referencia histórica y técnica.
2. **`AFINO-reproduction`:** adaptación mínima, trazable y documentada destinada a aproximar la ejecución descrita por Joshi et al.; cada diferencia respecto de `AFINO-public` deberá justificarse.
3. **`AFINO-study`:** versión metodológicamente corregida o ampliada para los experimentos propios, sin presentarla como reproducción del catálogo publicado.

Los resultados de estas tres líneas no deberán mezclarse ni compararse sin identificar de forma explícita qué implementación y configuración los produjo.

---

## 6. Clasificación del nivel posible de reproducción

### Categoría seleccionada: reproducción conceptual

La clasificación **reproducción conceptual** se aplica a la ejecución completa de Joshi et al. (2025), no al mero hecho de ejecutar el repositorio público. El núcleo `AFINO-public` sí puede reproducirse a nivel de código fijando el commit `6aceac9`: contiene normalización temporal, ventana de Hann, FFT, tres familias espectrales, likelihood exponencial, optimización por máxima verosimilitud, BIC y una estadística de bondad de ajuste. Esto permite estudiar de forma trazable el comportamiento del artefacto público.

No obstante, no puede demostrarse que ese artefacto, sin modificaciones, sea el usado en el estudio TESS. Joshi et al. no publican commit, entorno, semilla, wrapper ni configuración completa. Tampoco está disponible la capa que construye las ventanas \(0,1,2,3\tau\), restringe el dominio a 40–300 s, consolida resultados entre ventanas y transforma los ajustes en el catálogo final. El parámetro `low_frequency_cutoff` añade una incertidumbre concreta: su comentario indica conservar frecuencias superiores al umbral, pero el código aplica `frequencies < low_frequency_cutoff`, de modo que funciona como límite superior; no consta qué valor se empleó en TESS.

La discrepancia entre los vectores de 3, 6 y 5 parámetros y los valores `k=2,5,4` usados en BIC y grados de libertad tampoco debe corregirse todavía. El offset común conserva las diferencias BIC, pero modifica BIC absolutos, grados de libertad y probabilidades de ajuste; no sabemos si responde a una convención deliberada, heredada o errónea.

Por tanto, el código público es reproducible como artefacto fijado, mientras que las 61 selecciones TESS solo pueden reconstruirse conceptualmente hasta recuperar la configuración y lógica privadas.

---

## 7. Preguntas para los autores

1. **Código, entorno y convención de parámetros.** ¿Podrían indicar el repositorio y commit exactos, o compartir el snapshot, wrapper y archivo de entorno utilizados para ejecutar AFINO sobre las curvas TESS, incluyendo versiones de Python/NumPy/SciPy y cualquier semilla aleatoria? ¿La ejecución TESS conservó los valores `k=2,5,4` para modelos con 3, 6 y 5 parámetros y, en ese caso, cuál fue la justificación?
2. **Cuatro diferencias BIC.** En cuatro filas de `QPP_detections.csv`, `BIC_M2_M1` es inferior a 10 aunque la Ec. (12) exige que M1 supere a cada alternativa por más de 10. ¿Qué representan exactamente esas columnas y cuál fue la regla efectiva de inclusión de esas cuatro filas?
3. **Ventanas temporales.** ¿Cuál fue la regla exacta para escoger o consolidar resultados entre la ventana original y las extensiones \(1\tau,2\tau,3\tau\), especialmente cuando más de una ventana favorecía M1 o devolvía periodos distintos? ¿Se aplicó alguna corrección o calibración por probar cuatro ventanas?
4. **Resultados no seleccionados.** ¿Es posible obtener, para los 3.817 eventos no seleccionados, los BIC de M0/M1/M2, \(\chi^2_\nu\) o p-values, parámetros, ventana, estado de convergencia y motivo final de no selección?
5. **Configuración TESS específica.** ¿Qué columna de flujo, máscara de quality flags y tratamiento de gaps/NaN se usaron; qué valor se asignó a `low_frequency_cutoff`; cuáles fueron los bounds completos para los tres modelos en el dominio 40–300 s; y cómo se calculó `Error_P (s)`?

---

## 8. Fuentes primarias auditadas

1. [Inglis et al. (2015), *Quasi-periodic pulsations in solar and stellar flares: re-evaluating their nature in the context of power-law flare Fourier spectra*](https://arxiv.org/abs/1410.8162), especialmente §§3.2 y 4.1–4.6, Ecs. (1), (3)–(10).
2. [Inglis et al. (2016), *A large-scale search for quasi-periodic pulsations in solar flares*](https://arxiv.org/abs/1610.07454), especialmente §3, Ecs. (1)–(9).
3. [Broomhall et al. (2019), *A Blueprint of State-of-the-art Techniques for Detecting Quasi-periodic Pulsations in Solar and Stellar Flares*](https://doi.org/10.3847/1538-4365/ab40b3), especialmente §4.3 y §5.2.1.
4. [Joshi et al. (2025), arXiv v1](https://arxiv.org/abs/2506.22131), especialmente §4.1, Ecs. (12)–(14).
5. [Repositorio público AFINO fijado en `6aceac9`](https://github.com/aringlis/afino_release_version/tree/6aceac9518fc8056052807e666da9d0c8bebb010).
6. [Documentación pública AFINO 0.5](https://afino-release-version.readthedocs.io/en/latest/).

---

## 9. Registro de actividad

* **Fecha:** 2026-07-30.
* **Actividad:** F0.2 — Auditoría de la implementación pública de AFINO.
* **Objetivo:** clasificar el nivel de reproducción posible para la ejecución TESS.
* **Trabajo realizado:** fijación de commit y release; inspección de licencia, entorno, tests, documentación, modelos, preprocesamiento, likelihood, optimizadores, bounds, BIC, bondad de ajuste y outputs; comparación con cuatro fuentes metodológicas.
* **Métodos utilizados:** auditoría estática y correspondencia ecuación–código–artículo.
* **Datos o archivos empleados:** repositorio AFINO y artículos primarios; no se usaron curvas TESS.
* **Parámetros y configuraciones:** commit `6aceac9518fc8056052807e666da9d0c8bebb010`, tag/release `v1.0`.
* **Resultados obtenidos:** el paquete público recupera el núcleo de AFINO 2016, pero no la adaptación TESS ni la lógica de selección final.
* **Comprobaciones realizadas:** fórmulas de M0/M1/M2; likelihood; 20 inicializaciones; optimizadores; bounds; conteo real de parámetros frente a `k`; persistencia de resultados; tests y dependencias.
* **Errores o dificultades:** versionado `v1.0` frente a paquete `0.5`; dependencias no fijadas; `seaborn` no declarado; ausencia de dataset end-to-end; contradicción entre comentario e implementación de `low_frequency_cutoff`; discrepancia no resuelta de `k`; documentación incompleta de `savedir`.
* **Decisiones tomadas y justificación:** fijar `AFINO-public` en `v1.0/6aceac9`; clasificar únicamente la ejecución TESS como reproducción conceptual; reservar `AFINO-reproduction` para la adaptación mínima trazable y `AFINO-study` para modificaciones metodológicas propias; no corregir la convención `k=2,5,4` sin aclaración de los autores.
* **Limitaciones:** no se ejecutó el código; una auditoría estática no demuestra qué ramas funcionan en un entorno actual ni qué código privado usaron los autores.
* **Preguntas abiertas:** las cinco preguntas de la sección 7.
* **Archivos creados o modificados:** `fase0_tarea02_auditoria_afino.md`.
* **Estado de la actividad:** completada.
* **Siguiente acción recomendada:** revisar críticamente esta auditoría y, si se aprueba, preparar un contacto breve con los autores o una prueba mínima de instalación reproducible como actividad separada.
