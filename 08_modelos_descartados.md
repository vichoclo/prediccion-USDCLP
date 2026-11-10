# 8. Modelos probados y descartados

> **Resumen.** Antes de llegar al sistema final probamos una docena de líneas de trabajo: fundamentos macroeconómicos (regla de Taylor), árboles de decisión, búsqueda exhaustiva de variables, horizontes de varios días, aprendizaje por refuerzo, ensambles y varias formas de dimensionar la exposición. El patrón se repitió en casi todas: **más flexibilidad o más variables mejoraban el ajuste en desarrollo y empeoraban fuera de él**. La excepción fue adaptar el modelo 1 al pasado reciente, que resultó útil cuando las relaciones cambiaron en 2025-2026 (sección 8.3). Lo reportamos porque explica las decisiones del sistema final y porque cada prueba cuenta para el Sharpe deflactado (~349 configuraciones en total).

Las cifras de las secciones 8.1 y 8.2 provienen de desarrollo o validación; las de 8.3 incluyen el test 2025-2026 (salvo las señales técnicas), porque esas pruebas se hicieron después de ver ese tramo. El sistema base y los componentes sueltos del adaptativo no aparecen aquí como descartados: son los controles de las secciones 6 y 7.

---

## 8.1 Modelo 1 (dirección)

| Línea | Qué probamos | Resultado | Por qué se descartó |
|---|---|---|---|
| **Regla de Taylor** (Molodtsova y Papell, 2009; Ince, Molodtsova y Papell, 2016) | Diferencias de inflación, brecha de producto y tasas entre Chile y EE.UU.; 10 especificaciones × 3 ventanas × 3 bases (90 configuraciones). También una réplica mensual fiel del paper. | Ninguna especificación de Taylor pura supera al paseo aleatorio (Clark-West negativo en las 63 combinaciones); R² fuera de muestra negativo. Tampoco hay predictibilidad a un mes. | Los fundamentos se mueven demasiado lento para un horizonte de un día. La señal de esa ronda venía de las variables de mercado, no de Taylor. |
| **Combinación por bloques** (una logística por variable, un voto por bloque) | 88 variables clasificadas por bloque económico y signo teórico; filtro de estabilidad del signo. | Validación: mejora de log-loss +1,09 ×1000 y +39% con 1 pb. | No se descartó del todo: **de aquí salen las variables del sistema final**. La logística núcleo con más historia (desde 2001) la superó en validación (+5,29). |
| **XGBoost con indicadores técnicos** (RSI, medias móviles, Bollinger, MACD) | Esqueleto de un repositorio público, adaptado al USD/CLP. | Probabilidades peores que la frecuencia base en todas las versiones (log-loss −74 ×1000 en validación). | Los indicadores son transformaciones del precio pasado, que no tiene señal a un día (sección 2.3). Consistente con la literatura sobre data snooping en reglas técnicas. |
| **XGBoost sobre las variables del bloque** | Mismas variables que la combinación por bloques, árboles de profundidad 1 a 3. | Desarrollo: +5,84 (mejor que bloques); validación: −1,93 (peor). | Sobreajuste: gana en el tramo donde se eligió y pierde fuera. Elegía siempre profundidad 1, es decir, no encontraba interacciones útiles. |
| **Búsqueda exhaustiva de combinaciones** | Las 131.071 combinaciones posibles de 17 variables. | La correlación entre el desempeño de cada combinación en desarrollo y en validación fue −0,07. | Elegir la “mejor” combinación es elegir ruido (sección 2.8). |
| **Selección de variables solo con datos** | 75 candidatas, eliminación de redundantes, L1 con selección por estabilidad. | Validación: +3,5 a +4,0 de log-loss, frente a +8,0 con filtro previo. | Sin un filtro previo, la selección encuentra variables inestables. El filtro funciona como regularización. |
| **Probit** en vez de logística | Mismas variables y protocolo. | Correlación de probabilidades 1,0000; diferencias de log-loss < 0,05. | Equivalente a la logística, sin regularización disponible. |
| **Variantes de la logística** (calibración Platt, ponderación por recencia, etc.) | 9 variantes. | Ninguna supera a la logística original en desarrollo ni en validación; la calibración Platt es la que más daña. | Sin mejora. |
| **Rezagos explícitos y retorno propio del peso** (versión estricta) | 7 configuraciones con hasta 31 variables, L2 y Elastic Net. | Ninguna mejora el log-loss en desarrollo; el acierto en el quintil superior cae a ~50%. | Más variables empeoran de forma monótona. |
| **LSTM de 1 día y LSTM con 15 variables** | Controles del LSTM final. | El LSTM de 1 día está bien calibrado pero sin ventaja al operar; la versión de 15 variables empeora la log-loss en validación (−0,8). | Sección 4.5. |
| **Horizonte de varios días** (10 y 21 días) | 22 variantes con variables de tendencia, fundamentos y riesgo. | Mejora de log-loss negativa en todos los casos; la elegida en desarrollo perdió −47,5% en validación con 3 pb. | Las correlaciones a horizontes largos dependen de pocos episodios (2008, 2020). |
| **Ensamble XGBoost + LightGBM con abstención** | Walk-forward mensual, 18 configuraciones. | Validación: log-loss +0,11% sobre el ingenuo; +21,5% (Sharpe 0,59). | Inferior a la logística núcleo en todas las métricas. |
| **Aprendizaje por refuerzo (PPO)** | Agente que elige directamente la exposición; 8 versiones, hasta 10 semillas cada una. | Dentro de muestra: Sharpe 7,5 y acierto 74% (memorización). En validación, los Sharpe de los distintos checkpoints van de −2,5 a +1,0 y cambian mucho entre checkpoints vecinos. | Memoriza el entrenamiento, incluido el cierre asincrónico, y su resultado depende de la semilla. No es defendible ante un jurado. |

