# 9. Limitaciones, riesgos y operación en vivo

> **Resumen.** La limitación principal del sistema adaptativo es cómo se eligió: después de ver el tramo en que gana. Además:
>
> - su resultado se concentra en pocos días de máxima exposición;
> - sus probabilidades calibran peor que las del sistema base;
> - corregido por el número de pruebas, solo 2005-2014 es concluyente.
>
> En operación, el riesgo más concreto son las noticias locales que las variables globales no capturan. Esta sección documenta esos riesgos y el procedimiento para generar la señal diaria durante el monitoreo en vivo, con los parámetros congelados desde el 9 de noviembre de 2026.

---

## 9.1 Limitaciones del resultado

| Limitación | Evidencia | Sección |
|---|---|---|
| **El sistema se eligió con el test a la vista** | Con la regla fijada al inicio (elegir en 2015-2021) habría ganado el sistema base (+284% contra +137%). El cambio se decidió después de ver 2025-2026 y octubre-noviembre. | 3.5, 4.5 |
| **Rinde menos cuando las relaciones son estables** | Pierde contra el base en 2015-2021 (−2,8 pb/día) y en validación (−3,2 pb/día). Sumando 2006-2026, ninguno de los dos domina. | 6.3 |
| **Concentración** | Los 10 mejores días de cada tramo son todos de exposición 3. Sin ellos, el resultado de validación queda en cero y el del test pierde 25%. | 6.5, 7.1 |
| **Calibración** | Las probabilidades del adaptativo no superan a la frecuencia base en 2015-2021 ni en el test. La logística de 500 días es la más ruidosa. | 4.4 |
| **Pruebas múltiples** | Con ~349 configuraciones, el Sharpe deflactado solo supera 0,5 en 2005-2014 (0,60). En validación es 0,06 y en el test 0,01. | 6.4 |
| **Dirección en el test** | En 2025-2026 la dirección del adaptativo no se distingue del azar (placebo 19,8%). Su ventaja viene del tamaño de las posiciones, no del acierto. | 6.4 |
| **Dependencia de la semilla del LSTM** | Con otro juego de semillas, el Sharpe cambia hasta 0,2 en un tramo. Se mitiga promediando 5 redes, pero no desaparece. | 4.5 |
| **Validación usada más de una vez** | Para reincorporar el LSTM, para elegir el promedio con la logística y para comparar las variantes adaptativas. | 3.7 |
| **Selección de variables fuera del walk-forward** | Las variables se eligieron una vez con 2015-2021. | 3.7 |
| **Modelo 2 heredado** | Los umbrales y el tope del GARCH se eligieron con el sistema base y no se reoptimizaron. | 5.5 |
| **Cierre asincrónico** | Menos importante que en el base (39-46% de la ganancia en el gap en validación y test, contra 60-84%), pero sigue presente. | 6.5 |

---

## 9.2 Limitaciones de los datos

- **Costo de transacción y carry:** usamos 1 pb por unidad de cambio de exposición y nuestra propia fórmula de carry. [confirmar: ambos con el código de evaluación del laboratorio]
- **Posición en pesos:** suponemos que la exposición 0 rinde 0. Si el laboratorio abona la tasa en pesos a la posición fuera del mercado, cambia la comparación con las referencias.
- **Datos reales de octubre-noviembre:** provienen de la base actualizada que entregó el laboratorio. Algunas series llegaron sin dato el último día (cobre LME, MSCI EM): entran como “sin cambio”.
- **Fechas de publicación macro** incompletas antes de 2019, y valores ya revisados. No afecta al sistema final, que no usa variables macro.
- **Revisiones de Bloomberg:** no podemos verificar si se corrigieron cierres históricos. Si ocurre, el script de la señal lo detecta y reentrena el bloque afectado.

---

## 9.3 Riesgos en operación

| Riesgo | Ejemplo | Cómo lo enfrentamos |
|---|---|---|
| **Noticias locales fuera del alcance de las variables** | Anuncio de intervención cambiaria del Banco Central (14-jul-2022): uno de los peores días de validación. | El modelo no las ve. El tope del GARCH reduce el tamaño cuando la volatilidad ya está alta, pero no anticipa el anuncio. |
| **Horario de la decisión** | Si la señal debe enviarse antes del cierre de Nueva York (17:00 ET), los cierres de *t* del rand, el DXY o el oro no existirían al decidir. | [confirmar con el laboratorio: hora límite de envío y precio de evaluación]. Si el envío es antes de ese cierre, la versión correcta sería la estricta. |
| **Datos faltantes** | Una serie sin dato el día de la decisión. | El valor faltante se reemplaza por la media de entrenamiento (0 tras estandarizar), es decir, la variable no opina ese día. |
| **Cambio de régimen** | Que las relaciones vuelvan a cambiar. | El sistema se reentrena cada 21 días y da más peso a lo reciente, así que se ajusta en semanas. Mientras tanto, se abstiene cuando la confianza es baja. |
| **Adaptación a ruido** | Con ventanas cortas, un mes atípico puede mover los pesos. | La ventana de la logística (500 días) y la vida media del LSTM (250 días) son largas frente a un mes, y el promedio de ambos amortigua los cambios. |
| **Pocos días de evaluación** | El monitoreo en vivo dura ~13 jornadas. | Con 13 días, el resultado está dominado por el azar: un solo día con exposición 3 puede mover ±2% a ±9%. Lo declaramos de antemano. |

