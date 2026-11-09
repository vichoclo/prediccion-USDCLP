# 9. Limitaciones, riesgos y operación en vivo

> **Resumen.** El sistema tiene tres limitaciones principales: depende en buena parte del cierre asincrónico, un canal que se debilitó desde 2024; su resultado se concentra en pocos días de máxima exposición; y, corregido por el número de pruebas, la evidencia no es concluyente. En operación, el riesgo más concreto son las noticias locales que las variables globales no capturan. Esta sección documenta esos riesgos y el procedimiento para generar la señal diaria durante el monitoreo en vivo.

---

## 9.1 Limitaciones del resultado

| Limitación | Evidencia | Sección |
|---|---|---|
| **Dependencia del cierre asincrónico** | Más de la mitad de la ganancia de validación se genera en la apertura del día siguiente; sin ese canal (versión estricta) el sistema prácticamente no tiene señal. | 2.4, 6.4, 6.5 |
| **Debilitamiento de la señal** | 2024 fue cercano a cero para el sistema y ambos controles; la fracción del movimiento global que el peso incorpora al día siguiente cayó de 30-40% a 4-7%. | 2.4, 6.2 |
| **Concentración** | Más del 100% del resultado viene del ~19% de días con exposición 3; sin los 10 mejores días de validación queda alrededor de un cuarto de la ganancia. | 6.4, 7.1 |
| **Pruebas múltiples** | Con ~310 configuraciones, el Sharpe deflactado de validación es 0,18. | 6.3 |
| **Validación usada más de una vez** | Se usó para reincorporar el LSTM y para elegir el promedio como modelo final. | 3.7, 4.4 |
| **Selección de variables fuera del walk-forward** | Las variables se eligieron una vez con 2015-2021; ese tramo es dentro de muestra respecto de la selección. | 3.7 |
| **Elección del modelo final después de ver validación** | El promedio y la logística sola quedan casi empatados en validación; la elección se justifica por diversificación y no por rendimiento. | 4.4 |
| **Componente LSTM débil por sí solo** | En 2005-2014 el LSTM solo gana +22,5% y su dirección no supera al azar (placebo 18%). Su aporte al sistema es el ordenamiento de los días, no la dirección. | 6.3 |
| **Dependencia de la semilla del LSTM** | Con una sola red, el acierto en el quintil superior varía hasta 5 puntos. Se mitiga promediando 5 semillas. | 4.2 |
| **Tope del GARCH en el borde de la grilla** | Su aporte en validación proviene de un solo episodio (julio-octubre de 2022). | 5.5, 7.4 |

---

## 9.2 Limitaciones de los datos

- **Costo de transacción y carry:** usamos 1 pb por unidad de cambio de exposición y nuestra propia fórmula de carry. [confirmar: ambos con el código de evaluación del laboratorio]
- **Posición en pesos:** suponemos que la exposición 0 rinde 0. Si el laboratorio abona la tasa en pesos a la posición fuera del mercado, cambia la comparación con las referencias.
- **Fechas de publicación macro** incompletas antes de 2019, y valores ya revisados. No afecta al sistema final, que no usa variables macro.
- **Rezago de los flujos de la banca** supuesto en 2 días, sin verificar. Tampoco afecta al sistema final.
- **Revisiones de Bloomberg:** no podemos verificar si se corrigieron cierres históricos.

---

## 9.3 Riesgos en operación

| Riesgo | Ejemplo | Cómo lo enfrentamos |
|---|---|---|
| **Noticias locales fuera del alcance de las variables** | Anuncio de intervención cambiaria del Banco Central (14-jul-2022): el peor día de validación. | El modelo no las ve. El tope del GARCH reduce el tamaño cuando la volatilidad ya está alta, pero no anticipa el anuncio. |
| **Horario de la decisión** | Si la señal debe enviarse antes del cierre de Nueva York (17:00 ET), los cierres de *t* del rand, el DXY o el oro no existirían al decidir. | [confirmar con el laboratorio: hora límite de envío y precio de evaluación]. Si el envío es antes de ese cierre, la versión correcta sería la estricta. |
| **Datos faltantes** | Una serie sin dato el día de la decisión. | El valor faltante se reemplaza por la media de entrenamiento (0 tras estandarizar), es decir, la variable no opina ese día. |
| **Cambio de régimen** | Que el canal asincrónico desaparezca del todo. | El sistema se reentrena cada 126 días y se abstiene cuando la confianza es baja; en ese caso, la mayoría de los días quedaría en 0. |
| **Pocos días de evaluación** | El monitoreo en vivo dura ~13 jornadas. | Con 13 días, el resultado está dominado por el azar: un solo día con exposición 3 puede mover ±2%. Lo declaramos de antemano. |

---

## 9.4 Operación en vivo: cómo se genera la señal del día

Las bases piden, para cada jornada, la **dirección esperada, la probabilidad estimada y la posición sugerida**. El procedimiento diario, después del cierre:

| Paso | Qué se hace | Script |
|---|---|---|
| 1 | Actualizar la base cruda con los cierres del día. | [completar: fuente de datos en vivo entregada por el laboratorio] |
| 2 | Regenerar la base tratada. | `preparar_base_v2.py` |
| 3 | Calcular la probabilidad del modelo 1 con los modelos vigentes (no se reentrenan a diario; el próximo reajuste toca cada 126 días). | [completar: script de modelo 1] |
| 4 | Calcular la confianza (percentil contra los 250 días previos), el pronóstico del GARCH y la volatilidad relativa. | [completar: script de modelo 2] |
| 5 | Emitir dirección, probabilidad y exposición. | [completar] |

**Ejemplo de salida:**

```
Señal al cierre del AAAA-MM-DD (para la jornada siguiente):
  dirección: VENDER dólar | p = 0,412 | confianza (percentil) = 0,86 | vol. relativa = 1,08
  exposición sugerida: −3
```

**Señal enviada:** la exposición del sistema (promedio LSTM + logística, con tope GARCH). Las exposiciones de la logística sola y del LSTM solo se registran en la bitácora solo como diagnóstico.

**Reglas de operación fijadas antes del monitoreo:**

1. **No se cambia el sistema durante el monitoreo.** Ni variables, ni umbrales, ni la variante del GARCH.
2. **Los reentrenamientos siguen el calendario del walk-forward**, no se adelantan por resultados.
3. Si falta una serie, la señal se emite igual, sin esa variable, y se registra en la bitácora.

---

## 9.5 Qué haríamos con más tiempo

- **Repetir la selección de variables dentro del walk-forward**, para que todo el desarrollo sea fuera de muestra respecto de la selección.
- **Separar la validación interna del LSTM** en dos mitades: una para *early stopping* y otra para la calibración de Platt.
- **Reportar el sistema completo por semilla**, no solo el modelo 1.
- **Ponderar más los datos recientes** en el entrenamiento, para reducir el peso de un efecto que se está apagando, decidiéndolo en desarrollo.
- **Incorporar el calendario de anuncios del Banco Central** (reuniones de política monetaria, comunicados) para reducir la exposición en esos días.
