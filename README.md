# ¿Sube o baja el dólar mañana? · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas · Facultad de Economía y Negocios, Universidad de Chile

Vicente Acevedo y José Portillo

---

## Qué hace este repositorio

Construye una estrategia diaria sobre el USD/CLP en dos etapas (**sistema adaptativo**).

**1. Modelo 1 · Dirección.** Estima la probabilidad de que mañana convenga estar comprado en dólares, es decir, que el dólar suba más que el carry. Es el promedio de dos componentes con las mismas 11 variables de mercado y calendario:

- un **LSTM** que mira los últimos 20 días, entrenado con toda la historia y con peso exponencial (un día de hace un año pesa la mitad);
- una **regresión logística** entrenada solo con los últimos 500 días.

Ambos se reentrenan cada 21 días.

**2. Modelo 2 · Exposición.** Traduce esa probabilidad en una posición de **−3, −1, 0, +1 o +3** veces el nocional:

- no opera si la confianza está bajo el percentil 60 de los últimos 250 días;
- usa ±1 entre los percentiles 60 y 80;
- usa ±3 sobre el percentil 80;
- un **GARCH(1,1)** baja el 3 a 1 cuando la volatilidad esperada supera 1,5 veces su mediana reciente.

Todas las decisiones usan solo información disponible al cierre de Santiago del día de la decisión. La versión anterior del modelo 1 (**sistema base**: toda la historia con igual peso, reentrenada cada 126 días) se incluye como control.

## Resultado principal

Walk-forward, neto de carry y 1 pb de costo:

| Tramo | Sistema adaptativo | Sistema base (control) | Comprar siempre |
|---|---|---|---|
| 2005-2014 (no se usó para elegir) | **+205,2%** (Sharpe 1,12) | +85,5% | −2,9% |
| 2015-2021 | +137,4% (0,79) | **+284,3%** | +20,5% |
| Validación 2022-2024 | +63,7% (0,80) | **+107,7%** | +3,0% |
| Test 2025 a oct-2026 | **+13,4%** (0,47) | −18,5% | −4,4% |

**Advertencia:** el adaptativo se eligió después de ver el test. Con la regla fijada al inicio habría ganado el base. El resumen ejecutivo, la significancia y las limitaciones están en el [informe](informe/README.md).

---

## Estructura

```
├── README.md                 ← este archivo: qué hace el repositorio y cómo usarlo
├── requirements.txt
├── datos/
│   └── base_usdclp 2.xlsx    ← base Bloomberg del laboratorio (cruda)
├── src/
│   ├── preparar_base_v2.py        ← 1. limpieza y construcción de variables
│   ├── modelo_adaptativo_colab.py ← 2. walk-forward completo: predicciones y posiciones diarias
│   ├── evaluacion.py              ← 3. tablas y gráficos de las secciones 4, 6 y 7 del informe
│   └── senal_del_dia.py           ← 4. señal diaria para el monitoreo en vivo
├── resultados/               ← salidas de los pasos 2 y 3 (se pueden regenerar)
└── informe/                  ← informe metodológico, secciones 0 a 9
    ├── README.md             ← resumen ejecutivo e índice
    └── figuras/
```

---

## Cómo usarlo

### En Google Colab

Clonar el repositorio y correr, en celdas:

```python
!git clone https://github.com/vichoclo/prediccion-USDCLP.git
%cd prediccion-USDCLP
!pip install -q -r requirements.txt

# 1. Base tratada (≈ 1 minuto)
!python src/preparar_base_v2.py "datos/base_usdclp 2.xlsx" datos/procesados/

# 2. Walk-forward completo (≈ 20 minutos en CPU; menos con GPU)
!python src/modelo_adaptativo_colab.py datos/procesados/modelo_usdclp_desde_2001.csv

# 3. Tablas y gráficos del informe (≈ 1 minuto)
!python src/evaluacion.py datos/procesados/modelo_usdclp_desde_2001.csv

# 4. Señal para la jornada siguiente
!python src/senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
```

Los scripts se corren con `!python` desde una celda. Si se pega su código directamente en una celda, `preparar_base_v2.py` falla, porque lee argumentos.

### En un computador

```bash
pip install -r requirements.txt
python src/preparar_base_v2.py "datos/base_usdclp 2.xlsx" datos/procesados/
python src/modelo_adaptativo_colab.py datos/procesados/modelo_usdclp_desde_2001.csv
python src/evaluacion.py datos/procesados/modelo_usdclp_desde_2001.csv
python src/senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
```

### Qué hace cada paso

**1. `preparar_base_v2.py`: de la base cruda a la base tratada.**

- **Entrada:** la base cruda de Bloomberg (hoja `datos`).
- **Salida:** en `datos/procesados/`, tres cortes (desde 2001, 2010 y 2018) en `.csv` y `.xlsx`, con 105 columnas: variables `x_*`, calendario `cal_*`, objetivo `y_*` y carry. El sistema usa `modelo_usdclp_desde_2001`. El `.xlsx` trae además el diccionario de variables.
- **Opcional:** `--ipsa ipsa.csv` completa el IPSA después del 31-ago-2026. El sistema no lo usa.
- **Detalle:** [sección 1 del informe](informe/01_datos_y_limpieza.md).

**2. `modelo_adaptativo_colab.py`: walk-forward completo.**

