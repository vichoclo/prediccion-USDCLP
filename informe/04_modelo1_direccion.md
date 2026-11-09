# 4. Modelo 1: dirección

> **Resumen.** El modelo 1 estima, para cada día, la probabilidad *p* de que mañana convenga estar comprado en dólares (que el dólar suba más que el carry). Es un **modelo híbrido**: el promedio simple de dos componentes, una red **LSTM** que mira los últimos 20 días y una **regresión logística** con las mismas 11 variables. Esa probabilidad promedio es la que alimenta el modelo 2. La logística entrega las probabilidades mejor calibradas y el LSTM ordena los días de mayor confianza de una forma distinta. Combinarlos reduce la dependencia de un solo modelo sin estimar ningún parámetro adicional. Los dos componentes se reportan también por separado, como controles.

---

## 4.1 Qué predice

| Elemento | Definición |
|---|---|
| Objetivo | `y_sube_neto`: 1 si el retorno del dólar de *t* a *t+1* supera al carry (conviene estar comprado), 0 si no (conviene estar vendido). |
| Salida | Probabilidad *p* entre 0 y 1. |
| Dirección | Comprar si *p* > 0,5; vender si *p* < 0,5. |
| Confianza | \|*p* − 0,5\|: cuánto se aleja la probabilidad del empate. La usa el modelo 2. |
| Variables | Las 11 de la sección 2.8, con datos desde 2001. |

Usamos el retorno **neto de carry** porque es lo que realmente gana una posición: con carry positivo, el dólar tiene que subir más que el diferencial de tasas para que convenga estar comprado.

La función de pérdida es la **entropía cruzada binaria** (log-loss), que premia las probabilidades bien calibradas y no solo acertar la dirección. Las bases del torneo premian explícitamente la calibración.

---

## 4.2 El modelo híbrido y sus dos componentes

### Componente A · LSTM (20 días)

Una red recurrente **LSTM** recibe, para cada día, la secuencia de las 11 variables de los últimos 20 días y devuelve una probabilidad.

| Componente | Valor | Por qué |
|---|---|---|
| Capas | 1 capa LSTM + 1 capa lineal de salida | Con ~5.000 días de datos y ruido alto, una red grande se sobreajusta. |
| Unidades | 16 | Ídem. |
| Ventana de secuencia | 20 días hábiles (~1 mes) | Permite capturar dinámica reciente sin pedir demasiada historia. |
| Regularización | Dropout 0,2; *weight decay* 10⁻³; *clipping* del gradiente en 1 | Contra el sobreajuste. |
| Optimización | Adam, tasa 10⁻³, lotes de 128, máx. 60 épocas, *early stopping* con paciencia 8 | Sección 3.4. |
| Calibración | Platt en la validación interna | Convierte la salida en una probabilidad interpretable. |
| Semillas | 5 redes por reajuste; *p* = promedio | La inicialización aleatoria mueve el acierto hasta ~5 puntos; promediar reduce esa variabilidad. |

**Por qué una LSTM.** Es una arquitectura diseñada para series de tiempo: mantiene una “memoria” que le permite reconocer patrones en la secuencia reciente de las variables (por ejemplo, varios días seguidos de debilidad del rand) que un modelo de un solo día no ve.

### Componente B · Regresión logística

Una logística con las mismas 11 variables del día *t* (sin secuencia), con regularización L2 (C = 0,05). Es el modelo más simple que entrega una probabilidad, y la referencia contra la que se mide si el LSTM aporta algo.

### Modelo final · Promedio de ambos componentes

La probabilidad que usa el sistema es el promedio simple de las probabilidades del LSTM y de la logística:

$$p_{\text{promedio}} = \tfrac{1}{2}\,(p_{\text{LSTM}} + p_{\text{logística}})$$

En la literatura de pronósticos, combinar modelos con pesos iguales suele superar a elegir el mejor, porque los errores de cada uno se compensan en parte (Timmermann, 2006). No requiere estimar pesos, así que no agrega riesgo de sobreajuste. Además, compensa la principal debilidad de cada componente: la logística ve solo el día *t*, y el LSTM depende de la inicialización aleatoria.

---

## 4.3 Calidad de las probabilidades

Medimos dos cosas: si la probabilidad es mejor que la frecuencia base (mejora de log-loss) y si los días de mayor confianza aciertan más (acierto en el quintil superior, Q5).

