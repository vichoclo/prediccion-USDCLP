# 3. Protocolo de validación

> **Resumen.** La historia se divide en tramos con funciones fijas: **desarrollo** para estimar y elegir, **validación** para comparar y **test** para la evaluación final. Todos los modelos se reestiman en el tiempo (*walk-forward*), solo con el pasado y con un **embargo** entre entrenamiento y predicción. El sistema adaptativo se reentrena cada 21 días y da más peso al pasado reciente.
>
> Hay una excepción importante al protocolo: **el sistema adaptativo se eligió después de ver la validación, el test y los datos reales de octubre-noviembre de 2026**. Con la regla fijada al inicio (elegir con 2015-2021) habría ganado el sistema base. Por eso, para el adaptativo, el test no es un tramo limpio. La evaluación sin contaminación es el monitoreo en vivo, con los parámetros congelados desde el 9 de noviembre de 2026.

---

## 3.1 Por qué importa el protocolo

Con señales tan pequeñas como las de la sección 2, es fácil encontrar una estrategia que parece rentable solo porque se ajustó al ruido del periodo con que se evalúa. El protocolo busca que el resultado reportado se parezca lo más posible a lo que la estrategia habría obtenido en tiempo real. Sigue tres reglas:

1. **Cada dato tiene un solo uso.** Un tramo que sirvió para elegir algo ya no sirve para evaluarlo.
2. **Nunca se usa información posterior al día de la decisión**, ni en las variables ni en el ajuste de los modelos (sección 1.2).
3. **Toda configuración probada se cuenta.** Elegir la mejor de muchas infla el resultado; el Sharpe deflactado (sección 6) lo corrige.

La sección 3.5 detalla dónde se rompió la primera regla.

---

## 3.2 Tramos

| Tramo | Fechas | Para qué se usó |
|---|---|---|
| Calentamiento | 2001-08 → 2001-11 | Llenar ventanas móviles (momentum de 20 días, volatilidad). No se predice. |
| Entrenamiento inicial | 2001-12 → 2004-12 | Primer ajuste de los modelos. No se predice. |
| **Desarrollo, parte 1** | 2005-01 → 2014-12 | Predicciones fuera de muestra. **No se eligió nada aquí**, ni para el sistema base ni para el adaptativo. El sistema completo opera desde febrero de 2006, cuando el GARCH y el percentil de confianza ya tienen la historia que necesitan. |
| **Desarrollo, parte 2** | 2015-01 → 2021-12 | Elegir las variables del modelo 1, los umbrales del modelo 2 y la variante del GARCH. |
| **Validación** | 2022-01 → 2024-12 | Comparar configuraciones. También se usó para reincorporar el LSTM (sección 4.5) y para elegir el adaptativo. |
| **Test** | 2025-01 → 2026-10-05 | Evaluación final del sistema base. Para el adaptativo, es parte del tramo con que se eligió. |
| **Datos reales** | 2026-10-06 → 2026-11-05 | 22 decisiones con la base actualizada que entregó el laboratorio. Motivaron la revisión del modelo 1. |
| **Monitoreo en vivo** | desde 2026-11-09 | La única evaluación sin contaminación del adaptativo. |

**Por qué las elecciones se hicieron con 2015-2021 y no con todo el desarrollo:**

1. **Las variables se eligieron antes de extender la base a 2001.** El filtro de variables (sección 2.8) se corrió sobre la base que partía en 2010. Con una ventana de 1.000 días para estimar cada modelo univariado, las primeras predicciones fuera de muestra aparecen recién hacia 2014. El primer año completo disponible para elegir era 2015.
2. **El modelo 2 necesita historia del modelo 1.** Los umbrales se expresan como percentiles de la confianza de los 250 días anteriores, y el GARCH usa 1.000 retornos.
3. **Lo reciente se parece más a lo que viene.**

La parte 1 (2005-2014) no se usó para ninguna elección, así que funciona como un control: si un modelo rinde bien en 2015-2021 pero mal en 2005-2014, es señal de que se ajustó a un periodo particular. **Ese tramo es hoy la evidencia más limpia a favor del sistema adaptativo** (sección 6).

---

## 3.3 Walk-forward

Ningún modelo se estima una sola vez con toda la muestra. Se reestima periódicamente usando solo los días anteriores al momento de la predicción:

```
          entrenamiento (pasado, con más peso en lo reciente)   embargo   predicción
  2001 ─────────────────────────────────────────────────────── │ 5 días │ 21 días ──►
  2001 ─────────────────────────────────────────────────────────────── │ 5 │ 21 ──►
  ...
```

| Parámetro | LSTM | Logística | GARCH (modelo 2) |
|---|---|---|---|
| Datos de entrenamiento | Todo el pasado, con peso exponencial: un día de hace 250 días hábiles (~1 año) pesa la mitad que el de ayer | Solo los últimos 500 días hábiles (~2 años), con igual peso | Últimos 1.000 retornos |
| Reajuste | Cada 21 días hábiles (~1 mes) | Cada 21 días hábiles | Cada 21 días hábiles |
| Mínimo para el primer ajuste | 750 observaciones | 750 observaciones | 1.000 retornos |
| Embargo | 5 días | 5 días | No aplica (usa retornos hasta *t*) |

En el **sistema base (control)**, el LSTM y la logística usan todo el pasado con el mismo peso y se reentrenan cada 126 días.

**Por qué dos formas distintas de “mirar lo reciente”.** La logística tiene 11 coeficientes y se estima bien con 500 días. El LSTM tiene unos 1.800 parámetros: con solo 500 días se degrada (pierde 5,7% en validación). Con peso exponencial conserva toda la historia para aprender la forma de la relación, y los datos recientes deciden el ajuste fino.

