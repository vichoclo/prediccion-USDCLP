# -*- coding: utf-8 -*-
"""
evaluacion.py — Reproduce las tablas y gráficos de las secciones 4, 6 y 7 del informe.

Lee las salidas de modelo_adaptativo_colab.py (carpeta resultados/) y la base tratada, y
calcula para el sistema adaptativo, el sistema base (control) y sus componentes:

  · resultado neto por tramo, con 0, 1, 2 y 5 pb de costo, y las tres referencias del torneo
  · significancia: bootstrap por bloques de 20 días, Diebold-Mariano (Newey-West), placebo de
    dirección y Sharpe deflactado (Bailey y López de Prado, 2014)
  · calidad de las probabilidades: mejora de log-loss frente a la frecuencia base y acierto Q5
  · comparación adaptativo vs base, resultado por año, parte ganada en el gap nocturno
  · lectura de la convicción: aporte por nivel de exposición, abstención y efecto del GARCH
  · gráficos 4 (coeficientes de la logística) y 6 (resultado acumulado)

Uso (desde la raíz del repositorio, después de modelo_adaptativo_colab.py):
  python src/evaluacion.py datos/procesados/modelo_usdclp_desde_2001.csv

Salidas en resultados/: eval_*.csv, g4_coeficientes_logistica.png y g6_resultado_acumulado.png.
Tarda ~1 minuto.
"""
import os
import sys
import warnings
from math import sqrt

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew

warnings.filterwarnings("ignore")

ARCHIVO = sys.argv[1] if len(sys.argv) > 1 else "datos/procesados/modelo_usdclp_desde_2001.csv"
RES = "resultados"
TRAMOS = {"p1_05_14": ("2005-01-01", "2014-12-31"), "p2_15_21": ("2015-01-01", "2021-12-31"),
          "val_22_24": ("2022-01-01", "2024-12-31"), "test_25_26": ("2025-01-01", "2026-10-05")}
N_CONFIG = 349          # configuraciones probadas en el proyecto (informe, sección 3.7)
COSTOS = (0, 1, 2, 5)   # pb por unidad de cambio de exposición
# mismos parámetros del walk-forward (para la frecuencia base de referencia del log-loss)
DESDE, PRED_DESDE, MIN_TRAIN, EMBARGO, REAJUSTE_BASE = "2001-08-09", "2005-01-01", 750, 5, 126
rng = np.random.default_rng(0)

for f in (ARCHIVO, f"{RES}/posiciones_adaptativo.csv", f"{RES}/predicciones_modelo1.csv"):
    if not os.path.exists(f):
        sys.exit(f"No encuentro {f}. Corra primero preparar_base_v2.py y modelo_adaptativo_colab.py "
                 f"desde la raíz del repositorio.")

# ============================================================== datos
m = pd.read_excel(ARCHIVO, index_col=0, parse_dates=True) if ARCHIVO.endswith("xlsx") else \
    pd.read_csv(ARCHIVO, index_col=0, parse_dates=True)
POS = pd.read_csv(f"{RES}/posiciones_adaptativo.csv", header=[0, 1], index_col=0, parse_dates=True)
P = pd.read_csv(f"{RES}/predicciones_modelo1.csv", header=[0, 1], index_col=0, parse_dates=True)
P = P.rename(columns={"Adaptativo": "adaptativo", "Base (control)": "base"}, level=0)
VOL_REL = POS[("Adaptativo", "vol_rel")].combine_first(POS[("Base (control)", "vol_rel")]).reindex(m.index)
YRET = m["y_ret_neto_pb"]
cierre = m["usdclp_cierre"]
apert = cierre * np.exp(-m["x_usdclp_cuerpo"] / 1e4)
GAP = np.log(apert.shift(-1) / cierre) * 1e4                 # cierre t → apertura t+1
INTRA = np.log(cierre.shift(-1) / apert.shift(-1)) * 1e4     # apertura t+1 → cierre t+1