---

## 9.4 Operación en vivo: cómo se genera la señal del día

Las bases piden, para cada jornada, la **dirección esperada, la probabilidad estimada y la posición sugerida**. El procedimiento diario, después del cierre:

| Paso | Qué se hace | Script |
|---|---|---|
| 1 | Actualizar la base cruda con los cierres del día. | [completar: fuente de datos en vivo entregada por el laboratorio] |
| 2 | Regenerar la base tratada. | `preparar_base_v2.py` |
| 3 | Calcular las probabilidades del LSTM y de la logística con el calendario de reentrenamiento del walk-forward: cada 21 días, con los mismos pesos y semillas. | `senal_del_dia.py` |
| 4 | Calcular la confianza (percentil contra los 250 días previos), el pronóstico del GARCH y la volatilidad relativa. | `senal_del_dia.py` |
| 5 | Emitir dirección, probabilidad y exposición, y agregarlas a la bitácora (`bitacora_senales.csv`). | `senal_del_dia.py` |

```bash
python preparar_base_v2.py "base_usdclp 2.xlsx" datos/procesados/
python senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
```

El percentil de confianza necesita las probabilidades de los 250 días anteriores, así que el script usa los modelos de los bloques que cubren esos días (unos 13 bloques de 21 días).

- **Primera corrida:** los entrena, en unos minutos en CPU, y los guarda en `modelos_vigentes_adaptativo.pt`.
- **Corridas siguientes:** los cargan y solo predicen el día nuevo.
- **Cada 21 días hábiles** la base llega a un bloque nuevo y el script entrena solo ese bloque. Durante el monitoreo toca un reentrenamiento, alrededor del 26 de noviembre de 2026; la fecha exacta depende de los días hábiles de la base.
- **Si se corrige un dato antiguo**, el script lo detecta y reentrena el bloque afectado.

**Verificación.** `verificar_senal.py` compara el script de la señal diaria con el walk-forward del informe (`modelo_adaptativo_colab.py`).

- **Probabilidades:** coinciden en 551 días (julio de 2024 a octubre de 2026), con una diferencia máxima de 6·10⁻⁶, que es redondeo.
- **Exposiciones:** coinciden en los 301 días comparados.
- **Salida completa del script:** es la misma que la del walk-forward en fechas del test calculadas como si fueran el último día de la base (opción `--hasta`):

| Fecha | Script | Walk-forward |
|---|---|---|
| 2025-04-03 | +3 | +3 |
| 2026-06-17 | −3 | −3 |
| 2026-10-05 | 0 | 0 |

Como cada fecha se calcula con la base cortada en ese día, esto funciona también como prueba de truncamiento: el adaptativo no usa información futura.

**Ejemplos de salida.** El primero es la señal en vivo al cierre del último día de la base. El segundo es un día del test reproducido con `--hasta 2026-06-17`.

```
Señal al cierre del 2026-10-06 (para la jornada siguiente, 2026-10-07):
  dirección: COMPRAR dólar | p = 0,506 | confianza (percentil) = 0,08 | vol. relativa = 1,09
  exposición sugerida: 0   (abstención: confianza bajo el percentil 60)
  componentes: p LSTM = 0,504 · p logística = 0,509   [sistema adaptativo]

Señal al cierre del 2026-06-17 (para la jornada siguiente, 2026-06-18):
  dirección: VENDER dólar | p = 0,430 | confianza (percentil) = 0,94 | vol. relativa = 1,14
  exposición sugerida: −3
  componentes: p LSTM = 0,474 · p logística = 0,386   [sistema adaptativo]
```

La primera corrida en CPU tarda unos minutos, porque entrena los bloques. La segunda carga `modelos_vigentes_adaptativo.pt` y tarda 10 segundos, con la misma señal.

Cuando el sistema se abstiene o el GARCH recorta la exposición, la línea de la exposición lo indica, por ejemplo: `exposición sugerida: 0   (abstención: confianza bajo el percentil 60)`.

**Señal enviada:** la exposición del sistema adaptativo. Con `--sistema base` el mismo script calcula la señal del sistema base, que se registra en paralelo solo como diagnóstico.

**Reglas de operación fijadas antes del monitoreo:**

1. **No se cambia el sistema durante el monitoreo.** Ni variables, ni ventanas, ni vida media, ni umbrales, ni la variante del GARCH. Los parámetros quedaron congelados el 9 de noviembre de 2026.
2. **Los reentrenamientos siguen el calendario del walk-forward** (cada 21 días); no se adelantan por resultados.
3. Si falta una serie, la señal se emite igual, sin esa variable, y se registra en la bitácora.

---

## 9.5 Qué haríamos con más tiempo

- **Elegir el horizonte de aprendizaje dentro del walk-forward**: que la ventana y la vida media se escojan cada año con los datos disponibles hasta ese momento, en vez de fijarlas mirando el test.
- **Reoptimizar el modelo 2 para el adaptativo** con un tramo que no se haya mirado.
- **Repetir la selección de variables dentro del walk-forward.**
- **Reportar el sistema completo con varios juegos de semillas** y promediarlos.
- **Incorporar el calendario de anuncios del Banco Central** (reuniones de política monetaria, comunicados) para reducir la exposición en esos días.
