# 7. Lectura de la convicción

> **Resumen.** Las bases piden diagnosticar las jornadas de máxima exposición y aquellas en que el modelo se abstuvo. El sistema adaptativo **se abstiene en el 58-65% de los días** y usa exposición 3 en el 15-20%. En todos los tramos, **los días con exposición 3 explican casi todo el resultado**: ganan alrededor de +30 pb por día y los 10 mejores días de cada tramo son todos de ese nivel. En los días de abstención, la dirección del modelo no es mejor que una moneda (44-50% de acierto), así que no operar evitó pérdidas. La diferencia con el sistema base en 2025-2026 está en los ±3: los del adaptativo ganaron y los del base perdieron.

---

## 7.1 Cómo se reparte la exposición y qué aporta cada nivel

Columnas de las tablas:

- **Acierto:** % de días en que la dirección del modelo coincide con la que convenía.
- **Retorno de la dirección:** retorno neto de carry con exposición 1 en la dirección del modelo.
- **Resultado medio:** resultado diario con la exposición efectiva y 1 pb de costo.
- **Aporte:** parte del resultado total del tramo que genera cada nivel.

### Sistema adaptativo · validación 2022-2024

| Exposición | Días | % de días | Acierto | Retorno de la dirección (pb/día) | Resultado medio (pb/día) | Aporte al total |
|---|---|---|---|---|---|---|
| 0 (abstención) | 430 | 58% | 49,8% | −6,6 | −0,7 | −6% |
| ±1 | 173 | 23% | 52,0% | +5,0 | +3,8 | +13% |
| **±3 (máxima)** | **142** | **19%** | **55,6%** | **+11,4** | **+32,0** | **+92%** |

### Sistema adaptativo · test 2025-2026

| Exposición | Días | % de días | Acierto | Retorno de la dirección (pb/día) | Resultado medio (pb/día) | Aporte al total |
|---|---|---|---|---|---|---|
| 0 | 284 | 65% | 44,0% | −8,8 | −0,5 | −12% |
| ±1 | 91 | 21% | 49,5% | −6,2 | −7,5 | −54% |
| **±3** | **64** | **15%** | **51,6%** | **+11,7** | **+32,6** | **+166%** |

### En los otros tramos y en el sistema base

| Estrategia · tramo | ±3: días (% del total) | ±3: acierto | ±3: resultado medio | ±3: aporte | ±1: aporte |
|---|---|---|---|---|---|
| Adaptativo · desarrollo p1 | 306 (15%) | 54,9% | +29,6 pb | +81% | +26% |
| Adaptativo · desarrollo p2 | 345 (20%) | 55,7% | +22,4 pb | +89% | +19% |
| *Base · validación* | 141 (19%) | 61,0% | +61,9 pb | +119% | −15% |
| *Base · test* | 73 (17%) | **43,8%** | **−13,8 pb** | −1.008 pb | −845 pb |

El resultado medio de los días en 0 no es exactamente cero por el costo de cerrar posiciones.

**Lectura:**

- **La convicción ordena bien en los extremos.** En todos los tramos, el acierto sube de 44-50% en los días de abstención a 52-56% en los de máxima exposición.
- **El nivel intermedio aporta poco y es frágil.** En 2005-2024 los días con ±1 suman entre 13% y 26% del resultado; en el test pierden.
- **En el test, el base falló donde más apostaba.** Sus días con exposición 3 acertaron 43,8% y perdieron −13,8 pb por día. Los del adaptativo acertaron 51,6% y ganaron +32,6 pb por día. Es la diferencia que explica casi todo el contraste de 2025-2026 (sección 6.3).
- **El adaptativo acierta menos que el base en validación en sus ±3** (55,6% contra 61,0%). Es el costo de la adaptación en un periodo en que las relaciones de largo plazo todavía funcionaban.

---

## 7.2 Las jornadas de máxima exposición

### ¿Qué las distingue?

Tamaño típico de cada variable en los días de cada nivel (valor absoluto estandarizado con 2001-2021; 1 = un movimiento de una desviación estándar), sistema adaptativo:

| Variable | Validación · 0 | ±1 | **±3** | Test · 0 | ±1 | **±3** |
|---|---|---|---|---|---|---|
| BBDXY (dólar global) | 0,60 | 0,74 | **0,98** | 0,55 | 0,63 | **0,85** |
| DXY | 0,62 | 0,78 | **0,96** | 0,59 | 0,61 | **0,83** |
| Rand (USD/ZAR) | 0,57 | 0,67 | **0,79** | 0,44 | 0,48 | **0,66** |
| Oro | 0,56 | 0,68 | **0,79** | 0,84 | 1,20 | **1,61** |
| Cobre COMEX | 0,55 | 0,72 | **0,86** | 0,75 | 0,77 | **1,02** |
| Cobre LME | 0,51 | 0,68 | **0,76** | 0,48 | 0,58 | **0,76** |
| MSCI EM | 0,63 | 0,61 | 0,65 | 0,70 | 0,75 | **1,00** |
| Cambio vol. EM | 0,32 | 0,38 | 0,28 | 0,22 | 0,28 | 0,39 |

