# Informe metodológico · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas: ¿Sube o baja el dólar mañana?

[completar: nombres de la pareja]

## Resumen ejecutivo

**Estrategia.** El sistema tiene dos modelos.

- **Modelo 1:** estima la probabilidad de que convenga estar comprado en dólares al día siguiente, neto de carry. Es el promedio de dos componentes que usan las mismas 11 variables (cobre, oro, dólar global, rand, acciones emergentes, volatilidad emergente y calendario):
  - un **LSTM** que mira los últimos 20 días;
  - una **regresión logística**.
- **Modelo 2:** convierte esa probabilidad en una exposición. Se abstiene cuando la confianza es baja, usa ±1 cuando es media y ±3 cuando es alta. Un **GARCH(1,1)** baja el 3 a 1 cuando la volatilidad esperada supera 1,5 veces su nivel normal.

**Qué lo hace adaptativo.** Ambos componentes se reentrenan cada 21 días y aprenden sobre todo del pasado reciente:

- el LSTM usa toda la historia, pero cada día pesa la mitad que uno de un año después;
- la logística usa solo los últimos 500 días (unos dos años).

Así los pesos siguen a las relaciones que cambian. Por ejemplo, el coeficiente del rand pasó de positivo a negativo en 2025, cuando el peso dejó de seguir con un día de retraso a las monedas emergentes. La versión anterior (**sistema base**: toda la historia con igual peso, reentrenada cada 126 días) se reporta como control.

**Resultado fuera de muestra (walk-forward, neto de carry y 1 pb de costo).**

| Tramo | Sistema adaptativo | Sistema base (control) | Comprar siempre |
|---|---|---|---|
| Desarrollo, parte 1 · 2005-2014 | **+205,2%** (Sharpe 1,12) | +85,5% (0,58) | −2,9% |
| Desarrollo, parte 2 · 2015-2021 | +137,4% (0,79) | **+284,3%** (1,17) | +20,5% |
| Validación · 2022-2024 | +63,7% (0,80) | **+107,7%** (1,16) | +3,0% |
| Test · 2025 a oct-2026 | **+13,4%** (0,47) | −18,5% (−0,81) | −4,4% |
| Datos reales · 6-oct a 5-nov-2026 (22 días) | **−1,0%** | −9,8% | +0,4% |

**Por qué cambiamos de sistema, y con qué cautela.** El sistema base ganaba más en 2015-2024, pero perdió en 2025-2026: las relaciones que explotaba se debilitaron o se invirtieron. El adaptativo cuesta rentabilidad cuando las relaciones son estables y protege cuando cambian. Sumando 2006-2026, ambos rinden casi lo mismo: diferencia de +0,2 pb/día, p = 0,45.

**El adaptativo se eligió después de ver la validación, el test y los datos de octubre-noviembre.** Con la regla fijada al inicio (elegir en 2015-2021) habría ganado el sistema base. Por eso 2025-2026 no cuenta como un test limpio para el adaptativo. La evidencia más limpia a su favor es 2005-2014, un tramo que no se usó en ninguna elección: ahí rinde más del doble que el base.

**Significancia.** En validación y en el test, el adaptativo supera a operar siempre ±1 (bootstrap por bloques, p = 0,028 y 0,013). En 2005-2014 supera a las tres referencias (p ≤ 0,026) y en 2015-2021 supera a no operar (p = 0,024). En validación y en el test no supera a comprar siempre ni a no operar al 5%. Corregido por las ~349 configuraciones probadas (Sharpe deflactado), solo 2005-2014 da una probabilidad mayor a 0,5 de que el Sharpe verdadero sea positivo.

**Dónde está el valor.** El sistema no opera en el ~60% de los días, y en esos días su dirección no es mejor que una moneda. Los días con exposición 3 (15-20% del total) explican casi todo el resultado. En el test, el adaptativo usó menos ese tamaño (15% de los días, contra 17% del base) y esos días ganaron. Los del base perdieron.

**Limitaciones.**

1. Elegimos el sistema mirando el tramo en que gana. La única evaluación sin contaminación es el monitoreo en vivo, con los parámetros congelados desde el 9 de noviembre de 2026.
2. El resultado depende de pocos días: sin los 10 mejores días del test, el adaptativo pierde 25%.
3. Las probabilidades del adaptativo están peor calibradas que la frecuencia base en el test.
4. El resultado varía con las semillas del LSTM.
5. Las noticias locales, como la intervención del Banco Central en julio de 2022, quedan fuera del alcance de las variables.

## Índice

| # | Sección | Estado |
|---|---|---|
| 0 | [Problema, reglas y criterio de evaluación](00_problema_y_reglas.md) | borrador |
| 1 | [Datos y limpieza](01_datos_y_limpieza.md) | borrador |
| 2 | [Análisis exploratorio y selección de variables](02_analisis_exploratorio_y_variables.md) | borrador |
| 3 | [Protocolo de validación](03_protocolo_validacion.md) | borrador |
| 4 | [Modelo 1: dirección (adaptativo)](04_modelo1_direccion.md) | borrador |
| 5 | [Modelo 2: exposición (−3, −1, 0, +1, +3)](05_modelo2_exposicion.md) | borrador |
| 6 | [Resultados fuera de muestra y significancia](06_resultados_y_significancia.md) | borrador |
| 7 | [Lectura de la convicción](07_lectura_conviccion.md) | borrador |
| 8 | [Modelos probados y descartados](08_modelos_descartados.md) | borrador |
| 9 | [Limitaciones, riesgos y operación en vivo](09_limitaciones_y_operacion.md) | borrador |

## Convenciones del informe

- Retornos en puntos base (pb), logarítmicos.
- *t* es el día de la decisión (al cierre de Santiago); *t+1* es la jornada que se predice.
- Salvo que se indique otra cosa, las cifras son netas de carry con 1 pb de costo por unidad de cambio de exposición.
- El sistema opera desde febrero de 2006: antes, el GARCH y el percentil de confianza todavía no tienen la historia que necesitan.
- Los textos entre corchetes `[completar: …]` o `[confirmar: …]` marcan datos pendientes.
