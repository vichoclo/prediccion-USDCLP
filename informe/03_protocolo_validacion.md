# 3. Protocolo de validación

> **Resumen.** Dividimos la historia en tramos con funciones fijas: **desarrollo** para estimar y elegir, **validación** para comparar una vez y **test** para la evaluación final. Todos los modelos se reestiman en el tiempo con ventana creciente (*walk-forward*), usando solo el pasado, con un **embargo** entre entrenamiento y predicción. Cada decisión de diseño se tomó en desarrollo, y contamos las configuraciones probadas para corregir los resultados por pruebas múltiples.

---

## 3.1 Por qué importa el protocolo

Con señales tan pequeñas como las de la sección 2, es fácil encontrar una estrategia que parece rentable solo porque se ajustó al ruido del periodo con que se evalúa. El protocolo existe para que el resultado que reportamos sea lo más parecido posible a lo que la estrategia habría obtenido en tiempo real. Sigue tres reglas:

1. **Cada dato tiene un solo uso.** Un tramo que sirvió para elegir algo ya no sirve para evaluarlo.
2. **Nunca se usa información posterior al día de la decisión**, ni en las variables ni en el ajuste de los modelos (sección 1.2).
3. **Toda configuración probada se cuenta.** Elegir la mejor de muchas infla el resultado; el Sharpe deflactado (sección 6) lo corrige.

---

## 3.2 Tramos

| Tramo | Fechas | Para qué se usa |
|---|---|---|
| Calentamiento | 2001-08 → 2001-11 | Llenar ventanas móviles (momentum de 20 días, volatilidad). No se predice. |
| Entrenamiento inicial | 2001-12 → 2004-12 | Primer ajuste de los modelos. No se predice. |
| **Desarrollo, parte 1** | 2005-01 → 2014-12 | Predicciones fuera de muestra del modelo 1. Sirven para revisar que el modelo se comporte de forma estable y como historia para los percentiles del modelo 2. **No se elige nada aquí.** |
| **Desarrollo, parte 2** | 2015-01 → 2021-12 | Predicciones fuera de muestra con las que se **eligen** las variables del modelo 1, los umbrales del modelo 2 y la variante del GARCH. |
| **Validación** | 2022-01 → 2024-12 | **Comparar** las configuraciones ya elegidas. No se usa para ajustar nada. |
| **Test** | 2025-01 → último dato | Evaluación final. El código no lo predice salvo que se active `TOCAR_TEST = True`. |

La columna `periodo` de la base tratada marca a qué tramo pertenece cada día (en ella, “desarrollo” abarca las dos partes).

**Por qué las elecciones se hacen solo con 2015-2021 y no con todo el desarrollo:**

1. **Las variables se eligieron antes de extender la base a 2001.** El filtro de variables (sección 2.8) se corrió sobre la base que partía en 2010. Con una ventana de 1.000 días para estimar cada modelo univariado, las primeras predicciones fuera de muestra aparecen recién hacia 2014. El primer año completo disponible para elegir era 2015.
2. **El modelo 2 necesita historia del modelo 1.** Los umbrales se expresan como percentiles de la confianza de los 250 días anteriores, y el GARCH usa 1.000 retornos. Con 2005-2014 como antecedente, en 2015-2021 todas esas ventanas ya están completas.
3. **Lo reciente se parece más a lo que viene.** La sección 2.4 mostró que las relaciones entre variables cambiaron con el tiempo. Elegir con 2015-2021 es elegir con el periodo más parecido a validación y test.

La parte 1 (2005-2014) no se usó para ninguna elección, así que funciona como un control adicional: si un modelo rinde bien en 2015-2021 pero mal en 2005-2014, es una señal de que se ajustó a un periodo particular.

**Por qué validación son tres años:** con un acierto de 54% y ~250 días por año, hacen falta unos 600 días para que la diferencia contra 50% sea significativa al 5%. Un tramo más corto no permitiría distinguir señal de azar.

---

## 3.3 Walk-forward

Ningún modelo se estima una sola vez con toda la muestra. Se reestima periódicamente usando solo los días anteriores al momento de la predicción:

```
          entrenamiento (todo lo anterior)      embargo   predicción
  2001 ─────────────────────────────────────── │ 5 días │ 126 días ──►
  2001 ──────────────────────────────────────────────────── │ 5 │ 126 ──►
  ...
```