def frecuencia_base():
    """Frecuencia de 'sube' en el entrenamiento de cada bloque del sistema base (referencia del log-loss)."""
    d = m.loc[DESDE:]
    y = d["y_sube_neto"].to_numpy(float)
    valido, T = ~np.isnan(y), len(d)
    inicio = max(np.searchsorted(d.index, pd.Timestamp(PRED_DESDE)),
                 np.searchsorted(np.cumsum(valido), MIN_TRAIN) + EMBARGO + 1)
    out = np.full(T, np.nan)
    for r in range(inicio, T, REAJUSTE_BASE):
        tr = np.where(valido[:r - EMBARGO])[0]
        out[r:min(r + REAJUSTE_BASE, T)] = y[tr].mean()
    return pd.Series(out, index=d.index)


PBASE = frecuencia_base()


# ============================================================== modelo 2 y métricas
def sistema(p, tope=1.5):
    """Exposición diaria (igual que modelo_adaptativo_colab.py)."""
    p = p.dropna()
    p = p[VOL_REL.reindex(p.index).notna()]
    pct = (p - 0.5).abs().rolling(251, min_periods=120).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    vr = VOL_REL.reindex(p.index)
    tam = pd.Series(np.where(pct >= 0.8, 3.0, np.where(pct >= 0.6, 1.0, 0.0)), index=p.index).where(pct.notna(), 0.0)
    tam = tam.where(~((tam == 3) & (vr > tope)), 1.0)
    return pd.DataFrame({"p": p, "pct": pct, "vol_rel": vr, "exposicion": np.sign(p - 0.5) * tam,
                         "y": YRET.reindex(p.index)})


def resultado(e, y, c):
    return (e * y - c * e.diff().abs().fillna(e.abs())).where(y.notna())


def met(g, e):
    g = g.dropna(); e = e.reindex(g.index); acum = g.cumsum()
    return {"ret_%": round((np.exp(g.sum() / 1e4) - 1) * 100, 1),
            "sharpe": round(g.mean() / g.std() * sqrt(252), 2) if g.std() > 0 else 0.0,
            "max_caida_%": round((np.exp((acum - acum.cummax()).min() / 1e4) - 1) * 100, 1),
            "peor_mes_%": round((np.exp(g.resample("ME").sum().min() / 1e4) - 1) * 100, 1),
            "%dias_0": round(100 * (e == 0).mean()), "%dias_1": round(100 * (e.abs() == 1).mean()),
            "%dias_3": round(100 * (e.abs() == 3).mean()), "dias": len(g)}


def t_nw(f, lags=5):
    """t de la media con error estándar de Newey-West (Diebold-Mariano)."""
    f = np.asarray(f, float); f = f[~np.isnan(f)]
    u = f - f.mean(); n = len(f); s = u @ u / n
    for k in range(1, lags + 1):
        s += 2 * (1 - k / (lags + 1)) * (u[k:] @ u[:-k]) / n
    return f.mean() / sqrt(s / n)


def boot(g1, g2, B=2000, bloque=20):
    """P(la estrategia no es mejor): bootstrap de bloques móviles de la diferencia diaria."""
    r = np.random.default_rng(0); d = (g1 - g2).dropna().to_numpy(); n = len(d); nb = int(np.ceil(n / bloque))
    mm = [d[(r.integers(0, n - bloque, nb)[:, None] + np.arange(bloque)).ravel()[:n]].mean() for _ in range(B)]
    return round(float((np.array(mm) <= 0).mean()), 3)


def dsr(g):
    """Sharpe deflactado: P(Sharpe verdadero > 0) y umbral anual que alcanzaría el azar."""
    r = g.dropna().to_numpy() / 1e4; T = len(r); sr = r.mean() / r.std(); gam = 0.5772156649
    emax = sqrt(1 / (T - 1)) * ((1 - gam) * norm.ppf(1 - 1 / N_CONFIG) + gam * norm.ppf(1 - 1 / (N_CONFIG * np.e)))
    den = sqrt(1 - skew(r) * sr + (kurtosis(r, fisher=False) - 1) / 4 * sr ** 2)
    return round(float(norm.cdf((sr - emax) * sqrt(T - 1) / den)), 3), round(emax * sqrt(252), 2)