**Embargo.** Entre el último día de entrenamiento y el primero de predicción dejamos 5 días sin usar. El objetivo mira a *t+1*, así que un día bastaría; los 5 días son un margen conservador (López de Prado, 2018, cap. 7).

**Escalado dentro de la ventana.** La winsorización (percentiles 1 y 99) y la estandarización se calculan **solo con los datos de entrenamiento** de cada reajuste: los últimos 500 días para la logística, y toda la historia para el LSTM. Luego se aplican a los días que se predicen. Un dato faltante se reemplaza por 0, que equivale a la media de entrenamiento.

**Percentiles y volatilidad relativa.** En el modelo 2, la confianza de cada día se compara con la de los **250 días anteriores**, y la volatilidad relativa usa la mediana de los 250 días anteriores (rezagada un día). Ningún umbral se calcula con el tramo completo.

---

## 3.4 Validación interna del LSTM

Dentro de cada ventana de entrenamiento se reserva el **último 15%** (al menos 100 días) como validación interna:

- **Early stopping:** el entrenamiento se detiene cuando la pérdida en la validación interna deja de mejorar por 8 épocas.
- **Calibración de Platt:** la salida de la red se transforma en probabilidad con una logística ajustada en esa misma validación interna.
- **Hueco de 20 días** entre el entrenamiento y la validación interna, porque cada secuencia mira 20 días hacia atrás.
- **Los pesos exponenciales se aplican también aquí:** la pérdida de entrenamiento, la de validación y la calibración ponderan cada día por su peso.

---

## 3.5 Cómo se eligió cada cosa

| Decisión | Dónde se tomó | Criterio |
|---|---|---|
| Variables del modelo 1 | Desarrollo, parte 2 (2015-2021) | Estabilidad del signo y mejora de log-loss (sección 2.8) |
| Arquitectura del LSTM (16 unidades, dropout 0,2, 20 días) | Fijada antes de ver resultados | Red pequeña, por el tamaño de la muestra |
| Regularización de la logística (C = 0,05) | Fijada antes de ver resultados | — |
| Umbrales de confianza del modelo 2 (0,6 y 0,8) | Desarrollo, parte 2, con el sistema base | Retorno neto con 1 pb |
| Variante del GARCH (tope 1,5) | Desarrollo, parte 2, con el sistema base | Retorno neto con 1 pb |
| Reincorporar el LSTM y usar el promedio con la logística | Validación 2022-2024 | Sección 4.5 |
| Ventanas candidatas del modelo 1 adaptativo (250 y 500 días; correlaciones de 21 a 250 días) | Fijadas antes de correrlas | Sección 8.3 |
| **Sistema adaptativo como sistema oficial** (LSTM con vida media de 250 días + logística de 500 días, cada 21 días) | **Después de ver validación, test 2025-2026 y oct-nov 2026** | Robustez cuando las relaciones cambian (secciones 4.5 y 6) |

El modelo 2 del adaptativo **no se reeligió**: usa los mismos umbrales y el mismo tope del GARCH elegidos para el sistema base. Así el cambio se limita a cómo aprende el modelo 1.

**La regla fijada al inicio prefería el sistema base.** Con la elección en 2015-2021, el base gana: +284% contra +137% del adaptativo. Cambiamos de sistema por lo que vimos en 2025-2026 y en octubre-noviembre. Lo declaramos porque es la principal limitación de esta versión del informe.

---

## 3.6 Pruebas contra fugas de información

| Prueba | Qué hace | Resultado |
|---|---|---|
| **Truncamiento** | Corta los datos en una fecha, vuelve a correr todo y compara las predicciones hasta esa fecha con las de la corrida completa. Si algo usara el futuro, cambiarían. | Logística, LSTM y GARCH del sistema base: predicciones idénticas (diferencias ≤ 5·10⁻⁷, redondeo). El adaptativo se verificó recalculando su señal con la base cortada en cada fecha: coincide con el walk-forward (sección 9.4). |
| **Etiqueta barajada** | Desordena el objetivo y repite todo el proceso. Sin relación real, el sistema no debería encontrar señal. | LSTM: acierto en el quintil de mayor confianza de 45-50%, sin mejora de log-loss. Sistema completo: el resultado real supera a las 30 permutaciones. |
| **Réplica del sistema base** | El código del adaptativo, con los parámetros del base, debe reproducir el base. | Probabilidades idénticas a las de la implementación original del sistema base (diferencia máxima 10⁻⁶). |

---

## 3.7 Limitaciones del protocolo

- **El adaptativo se eligió con el test a la vista.** Su resultado en 2025-2026 y en octubre-noviembre está, por construcción, inflado respecto de lo que se puede esperar.
- **Validación se miró más de una vez**, para reincorporar el LSTM, para elegir el promedio con la logística y para comparar las variantes adaptativas.
- **La selección de variables no se repite dentro del walk-forward.** Las variables se eligieron una vez con 2015-2021.
- **Número de configuraciones.** Llevamos registradas unas **349** en todo el proyecto: unas 310 hasta el sistema base, 25 del modelo técnico, 7 variantes adaptativas del modelo 1, 6 combinaciones del sistema adaptativo y 1 prueba con el IPSA. Es el *N* del Sharpe deflactado.

### Referencias

- Bailey, D. y López de Prado, M. (2014). The deflated Sharpe ratio. *Journal of Portfolio Management*, 40(5), 94-107.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