| Parámetro | Modelo 1 (LSTM y logística) | Modelo 2 (GARCH) |
|---|---|---|
| Ventana | Expansiva (todo el pasado disponible) | Móvil, últimos 1.000 días |
| Reajuste | Cada 126 días hábiles (~6 meses) | Cada 21 días hábiles (~1 mes) |
| Mínimo para el primer ajuste | 750 observaciones | 1.000 retornos |
| Embargo | 5 días | No aplica (usa retornos hasta *t*) |

**Embargo.** Entre el último día de entrenamiento y el primero de predicción dejamos 5 días sin usar. El objetivo mira a *t+1*, así que un día bastaría; los 5 días son un margen conservador contra cualquier dependencia de corto plazo entre el final del entrenamiento y el inicio de la predicción (López de Prado, 2018, cap. 7).

**Escalado dentro de la ventana.** La winsorización (percentiles 1 y 99) y la estandarización se calculan **solo con los datos de entrenamiento** de cada reajuste y luego se aplican a los días que se predicen. Un dato faltante se reemplaza por 0, que equivale a la media de entrenamiento.

**Percentiles y volatilidad relativa.** En el modelo 2, la confianza de cada día se compara con la de los **250 días anteriores**, y la volatilidad relativa usa la mediana de los 250 días anteriores (rezagada un día). Ningún umbral se calcula con el tramo completo.

---

## 3.4 Validación interna del LSTM

El LSTM necesita decidir cuándo dejar de entrenar y cómo convertir su salida en una probabilidad. Para eso reservamos, dentro de cada ventana de entrenamiento, el **último 15%** como validación interna:

- **Early stopping:** se detiene el entrenamiento cuando la pérdida en la validación interna deja de mejorar por 8 épocas. Nunca se usa la pérdida de entrenamiento.
- **Calibración de Platt:** la salida de la red se transforma en probabilidad con una logística ajustada en esa misma validación interna.
- **Hueco de *L* días** entre el entrenamiento y la validación interna, porque cada secuencia mira 20 días hacia atrás.

---

## 3.5 Cómo se eligió cada cosa

| Decisión | Dónde se tomó | Criterio |
|---|---|---|
| Variables del modelo 1 | Desarrollo, parte 2 (2015-2021) | Estabilidad del signo y mejora de log-loss (sección 2.8) |
| Arquitectura del LSTM (16 unidades, dropout 0,2, 20 días) | Fijada antes de ver resultados | Red pequeña, por el tamaño de la muestra |
| Regularización de la logística (C = 0,05) | Fijada antes de ver resultados | — |
| Umbrales de confianza del modelo 2 | Desarrollo, parte 2 (2015-2021) | Retorno neto de 1 pb (criterio de las bases) |
| Variante del GARCH | Desarrollo, parte 2 (2015-2021) | Retorno neto de 1 pb |
| Señales candidatas | Validación 2022-2024 | Ver sección 4.4 |

---

## 3.6 Pruebas contra fugas de información

Para verificar que el walk-forward no usa información futura aplicamos dos pruebas automáticas:

| Prueba | Qué hace | Resultado |
|---|---|---|
| **Truncamiento** | Corta los datos en una fecha, vuelve a correr todo y compara las predicciones hasta esa fecha con las de la corrida completa. Si algo usara el futuro, cambiarían. | Logística, LSTM y GARCH: predicciones idénticas (diferencias ≤ 5·10⁻⁷, redondeo). |
| **Etiqueta barajada** | Desordena el objetivo y repite todo el proceso. Sin relación real, el sistema no debería encontrar señal. | LSTM: acierto en el quintil de mayor confianza de 45-50%, sin mejora de log-loss. Sistema completo: el resultado real supera a las 30 permutaciones. |

---

## 3.7 Limitaciones del protocolo

- **Validación se miró más de una vez.** Se usó para comparar señales y, en el caso del LSTM, para reincorporarlo tras un primer descarte (sección 4.4). Por eso su resultado está algo inflado.
- **El test también se consultó** en análisis exploratorios anteriores (sección 2.8). No se usó para elegir el sistema final, pero no es un tramo completamente virgen. La única evaluación sin ninguna contaminación es el **monitoreo en vivo**.
- **La selección de variables no se repite dentro del walk-forward**: las variables se eligieron una vez con la parte 2 del desarrollo (2015-2021). Ese tramo es, respecto de esa elección, dentro de muestra; la parte 1 (2005-2014) no.
- **Número de configuraciones:** llevamos registradas unas 310 en todo el proyecto. Es el *N* que usamos para el Sharpe deflactado.

### Referencias

- Bailey, D. y López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management*, 40(5), 94-107.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
