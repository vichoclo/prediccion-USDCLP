# ¿Sube o baja el dólar mañana? · Predicción de la dirección del USD/CLP

Torneo Banco Itaú y FEN · Data Science en Finanzas · Facultad de Economía y Negocios, Universidad de Chile

[completar: nombres de la pareja]

---

## Qué hace este repositorio

Construye una estrategia diaria sobre el USD/CLP en dos etapas (**sistema adaptativo**).

**1. Modelo 1 · Dirección.** Estima la probabilidad de que mañana convenga estar comprado en dólares, es decir, que el dólar suba más que el carry. Es el promedio simple de dos componentes con las mismas 11 variables de mercado y calendario:

- un **LSTM** que mira los últimos 20 días. Se entrena con toda la historia, con peso exponencial: un día de hace un año pesa la mitad.
- una **regresión logística** entrenada solo con los últimos 500 días.

Ambos se reentrenan cada 21 días, así que los pesos siguen a las relaciones que cambian.

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

**Advertencia:** el adaptativo se eligió después de ver el test. Con la regla fijada al inicio habría ganado el base. El detalle y las limitaciones están en las [secciones 3, 6 y 9 del informe](informe/README.md).

[completar: resultado en el tramo de test con el código de evaluación del laboratorio]

---

## Estructura

```
├── README.md
├── requirements.txt
├── datos/
│   ├── crudos/          ← base_usdclp 2.xlsx (base Bloomberg del laboratorio)
│   └── procesados/      ← bases tratadas; las genera preparar_base_v2.py
├── src/
│   ├── preparar_base_v2.py        ← limpieza y construcción de variables
│   ├── modelo_adaptativo_colab.py ← walk-forward completo: modelo 1 + modelo 2, resultados y gráficos
│   ├── senal_del_dia.py           ← señal diaria para el monitoreo en vivo
│   ├── verificar_senal.py         ← comprueba que la señal diaria coincide con el walk-forward
│   └── test_fuera_de_muestra.py   ← simula la operación en vivo día por día con datos nuevos
├── resultados/          ← señales, tablas y gráficos generados
└── informe/             ← informe metodológico (secciones 0 a 9) y gráficos
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

Genera tres cortes (desde 2001, 2010 y 2018) en `.csv` y `.xlsx`; el sistema usa el corte desde 2001. El detalle está en la [sección 1 del informe](informe/01_datos_y_limpieza.md).

### 4. Correr el walk-forward y la evaluación

```bash
cd datos/procesados && python ../../src/modelo_adaptativo_colab.py
```

`modelo_adaptativo_colab.py` está pensado para Colab: cada bloque `# %%` es una celda. Calcula las predicciones del adaptativo y de la base, los resultados por tramo (`resultados_adaptativo.csv`), las posiciones diarias (`posiciones_adaptativo.csv`) y los gráficos. Tarda unos 20 minutos en CPU y guarda su avance en `cache_adaptativo/`.

### 5. Señal del día

```bash
python src/senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
```

Entrega la dirección, la probabilidad, la confianza, la volatilidad relativa y la exposición sugerida para la jornada siguiente, y agrega una fila a `bitacora_senales.csv`.

- La primera corrida entrena los modelos vigentes y los guarda en `modelos_vigentes_adaptativo.pt`; las siguientes los cargan.
- Con `--hasta AAAA-MM-DD` calcula la señal como si esa fecha fuera el último día.
- Con `--sistema base` calcula la del sistema base.

Para comprobar que la señal coincide con el walk-forward:

```bash
python src/verificar_senal.py datos/procesados/modelo_usdclp_desde_2001.csv posiciones_adaptativo.csv --fechas 2025-04-03
```

### En Google Colab

```python
!git clone [completar: URL del repositorio]
%cd [completar: nombre de la carpeta]
!pip install -q -r requirements.txt
!python src/preparar_base_v2.py "datos/crudos/base_usdclp 2.xlsx" datos/procesados/
!python src/senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
```

---

## Protocolo de validación

| Tramo | Fechas | Uso |
|---|---|---|
| Entrenamiento inicial | 2001 → 2004 | Primer ajuste del walk-forward |
| Desarrollo, parte 1 | 2005 → 2014 | Fuera de muestra; no se usó para ninguna elección |
| Desarrollo, parte 2 | 2015 → 2021 | Elegir variables, umbrales del modelo 2 y variante del GARCH |
| Validación | 2022 → 2024 | Comparar modelos |
| Test | 2025 → oct-2026 | Evaluación final; se usó también para elegir el sistema adaptativo |
| Monitoreo en vivo | desde 9-nov-2026 | Única evaluación limpia del adaptativo (parámetros congelados) |

El LSTM y la logística se reentrenan cada 21 días, con un embargo de 5 días. El detalle está en la [sección 3 del informe](informe/03_protocolo_validacion.md).

---

## Entregables exigidos por las bases

| Entregable | Dónde |
|---|---|
| Señal del día (dirección, probabilidad, posición sugerida) | `src/senal_del_dia.py` · procedimiento en la [sección 9.4](informe/09_limitaciones_y_operacion.md) |
| Curva de resultado neto de costos vs. las tres referencias | [Sección 6](informe/06_resultados_y_significancia.md) (gráfico 6) |
| Lectura de la convicción (días de máxima exposición y de abstención) | [Sección 7](informe/07_lectura_conviccion.md) |
| Informe metodológico | [`informe/`](informe/README.md) |

---

## Datos

Series diarias de Bloomberg entregadas por el laboratorio: USD/CLP (OHLC), monedas, commodities, bolsas, tasas locales y de EE.UU., volatilidades, posiciones de la banca y series macro. Todas son datos públicos de mercado.

## Licencia

[completar: licencia abierta del repositorio, por ejemplo MIT]
