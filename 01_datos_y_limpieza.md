# 1. Datos y limpieza

> **Resumen.** Partimos de la base Bloomberg entregada por el laboratorio (66 series, formato ancho) y la transformamos, con un único script reproducible, en una tabla diaria de **días hábiles chilenos desde el 9 de agosto de 2001**, con 105 columnas. Cada fila *t* contiene solo información conocida al cierre de *t*, y los objetivos miran a *t+1*. Las principales dificultades fueron: huecos en el spot del USD/CLP, series que “repiten” valores porque no hubo cotización, fechas de publicación de datos macro, y series discontinuadas o que terminan antes. Una auditoría posterior detectó una fuga de información en nuestra primera versión de la limpieza; la corregimos y la documentamos más abajo.

---

## 1.1 Fuente de datos

| Insumo | Descripción |
|---|---|
| `base_usdclp 2.xlsx` | Base cruda del laboratorio Bloomberg. 66 series desde 1990 hasta el 2026-10-06, en formato ancho `ticker\|campo` (ej. `USDCLP Curncy\|PX_LAST`). Incluye OHLC del USD/CLP, monedas, commodities, bolsas, tasas locales y de EE.UU., volatilidades, posiciones de la banca y series macro mensuales con su `FECHA_RELEASE`. |
| Diccionario del laboratorio | Describe cada serie y su hora de cierre. Establece que los cierres de una misma fecha se asumen disponibles al momento de decidir. |

Todas las series son datos públicos de mercado vía Bloomberg, como exigen las bases.

---

## 1.2 Principios que guiaron la limpieza

Antes de tocar los datos fijamos cuatro reglas. Casi todas las decisiones que siguen se derivan de ellas.

1. **Nada del futuro en las variables.** En la fila *t*, toda variable `x_*` usa solo información disponible al cierre de *t*. Los objetivos `y_*` son los únicos que miran a *t+1*. Esto es lo que exigen las bases (“información disponible hasta el cierre de la jornada previa”) y es la principal fuente de resultados falsamente buenos en series de tiempo financieras (López de Prado, 2018).
2. **No borrar filas.** Borrar un día con datos faltantes rompe los rezagos y las ventanas móviles (un “retorno de 5 días” pasaría a abarcar 6). Preferimos conservar la fila, dejar vacío lo que no se puede calcular y marcarlo con una columna `flag_*`.
3. **Sin cálculos globales.** Nada en la base puede depender de la muestra completa (máximos, medias, normalizaciones), porque eso filtra información del futuro hacia el pasado. La normalización se hace **dentro** de cada ventana de entrenamiento del walk-forward, no en la base.
4. **Reproducible desde la base cruda.** Toda la limpieza vive en un script (`preparar_base_v2.py`) que toma el Excel original y genera las bases tratadas. No hay pasos manuales en Excel.

### Convención de columnas

| Prefijo | Significado |
|---|---|
| `x_*` | Variable explicativa. Usa solo información al cierre de *t*. |
| `y_*` | Objetivo. Mira a *t+1*. |
| `carry_pb` | Carry de *t* a *t+1*, en puntos base. |
| `flag_*` | Control de calidad del dato (relleno, faltante, origen externo). |
| `edad_*` | Días hábiles desde la última cotización nueva de una serie. |
| `cal_*` | Calendario (día de la semana, días corridos hasta la próxima jornada). |
| `periodo` | Tramo del protocolo de validación al que pertenece la fila (ver sección de validación). |

---

## 1.3 Flujo de la limpieza

```
               base_usdclp 2.xlsx (cruda)
                          │
                 preparar_base_v2.py
                          │
   1. calendario hábil chileno      6. rezagos de publicación
   2. ventana desde 2001-08-09      7. depuración y empalmes
   3. huecos del spot               8. carry y objetivos
   4. series rancias                9. transformaciones y variables
   5. macro point-in-time          10. cortes 2001 / 2010 / 2018
                          │
   modelo_usdclp_desde_{2001,2010,2018}.{csv,xlsx}
   (hojas: modelo, diccionario_variables, periodos, series_rancias, feriados_cl)
```

---

## 1.4 Calendario hábil chileno

