# 7. Lectura de la convicción

> **Resumen.** Las bases piden diagnosticar las jornadas de máxima exposición y aquellas en que el modelo se abstuvo. En validación, el sistema **se abstiene en ~60% de los días** y usa exposición 3 en ~19%. **Toda la ganancia viene de los días con exposición 3**: aciertan 61-62% de las veces (promedio y logística) y aportan más del 100% del resultado. En cambio, los días con exposición 1 pierden. En los días de abstención, la dirección del modelo no es mejor que una moneda, así que no operar evitó pérdidas. La convicción alta aparece cuando el dólar global, el rand, el oro y el cobre se mueven con fuerza el mismo día, no por efectos de calendario.

---

## 7.1 Cómo se reparte la exposición y qué aporta cada nivel

Validación 2022-2024, 1 pb de costo. “Acierto” es el % de días en que la dirección del modelo coincide con la que convenía; “retorno de la dirección” es el retorno neto de carry con exposición 1 en la dirección del modelo; “aporte” es la parte del resultado total que genera cada nivel.

### Promedio LSTM + logística

| Exposición | Días | % de días | Acierto | Retorno de la dirección (pb/día) | Resultado medio (pb/día) | Aporte al total |
|---|---|---|---|---|---|---|
| 0 (abstención) | 434 | 58% | 49,5% | −1,0 | −0,7 | −4% |
| ±1 | 170 | 23% | 51,8% | −5,3 | −6,5 | −15% |
| **±3 (máxima)** | **141** | **19%** | **61,0%** | **+21,4** | **+61,9** | **+119%** |

### Logística

| Exposición | Días | % de días | Acierto | Retorno de la dirección (pb/día) | Resultado medio (pb/día) | Aporte al total |
|---|---|---|---|---|---|---|
| 0 | 442 | 59% | 50,0% | −1,0 | −0,8 | −5% |
| ±1 | 170 | 23% | 51,8% | −7,5 | −8,7 | −21% |
| **±3** | **133** | **18%** | **62,4%** | **+23,0** | **+66,2** | **+126%** |

### LSTM 20 días

| Exposición | Días | % de días | Acierto | Retorno de la dirección (pb/día) | Resultado medio (pb/día) | Aporte al total |
|---|---|---|---|---|---|---|
| 0 | 283 | 38% | 46,6% | −7,8 | −0,7 | −4% |
| ±1 | 322 | 43% | 53,4% | +4,3 | +3,4 | +21% |
| **±3** | **140** | **19%** | **53,6%** | **+10,7** | **+30,5** | **+83%** |

El resultado medio por día de los niveles 0 no es exactamente cero por el costo de cerrar posiciones.

**Lectura:**

- **La convicción ordena bien en los extremos.** En las tres señales, el acierto sube de ~50% en los días de abstención a 54-62% en los de máxima exposición.
- **El nivel intermedio no aporta en el promedio ni en la logística:** los días con ±1 aciertan ~52% y pierden después de costos. El LSTM es la excepción: su nivel ±1 sí gana, y su exposición 3 es menos precisa.
- **El patrón se repite fuera de validación.** En la parte 1 del desarrollo (2005-2014), que no se usó para elegir nada, los días con exposición 3 del promedio aciertan 56,4% y aportan el 120% del resultado; los de ±1 y 0 quedan cerca de cero.

---

## 7.2 Las jornadas de máxima exposición

### ¿Qué las distingue?

Tamaño típico de cada variable en los días de cada nivel (valor absoluto estandarizado; 1 = un movimiento de una desviación estándar), promedio LSTM + logística, validación:

| Variable | Días en 0 | Días en ±1 | Días en ±3 |
|---|---|---|---|
| BBDXY (dólar global) | 0,55 | 0,79 | **1,09** |
| DXY | 0,59 | 0,82 | **1,01** |
| Rand (USD/ZAR) | 0,50 | 0,70 | **0,98** |
| Oro | 0,54 | 0,65 | **0,88** |
| Cobre COMEX | 0,60 | 0,63 | **0,83** |
| Cobre LME | 0,55 | 0,58 | **0,75** |
| MSCI EM | 0,60 | 0,66 | 0,67 |
| Cambio vol. EM | 0,31 | 0,35 | 0,33 |
| Viernes / días corridos | 0,81 | 0,80 | 0,75 |

**La convicción alta aparece en días de movimientos fuertes y coordinados del dólar global, el rand, el oro y el cobre**, es decir, cuando ocurre una noticia global que todavía no se refleja en el cierre de Santiago (sección 2.4). Las variables de calendario no explican la convicción: los viernes son 17% de los días con exposición 3, igual que en el resto de la muestra.

