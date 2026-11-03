# ¿Sube o baja el dólar mañana? · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas · Facultad de Economía y Negocios, Universidad de Chile

[completar: nombres de la pareja]

---

## Qué hace este repositorio

Construye una estrategia diaria sobre el USD/CLP en dos etapas:

1. **Modelo 1 · Dirección.** Estima la probabilidad de que mañana convenga estar comprado en dólares (que el dólar suba más que el carry).
2. **Modelo 2 · Exposición.** Traduce esa probabilidad en una posición de **−3, −1, 0, +1 o +3** veces el nocional, según la confianza del modelo 1 y la volatilidad pronosticada. Cuando la señal es débil, la estrategia se abstiene (0).

Todas las decisiones usan solo información disponible al cierre de Santiago del día de la decisión.

[completar: una o dos frases con la versión final de cada modelo]

## Resultado principal

[completar al final: resultado fuera de muestra neto de carry, antes y después de costos, frente a *comprar siempre*, *no operar nunca* y *operar siempre con exposición 1*, con su significancia (Diebold-Mariano y bootstrap).]

---

## Estructura

```
├── README.md
├── requirements.txt
├── datos/
│   ├── crudos/          ← base_usdclp 2.xlsx (base Bloomberg del laboratorio)
│   └── procesados/      ← bases tratadas; las genera preparar_base_v2.py
├── src/
│   ├── preparar_base_v2.py   ← limpieza y construcción de variables
│   └── [completar: scripts de modelo 1, modelo 2 y evaluación]
├── resultados/          ← señales, tablas y gráficos generados
└── informe/             ← informe metodológico
    ├── README.md
    └── 01_datos_y_limpieza.md
```

[ajustar: la estructura a la estructura base entregada por el laboratorio]

---

## Cómo ejecutarlo

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Poner la base cruda

Copiar `base_usdclp 2.xlsx` (entregada por el laboratorio Bloomberg) en `datos/crudos/`.

[confirmar con el laboratorio si la base puede publicarse en el repositorio. Si no, este paso indica cómo obtenerla.]

### 3. Generar las bases tratadas

```bash
python src/preparar_base_v2.py "datos/crudos/base_usdclp 2.xlsx" datos/procesados/
```

Genera tres cortes (desde 2001, 2010 y 2018) en `.csv` y `.xlsx`. Opcional: `--ipsa ipsa.csv` completa el IPSA después del 2026-08-31 (CSV con columnas `fecha,valor`). El detalle está en la [sección 1 del informe](informe/01_datos_y_limpieza.md).

### 4. Correr los modelos y la evaluación

```bash
[completar: comandos del modelo 1, modelo 2 y evaluación]
```

### 5. Señal del día

[completar: comando que entrega la dirección esperada, la probabilidad y la posición sugerida para la jornada siguiente]

### En Google Colab

Subir el repositorio (o clonarlo) y ejecutar en una celda:

```python
!git clone [completar: URL del repositorio]
%cd [completar: nombre de la carpeta]
!pip install -q -r requirements.txt
!python src/preparar_base_v2.py "datos/crudos/base_usdclp 2.xlsx" datos/procesados/
```

---

## Protocolo de validación

| Tramo | Fechas | Uso |
|---|---|---|
| Desarrollo | 2005-01 → 2021-12 | Elegir variables, hiperparámetros y umbrales |
| Validación | 2022-01 → 2024-12 | Comparar configuraciones |
| Test | 2025-01 → 2026 | Evaluación final, mirada una sola vez |

Todos los modelos se estiman con ventana móvil (walk-forward) y solo con el pasado. [confirmar: tramos finales usados por el modelo elegido]

---

## Entregables exigidos por las bases

| Entregable | Dónde |
|---|---|
| Señal del día (dirección, probabilidad, posición sugerida) | [completar] |
| Curva de resultado neto de costos vs. las tres referencias | [completar] |
| Lectura de la convicción (días de máxima exposición y de abstención) | [completar] |
| Informe metodológico | [`informe/`](informe/README.md) |

---

## Datos

Series diarias de Bloomberg entregadas por el laboratorio: USD/CLP (OHLC), monedas, commodities, bolsas, tasas locales y de EE.UU., volatilidades, posiciones de la banca y series macro. Todas son datos públicos de mercado.

## Licencia

[completar: licencia abierta del repositorio, por ejemplo MIT]