**Qué hicimos.** Dejamos solo los días en que opera el mercado cambiario chileno: eliminamos sábados, domingos, feriados legales y el feriado bancario del 31 de diciembre. Usamos la librería `holidays` (`holidays.Chile(categories=("public", "bank"))`).

**Por qué.** El USD/CLP que se evalúa es el cierre de Santiago. Un día sin mercado local no es una jornada de decisión, y mantenerlo generaría retornos nulos artificiales.

**Verificación.** Revisamos que ningún día hábil no feriado careciera *a la vez* de todas las series locales (dólar observado, IPSA, swaps, índice de cámara). Si eso pasara, sería un feriado que la librería no conoce. No encontramos ninguno.

**Detalle.** Las series macro mensuales vienen fechadas a fin de mes, y cerca del 40% de esos fines de mes caen en fin de semana o feriado. Por eso las macro no se filtran por calendario: se incorporan por su fecha de publicación (sección 1.8).

---

## 1.5 Ventana de inicio: 2001-08-09

Nuestra primera versión partía en 2010. La extendimos al **9 de agosto de 2001** por tres razones:

- El peso chileno flota libremente desde el 2 de septiembre de 1999 (fin de la banda cambiaria). Antes de eso, la dirección del tipo de cambio responde a otra lógica.
- La TPM nominal (`CHOVCHOV`) comienza el 2001-08-09. Antes, la TPM se fijaba en UF y no es posible calcular el carry nominal con la base.
- Más historia permite un protocolo de validación con más tramos fuera de muestra.

El script genera además dos cortes más cortos, desde 2010 y desde 2018 (este último sin huecos en el spot), para comparar ventanas de entrenamiento en validación. **La elección entre cortes se hace en validación, nunca mirando el tramo de test.**

Finalmente se uso la base a partir del 2001 para el modelo LSTM

---

## 1.6 Dificultad 1: huecos en el spot del USD/CLP

**El problema.** Bloomberg no trae el USD/CLP en **156 días hábiles**, concentrados entre noviembre de 2011 y 2012 (racha máxima de 16 días), más una veintena de días sueltos hasta enero de 2018. Las cuatro columnas OHLC faltan siempre juntas. No son feriados: el resto de las series locales sí tiene dato esos días.

**Lo que hicimos:**

- **No borramos las filas** (principio 2).
- **No imputamos el objetivo.** Si falta el spot en *t* o en *t+1*, el retorno a *t+1* no existe y `y_*` queda vacío. Esas filas no se usan para entrenar ni evaluar.
- **Para las variables**, el nivel del spot se arrastra desde el último día con dato (máximo 10 días hábiles). El día sin dato tiene retorno 0 y el movimiento completo aparece cuando vuelve a haber cotización. Se marca con `flag_usdclp_relleno`.
- `x_usdclp_rango` y `x_usdclp_cuerpo` (que necesitan apertura, máximo y mínimo) quedan vacíos esos días.
- La volatilidad realizada de 20 días puede incluir un retorno rellenado. Esos días se marcan con `flag_vol20_contaminada`.

### La fuga que encontramos y corregimos

En la primera versión rellenábamos el spot con el **dólar observado del día siguiente** (`CLFXDOOB` de *t+1*), porque vimos que el observado de un día es casi igual al spot del día anterior (diferencia mediana de 1,25 CLP, contra 3,2 CLP respecto del spot del mismo día). Como proxy de nivel era bueno.

El problema es que **el observado de *t+1* se publica en la mañana de *t+1***: al cierre de *t* todavía no existe. Usarlo en las variables de *t* es información del futuro. Lo detectamos en la auditoría de fuga (prueba de truncamiento, sección 1.12): al cortar la base en un día sin spot, 15 columnas cambiaban de valor respecto de la base completa.

La corrección fue reemplazar ese relleno por el arrastre del último dato conocido. Volvimos a correr el sistema completo y **los resultados no cambiaron**, pero la base dejó de violar la regla.

---

## 1.7 Dificultad 2: series “rancias”

**El problema.** Varias series cotizadas localmente o en mercados poco líquidos repiten el valor del día anterior cuando no hubo transacción nueva. Un valor repetido no significa “el precio no cambió”, sino “no hubo precio”. Si se trata como dato real, el modelo ve cambios de 0 que no existieron y luego un salto acumulado.

