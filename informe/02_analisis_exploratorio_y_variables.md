# 2. Análisis exploratorio y selección de variables

> **Resumen.** Antes de modelar medimos cuánta información tiene cada variable sobre el retorno del día siguiente. Las señales son pequeñas (la mejor correlación individual ronda 0,06) y, corrigiendo por pruebas múltiples, solo unas 10 de 86 variables son defendibles. Cuatro hallazgos ordenaron todo lo que vino después: (1) casi toda la señal viene de mercados que cierran **después** de Santiago y se materializa en la **apertura** del día siguiente, un efecto que se apagó desde 2024; (2) existe un efecto **día de la semana** (lunes y viernes al alza del dólar), real pero concentrado en pocos días; (3) la no linealidad está en la **magnitud** del movimiento, no en su dirección, lo que justifica separar el sistema en un modelo de dirección y otro de exposición; y (4) elegir variables solo con datos, sin un filtro previo, rinde **peor** fuera de muestra.

---

## 2.1 Qué buscamos y cómo lo medimos

El objetivo es predecir el retorno del USD/CLP de *t* a *t+1* neto de carry (`y_ret_neto_pb`) o su signo (`y_sube_neto`). Para cada variable `x_*` medimos:

| Medida | Qué captura | Por qué la usamos |
|---|---|---|
| **IC** (correlación entre *x* en *t* e *y* en *t+1*), Pearson y Spearman | Relación lineal o monótona | Es la medida estándar de poder predictivo en finanzas. Con *n* ≈ 3.400, \|IC\| > 0,034 equivale a t > 2. |
| **Estabilidad del IC** año a año | Si la relación se mantiene o depende de un periodo | Una señal que cambia de signo no sirve para operar. |
| **Información mutua** con test de permutación | Relaciones no lineales | Detecta formas que la correlación no ve. |
| **IC sobre el gap y el intradía** | En qué parte del día se materializa la señal | Distingue predicción real de un artefacto de horario (sección 2.4). |

**Corrección por pruebas múltiples.** Con 86 variables, a un nivel de 5% se esperan unas 4 “significativas” por puro azar. Por eso toda lista de variables se filtra con **Benjamini-Hochberg** (tasa de falsos descubrimientos de 10%).

> Las cifras de las secciones 2.2, 2.3 y 2.6 se calcularon sobre la base desde 2013 (≈ 3.400 días); las de 2.4, sobre la base desde 2010; las de 2.5, sobre toda la historia desde 2001. Se indica en cada tabla.

---

## 2.2 Panorama univariado: señales pequeñas

Variables con mayor IC (base desde 2013, objetivo `y_ret_neto_pb`):

| Variable | IC | t | ρ Spearman |
|---|---|---|---|
| Rand (USD/ZAR) | +0,064 | 3,72 | +0,062 |
| Basis NDF 1M − TPM | +0,060 | 3,47 | +0,063 |
| IPSA | −0,056 | −3,25 | −0,070 |
| Peso mexicano (USD/MXN) | +0,051 | 2,95 | +0,056 |
| Rendimiento implícito NDF 3M (cambio) | +0,049 | 2,88 | +0,061 |
| Vol. realizada USD/CLP 20 días | −0,043 | −2,53 | −0,029 |
| Real (USD/BRL) | +0,043 | 2,52 | +0,046 |
| Vol. implícita emergentes (EM-VXY) | −0,043 | −2,50 | −0,040 |

**Después de Benjamini-Hochberg sobreviven 10 de 86 variables.** Los signos tienen lectura económica: cuando el rand o el peso mexicano se deprecian, el peso chileno tiende a seguirlos (shock común a monedas emergentes y de materias primas); cuando sube el IPSA, el dólar tiende a bajar (entrada de capitales).

Para dimensionar: un IC de 0,06 significa que la variable explica alrededor de 0,4% de la varianza del retorno del día siguiente. Ninguna variable predice sola; el valor está en combinarlas y en saber cuándo no operar.

---

## 2.3 Estabilidad en el tiempo: la señal decae

Calculamos el IC año a año (2013-2026) y su estabilidad (media / desviación × √14):