**La convicción alta aparece con movimientos fuertes y coordinados del dólar global y de las materias primas.** En el test, el oro pasa a ser la variable más extrema en los días ±3 (1,6 desviaciones), en un periodo de alzas fuertes del oro.

### Otras características

| Rasgo (sistema adaptativo) | Valor |
|---|---|
| Dirección | Las ventas de dólar son el 64% de los ±3 en 2005-2014 y en validación, el 36% en 2015-2021 y el 58% en el test. No hay un sesgo fijo. |
| Volatilidad | La volatilidad relativa media de los días ±3 es 1,0, igual que la del resto. La convicción no depende de días agitados. |
| Dónde se gana | En los ±3 de 2005-2014, la dirección gana +8,5 pb en el salto de apertura y +2,0 pb durante la jornada. En validación (+3,1 y +7,5) y en el test (+1,9 y +9,8), la mayor parte se gana **durante la jornada**. El adaptativo depende cada vez menos del cierre asincrónico. |

### Días con mayor y menor resultado (sistema adaptativo)

| Tramo | Fecha | Exposición | Resultado (pb) | Contexto |
|---|---|---|---|---|
| Test | 2025-04-03 | +3 | +893 | Semana del anuncio de aranceles de EE.UU. (2 de abril de 2025) |
| Test | 2026-03-19 | +3 | +647 | |
| Test | 2025-03-07 | +3 | +504 | |
| Test | 2025-04-10 | −3 | +453 | Semana de la pausa de esos aranceles (9 de abril de 2025) |
| Test | 2025-02-28 | +3 | −406 | |
| Test | 2026-06-17 | −3 | −357 | |
| Validación | 2022-11-15 | −3 | −781 | |
| Validación | 2022-07-14 | +1 | −740 | Anuncio de la intervención cambiaria del Banco Central (US$ 25.000 millones), después del cierre |

El peor día de validación ilustra el principal riesgo: **una noticia local que ocurre fuera del horario de las variables globales**. El 14 de julio de 2022 el Banco Central anunció su intervención cambiaria y el dólar cayó con fuerza al día siguiente. El modelo, que lee mercados externos, estaba comprado.

---

## 7.3 Las jornadas de abstención

| Diagnóstico (sistema adaptativo) | Desarrollo p1 | Desarrollo p2 | Validación | Test |
|---|---|---|---|---|
| Días sin operar | 1.257 (62%) | 1.016 (59%) | 430 (58%) | 284 (65%) |
| Acierto de la dirección del modelo en esos días | 49,9% | 49,8% | 49,8% | 44,0% |
| Resultado si se hubiera operado ±1 en esos días | −156 pb | +1.336 pb | −2.819 pb | −2.499 pb |

**Abstenerse fue correcto.** En los días en que el modelo no opera, su dirección acierta como una moneda, o peor en el test. Operarlos habría restado resultado en tres de los cuatro tramos. El modelo reconoce cuándo no tiene información, que es lo que las bases describen como la principal dificultad del problema.

---

## 7.4 El papel del GARCH

El tope del GARCH (un 3 baja a 1 si la volatilidad relativa supera 1,5) actúa pocos días, casi siempre en crisis:

| Tramo | Días en que cambió la exposición | Aporte al resultado | Cuándo |
|---|---|---|---|
| Desarrollo p1 | 97 | +632 pb | Sobre todo 2008-2009 (crisis financiera) y 2011 |
| Desarrollo p2 | 20 | +662 pb | Julio de 2015, fines de 2019 (estallido social) y marzo-abril de 2020 (covid) |
| Validación | 16 | +163 pb | Julio a octubre de 2022 (dólar sobre $1.000, intervención del Banco Central) |
| Test | 3 | +319 pb | Marzo-abril de 2026 |

En 2005-2014, el GARCH bajó la máxima caída del adaptativo de −36,7% a −15,8%. Actúa como un seguro que se activa pocas veces.

---

## 7.5 Conclusiones

1. **El valor del sistema está en distinguir cuándo apostar fuerte y cuándo no apostar.** Los días con exposición 3 explican casi todo el resultado y los días de abstención tienen una dirección indistinguible del azar.
2. **La convicción tiene una lectura económica clara:** aparece con movimientos grandes y coordinados del dólar global y de las materias primas.
3. **En 2025-2026, la diferencia entre sistemas está en los ±3.** Los del base, aprendidos con relaciones que ya no se cumplían, perdieron. Los del adaptativo ganaron, y su ganancia vino más de la jornada siguiente que del salto de apertura.
4. **El principal riesgo son las noticias locales** fuera del alcance de las variables, como la intervención del Banco Central de julio de 2022.

### Referencias

- Banco Central de Chile (2022). Comunicado del 14 de julio de 2022: programa de intervención cambiaria y provisión preventiva de liquidez en dólares. https://www.bcentral.cl/contenido/-/detalle/comunicado-14072022