def ll(y, q):
    q = np.clip(q, 1e-6, 1 - 1e-6); return -(y * np.log(q) + (1 - y) * np.log(1 - q))


# ============================================================== cálculo
SEN = {}
for sis in ("adaptativo", "base"):
    for comp, et in (("p", ""), ("p_logit", " · logística"), ("p_lstm", " · LSTM")):
        SEN[sis + et] = sistema(P[(sis, comp)])
SEN["adaptativo · sin GARCH"] = sistema(P[("adaptativo", "p")], tope=np.inf)

tr, sg, an, cv = [], [], [], []
for nom, D in SEN.items():
    G = {c: resultado(D.exposicion, D.y, c) for c in COSTOS}
    ref = {"±1": resultado(np.sign(D.p - 0.5), D.y, 1), "comprar": resultado(pd.Series(1.0, D.index), D.y, 1),
           "no operar": pd.Series(0.0, D.index).where(D.y.notna())}
    for t, (a, b) in TRAMOS.items():
        fila = {"senal": nom, "tramo": t, **met(G[1].loc[a:b], D.exposicion)}
        for c in COSTOS:
            if c != 1:
                fila[f"ret_{c}pb_%"] = met(G[c].loc[a:b], D.exposicion)["ret_%"]
        for k, g in ref.items():
            fila[f"ref_{k}_%"] = met(g.loc[a:b], D.exposicion)["ret_%"]
        tr.append(fila)
        if " · sin" in nom:
            continue
        d = D.loc[a:b].dropna(subset=["y"]); g = G[1].loc[a:b].dropna()
        f2 = {"senal": nom, "tramo": t}
        for k, gr in ref.items():
            gr = gr.loc[a:b].reindex(g.index)
            f2[f"boot_vs_{k}"] = boot(g, gr); f2[f"dm_vs_{k}"] = round(1 - norm.cdf(t_nw((g - gr).to_numpy())), 3)
        yy = m["y_sube_neto"].reindex(d.index); pb = PBASE.reindex(d.index)
        ok = yy.notna() & pb.notna()
        dl = (ll(yy, pb) - ll(yy, d.p))[ok]
        f2["mejora_LL_x1000"] = round(1000 * dl.mean(), 2); f2["t_LL"] = round(t_nw(dl.to_numpy()), 2)
        f2["acierto_dir_%"] = round(100 * ((d.p > 0.5) == (yy > 0.5))[ok].mean(), 1)
        cf = (d.p - 0.5).abs(); q5 = cf >= cf.quantile(0.8)
        f2["acierto_Q5_%"] = round(100 * ((d.p > 0.5) == (yy == 1))[q5].mean(), 1)
        E_, R_ = d.exposicion.abs().to_numpy(), d.y.to_numpy(); real = (d.exposicion * d.y).sum()
        sims = np.array([(E_ * rng.choice([-1, 1], len(E_)) * R_).sum() for _ in range(2000)])
        f2["placebo_%"] = round(100 * (sims >= real).mean(), 1)
        f2["dsr_P"], f2["dsr_umbral"] = dsr(g)
        f2["total_pb"] = round(g.sum()); f2["sin_10_mejores_pb"] = round(g.sort_values().iloc[:-10].sum())
        gg = (d.exposicion * GAP.reindex(d.index)).sum(); ii = (d.exposicion * INTRA.reindex(d.index)).sum()
        f2["parte_gap_%"] = round(100 * gg / (gg + ii)) if gg + ii != 0 else np.nan
        f2["costo_equilibrio_pb"] = round(real / d.exposicion.diff().abs().fillna(d.exposicion.abs()).sum(), 1)
        sg.append(f2)
        for niv, x in d.groupby(d.exposicion.abs()):
            l = np.sign(x.p - 0.5); gx = G[1].reindex(x.index)
            cv.append({"senal": nom, "tramo": t, "nivel": int(niv), "dias": len(x), "%dias": round(100 * len(x) / len(d)),
                       "acierto_%": round(100 * (l * x.y > 0).mean(), 1), "ret_direccion_pb": round((l * x.y).mean(), 1),
                       "resultado_medio_pb": round(gx.mean(), 1),
                       "aporte_%": round(100 * gx.sum() / g.sum()) if g.sum() else np.nan, "aporte_pb": round(gx.sum())})
    g = G[1].loc["2005":"2026-10-05"]
    for y_, gg in g.groupby(g.index.year):
        an.append({"senal": nom, "anio": y_, "ret_%": round((np.exp(gg.sum() / 1e4) - 1) * 100, 1)})