- **Qué hace:** reentrena el modelo 1 cada 21 días desde 2005, solo con el pasado, y aplica el modelo 2. Corre también el sistema base como control.
- **Salidas, en `resultados/`:**
  - `posiciones_adaptativo.csv`: probabilidad, percentil de confianza, volatilidad relativa, exposición y resultado de cada día, para el adaptativo y el base;
  - `predicciones_modelo1.csv`: probabilidad de cada componente (LSTM y logística) de ambos sistemas;
  - `coeficientes_logistica.csv`: coeficientes de la logística en cada reentrenamiento;
  - `resultados_adaptativo.csv`: retorno, Sharpe, máxima caída y acierto por tramo;
  - gráficos `a1`-`a4`, de diagnóstico.
- **Si Colab se desconecta:** el avance queda en `cache_adaptativo/`, así que al volver a correrlo retoma donde iba.
- **Formato:** cada bloque `# %%` es una celda, así que también se puede abrir como notebook.

**3. `evaluacion.py`: tablas y gráficos del informe.**

- **Qué hace:** a partir de las salidas del paso 2, calcula todas las cifras de las secciones 4, 6 y 7:
  - resultado por tramo y con distintos costos, frente a las tres referencias del torneo;
  - bootstrap por bloques, Diebold-Mariano, placebo de dirección y Sharpe deflactado;
  - log-loss y acierto en el quintil de mayor confianza;
  - comparación adaptativo contra base y resultado por año;
  - aporte de cada nivel de exposición, abstención y efecto del GARCH.
- **Salidas, en `resultados/`:** `eval_*.csv` y los gráficos 4 y 6 del informe.

**4. `senal_del_dia.py`: señal del día.** Toma el último día de la base tratada y entrega lo que piden las bases:

```
Señal al cierre del 2026-06-17 (para la jornada siguiente, 2026-06-18):
  dirección: VENDER dólar | p = 0,430 | confianza (percentil) = 0,94 | vol. relativa = 1,14
  exposición sugerida: −3
  componentes: p LSTM = 0,474 · p logística = 0,386   [sistema adaptativo]
```

- **Modelos guardados:** la primera corrida entrena los modelos vigentes (unos minutos) y los guarda en `modelos_vigentes_adaptativo.pt`. Las siguientes los cargan y tardan segundos.
- **Bitácora:** cada corrida agrega una fila a `bitacora_senales.csv`.
- **Opciones:**
  - `--hasta AAAA-MM-DD` calcula la señal como si esa fecha fuera el último día de la base;
  - `--sistema base` calcula la del sistema base.

### Reproducibilidad

- Las semillas del LSTM están fijas, así que el walk-forward es determinista **en un mismo tipo de equipo**. Entre CPU y GPU, las probabilidades del LSTM pueden diferir en el cuarto decimal.
- Las cifras del informe se generaron en CPU; `resultados/` trae esas salidas.

### Operación diaria durante el monitoreo

1. Reemplazar `datos/base_usdclp 2.xlsx` por la base actualizada del laboratorio. Si solo llegan los días nuevos, primero hay que agregarlos al final de la hoja `datos`.
2. `python src/preparar_base_v2.py "datos/base_usdclp 2.xlsx" datos/procesados/`
3. `python src/senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv`

`senal_del_dia.py` usa el mismo código, parámetros y semillas que el walk-forward. Lo comprobamos: con la base cortada en fechas del test, entrega la misma probabilidad y exposición que `posiciones_adaptativo.csv`.

El detalle, las reglas de operación y los riesgos están en la [sección 9.4 del informe](informe/09_limitaciones_y_operacion.md).

---

## Informe

| # | Sección |
|---|---|
| — | [Resumen ejecutivo e índice](informe/README.md) |
| 0 | [Problema, reglas y criterio de evaluación](informe/00_problema_y_reglas.md) |
| 1 | [Datos y limpieza](informe/01_datos_y_limpieza.md) |
| 2 | [Análisis exploratorio y selección de variables](informe/02_analisis_exploratorio_y_variables.md) |
| 3 | [Protocolo de validación](informe/03_protocolo_validacion.md) |
| 4 | [Modelo 1: dirección (adaptativo)](informe/04_modelo1_direccion.md) |
| 5 | [Modelo 2: exposición](informe/05_modelo2_exposicion.md) |
| 6 | [Resultados fuera de muestra y significancia](informe/06_resultados_y_significancia.md) |
| 7 | [Lectura de la convicción](informe/07_lectura_conviccion.md) |
| 8 | [Modelos probados y descartados](informe/08_modelos_descartados.md) |
| 9 | [Limitaciones, riesgos y operación en vivo](informe/09_limitaciones_y_operacion.md) |

## Entregables exigidos por las bases

| Entregable | Dónde |
|---|---|
| Señal del día (dirección, probabilidad, posición sugerida) | `src/senal_del_dia.py` · [sección 9.4](informe/09_limitaciones_y_operacion.md) |
| Curva de resultado neto de costos vs. las tres referencias | [Sección 6](informe/06_resultados_y_significancia.md), gráfico 6 |
| Lectura de la convicción (días de máxima exposición y de abstención) | [Sección 7](informe/07_lectura_conviccion.md) |
| Informe metodológico | [`informe/`](informe/README.md) |

## Datos

Series diarias de Bloomberg entregadas por el laboratorio: USD/CLP (OHLC), monedas, commodities, bolsas, tasas locales y de EE.UU., volatilidades, posiciones de la banca y series macro. Todas son datos públicos de mercado. [confirmar con el laboratorio que la base puede publicarse en el repositorio]
