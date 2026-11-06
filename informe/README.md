# Informe metodológico · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas: ¿Sube o baja el dólar mañana?

Vicente Acevedo y Luis Portillo

## Resumen ejecutivo

**Estrategia.** Usamos dos modelos. El **modelo 1** estima la probabilidad de que convenga estar comprado en dólares al día siguiente, neto de carry. Reportamos tres señales: un LSTM de 20 días, una logística regularizada y el promedio de ambas. Las tres usan las mismas 11 variables: cobre, oro, dólar global (DXY y BBDXY), rand, acciones emergentes, volatilidad emergente y calendario. El **modelo 2** convierte esa probabilidad en una exposición. Se abstiene cuando la confianza es baja, usa ±1 cuando es media y ±3 cuando es alta, y un GARCH(1,1) baja el 3 a 1 cuando la volatilidad esperada supera 1,5 veces su nivel normal. Todo se evalúa en walk-forward: cada día se predice con modelos entrenados solo con datos anteriores.

**Resultado fuera de muestra (validación 2022-2024, neto de carry).**

| Señal | Sin costos | Con 1 pb | Sharpe (1 pb) | Comprar siempre |
|---|---|---|---|---|
| Promedio LSTM + logística | +126,3% | +107,7% | 1,16 | +3,0% |
| Logística | +120,3% | +101,1% | 1,15 | |
| LSTM 20 días | +79,6% | +67,3% | 0,82 | |

El resultado se mantiene en 2005-2014, un tramo que no se usó para ninguna elección: el promedio ganó +82,4% y la logística +126,0%, frente a −2,9% de comprar siempre.

[completar: resultado en el tramo de test con el código de evaluación del laboratorio]

**Significancia.** En validación, las tres señales superan a operar siempre ±1 (bootstrap por bloques, p = 0,013-0,022), y el promedio y la logística también superan a no operar (p = 0,030 y 0,042). Ninguna supera a comprar siempre al 5%. La dirección elegida por el modelo le gana a una dirección al azar con la misma exposición en el 98-99% de los sorteos (promedio y logística).

**Dónde está el valor.** El sistema no opera en ~60% de los días, y en esos días su dirección no es mejor que una moneda. Más del 100% del resultado proviene del ~19% de días con exposición 3, que aciertan 61-62%. Esos días coinciden con movimientos fuertes y coordinados del dólar global y las materias primas que el peso todavía no incorporó al cierre de Santiago.

**Limitaciones.**

1. Más de la mitad de la ganancia se genera en la apertura del día siguiente, por el desfase de horarios de cierre. Ese canal se debilitó desde 2024, año en que el sistema quedó cerca de cero.
2. Corregido por las ~310 configuraciones probadas (Sharpe deflactado), la evidencia no es concluyente.
3. Las noticias locales, como la intervención del Banco Central en julio de 2022, quedan fuera del alcance de las variables.

Por estas razones esperamos un desempeño en vivo menor al de 2022-2023.

## Índice

| # | Sección | Estado |
|---|---|---|
| 0 | [Problema, reglas y criterio de evaluación](00_problema_y_reglas.md) | borrador |
| 1 | [Datos y limpieza](01_datos_y_limpieza.md) | borrador |
| 2 | [Análisis exploratorio y selección de variables](02_analisis_exploratorio_y_variables.md) | borrador |
| 3 | [Protocolo de validación](03_protocolo_validacion.md) | borrador |
| 4 | [Modelo 1: dirección](04_modelo1_direccion.md) | borrador |
| 5 | [Modelo 2: exposición (−3, −1, 0, +1, +3)](05_modelo2_exposicion.md) | borrador |
| 6 | [Resultados fuera de muestra y significancia](06_resultados_y_significancia.md) | borrador |
| 7 | [Lectura de la convicción](07_lectura_conviccion.md) | borrador |
| 8 | [Modelos probados y descartados](08_modelos_descartados.md) | borrador |
| 9 | [Limitaciones, riesgos y operación en vivo](09_limitaciones_y_operacion.md) | borrador |

## Convenciones del informe

- Retornos en puntos base (pb), logarítmicos.
- *t* es el día de la decisión (al cierre de Santiago); *t+1* es la jornada que se predice.
- Los textos entre corchetes `[completar: …]` o `[confirmar: …]` marcan datos pendientes.