---

## 8.2 Modelo 2 (exposición)

| Línea | Qué probamos | Resultado | Decisión |
|---|---|---|---|
| **Tamaño solo por volatilidad**, independiente del modelo 1 | Escalar la exposición por la volatilidad pronosticada. | Sharpe 0,31, frente a 0,45 filtrando por la confianza del modelo 1. | La volatilidad sirve para recortar, no para decidir cuándo operar (sección 5.1). |
| **Otros modelos de volatilidad** (EWMA, GJR-GARCH, HAR, HAR con volatilidad implícita) | Pronóstico de la varianza del día siguiente. | Ninguno supera significativamente a GARCH(1,1). | Se mantuvo GARCH(1,1) (sección 5.3). |
| **Meta-labeling con logística** (P(acierta el modelo 1) según confianza y volatilidad) | Alternativa al percentil directo. | Discriminaba mejor en validación, pero se probó después de mirar otras variantes. | No se adoptó, para no elegir con validación. |
| **Ajuste parcial y reglas para bajar la rotación** | Suavizar la señal, exigir persistencia, umbrales por valor esperado. | Ninguna supera a la referencia en validación; varias terminan casi sin operar. | Sin mejora. |
| **Efecto día de la semana + GARCH** como estrategia complementaria | GARCH-t con un efecto por día, combinado con el sistema. | Validación: +177% (Sharpe 1,70). | **Descartado por sesgo de selección:** el efecto se descubrió mirando la muestra completa, incluido el tramo de validación, así que ese resultado no es independiente. Además, el efecto viernes podría ser un artefacto del horario de cierre (sección 2.5). |

---

## 8.3 Pruebas de noviembre de 2026

Después de la falla del sistema base en 2025-2026 y en octubre-noviembre probamos varias líneas. El diseño de cada una se fijó antes de correrla y el test se reporta como informativo. La excepción son las señales técnicas: esa prueba se hizo antes y no tocó el test.