| Variable | IC medio | Desv. | t de estabilidad |
|---|---|---|---|
| Rand | +0,07 | 0,08 | 3,10 |
| Peso mexicano | +0,05 | 0,07 | 2,92 |
| IPSA | −0,06 | 0,08 | −2,73 |
| Basis NDF 1M | +0,04 | 0,06 | 2,55 |
| Cambio del VIX | +0,03 | 0,05 | 2,37 |
| Cobre LME | −0,04 | 0,07 | −2,17 |
| Cambio NDF 3M | +0,03 | 0,09 | 1,14 |
| Retorno propio del USD/CLP | −0,00 | 0,10 | −0,09 |

**Alerta:** el IC de casi todas las variables cae con fuerza en 2024-2026. El del rand pasa de +0,20 en 2013 a −0,08 en 2026. La sección 2.4 explica por qué.

El retorno pasado del propio USD/CLP no tiene signo estable: no hay ni momentum ni reversión aprovechable a un día.

---

## 2.4 El hallazgo central: el cierre asincrónico

### Qué ocurre

El USD/CLP de la base es el cierre del mercado formal de Santiago. Muchas otras series cierran más tarde:

| Respecto del cierre de Santiago | Series |
|---|---|
| Mismo momento | USD/CLP, IPSA, swaps CLP, TPM, cámara |
| Antes | Cobre y aluminio LME, Brent, hierro, Shanghai, USD/CNY, peso colombiano, sol peruano |
| Después | Rand, peso mexicano, DXY, BBDXY, euro, yen, CNH, oro, NDF y rendimientos CHNI, vol. implícita del peso (NY 17:00 ET); S&P 500, VIX, MOVE, Tesoros. El real cierra en São Paulo, probablemente después de Santiago. |

Si a las 16:30 de Santiago aparece una noticia global, el rand la refleja en su cierre del día *t*. El peso chileno la refleja recién en la **apertura** de *t+1*. En la fila *t*, el rand ya trae información que el USD/CLP todavía no incorporó, y por eso parece predecirlo.

### La evidencia: toda la señal está en la apertura

Separamos el retorno de *t* a *t+1* en dos partes: del cierre de *t* a la apertura de *t+1* (**gap**) y de la apertura al cierre de *t+1* (**intradía**). Base desde 2010:

| Variable (cierre) | IC con el retorno *t+1* | IC con el gap | IC con el intradía |
|---|---|---|---|
| Rand (NY) | +0,083 | **+0,115** | +0,014 |
| Peso mexicano (NY) | +0,060 | **+0,121** | −0,018 |
| Real (São Paulo) | +0,064 | **+0,120** | −0,013 |
| DXY (NY) | +0,045 | +0,074 | −0,002 |
| NDF 3M (NY) | +0,046 | +0,077 | −0,002 |
| VIX (NY) | +0,034 | +0,077 | −0,016 |
| S&P 500 (NY) | −0,027 | −0,096 | +0,039 |
| Cobre LME (Londres, cierra antes) | −0,045 | −0,058 | −0,010 |

Si fuera una reacción lenta del mercado chileno (predicción con contenido económico), habría señal también durante la jornada siguiente. No la hay: es el efecto de **transacción no sincrónica** descrito por Scholes y Williams (1977) y Lo y MacKinlay (1990).

### El efecto se apagó desde 2024

Medimos qué parte del movimiento del rand el peso chileno incorpora recién al día siguiente:

| Periodo | % que llega al día siguiente (rand) | IC del rand |
|---|---|---|
| 2010-2013 | 28 a 47% | 0,16 a 0,30 |
| 2014-2019 | 13 a 36% | 0,05 a 0,18 |
| 2020-2022 | 8 a 22% | 0,03 a 0,07 |
| 2024-2026 | **4 a 7%** | **−0,08 a 0,01** |

Esto explica la caída del IC de la sección 2.3. No encontramos documentación de un cambio de horario; las hipótesis son un cierre de referencia local más tardío, más negociación fuera del horario formal o más peso del NDF offshore en la formación del precio. Cada año tiene unas 250 observaciones, así que las cifras anuales son ruidosas; lo robusto es la tendencia.

### Qué decidimos