### Otras características

| Rasgo (validación, promedio) | Valor |
|---|---|
| Dirección | **72% de los días con exposición 3 son ventas de dólar** (102 de 141). Las ventas acertaron 60,8% y aportaron +6.445 pb; las compras, 61,5% y +2.286 pb. |
| Volatilidad | La volatilidad relativa media es 1,0, igual que en los demás días. La convicción no depende de días agitados. |
| Tamaño del movimiento | El movimiento medio del dólar es similar en todos los niveles (76-80 pb). La ganancia viene de acertar la dirección, no de elegir días más volátiles. |
| Dónde se gana | En los días con exposición 3, la dirección gana +12,1 pb en el salto de apertura y +9,2 pb durante la jornada siguiente. A diferencia del promedio de la muestra, en estos días también hay ganancia intradía. |
| Estabilidad | Entre 18% y 21% de los días de cada año de validación tienen exposición 3. |

### Días con mayor y menor resultado (validación, promedio)

| Fecha | Exposición | Resultado (pb) | Contexto |
|---|---|---|---|
| 2023-10-26 | −3 | +846 | |
| 2024-04-02 | −3 | +641 | |
| 2022-07-05 | +3 | +635 | Semanas de máximos históricos del dólar en Chile |
| 2024-03-07 | −3 | +618 | |
| 2022-12-20 | −3 | +571 | |
| 2024-05-31 | +3 | −494 | |
| 2024-04-29 | −3 | −595 | |
| 2022-07-06 | +3 | −648 | |
| 2024-11-07 | −3 | −729 | |
| 2022-07-14 | +1 | −740 | Anuncio del programa de intervención cambiaria del Banco Central (US$ 25.000 millones), después del cierre |

El peor día ilustra el principal riesgo: **una noticia local que ocurre fuera del horario de las variables globales**. El 14 de julio de 2022 el Banco Central anunció su intervención cambiaria y el dólar cayó con fuerza al día siguiente. El modelo, que lee mercados externos, estaba comprado.

---

## 7.3 Las jornadas de abstención

| Diagnóstico (validación) | Promedio | Logística | LSTM |
|---|---|---|---|
| Días sin operar | 434 (58%) | 442 (59%) | 283 (38%) |
| Acierto de la dirección del modelo en esos días | 49,5% | 50,0% | 46,6% |
| Resultado si se hubiera operado ±1 en esos días | −438 pb | −440 pb | −2.206 pb |

**Abstenerse fue correcto.** En los días en que el modelo no opera, su dirección acierta como una moneda (o peor, en el LSTM), y operarlos habría restado resultado. El modelo reconoce cuándo no tiene información, que es lo que las bases describen como la principal dificultad del problema.

---

## 7.4 El papel del GARCH

El tope del GARCH (un 3 baja a 1 si la volatilidad relativa supera 1,5) cambió la exposición en **unos 20 días de validación, todos entre julio y octubre de 2022**, el periodo de máxima volatilidad del peso (dólar sobre $1.000 e intervención del Banco Central). En esos días, reducir el tamaño sumó +1.377 pb al promedio, +1.206 pb a la logística y +2.218 pb al LSTM, y bajó la máxima caída del promedio de −30,5% a −18,6% (sección 6.2).

El GARCH actúa como un seguro que se activa pocas veces. Su aporte en validación depende de un solo episodio.

---

## 7.5 Conclusiones

1. **El valor del sistema está en distinguir cuándo apostar fuerte y cuándo no apostar.** Más del 100% del resultado viene del ~19% de días con exposición 3, y los días de abstención tienen una dirección indistinguible del azar.
2. **La convicción tiene una lectura económica clara:** aparece con movimientos grandes y coordinados del dólar global y de las materias primas, que el peso chileno todavía no ha incorporado al cierre.
3. **El nivel intermedio (±1) no aporta** en el promedio ni en la logística. Es una observación para el futuro, no un cambio al sistema: modificarlo ahora sería elegir con validación.
4. **El principal riesgo son las noticias locales** fuera del alcance de las variables, como la intervención del Banco Central de julio de 2022.

### Referencias

- Banco Central de Chile (2022). Comunicado del 14 de julio de 2022: programa de intervención cambiaria y provisión preventiva de liquidez en dólares. https://www.bcentral.cl/contenido/-/detalle/comunicado-14072022
