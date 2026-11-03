# Informe metodológico · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas: ¿Sube o baja el dólar mañana?

Vicente Acevedo y Luis portillo

## Resumen ejecutivo

[completar al final: estrategia elegida, resultado fuera de muestra neto de carry y costos (antes y después de costos), significancia contra las referencias y principales limitaciones]

## Índice

| # | Sección | Estado |
|---|---|---|
| 0 | Problema, reglas y criterio de evaluación | pendiente |
| 1 | [Datos y limpieza](01_datos_y_limpieza.md) | borrador |
| 2 | Análisis exploratorio y selección de variables (IC, estacionalidad, no linealidad, cierre asincrónico) | pendiente |
| 3 | Protocolo de validación (tramos, walk-forward, purga y embargo, test de una sola vez) | pendiente |
| 4 | Modelo 1: dirección | pendiente |
| 5 | Modelo 2: exposición (−3, −1, 0, +1, +3) | pendiente |
| 6 | Resultados fuera de muestra y significancia (Diebold-Mariano, bootstrap, Sharpe deflactado) | pendiente |
| 7 | Lectura de la convicción (jornadas de máxima exposición y de abstención) | pendiente |
| 8 | Modelos probados y descartados | pendiente |
| 9 | Limitaciones, riesgos y operación en vivo | pendiente |

## Convenciones del informe

- Retornos en puntos base (pb), logarítmicos.
- *t* es el día de la decisión (al cierre de Santiago); *t+1* es la jornada que se predice.
- Los textos entre corchetes `[completar: …]` o `[confirmar: …]` marcan datos pendientes.
