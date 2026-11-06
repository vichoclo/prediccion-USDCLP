# 8. Modelos probados y descartados

> **Resumen.** Antes de llegar al sistema final probamos una docena de líneas de trabajo: fundamentos macroeconómicos (regla de Taylor), árboles de decisión, búsqueda exhaustiva de variables, horizontes de varios días, aprendizaje por refuerzo, ensambles y varias formas de dimensionar la exposición. El patrón se repitió en casi todas: **más flexibilidad o más variables mejoraban el ajuste en desarrollo y empeoraban fuera de él**. Lo reportamos porque explica las decisiones del sistema final y porque cada prueba cuenta para el Sharpe deflactado (~310 configuraciones en total).

Todas las cifras de esta sección provienen de desarrollo o validación.

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

## 8.3 Lo que aprendimos

1. **La flexibilidad no paga con esta razón señal/ruido.** Árboles, redes recurrentes con más contexto y aprendizaje por refuerzo mejoran el ajuste y empeoran fuera de muestra. Por eso los componentes del sistema final son pequeños: una logística regularizada y un LSTM de 16 unidades.
2. **Lo que funciona en un periodo no anticipa el siguiente** cuando se elige entre muchas opciones. La búsqueda de combinaciones lo mostró de forma directa.
3. **Un buen resultado en validación no basta.** Varias líneas (XGBoost, aprendizaje por refuerzo, calendario) tuvieron validaciones atractivas que se explicaban por cómo se eligieron, no por la señal.
4. **Contar las pruebas es parte del resultado.** Las ~310 configuraciones de esta sección son el *N* del Sharpe deflactado de la sección 6.

### Referencias

- Ince, O., Molodtsova, T. y Papell, D. (2016). Taylor rule deviations and out-of-sample exchange rate predictability. *Journal of International Money and Finance*, 69, 22-44.
- Molodtsova, T. y Papell, D. (2009). Out-of-sample exchange rate predictability with Taylor rule fundamentals. *Journal of International Economics*, 77(2), 167-180.
- Schulman, J., Wolski, F., Dhariwal, P., Radford, A. y Klimov, O. (2017). Proximal policy optimization algorithms. arXiv:1707.06347.
