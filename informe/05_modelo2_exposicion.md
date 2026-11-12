# 5. Modelo 2: exposición (−3, −1, 0, +1, +3)

> **Resumen.** El modelo 2 traduce la probabilidad del modelo 1 en una de las cinco exposiciones permitidas. Lo hace en dos pasos: primero, la **confianza** del modelo 1 (comparada con la de los últimos 250 días) decide si operar y si hacerlo con tamaño 1 o 3; después, un **GARCH(1,1)** pronostica la volatilidad del día siguiente y, si es anormalmente alta, recorta las apuestas fuertes. Los umbrales se eligieron en desarrollo con el sistema base: no operar bajo el percentil 60 de confianza, exposición 1 entre los percentiles 60 y 80, y exposición 3 sobre el percentil 80; recortar de 3 a 1 cuando la volatilidad relativa supera 1,5. **El sistema adaptativo usa el mismo modelo 2 sin reelegir nada**, para que el cambio de sistema se limite al modelo 1.

---

## 5.1 Por qué un segundo modelo

Las bases premian “discriminar cuándo tomar posición y cuándo abstenerse”, no acertar más veces. La sección 2 mostró que:

- la señal de dirección es débil en promedio, pero **más fuerte en los días de mayor confianza** del modelo 1;
- la volatilidad **no predice la dirección**, pero sí el tamaño del movimiento (sección 2.6).

Separar estas dos tareas es lo que en la literatura se llama **meta-labeling** (López de Prado, 2018): un modelo decide el lado de la apuesta y otro decide si apostar y cuánto.

---

## 5.2 Paso 1 · Tamaño según la confianza

Para cada día:

1. Se calcula la confianza del modelo 1: \|*p* − 0,5\|.
2. Se compara con la confianza de los **250 días hábiles anteriores** y se obtiene su **percentil** (0,9 = más confiado que el 90% de los días recientes).
3. Se asigna el tamaño base:

| Percentil de confianza | Tamaño |
|---|---|
| Menor que *u₁* | 0 (no operar) |
| Entre *u₁* y *u₃* | 1 |
| Mayor o igual a *u₃* | 3 |

4. El signo lo da el modelo 1: positivo si *p* > 0,5 (comprar dólar), negativo si *p* < 0,5 (vender).

**Por qué un percentil y no la probabilidad directa.** La escala de la confianza cambia entre reajustes del modelo 1. El percentil móvil la hace comparable en el tiempo y solo usa información pasada, así que se puede aplicar en vivo.

### Umbrales elegidos

Buscamos en una grilla fijada antes de ver resultados (*u₁* ∈ {0,4; 0,6; 0,8}, *u₃* ∈ {0,8; 0,9; 0,95; nunca}) y elegimos la combinación con mayor retorno neto de 1 pb en la parte 2 del desarrollo (2015-2021, sección 3.2):

| Modelo | *u₁* (operar) | *u₃* (tamaño 3) | Días que opera (aprox.) |
|---|---|---|---|
| Sistema base (donde se eligieron) | 0,6 | 0,8 | 40% más confiado |
| **Sistema adaptativo (heredados)** | **0,6** | **0,8** | **40% más confiado** |

Con el adaptativo, el sistema queda fuera del mercado entre el 58% y el 65% de los días según el tramo, y usa el tamaño 3 entre el 15% y el 20% (sección 6.2). Los componentes sueltos que se reportan como control (LSTM solo, logística sola) usan los mismos umbrales.

---

## 5.3 Paso 2 · Ajuste por volatilidad con GARCH(1,1)

### El pronóstico

Un **GARCH(1,1)** pronostica la varianza del retorno del día siguiente:

$$\sigma^2_{t+1} = \omega + \alpha\, r_t^2 + \beta\, \sigma^2_t$$

- Se estima con los **últimos 1.000 retornos** y se reestima cada **21 días**.
- Entre reestimaciones, la varianza se actualiza día a día con los parámetros vigentes.
- Usa solo retornos hasta *t*.

Con la volatilidad pronosticada se calcula la **volatilidad relativa**: σ del día dividida por la mediana de σ de los 250 días anteriores. Vale ~1 en un día normal y más de 1 en días agitados. Usamos la volatilidad relativa porque el nivel de volatilidad del peso cambió de régimen desde 2022, y un umbral fijo en nivel habría dejado de discriminar.