- **Es legal según las reglas.** El diccionario del laboratorio establece que los cierres de una misma fecha se asumen disponibles al decidir.
- **Pero no podemos tratarlo como una ventaja permanente.** Un modelo entrenado con 2010-2019 sobrepondera un efecto que ya casi no existe.
- **Las variables de este canal cuentan como un solo factor** (“noticias globales posteriores al cierre”): rand, peso mexicano, real, DXY y NDF reaccionan a la misma noticia.
- **Comparamos dos versiones del sistema:** *torneo* (todas las series al cierre de *t*) y *estricta* (las que cierran después de Santiago, rezagadas un día). En la versión estricta, ningún modelo supera a comprar siempre en desarrollo: casi toda la ganancia de la versión torneo viene de este canal.

**El modelo final usa la versión torneo**: todas las variables entran con su cierre de *t*, como permite el diccionario. La versión estricta se evaluó como control con el sistema base, porque muestra qué parte del resultado depende de este canal: en validación gana +7,3%, sin significancia. El sistema adaptativo depende menos de este canal (sección 6.5).

---

## 2.5 Estacionalidad y calendario

### Día de la semana: lunes y viernes al alza del dólar

Retorno medio del USD/CLP según el día en que se realiza (pb):

| Base | Lunes | Martes | Miércoles | Jueves | Viernes |
|---|---|---|---|---|---|
| Desde 2001 | +6,0 | −1,2 | −1,7 | −4,9 | +5,0 |
| Desde 2010 | +9,8 | −3,7 | −2,8 | −4,1 | +9,4 |
| Desde 2018 | +10,2 | −8,8 | −7,0 | +4,2 | +13,1 |

ANOVA, Kruskal-Wallis y χ² rechazan igualdad entre días en todas las bases (p ≤ 0,001). Por tramo del protocolo (diferencia contra el resto de los días, t de Welch):

| Tramo | Lunes | Viernes |
|---|---|---|
| Entrenamiento inicial 2001-04 | −1,7 (t −0,3) | −10,2 (t −1,8) |
| Desarrollo 2005-14 | +4,8 (t 1,4) | +1,6 (t 0,5) |
| Desarrollo 2015-21 | +11,6 (t 2,6) | +8,0 (t 1,9) |
| Validación 2022-24 | +15,2 (t 1,7) | +18,1 (t 1,7) |

**Robustez:**

- **Lunes:** mediana +6,2 pb, sin extremos t 3,7, neto de carry +4,0 pb (t 2,3). Aparece también en el dólar observado y en otras monedas latinoamericanas (MXN, BRL, COP, PEN), así que es un efecto amplio de emergentes y no un artefacto del cierre.
- **Viernes:** neto de carry +4,3 pb (t 2,4), pero los 20 mejores viernes aportan 87% del total; sin ellos, t 0,5. No aparece en el dólar observado ni en otras monedas emergentes. Es propio del cierre BGN del viernes y podría ser un artefacto de horario o fuente.

**¿Sirve como estrategia por sí solo?** Simulamos (Monte Carlo, 2010-2024) la regla “comprar dólar el viernes y vender el lunes”, neta de carry y de 2 pb de costo. Aun suponiendo que el efecto es real, **4 de cada 10 meses son negativos**: a un mes, la volatilidad (±220 pb con exposición 1) tapa un efecto de ~10 pb por operación. Lo incorporamos como **variable del modelo** (`cal_viernes`, `cal_dias_corridos_sig`), no como estrategia aparte.

**Lo que decidimos no hacer:** desestacionalizar. El patrón es señal para predecir, no ruido, y métodos como X-13 o STL usan datos futuros.

### Día del mes y anuncios

- **Día del mes:** ninguna prueba global rechaza igualdad (Kruskal p = 0,10) y ningún día sobrevive a Benjamini-Hochberg.
- **Anuncios:** los datos (IPC, IMACEC, desempleo, FOMC, empleo de EE.UU.) no mueven la **dirección** de forma significativa. El único efecto cercano a significativo es sobre la **volatilidad**: +32% el día después de un cambio de TPM (q = 0,11). Es información para el modelo 2, no para la señal.
- **Fin de trimestre:** el dólar tiende a bajar el último día hábil del trimestre (−13,3 pb, p = 0,05), con el efecto concentrado desde 2022. Con tan pocos casos no pasa la corrección; queda como hipótesis.