Medimos el porcentaje de días con valor repetido (solo en días con mercado de EE.UU. abierto, para no confundirlo con feriados):

| Serie | 2001-2007 | 2008 | 2009 | 2010+ | Se usa desde |
|---|---|---|---|---|---|
| Vol. implícita USD/CLP 1M y 3M | 27-63% | 19-22% | 2% | 1-11% | 2009-01 |
| Rendimiento implícito NDF (`CHNI` 1M, 3M, 6M) | 17-35% + 2-12% vacío | 6-9% + 11% vacío | 11-14% + 18% vacío | 0-10% | 2010-01 |
| Swaps CLP y UF | sin datos hasta 2003-04; 10-30% en 2004-06 | 4-8% | 6-14% | 1-17% | 2007-01 |

**Lo que hicimos:**

1. **Fecha de confiabilidad por serie.** Antes de la fecha “se usa desde”, la serie queda vacía. El criterio fue el año desde el cual la repetición queda bajo ~10-15% y sin huecos largos.
2. **Repetición = sin cotización.** Después de esa fecha, un valor repetido se marca como faltante: el nivel se arrastra (máx. 10 días), el cambio del día es 0 y el día que vuelve a cotizar lleva el cambio acumulado. Agregamos columnas `edad_*` con los días desde la última cotización nueva, para que el modelo sepa cuán fresco es el dato.
3. **Repeticiones legítimas no se tocan:** TPM, Fed funds, SOFR, UF, USD/CNY (paridad fija hasta julio de 2005) y el Tesoro a 3 meses en el periodo de tasa cero. En esas series, que el valor se repita es lo normal.

Las demás series (USD/CLP, monedas, bolsas, commodities, VIX, MOVE, Tesoros, tasas) están limpias desde 2001, con menos de 6% de repeticiones.

---

## 1.8 Dificultad 3: cuándo se conoce cada dato

Una serie fechada en *t* no siempre está disponible al cierre de *t*. Aplicamos rezagos por publicación:

| Serie | Rezago | Motivo |
|---|---|---|
| SOFR / Fed funds | 1 día | Se publican la mañana siguiente. |
| Posiciones en derivados y spot de la banca (`CLPBODMB`, `CLPBLDMB`, `CLPBSMB`) | 2 días | Supuesto conservador. [confirmar el rezago real] |
| UF | 0 | Se conoce por anticipado. |
| Macro (IMACEC m/m y a/a, IPC a/a, desempleo) | Por `FECHA_RELEASE` | Ver abajo. |

**Macro point-in-time.** Cada dato macro entra a la base recién el día de su publicación, no en su mes de referencia. Esto se hace con un *merge as-of* contra la fecha de publicación. La dificultad fue que `FECHA_RELEASE` está incompleta antes de 2019. En la primera versión rellenábamos la fecha faltante con el **rezago máximo observado en toda la muestra**, lo que viola el principio 3 (un cálculo global que cambia si se trunca la base). La auditoría lo detectó y lo reemplazamos por **rezagos fijos y documentados**:

| Serie | Rezago fijo (días) | Rezago mínimo plausible (días) |
|---|---|---|
| IMACEC m/m | 38 | 25 |
| IMACEC a/a | 50 | 25 |
| IPC a/a | 8 | 5 |
| Desempleo | 34 | 25 |

Una fecha de publicación más temprana que el mínimo plausible se trata como error del archivo y se reemplaza por el rezago fijo. Encontramos un caso: el IMACEC de diciembre de 2008 aparecía publicado 5 días después de cerrar el mes, lo que es imposible.

**Limitación:** los valores macro de Bloomberg ya incorporan revisiones posteriores; no son la primera cifra publicada. En nuestros modelos finales las macro no entran, así que el efecto es nulo, pero lo dejamos declarado.

---

## 1.9 Dificultad 4: series eliminadas, empalmadas o incompletas