### Por qué GARCH(1,1)

| Alternativa | Lo que encontramos |
|---|---|
| GARCH(1,1) | Persistencia α + β ≈ 0,98 (α 0,07; β 0,91). Volatilidad pronosticada media 10,7% vs realizada 11,1% en desarrollo; 15,6% vs 16,4% en validación. Calibración por deciles cerca de la diagonal. |
| EWMA (RiskMetrics, λ = 0,94) | Prácticamente igual (pérdida QLIKE +0,02% en desarrollo). |
| GJR-GARCH (asimétrico) | Las depreciaciones del peso sí suben más la volatilidad, pero modelarlo no mejora el pronóstico. |
| HAR con volatilidad implícita | Algo mejor, sin diferencia significativa. |

Es consistente con la literatura: con datos diarios, es difícil superar a un GARCH(1,1) (Hansen y Lunde, 2005).

### La regla

Probamos variantes fijadas antes de ver resultados y elegimos en desarrollo con el sistema base. Se eligió un **tope**, que el adaptativo hereda:

| Volatilidad relativa | Ajuste |
|---|---|
| ≤ 1,5 | Sin cambio |
| > 1,5 | Una exposición de 3 baja a 1 |

**Por qué un tope y no escalar todo por volatilidad.** En monedas, ajustar el tamaño por volatilidad casi no mejora el Sharpe, pero sí reduce las pérdidas extremas (Harvey et al., 2018). El tope evita la apuesta más fuerte justo en los días más riesgosos, sin intervenir el resto del tiempo.

---

## 5.4 La decisión completa de un día

```
p del modelo 1 ──► dirección = signo(p − 0,5)
      │
      └──► confianza |p − 0,5| ──► percentil vs 250 días previos ──► tamaño 0 / 1 / 3
                                                                          │
retornos hasta t ──► GARCH(1,1) ──► σ(t+1) / mediana 250 días ──► si > 1,5: 3 → 1
                                                                          │
                                         exposición = dirección × tamaño ∈ {−3, −1, 0, +1, +3}
```

**Resultado diario:**

$$\text{resultado}_t = e_t \times \text{retorno neto de carry}_{t \to t+1} - c \times |e_t - e_{t-1}|$$

donde *c* es el costo por unidad de cambio de exposición. Elegimos con *c* = 1 pb, un supuesto propio, y reportamos 0, 1 y 2 pb. El costo exacto lo aplica el código de evaluación del laboratorio.

---

## 5.5 Advertencias

- **El tope está en el borde de la grilla** (1,5 es el valor menos intervencionista probado) y actúa pocos días, casi siempre en episodios de crisis. En el adaptativo cambió 97 días en 2005-2014 (sobre todo en 2008), 20 en 2015-2021, 16 en validación (julio a octubre de 2022) y 3 en el test (marzo-abril de 2026). En todos los tramos sumó resultado. En 2005-2014 redujo la máxima caída de −36,7% a −15,8%.
- **Casi toda la ganancia viene de los días con exposición 3.** En el adaptativo, los días con ±1 aportan algo en 2005-2024 (13-26% del resultado), pero pierden en el test. Maximizar el retorno empuja hacia el tamaño 3, que es el que más amplifica también la suerte (sección 7).
- **Exposición 0 vale 0** según la fórmula de las bases (sin carry). Si el laboratorio abona la tasa en pesos a la posición fuera del mercado, cambiaría la comparación.
- **Umbrales elegidos para otro modelo 1.** Los cortes 0,6 / 0,8 se eligieron con las probabilidades del sistema base. No los reoptimizamos para el adaptativo, para no sumar otra elección hecha con el test a la vista.
- **Señal en vivo:** se envía la exposición del sistema adaptativo. La del sistema base se calcula en paralelo, solo como diagnóstico.

### Referencias

- Bollerslev, T. (1986). Generalized autoregressive conditional heteroskedasticity. *Journal of Econometrics*, 31(3), 307-327.
- Hansen, P. y Lunde, A. (2005). A forecast comparison of volatility models: does anything beat a GARCH(1,1)? *Journal of Applied Econometrics*, 20(7), 873-889.
- Harvey, C., Hoyle, E., Korgaonkar, R., Rattray, S., Sargaison, M. y Van Hemert, O. (2018). The impact of volatility targeting. *Journal of Portfolio Management*, 45(1), 14-33.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
