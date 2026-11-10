# 0. Problema, reglas y criterio de evaluación

> **Resumen.** El torneo pide predecir si el dólar sube o baja en Chile al día siguiente y convertir esa predicción en una posición de −3, −1, 0, +1 o +3. Gana la estrategia con mayor valor económico neto de carry y costos, no la que más acierta. Como predecir una moneda a un día es apenas mejor que el azar, el problema central es **saber cuándo apostar y cuándo abstenerse**. Nuestra respuesta es un sistema de dos modelos. El primero estima la dirección y su probabilidad promediando un LSTM y una regresión logística que se reentrenan cada mes y aprenden sobre todo del pasado reciente (por eso lo llamamos **adaptativo**). El segundo decide el tamaño de la posición según la confianza de esa probabilidad y la volatilidad esperada por un GARCH(1,1).

---

## 0.1 El problema

Cada día hábil, al cierre del mercado chileno, la estrategia debe decidir su exposición al USD/CLP para la jornada siguiente:

| Exposición | Significado |
|---|---|
| +3 / +1 | Comprar dólares (3 o 1 vez el nocional) |
| 0 | Quedarse en pesos |
| −1 / −3 | Vender dólares en corto (1 o 3 veces el nocional) |

**Resultado de cada jornada** (según las bases):

$$\text{resultado}_t = e_t \times \Delta \text{USD/CLP}_{t \to t+1} \;-\; \text{carry}_t \;-\; \text{costos}_t$$

- **Carry:** diferencial entre la tasa *overnight* en pesos y la tasa en dólares. Una posición comprada en dólares lo paga y una corta lo recibe. Con tasas chilenas mayores que las de EE.UU., estar comprado tiene un costo diario.
- **Costos de transacción:** se pagan al cambiar la exposición.

---

## 0.2 Reglas que condicionan el diseño

| Regla de las bases | Consecuencia para el modelo |
|---|---|
| Solo información disponible hasta el cierre de la jornada previa | Toda variable de la fila *t* usa datos conocidos al cierre de *t* (sección 1.2). El diccionario del laboratorio establece que los cierres de una misma fecha se asumen disponibles al decidir. |
| Se premia la **calibración** y no la precisión | El modelo 1 entrega una probabilidad y se entrena con log-loss, que castiga la sobreconfianza (sección 4). |
| Gana el mayor **valor económico neto**, no el mayor acierto | Los umbrales del modelo 2 se eligen por retorno neto de carry y costos (sección 5). |
| Exposiciones discretas {−3, −1, 0, +1, +3} | El modelo 2 traduce la probabilidad en uno de esos cinco niveles. |
| Solo datos públicos de mercado vía Bloomberg | Usamos únicamente la base del laboratorio (sección 1). |

---

## 0.3 Cómo se evalúa

| Instancia | Qué se mide |
|---|---|
| **Evaluación técnica** | Rentabilidad neta de carry y costos en el tramo final fuera de muestra, reportada antes y después de costos. |
| **Significancia** | Diebold-Mariano (calidad de la predicción) y bootstrap no paramétrico (resultado económico) contra las referencias. |
| **Referencias** | Comprar siempre, no operar nunca y operar siempre con exposición 1. |
| **Monitoreo en vivo** | La estrategia opera en modo simulado con datos reales diarios desde el 13 de noviembre hasta el 1 de diciembre de 2026. |
| **Final** | Presentación ante un jurado de Banco Itaú, académicos de la FEN y el CENIA: calidad técnica y capacidad de defender los resultados. |

---

## 0.4 Nuestro enfoque en una página

```
Base Bloomberg ──► limpieza (sección 1) ──► 11 variables (sección 2)
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         │  MODELO 1 · dirección (sección 4)          │
                         │  promedio de LSTM (20 días) y logística    │
                         │  reentrenados cada 21 días, con más peso   │
                         │  en el pasado reciente (adaptativo)        │
                         │  → p = P(conviene estar comprado)          │
                         └─────────────────────┬─────────────────────┘
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         │  MODELO 2 · exposición (sección 5)         │
                         │  percentil de confianza → 0 / 1 / 3        │
                         │  GARCH(1,1) → recorta el 3 en días agitados│
                         └─────────────────────┬─────────────────────┘
                                               │
                              exposición ∈ {−3, −1, 0, +1, +3}
```

**Principios que guiaron el trabajo:**

1. **Primero no engañarse.** Con señales tan débiles, el mayor riesgo es encontrar una estrategia que parece rentable solo porque se ajustó al pasado. Por eso el protocolo separa tramos, usa walk-forward, cuenta todas las configuraciones probadas y aplica pruebas contra fugas (sección 3).
2. **Simple antes que complejo.** Probamos modelos flexibles (árboles, aprendizaje por refuerzo, búsqueda exhaustiva de variables) y en general rindieron peor fuera de muestra (sección 8).
3. **Las relaciones cambian.** Las que explotaba la primera versión del sistema se debilitaron desde 2024 y se invirtieron en 2025-2026. Un modelo que aprende sobre todo del pasado reciente las sigue mejor, a cambio de rendir menos cuando son estables (secciones 4 y 6).
4. **Separar dirección y tamaño.** La volatilidad no predice hacia dónde se mueve el dólar, pero sí cuánto (sección 2.6). Por eso informa al modelo 2 y no al modelo 1.

---

## 0.5 Estructura del informe

| Sección | Contenido |
|---|---|
| 1 | Datos y limpieza |
| 2 | Análisis exploratorio y selección de variables |
| 3 | Protocolo de validación |
| 4 | Modelo 1: dirección |
| 5 | Modelo 2: exposición |
| 6 | Resultados y significancia |
| 7 | Lectura de la convicción |
| 8 | Modelos probados y descartados |
| 9 | Limitaciones, riesgos y operación en vivo |