| Serie | Decisión | Motivo |
|---|---|---|
| LIBOR 1M | Eliminada | Discontinuada en 2024. La reemplazan SOFR y Fed funds. Correlación con el retorno del día siguiente prácticamente nula (+0,008). |
| Bonos BTP 5 y 10 años | Eliminadas | Cobertura de 0% a 60% según el año. El swap a 5 años cubre la misma información. |
| WTI (`CL1`) | Eliminada | El precio negativo del 20 de abril de 2020 hace imposible el retorno logarítmico. Se usa el Brent. |
| IPC m/m | Eliminada | No está desestacionalizado. Se usa el IPC a/a. |
| Puntos forward NDF | Eliminadas | Se usan los rendimientos implícitos `CHNI*`, que contienen la misma información en una escala comparable. |
| `CLPBODM` → `CLPBODMB` | Empalme en diferencias (corte 2022-01-01) | Bloomberg cambió de ticker. Correlación de 0,998 en el traslape. |
| `CLPBLDM` → `CLPBLDMB` | Empalme en diferencias (corte 2022-01-01) | Hay un salto de nivel de −258 MM USD entre ambos tickers. Empalmar en niveles habría creado un movimiento falso; en diferencias desaparece. |

**Relleno hacia adelante:** en todas las series, como máximo 10 días hábiles. Más allá de eso, el dato queda vacío.

### El caso del IPSA

El IPSA era una de las variables con mayor relación con el retorno del día siguiente entre bolsas y commodities, pero la base **termina el 2026-08-31**, justo antes del tramo final y del monitoreo en vivo. Lo mantuvimos con un `flag_ipsa_falta`, y el script acepta un archivo externo (`--ipsa`) que se empalma por razón con los últimos 20 días comunes y se marca con `flag_ipsa_externo`. En la base es el IPSA de retorno total, así que el reemplazo debería ser ese mismo índice.

> [completar: decisión final sobre el IPSA. En la auditoría, el IPSA no entra en los modelos finales.]

---

## 1.10 Carry y objetivos

**Carry.** Lo calculamos como:

$$
\text{carry}_t = (\text{TPM}_t - i^{USD}_t)\times\frac{\text{días corridos hasta la próxima jornada}}{360}
$$

en puntos base, donde $i^{USD}$ es SOFR desde abril de 2018 y Fed funds antes. Una posición comprada en dólar paga el carry y una corta lo recibe. Los viernes y las vísperas de feriado el carry se triplica o más, porque cubre varios días corridos.

Su magnitud no es despreciable: entre 2010 y 2026, comprar dólar siempre da +67,2% bruto y +26,4% neto de carry. En 2022 el dólar subió 0,9%, pero comprar siempre terminó en −6,1%.


**Objetivos:**

| Columna | Definición |
|---|---|
| `y_ret_pb` | Retorno logarítmico del USD/CLP de *t* a *t+1*, en pb. |
| `y_ret_neto_pb` | Retorno menos carry: lo que gana un largo 1x antes de costos. |
| `y_sube` | 1 si el dólar sube de *t* a *t+1*. |
| `y_sube_neto` | 1 si conviene estar comprado (el dólar sube más que el carry). |

Con datos hasta el 2026-10-06 hay **6.047 objetivos válidos** desde 2001.

---

## 1.11 Transformaciones y variables

Ninguna serie entra en niveles crudos de precio, porque no son estacionarias. Aplicamos:

| Familia | Transformación | Ejemplos |
|---|---|---|
| Precios (monedas, commodities, bolsas) | Retorno logarítmico diario en pb | `x_usdzar_ret`, `x_cobre_lme_ret`, `x_spx_ret` |
| Tasas | Diferencia diaria en pb | `x_chswp5_dif`, `x_usgg10yr_dif` |
| Volatilidades e índices de riesgo | Nivel y diferencia | `x_vix`, `x_vix_dif`, `x_move` |
| USD/CLP | Retorno y 4 rezagos, momentum 5/20/60, vol. realizada 5/20/60, rango y cuerpo OHLC | `x_usdclp_mom20`, `x_usdclp_vol20` |
| Construidas | Prima de vol. (implícita 1M − realizada 20d), basis NDF − TPM, pendiente de swaps 10a−1a, inflación implícita 2a, diferencial swap CLP 2a − Tesoro 2a, tasa de cámara implícita en `CLICP` | `x_vol_prima`, `x_basis_ndf1m` |
| Flujos de la banca | Cambio diario y de 20 días, rezago 2 días | `x_pos_offshore_dif20` |
| Macro | Último valor publicado y su cambio (point-in-time) | `x_imacec_aa`, `x_ipc_aa_cambio` |
| Calendario | Día de la semana, días corridos hasta la próxima jornada | `cal_dia_semana` |