| Modelo | Mejora de log-loss ×1000, validación | Acierto Q5 desarrollo, parte 2 (2015-21) | Acierto Q5 validación | Retorno medio Q5 validación (pb/día) |
|---|---|---|---|---|
| **Modelo final: promedio LSTM + logística** | **+3,8** | **56,2%** | **60,4%** | **+14,3** |
| Componente: LSTM 20 días | +1,4 | 54,1% | 53,7% | +7,1 |
| Componente: logística | +5,3 | 55,2% | 61,7% | +15,6 |
| Control: LSTM de 1 día | +3,6 | 50,0% | 58,4% | +7,2 |

Retorno medio con exposición 1 en la dirección del modelo, sin costos.

**Lectura:**

- **La logística es la mejor calibrada** (mayor mejora de log-loss) y la que más acierta en sus días de mayor confianza.
- **El LSTM con secuencia no supera al LSTM de un solo día en calibración**: mirar 20 días hacia atrás no mejora la probabilidad promedio. Coincide con la sección 2.3, donde la dinámica pasada no mostró signo estable.
- **Pero el LSTM ordena distinto los días.** Operando solo el 40% de días con mayor confianza (percentil móvil), el LSTM gana +35,8% en validación frente a +19,5% de la logística. Esa diferencia en el ordenamiento es lo que justifica mantenerlo como señal y combinarlo.
- **El promedio queda entre ambos componentes en calibración y cerca de la logística en los días de mayor confianza**, y es el que más acierta en Q5 en la parte 2 del desarrollo. En la parte 1 del desarrollo (2005-2014), que no se usó para elegir, también mejora a la frecuencia base (+1,7 ×1000), mientras el LSTM solo no lo hace (sección 6.3).
- **La semilla importa.** Con una sola red, el acierto en Q5 del LSTM varía entre 49,7% y 54,4% según la semilla; por eso promediamos 5.

---

## 4.4 Cómo llegamos al modelo híbrido

Lo dejamos explícito porque afecta la lectura de los resultados.

1. **Regla fijada antes de ver resultados:** el LSTM de 20 días se descartaba si, en validación, su acierto en el quintil de mayor confianza no superaba al de la logística y al del LSTM de 1 día. **No pasó la regla** (53,7% contra 61,7% y 58,4%).
2. **Revisión por retorno:** como el criterio del torneo es el valor económico y no el acierto, revisamos el retorno operando los días de mayor confianza. Ahí el LSTM sí destacaba (+35,8% vs +19,5% en el 40% superior), aunque la diferencia con la logística no es significativa (bootstrap: P = 0,23) y depende del corte (en el 20% superior gana la logística: +28,0% vs +4,0%).
3. **Mantener el LSTM como componente:** se conservó el LSTM junto con la logística y su promedio, y se eligieron los umbrales del modelo 2 de cada uno en desarrollo.
4. **Elección del modelo final:** usamos el **promedio** como sistema. La razón es de principio y no de rendimiento: combinar dos modelos con pesos iguales diversifica el riesgo de modelo (Timmermann, 2006) sin estimar nada adicional.

La evidencia de los tramos es consistente con esa elección, pero no la decide. En validación, el promedio y la logística sola quedan prácticamente empatados (Sharpe 1,16 contra 1,15). La logística sola rindió más en la parte 1 del desarrollo (+126% contra +82%) y calibra mejor. A favor del promedio, es el único de los tres que supera a operar siempre ±1 al 5% tanto en la parte 1 del desarrollo como en validación (sección 6.3).

Estos pasos usaron la validación más de una vez, así que sus resultados deben leerse como optimistas (sección 3.7).

---

## 4.5 Versiones descartadas

| Versión | Por qué se descartó |
|---|---|
| Versión “completa” (15 variables, datos desde 2010) | Menos historia; el LSTM empeora la log-loss en validación (−0,8). |
| LSTM de 1 día | Control para medir si la secuencia aporta. Bien calibrado, pero sin ventaja al operar. |
| LSTM solo o logística sola como modelo final | No se descartaron: son los componentes del modelo híbrido y se reportan como controles en las secciones 6 y 7. |
| Otros modelos (Taylor, XGBoost, aprendizaje por refuerzo y otros) | Sección 8. |

### Referencias

- Hochreiter, S. y Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.
- Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. *Advances in Large Margin Classifiers*, 61-74.
- Timmermann, A. (2006). Forecast combinations. En *Handbook of Economic Forecasting*, vol. 1, 135-196. Elsevier.
