# Fase 1 — Tarea 1.9

## Validación del generador anidado padre–prefijos

**Conclusión:** `NESTED_GENERATOR_VALIDATED`

Los 120 bloques independientes de ruido y fase se regeneraron con el generador
congelado de F1.2, bajo NumPy `2.3.5`. Para
cada combinación de pendiente y semilla, los hashes de tiempo, ruido y fase
coincidieron con el manifiesto N=120 de F1.2. El resultado fue `120/120 block
hash sets matched`; no se sustituyó ni redibujó ninguna realización.

La envolvente fija se construyó una sola vez sobre los 120 tiempos del padre.
Se verificaron `peak_index=3`, `time[3]=60 s`, `envelope[3]=0,5`,
`rise_tau=11,2 s` y `decay_tau=84 s`. A partir de cada bloque se formaron un
padre nulo y dos padres positivos de 50 y 80 s. Los 360 padres fueron finitos y
válidos, con 360 hashes de flujo
distintos.

Las 54 condiciones y las semillas 0–39 produjeron exactamente 2.160 hijos: 720
nulos y 1.440 positivos. Cada hijo se obtuvo mediante el prefijo contiguo del
padre y los 2.160 hashes de prefijo coincidieron byte a byte. No se recentró,
reescaló ni reestandarizó ruido alguno. Como era previsible en prefijos de una
realización normalizada solamente a N=120, la media observada del ruido hijo
abarcó `-0.0074908022646548288` a `0.0090755850357969754` y su desviación
muestral abarcó `0.0010569131788239841` a
`0.0076281533999288534`; no se exigió que fuese 0,005 en cada ventana.

La generación completa se repitió en orden normativo, inverso y aleatorio de
test. Las discrepancias fueron cero para los 120 bloques, 360 padres y 2.160
hijos en ambas comparaciones de orden. La implementación de referencia,
separada de las funciones de construcción de envolvente, señal y prefijo,
coincidió exactamente en las 90 comparaciones predeclaradas.

La estructura de medidas repetidas también quedó preservada: cada bloque tiene
tres padres y 18 hijos, todos comparten ruido, fase y metadatos de semilla; cada
padre contiene las seis ventanas anidadas N15⊂N30⊂N45⊂N60⊂N90⊂N120. Se
confirmaron 240 trayectorias positivas y 1.200 transiciones adyacentes.

No se ejecutó AFINO, no se analizaron resultados de selección y no se
persistieron los arrays completos del benchmark. Solo se guardaron scripts,
manifiestos, auditoría e informe.

## Conclusión

`NESTED_GENERATOR_VALIDATED`