---

## 2.6 No linealidad: está en la magnitud, no en la dirección

### Información mutua con test de permutación

La información mutua tiene sesgo positivo, así que la comparamos con su distribución bajo la hipótesis nula (300 permutaciones del objetivo):

| Variable | Información mutua | p |
|---|---|---|
| Rango alto-bajo del USD/CLP | 0,050 | 0,000 |
| MOVE | 0,037 | 0,003 |
| VIX | 0,036 | 0,007 |
| Rand | 0,000 | 1,000 |
| Basis NDF 1M | 0,000 | 1,000 |

Las variables con relación no lineal significativa son de **volatilidad** y se relacionan con el **tamaño** del movimiento, no con su signo:

| Variable | Inf. mutua con el signo de *y* | Inf. mutua con \|*y*\| |
|---|---|---|
| Rango USD/CLP | 0,011 | 0,052 |
| VIX | 0,000 | 0,040 |
| MOVE | 0,000 | 0,032 |

### Las mejores variables direccionales son monótonas

Retorno medio del día siguiente por quintil de la variable (pb; error estándar ≈ 3):

| Variable | Q1 | Q2 | Q3 | Q4 | Q5 | Forma |
|---|---|---|---|---|---|---|
| Basis NDF 1M | −6,2 | −1,0 | +0,7 | +5,4 | +6,3 | monótona |
| IPSA | +9,8 | +1,2 | +3,5 | +0,1 | −9,7 | monótona |
| Rand | −8,4 | +0,6 | +3,5 | +7,0 | +2,5 | satura en Q5 |
| VIX (nivel) | +3,9 | +5,7 | +3,3 | −4,4 | −3,4 | escalón |

Una relación lineal ya captura casi todo; la no linealidad que aparece es del orden del error estándar.

### Agregar flexibilidad empeora

Walk-forward 2018-2026 con 12 variables, mejora de log-loss ×1000 frente a predecir siempre la frecuencia base (positivo es mejor):

| Modelo | Mejora |
|---|---|
| Logística | −4,26 |
| Logística con interacciones y cuadráticos | −18,34 |
| Gradient boosting (profundidad 2) | −9,08 |
| Random forest (profundidad 4, hojas ≥ 50) | +0,13 |

### Consecuencia para la arquitectura

Estos tres resultados son la base empírica de separar el sistema en dos modelos:

1. **Modelo 1 (dirección):** lineal y regularizado, con variables de precios, tasas y calendario.
2. **Modelo 2 (exposición):** usa la volatilidad, que sí tiene estructura (no lineal) con el tamaño del movimiento, para decidir cuánto apostar y cuándo abstenerse.

---

## 2.7 Redundancia

Muchas variables miden lo mismo. Con un clustering jerárquico (distancia 1 − |correlación|, corte 0,3), las 86 variables forman 57 grupos. Los más claros: {DXY, BBDXY, euro}, {swaps de 1, 2, 5 y 10 años}, {vol. realizada de 60 días, vol. implícita 1M y 3M, NDF 1M}.

Esto importa por dos razones:

- **En una regresión conjunta**, variables casi iguales reciben coeficientes de signo opuesto (por ejemplo, cobre LME positivo y COMEX negativo) y el coeficiente individual deja de ser interpretable.
- **Al combinar señales**, contar cinco variables del mismo factor como cinco votos sobrepondera ese factor. Por eso agrupamos las variables en **bloques económicos** y damos un voto por bloque.

---

## 2.8 Cómo seleccionamos las variables

### Principio: filtrar antes de mirar el resultado

Toda selección se hace **solo con la segunda parte del tramo de desarrollo** (2015-2021; la sección 3.2 explica por qué no con todo el desarrollo, que parte en 2005). Validación sirve para comparar. El test no se usó para elegir variables; más tarde sí influyó en la elección del sistema adaptativo (sección 3.5). Elegir variables mirando la muestra completa, o el tramo con que luego se evalúa, produce resultados falsamente buenos.