| Línea | Qué probamos | Resultado | Decisión |
|---|---|---|---|
| **Pesos por correlación móvil** | Cada variable pondera por su correlación con el retorno del día siguiente en los últimos 21, 63, 126 o 250 días. | Pierde contra la base en desarrollo, validación y test (de −52% a −14% en el test). Su +10,7% en octubre-noviembre (ventana de 21 días) es una racha de 22 días. | Descartado: con 21 días, el error de una correlación (±0,22) supera a las correlaciones reales (0,05-0,15). |
| **Ventana móvil para la logística** | Entrenar solo con los últimos 250 o 500 días, cada 21 días. | 500 días: +150,9% en desarrollo, +116,7% en validación, +2,7% en el test (la base: +209,9%, +101,1%, −9,1%). | **Adoptado como componente del adaptativo** (sección 4.5). |
| **Retorno propio del peso** | Agregar el retorno del USD/CLP de *t* como variable, para captar la reversión de 2025-2026. | Igual a la base en todos los tramos. | Descartado: la logística ya tiene los retornos de los activos correlacionados. |
| **Combinaciones del sistema adaptativo** | LSTM y logística con ventana, peso exponencial o expansivos (6 combinaciones). | Tabla de la sección 4.5. El LSTM con solo 500 días se degrada (−5,7% en validación). | Adoptado: LSTM exponencial + logística de 500 días. |
| **IPSA en el adaptativo** | Agregar el retorno del IPSA. Después del último dato real (31-ago-2026) se rellena con su media de 20 días, porque el torneo no permite usar el IPSA posterior. | Mejora el Sharpe en desarrollo (0,79 → 1,02) y validación (0,80 → 1,14), sin significancia (t de Newey-West 1,4-1,5). No mejora el test, y cada componente por separado empeora. | Descartado: no concluyente, y con el IPSA congelado la variable no opina en vivo. |
| **Señales técnicas** (RSI, medias móviles, momentum, canales, Bollinger, MACD) | 19 señales del precio del USD/CLP, solas y agregadas a la base. | Ninguna regla sobrevive a Benjamini-Hochberg. Solas: +20,0% en validación (sin significancia). Agregadas a la base, empeoran los tres tramos (validación: +48,7% contra +101,1%). | Descartado. Consistente con la literatura sobre *data snooping* en reglas técnicas. |

---

## 8.4 Lo que aprendimos

1. **La flexibilidad no paga con esta razón señal/ruido.** Árboles, redes recurrentes con más contexto y aprendizaje por refuerzo mejoran el ajuste y empeoran fuera de muestra. Por eso los componentes del sistema final son pequeños: una logística regularizada y un LSTM de 16 unidades.
2. **Lo que funciona en un periodo no anticipa el siguiente** cuando se elige entre muchas opciones. La búsqueda de combinaciones lo mostró de forma directa.
3. **Un buen resultado en validación no basta.** Varias líneas (XGBoost, aprendizaje por refuerzo, calendario) tuvieron validaciones atractivas que se explicaban por cómo se eligieron, no por la señal.
4. **Contar las pruebas es parte del resultado.** Las ~349 configuraciones de esta sección son el *N* del Sharpe deflactado de la sección 6.
5. **Lo que sí ayudó fue adaptar el horizonte de aprendizaje, no agregar complejidad.** El cambio que protegió en 2025-2026 no fue un modelo más flexible, sino los mismos modelos pequeños aprendiendo de una historia más reciente (Pesaran y Timmermann, 2007).

### Referencias

- Hutchinson, M. et al. (2022). Technical trading rule profitability in currencies: It's all about momentum. *Research in International Business and Finance*, 63.

- Ince, O., Molodtsova, T. y Papell, D. (2016). Taylor rule deviations and out-of-sample exchange rate predictability. *Journal of International Money and Finance*, 69, 22-44.
- Molodtsova, T. y Papell, D. (2009). Out-of-sample exchange rate predictability with Taylor rule fundamentals. *Journal of International Economics*, 77(2), 167-180.
- Pesaran, M. H. y Timmermann, A. (2007). Selection of estimation window in the presence of breaks. *Journal of Econometrics*, 137(1), 134-161.
- Schulman, J., Wolski, F., Dhariwal, P., Radford, A. y Klimov, O. (2017). Proximal policy optimization algorithms. arXiv:1707.06347.