# adaptativo vs base
ga = resultado(SEN["adaptativo"].exposicion, SEN["adaptativo"].y, 1)
gb = resultado(SEN["base"].exposicion, SEN["base"].y, 1)
comp = []
for t, (a, b) in {**TRAMOS, "todo_06_26": ("2005-01-01", "2026-10-05")}.items():
    dd = (ga - gb).loc[a:b].dropna()
    comp.append({"tramo": t, "dif_media_pb_dia": round(dd.mean(), 2), "P_adaptativo_no_mejor": boot(dd, dd * 0),
                 "correlacion_diaria": round(ga.loc[a:b].corr(gb.loc[a:b]), 2)})

# abstención y GARCH (adaptativo)
D, D0 = SEN["adaptativo"], SEN["adaptativo · sin GARCH"]
G0 = resultado(D0.exposicion, D0.y, 1)
det = []
for t, (a, b) in TRAMOS.items():
    d = D.loc[a:b].dropna(subset=["y"]); lado = np.sign(d.p - 0.5); cero = d.exposicion == 0
    t3 = d[d.exposicion.abs() == 3]; ch = D0.exposicion.reindex(d.index) != d.exposicion
    det.append({"tramo": t, "abstencion_dias": int(cero.sum()), "abstencion_acierto_%": round(100 * ((lado * d.y)[cero] > 0).mean(), 1),
                "abstencion_si_opera_±1_pb": round((lado * d.y)[cero].sum()),
                "±3_ventas_%": round(100 * (t3.exposicion < 0).mean()),
                "±3_gap_pb": round((np.sign(t3.p - .5) * GAP.reindex(t3.index)).mean(), 1),
                "±3_intradia_pb": round((np.sign(t3.p - .5) * INTRA.reindex(t3.index)).mean(), 1),
                "garch_dias": int(ch.sum()), "garch_aporte_pb": round((ga.reindex(d.index) - G0.reindex(d.index))[ch].sum()),
                "max_caida_sin_garch_%": met(G0.loc[a:b], D0.exposicion)["max_caida_%"]})

TABLAS = {"eval_tramos": pd.DataFrame(tr), "eval_significancia": pd.DataFrame(sg),
          "eval_anual": pd.DataFrame(an).pivot(index="anio", columns="senal", values="ret_%"),
          "eval_conviccion": pd.DataFrame(cv), "eval_adaptativo_vs_base": pd.DataFrame(comp),
          "eval_abstencion_garch": pd.DataFrame(det)}
pd.set_option("display.width", 250, "display.max_columns", 40)
for nombre, T_ in TABLAS.items():
    T_.to_csv(f"{RES}/{nombre}.csv", index=nombre == "eval_anual")
sel = ["senal", "tramo", "ret_%", "sharpe", "max_caida_%", "ret_0pb_%", "ref_comprar_%", "ref_±1_%"]
print("\nResultado por tramo (1 pb)\n", TABLAS["eval_tramos"][sel].to_string(index=False))
print("\nSignificancia\n", TABLAS["eval_significancia"].to_string(index=False))
print("\nAdaptativo vs base\n", TABLAS["eval_adaptativo_vs_base"].to_string(index=False))

# ============================================================== gráficos 4 y 6
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e",
                     "xtick.color": "#52514e", "ytick.color": "#52514e", "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb"})