### Paso 1 · Universo inicial

Partimos de las variables `x_*` de la base tratada y separamos las de **volatilidad** (realizada, implícita, rango, VIX, MOVE, EM-VXY), que van al modelo 2 (sección 2.9). Quedan 74 candidatas para el modelo 1.

### Paso 2 · Filtro por estabilidad del signo

Para cada variable estimamos una logística propia en ventana móvil de 1.000 días, reajustada cada 21 días, y medimos en desarrollo:

- **% de reajustes con el signo esperado.** Exigimos al menos 80%. Para las variables con hipótesis económica, el signo esperado es el teórico; para las demás, el signo que mantienen en el pasado.
- **Mejora de log-loss** frente a la frecuencia base: no negativa.

Ninguna variable sobrevive por sí sola a Benjamini-Hochberg (la mejor mejora individual es +2,8 milésimas de log-loss, t = 1,13). Por eso el filtro exige **estabilidad del signo** y no significancia individual: buscamos variables que apunten siempre en la misma dirección, aunque su efecto sea pequeño.

### Variables del modelo final

El filtro dejó 15 variables (base desde 2010). El modelo final (sistema adaptativo, sección 4) usa la **versión “núcleo”**: las 11 que existen desde 2001. Quedan fuera los rendimientos implícitos NDF (`x_chni3m`, `x_chni3m_dif`, `x_chni6m_dif`) y el yuan offshore (`x_usdcnh_ret`), que comienzan en 2010. Entrenar desde 2001 da más historia al modelo; la versión completa (desde 2010) se evaluó y rindió peor en validación.

| Variable | Bloque | Signo esperado | Cierra respecto de Santiago |
|---|---|---|---|
| `x_cobre_lme_ret` | Cobre y metales | − | Antes |
| `x_cobre_comex_ret` | Cobre y metales | − | Aprox. simultáneo |
| `x_oro_ret` | Materias primas | − | Después |
| `x_dxy_ret` | Dólar global | + | Después |
| `x_bbdxy_ret` | Dólar global | + | Después |
| `x_dxy_mom20` | Dólar global | sin hipótesis | Después |
| `x_usdzar_ret` | Monedas emergentes | + | Después |
| `x_mxef_ret` | Renta variable | − | Después |
| `x_vol_em_dif` | Riesgo global | + | Después |
| `cal_viernes` | Calendario | + | — |
| `cal_dias_corridos_sig` | Calendario | + | — |

Signo esperado: + significa que, si la variable sube, se espera que suba el dólar. Siete de las once cierran después de Santiago, lo que refuerza la advertencia de la sección 2.4.

### ¿Y si elegimos solo con datos?

Nuestro profesor nos señaló que, como el objetivo es predecir y no explicar, no hace falta teoría económica para elegir variables. Lo probamos: partiendo de las 75 candidatas, eliminamos las redundantes (correlación > 0,7) y aplicamos selección por estabilidad con regularización L1 (50 submuestras por bloques de 3 meses).

| Conjunto | Mejora de log-loss ×1000 en validación 2023-24 |
|---|---|
| Elegido solo con datos (11 variables) | +3,5 a +4,0 |
| Con filtro previo (16 variables) | **+8,0** |

La diferencia no es significativa (Diebold-Mariano 1,14), pero va en la misma dirección en las dos versiones (torneo y estricta). **Lectura:** no hace falta una historia causal para predecir, pero el filtro previo cumple otra función: reduce el número de candidatas antes de mirar los datos, y eso **actúa como regularización** contra las pruebas múltiples.

### ¿Y si probamos todas las combinaciones?

Evaluamos las 131.071 combinaciones posibles de las 17 variables que pasaron el filtro. La correlación entre la mejora de log-loss de cada combinación en desarrollo y en validación fue **−0,07**: que una combinación funcione en un periodo no anticipa nada del otro. Las combinaciones elegidas por su desempeño en desarrollo y validación cayeron de un Sharpe de 1,1-1,2 en validación a 0,2-0,3 en test. Concluimos que buscar la “mejor” combinación es sobreajustar ruido, y fijamos el conjunto de variables con el filtro de desarrollo.

