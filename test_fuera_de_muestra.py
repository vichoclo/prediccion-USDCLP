# -*- coding: utf-8 -*-
"""
test_fuera_de_muestra.py — Compara la señal del sistema con lo que pasó en la realidad.

Simula la operación en vivo día por día: para cada fecha de decisión d del tramo pedido,
corta la base en d (el resultado de d todavía "no se conoce"), calcula la señal con
senal_del_dia.calcular_senal —el mismo código que se usará en el monitoreo— y la
compara con el retorno real de d a la jornada siguiente.

  resultado_d = exposición_d × (retorno USD/CLP d→d+1 − carry) − 1 pb × |cambio de exposición|

Referencias: no operar (0), comprar siempre (+1) y operar ±1 todos los días con la
misma dirección del modelo.

USO (misma carpeta que senal_del_dia.py; la base tratada debe llegar hasta el último
día con dato, ej. 6-nov):
  python test_fuera_de_muestra.py modelo_usdclp_desde_2001.csv --desde 2026-10-07 --hasta 2026-11-05
  Opcional: --sistema base   para simular el sistema base (control)

Salidas: test_fuera_de_muestra.csv (día a día) y test_fuera_de_muestra.png.
"""
import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import senal_del_dia as S

COSTO = 1.0
ap = argparse.ArgumentParser()
ap.add_argument("archivo")
ap.add_argument("--desde", required=True, help="primera fecha de decisión (AAAA-MM-DD)")
ap.add_argument("--hasta", default=None, help="última fecha de decisión; por defecto, la penúltima de la base")
ap.add_argument("--sistema", default=S.SISTEMA, choices=list(S.COMPONENTES))
ap.add_argument("--modelos", default=None, help="archivo de modelos guardados (por defecto modelos_test_<sistema>.pt)")
a = ap.parse_args()
ruta = a.modelos or f"modelos_test_{a.sistema}.pt"

completo = S.cargar(a.archivo)                                   # con el resultado real de cada día
fechas = completo.loc[a.desde:a.hasta].index
fechas = [f for f in fechas if pd.notna(completo.loc[f, "y_ret_neto_pb"])]   # días con resultado conocido
print(f"Sistema {a.sistema} · base hasta {completo.index[-1].date()} · {len(fechas)} decisiones a evaluar "
      f"({fechas[0].date()} → {fechas[-1].date()})\n")

filas = []
for f in fechas:
    s = S.calcular_senal(S.cargar(a.archivo, hasta=str(f.date())), verbose=False, ruta_modelos=ruta, sistema=a.sistema)
    filas.append({"fecha_decision": f.date(), "jornada": s["jornada"].date(), "p": s["p"],
                  "percentil_conf": s["percentil_confianza"], "vol_rel": s["vol_relativa"],
                  "tope_garch": s["tope_garch"], "exposicion": s["exposicion"],
                  "mov_real_pb": completo.loc[f, "y_ret_pb"], "carry_pb": completo.loc[f, "carry_pb"],
                  "ret_neto_pb": completo.loc[f, "y_ret_neto_pb"]})
    print(f"  {f.date()}  p={s['p']:.3f}  pct={s['percentil_confianza']:.2f}  exp={s['exposicion']:+d}  "
          f"real={completo.loc[f, 'y_ret_pb']:+.1f} pb")

T = pd.DataFrame(filas).set_index("fecha_decision")
e, y = T.exposicion.astype(float), T.ret_neto_pb
T["resultado_pb"] = e * y - COSTO * e.diff().abs().fillna(e.abs())
T["acierta"] = np.where(e != 0, np.sign(e) == np.sign(y), np.nan)
lado = np.sign(T.p - 0.5)
ref = {"Sistema": T.resultado_pb,
       "No operar": pd.Series(0.0, index=T.index),
       "Comprar siempre": y - COSTO * pd.Series([1.0] + [0.0] * (len(y) - 1), index=T.index),
       "±1 todos los días": lado * y - COSTO * lado.diff().abs().fillna(lado.abs())}

pct = lambda g: (np.exp(g.sum() / 1e4) - 1) * 100
op = T[e != 0]
print("\n" + "=" * 74)
print(f"Días evaluados: {len(T)} · días operados: {len(op)} · días en ±3: {int((e.abs() == 3).sum())}")
if len(op):
    k, n = int(op.acierta.sum()), len(op)
    ic = stats.binomtest(k, n).proportion_ci()
    print(f"Acierto en días operados: {k}/{n} = {k / n:.0%}  (IC 95%: {ic.low:.0%} a {ic.high:.0%})")
print(f"Acierto de dirección, todos los días: {(lado == np.sign(y)).mean():.0%}")
for nombre, g in ref.items():
    print(f"  {nombre:20s} {g.sum():+8.1f} pb  ({pct(g):+.2f}%)")
d = ref["Sistema"] - ref["No operar"]
if d.std() > 0:
    tt = d.mean() / d.std() * np.sqrt(len(d))
    print(f"t del resultado diario vs no operar: {tt:.2f} (con {len(d)} días, |t| < 2 no distingue del azar)")
print("=" * 74)
T.to_csv("test_fuera_de_muestra.csv", float_format="%.4f")

# ---------------------------------------------------------------- gráfico
fig, (a0, a1) = plt.subplots(2, 1, figsize=(12, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
x = pd.to_datetime(T.index)
for (nombre, g), c, ls in zip(ref.items(), ["#2a78d6", "#8a8984", "#52514e", "#eb6834"], ["-", "-", ":", "--"]):
    a0.plot(x, g.cumsum(), color=c, ls=ls, lw=2 if nombre == "Sistema" else 1.3, label=nombre)
a0.axhline(0, color="#52514e", lw=0.8)
a0.set_ylabel("Resultado acumulado (pb)")
a0.set_title(f"Sistema {a.sistema} vs realidad, día por día (neto de carry y 1 pb de costo)", loc="left", fontweight="bold")
a0.legend(frameon=False, fontsize=9)
col = {-3: "#c23b3a", -1: "#f2a6a5", 0: "#d9d8d4", 1: "#86b6ef", 3: "#1c5cab"}
a1.bar(x, T.mov_real_pb, color=[col[int(v)] for v in e], width=0.8)
a1.axhline(0, color="#52514e", lw=0.8)
a1.set_ylabel("Mov. real (pb)")
a1.set_title("Movimiento real del dólar; color = posición tomada (azul compra, rojo venta, gris fuera)",
             loc="left", fontsize=10)
for ax in (a0, a1):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color="#e4e3df", lw=0.6)
fig.tight_layout()
fig.savefig("test_fuera_de_muestra.png", dpi=150)
print("Guardado: test_fuera_de_muestra.csv y test_fuera_de_muestra.png")