AZ, NA, GR, TX = "#2a78d6", "#eb6834", "#8a8984", "#0b0b0b"
# Gráfico 6: resultado acumulado vs referencias (arriba) y exposición diaria del adaptativo (abajo)
D_ad = SEN["adaptativo"]
idx6 = D_ad.loc["2006-01-01":"2026-10-05"].index
e_ad = D_ad.exposicion.reindex(idx6)
y6 = D_ad.y.reindex(idx6)
curvas = {"Sistema adaptativo": (e_ad, AZ, "-", 2.0),
          "Sistema base (control)": (SEN["base"].exposicion.reindex(idx6), NA, "-", 1.3),
          "Comprar siempre": (pd.Series(1.0, idx6), GR, ":", 1.3),
          "Operar siempre ±1": (np.sign(D_ad.p.reindex(idx6) - 0.5), "#52514e", "--", 1.3),
          "No operar nunca": (pd.Series(0.0, idx6), "#c3c2b7", "-", 1.3)}
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(13, 6.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
for lab, (e, c, ls, lw) in curvas.items():
    g = resultado(e, y6, 1).fillna(0).cumsum() / 100
    ax.plot(g.index, g, color=c, ls=ls, lw=lw, label=lab)
for t, (a, b) in TRAMOS.items():
    if pd.Timestamp(a) > idx6[0]:
        ax.axvline(pd.Timestamp(a), color="#c3c2b7", lw=0.8)
ax.axhline(0, color="#52514e", lw=0.8)
ax.set_ylabel("Resultado acumulado (puntos %)")
ax.set_title("Gráfico 6 · Resultado acumulado neto de carry y 1 pb de costo · 2006-2026", loc="left", fontweight="bold", color=TX)
ax.legend(frameon=False, ncol=3, fontsize=9)
col_e = {-3: "#c23b3a", -1: "#f2a6a5", 0: "#d9d8d4", 1: "#86b6ef", 3: "#1c5cab"}
ax2.bar(e_ad.index, e_ad, color=[col_e[int(v)] for v in e_ad], width=1.5)
ax2.set_yticks([-3, -1, 0, 1, 3]); ax2.set_ylabel("Exposición")
ax2.set_title("Exposición del sistema adaptativo (azul: compra de dólar · rojo: venta)", loc="left", fontsize=10)
for x in (ax, ax2):
    x.spines[["top", "right"]].set_visible(False); x.grid(axis="y", color="#e4e3df", lw=0.6)
fig.tight_layout(); fig.savefig(f"{RES}/g6_resultado_acumulado.png", dpi=150)

ruta_coef = f"{RES}/coeficientes_logistica.csv"
if os.path.exists(ruta_coef):
    CO = pd.read_csv(ruta_coef, header=[0, 1], index_col=0, parse_dates=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharex=True)
    for ax, (v, t) in zip(axes, (("x_usdzar_ret", "Rand (USD/ZAR)"), ("x_oro_ret", "Oro"), ("cal_viernes", "Viernes"))):
        a_ = CO[("Adaptativo", v)].dropna()
        ax.step(a_.index, a_, where="post", color=AZ, lw=1.8, label="Adaptativo (últimos 500 días)")
        b_ = CO[("Base (control)", v)].dropna()
        ax.step(b_.index, b_, where="post", color=NA, lw=1.6, label="Base (toda la historia)")
        ax.axhline(0, color="#52514e", lw=0.8); ax.set_title(t, loc="left", fontsize=10, color=TX)
        ax.grid(axis="y", color="#e4e3df", lw=0.6); ax.spines[["top", "right"]].set_visible(False)
        ax.xaxis.set_major_locator(mdates.YearLocator(5)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[0].set_ylabel("Coeficiente (variable estandarizada)")
    axes[0].legend(frameon=False, fontsize=9, loc="lower left")
    fig.suptitle("Gráfico 4 · Coeficiente de la logística en cada reentrenamiento", x=0.01, ha="left", fontweight="bold", color=TX)
    fig.tight_layout(); fig.savefig(f"{RES}/g4_coeficientes_logistica.png", dpi=150)
print(f"\nGuardado en {RES}/: {', '.join(n + '.csv' for n in TABLAS)}, g4_coeficientes_logistica.png y g6_resultado_acumulado.png")