---

## 2.9 Variables que van al modelo 2

Estas variables miden **cuánto** se mueve el dólar, no hacia dónde (sección 2.6). No entran al modelo 1:

| Grupo | Variables |
|---|---|
| Volatilidad realizada del USD/CLP | `x_usdclp_vol5`, `x_usdclp_vol20`, `x_usdclp_vol60`, `x_usdclp_rango` |
| Volatilidad implícita del peso | `x_vol_impl_1m`, `x_vol_impl_1m_dif`, `x_vol_impl_3m`, `x_vol_prima` |
| Riesgo global | `x_vix`, `x_vix_dif`, `x_move`, `x_move_dif`, `x_vol_em`, `x_vol_em_dif` |

**Excepción:** `x_vol_em_dif` (el *cambio* diario de la volatilidad implícita de monedas emergentes) también entra al modelo 1, porque pasó el filtro de dirección con el signo esperado: un alza de la aversión al riesgo global precede a una depreciación del peso. El *nivel* de la volatilidad no tiene signo estable y queda solo en el modelo 2.

---

## 2.10 Lo que probamos y no aportó

| Familia | Resultado | Fuente |
|---|---|---|
| **Tasas** (TPM − Fed, swaps CLP, swap 2a − Tesoro 2a) | Todas con \|t\| < 1,7. Varios swaps tienen el signo al revés de la teoría de forma estable. El cambio de TPM tiene el signo esperado solo en 7% de los reajustes: el mercado anticipa la decisión. | Diagnóstico de tasas; filtro de desarrollo |
| **Macro** (IMACEC, IPC, desempleo, point-in-time) | Ninguna con signo estable ni mejora de log-loss. | Filtro de desarrollo |
| **Flujos de la banca** | Sin signo estable; rezago de publicación no verificado. | Filtro de desarrollo |
| **Retorno pasado del USD/CLP** (momentum, reversión) | IC ≈ 0 y cambia de signo cada año. | Sección 2.3 |
| **Indicadores técnicos** (RSI, medias móviles, Bollinger, MACD) con un modelo de árboles | Probabilidades peores que la frecuencia base. Consistente con la literatura: las reglas técnicas en FX decaen con el tiempo y su rentabilidad desaparece al corregir por data snooping (Sullivan, Timmermann y White, 1999; Hutchinson et al., 2022). | Descarte de XGBoost técnico |
| **Monedas pares como valor relativo** (residuo frente a COP, PEN, BRL, MXN, ZAR) | En la versión estricta, el residuo es en realidad el retorno propio del peso arrastrado a la apertura (correlación 0,93). | Diagnóstico de pares |

---

## 2.11 Lecciones para el modelado

1. **Las señales son pequeñas y frágiles.** Ninguna variable predice sola; el sistema depende de combinar señales débiles y de abstenerse cuando no hay convicción.
2. **El mayor riesgo es el sobreajuste, no la falta de variables.** Cada prueba adicional aumenta la probabilidad de encontrar algo por azar. Por eso contamos las configuraciones probadas y aplicamos el Sharpe deflactado (sección 6).
3. **Lo que funcionó en 2010-2019 no necesariamente funciona hoy.** El cierre asincrónico se apagó; cualquier resultado que dependa de él debe leerse con cautela.
4. **La volatilidad es información para el tamaño de la posición**, no para la dirección.

---

### Referencias

- Benjamini, Y. y Hochberg, Y. (1995). Controlling the false discovery rate: a practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society B*, 57(1), 289-300.
- Hutchinson, M. et al. (2022). Technical trading rule profitability in currencies: It's all about momentum. *Research in International Business and Finance*, 63.
- Lo, A. y MacKinlay, A. C. (1990). An econometric analysis of nonsynchronous trading. *Journal of Econometrics*, 45, 181-211.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Scholes, M. y Williams, J. (1977). Estimating betas from nonsynchronous data. *Journal of Financial Economics*, 5, 309-327.
- Sullivan, R., Timmermann, A. y White, H. (1999). Data-snooping, technical trading rule performance, and the bootstrap. *Journal of Finance*, 54(5), 1647-1691.