El diccionario completo (descripción, fuente, rezago, primer dato y cobertura por tramo de cada columna) está en la hoja `diccionario_variables` de cada base generada.

**Lo que decidimos no hacer:**

- **No desestacionalizar.** Encontramos un efecto día de la semana estable (el retorno viernes→lunes promedia +9 pb en cuatro subperiodos distintos), pero ningún efecto mes. Para predecir, ese patrón es señal y no ruido. Además, métodos como X-13 o STL usan datos futuros. Lo incorporamos como variable (`cal_dia_semana`).
- **No usar diferenciación fraccional.** La probamos (López de Prado, cap. 5) y no mejoró a un clasificador ingenuo en walk-forward; además, el orden *d* óptimo cambiaba según la ventana.
- **No normalizar en la base** (principio 3).

---

## 1.12 Verificaciones

| Prueba | Qué detecta | Resultado |
|---|---|---|
| **Truncamiento:** generar la base cortada en una fecha (2011-11-16 y 2019-06-28) y comparar con la base completa hasta esa fecha | Cualquier cálculo que use datos posteriores a *t* | Primera versión: 15 y 2 columnas difieren. Tras las correcciones de 1.6 y 1.8: **0 diferencias**. |
| Correlación de cada `x_*` con el objetivo de *t+1* | Fugas groseras (una variable que “ve” el objetivo) | Ninguna supera \|0,09\|. |
| Feriados vs series locales | Feriados que la librería no conoce | Ninguno. |
| Infinitos y valores imposibles | Errores de transformación | Ninguno. |

---

## 1.13 Hallazgos de los datos que condicionan el modelado

Estos resultados surgieron durante la limpieza y determinaron decisiones posteriores:

- **Cierre asincrónico.** Varias series cierran en Nueva York (17:00 ET) o São Paulo, *después* del cierre de Santiago: ZAR, MXN, BRL, DXY, S&P 500, VIX, entre otras. Las bases permiten usarlas como información de *t*, y son las que más se relacionan con el retorno del día siguiente. Pero su “poder predictivo” se concentra en la **apertura** del día siguiente (la noticia global que ocurrió después del cierre local), no en la jornada, y ese efecto prácticamente desapareció desde 2024. Por eso mantenemos dos versiones del modelo: **torneo** (todas las series al cierre de *t*) y **estricta** (las series que cierran después de Santiago, rezagadas un día). Ver sección [X].
- **El dólar observado no sirve como dato de hoy.** `CLFXDOOB` de *t* corresponde aproximadamente al spot de *t−1* y se publica en la mañana. Ni como variable ni como objetivo.
- **El carry cambia el umbral de decisión.** Comprar y vender no son simétricos: el umbral para comprar no es 0 sino el carry más los costos.

---

## 1.14 Limitaciones y pendientes

- La fórmula del carry y el costo de transacción deben confirmarse contra el código de evaluación del laboratorio.
- El rezago de 2 días para los flujos de la banca es un supuesto conservador, no verificado.
- Las fechas de publicación macro están incompletas antes de 2019 y los valores incluyen revisiones.
- No podemos verificar si Bloomberg revisó retroactivamente cierres históricos.
- El relleno del spot en 2011-2012 introduce ruido en las variables de esos años (marcado con `flag_usdclp_relleno` y `flag_vol20_contaminada`).

---

## 1.15 Cómo reproducir

```bash
python preparar_base_v2.py "base_usdclp 2.xlsx" datos/procesados/ [--ipsa ipsa.csv]
```

Dependencias: `pandas`, `numpy`, `openpyxl`, `holidays`.

---

### Referencias

- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Lo, A. y MacKinlay, A. C. (1990). An econometric analysis of nonsynchronous trading. *Journal of Econometrics*, 45, 181-211.
- Scholes, M. y Williams, J. (1977). Estimating betas from nonsynchronous data. *Journal of Financial Economics*, 5, 309-327.
