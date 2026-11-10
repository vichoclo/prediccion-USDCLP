# %% [markdown]
# # Sistema ADAPTATIVO · LSTM + logística + GARCH · Torneo Itaú-FEN (USD/CLP)
#
# Walk-forward completo del sistema del informe. El **modelo 1 aprende sobre todo de la
# historia reciente**, así que sus pesos siguen a las relaciones que cambian (rand,
# autocorrelación del peso, efecto viernes) en vez de arrastrar 20 años de historia. Se corre
# también el **sistema base** (la versión anterior, con toda la historia) como control.
#
# | Pieza | Sistema base (control) | Sistema adaptativo (oficial) |
# |---|---|---|
# | LSTM L20 (5 semillas) | toda la historia, igual peso, cada 126 días | toda la historia con peso exponencial (vida media 1 año), cada 21 días |
# | Logística C = 0,05 | toda la historia, cada 126 días | últimos 500 días (≈ 2 años), cada 21 días |
# | Señal | promedio LSTM + logística | igual |
# | Modelo 2: percentil de confianza (u1 0,6 / u3 0,8) + tope GARCH 1,5 | igual | igual |
#
# Advertencia: la combinación (LSTM exponencial + logística ventana 500) se fijó después de ver
# validación y 2025-26 (informe, sección 3.5). Su evaluación limpia son los datos posteriores
# al 9-nov-2026; los parámetros quedan congelados.
#
# **Uso:** desde la raíz del repositorio,
#   python src/modelo_adaptativo_colab.py datos/procesados/modelo_usdclp_desde_2001.csv
# (en Colab, con `!python`). También se puede abrir como notebook: cada `# %%` es una celda.
# Las salidas quedan en `resultados/`. El walk-forward guarda su avance en `cache_adaptativo/`;
# si Colab se desconecta, al volver a correr retoma donde iba.
# Tiempo aprox.: ~20 min en CPU (menos con GPU). Luego, `python src/evaluacion.py` reproduce
# las tablas y gráficos de las secciones 4, 6 y 7 del informe.

# %% 0 · instalación y configuración
# !pip -q install arch holidays          # ← descomentar en Colab

import os, pickle, time, warnings
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from arch import arch_model
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")

ARCHIVO = "modelo_usdclp_desde_2001.csv"   # base tratada (la celda 1 la sube si no está)
ESTRICTA = False        # True: rezaga 1 día las variables que cierran después de Santiago + reglas estrictas
# Cómo se adapta cada componente del modelo 1 (se pueden elegir por separado):
#   "ventana"     → solo los últimos VENTANA_M1 días, reentrenando cada REAJUSTE_M1
#   "exponencial" → toda la historia, con peso 0,5^(antigüedad / VIDA_MEDIA), cada REAJUSTE_M1
#   "expansiva"   → toda la historia con igual peso, cada 126 días (= sistema base)
# El LSTM necesita muchos datos: con solo 500 días se degrada; con peso exponencial conserva
# la historia y aun así sigue al régimen reciente. La logística (11 pesos) sí funciona con 500.
MODO_LSTM = "exponencial"
MODO_LOGIT = "ventana"
VENTANA_M1 = 500        # días de entrenamiento en modo ventana
VIDA_MEDIA = 250        # días hábiles, modo exponencial (peso 1/2 a 1 año, ≈ equivalente a ventana de 2 años)
REAJUSTE_M1 = 21        # cada cuántos días se reentrena el modelo adaptativo
COMPARAR_BASE = True    # corre también el sistema base (expansivo, cada 126 días) como control

VARS_NUCLEO = ["x_cobre_lme_ret", "x_cobre_comex_ret", "x_oro_ret", "x_dxy_ret", "x_bbdxy_ret",
               "x_dxy_mom20", "x_usdzar_ret", "x_mxef_ret", "x_vol_em_dif",
               "cal_viernes", "cal_dias_corridos_sig"]
DESPUES_DE_SANTIAGO = ["x_cobre_comex_ret", "x_oro_ret", "x_dxy_ret", "x_bbdxy_ret", "x_dxy_mom20",
                       "x_usdzar_ret", "x_mxef_ret", "x_vol_em_dif"]
DESDE, PRED_DESDE = "2001-08-09", "2005-01-01"
L, EMBARGO, MIN_TRAIN, VAL_FRAC, MIN_VAL, SEMILLAS = 20, 5, 750, 0.15, 100, 5
HIDDEN, DROPOUT, LR, WEIGHT_DECAY, BATCH, EPOCAS, PACIENCIA = 16, 0.2, 1e-3, 1e-3, 128, 60, 8
C_LOGIT = 0.05
VENTANA_GARCH, REAJUSTE_GARCH, VENTANA_PCT = 1000, 21, 250
U1, U3, TOPE_VOL, VOL_CERO = (0.8, 1.01, 1.5, 2.0) if ESTRICTA else (0.6, 0.8, 1.5, np.inf)
COSTO = 1.0             # pb por unidad de cambio de exposición
TRAMOS = {"desarrollo_p1": ("2005-01-01", "2014-12-31"), "desarrollo_p2": ("2015-01-01", "2021-12-31"),
          "validacion": ("2022-01-01", "2024-12-31"), "test": ("2025-01-01", "2026-10-05"),
          "datos_nuevos": ("2026-10-06", "2026-12-31")}       # tramos del informe (sección 3.2)
SALIDA = "resultados"   # carpeta de salida (CSV y gráficos)
os.makedirs(SALIDA, exist_ok=True)
CACHE = "cache_adaptativo"
os.makedirs(CACHE, exist_ok=True)
DISP = "cuda" if torch.cuda.is_available() else "cpu"
C = {"azul": "#2a78d6", "naranjo": "#eb6834", "gris": "#8a8984", "tinta": "#2b2a27",
     "tinta2": "#52514e", "rejilla": "#e4e3df", "rojo": "#c23b3a", "verde": "#2e8b57"}
print("Dispositivo:", DISP, "| LSTM:", MODO_LSTM, "| logística:", MODO_LOGIT, "| estricta:", ESTRICTA)

# %% 1 · datos
# Se usa, en orden: el archivo pasado como argumento (!python modelo_adaptativo_colab.py base.xlsx),
# ARCHIVO, o la base tratada en .csv/.xlsx en esta carpeta o en procesados/.
import sys
_cands = [a for a in sys.argv[1:] if a.lower().endswith((".csv", ".xlsx"))] + [ARCHIVO]
for _carpeta in ("", "procesados/", "datos/procesados/"):
    for _ext in (".csv", ".xlsx"):
        _cands.append(f"{_carpeta}modelo_usdclp_desde_2001{_ext}")
_encontrado = next((c for c in _cands if os.path.exists(c)), None)
if _encontrado:
    ARCHIVO = _encontrado
else:
    try:                                            # solo funciona si el código se pega en una celda
        from IPython import get_ipython
        if get_ipython() is None or getattr(get_ipython(), "kernel", None) is None:
            raise RuntimeError
        from google.colab import files
        print("Suba la base tratada (modelo_usdclp_desde_2001.csv o .xlsx):")
        ARCHIVO = list(files.upload().keys())[0]
    except Exception:
        raise SystemExit("No encuentro la base tratada. Súbala al panel de archivos de Colab "
                         "(modelo_usdclp_desde_2001.csv o .xlsx) o pase su ruta: "
                         "!python modelo_adaptativo_colab.py procesados/modelo_usdclp_desde_2001.xlsx")
print("Base:", ARCHIVO)


def cargar(archivo):
    if archivo.lower().endswith((".xlsx", ".xls")):
        m = pd.read_excel(archivo, index_col=0, parse_dates=True)
    else:
        m = pd.read_csv(archivo, index_col=0, parse_dates=True)
    m["cal_viernes"] = (m["cal_dia_semana"] == 4).astype(float)
    if ESTRICTA:
        for v in DESPUES_DE_SANTIAGO:
            m[v] = m[v].shift(1)
    return m


m = cargar(ARCHIVO)
d = m.loc[DESDE:]
Z_RAW = d[VARS_NUCLEO].to_numpy(float)
Y = d["y_sube_neto"].to_numpy(float)
VALIDO = ~np.isnan(Y)
FECHAS, T = d.index, len(d)
print(f"Base: {FECHAS[0].date()} → {FECHAS[-1].date()} ({T} días). Último día con resultado: "
      f"{d['y_ret_neto_pb'].dropna().index[-1].date()}")

# %% 2 · piezas del modelo 1 (las mismas del sistema base, con pesos por observación)


def escalador(Xtr):
    lo, hi = np.nan_to_num(np.nanpercentile(Xtr, 1, axis=0)), np.nan_to_num(np.nanpercentile(Xtr, 99, axis=0))
    Xc = np.clip(Xtr, lo, hi)
    mu, sd = np.nan_to_num(np.nanmean(Xc, axis=0)), np.nan_to_num(np.nanstd(Xc, axis=0))
    return {"lo": lo, "hi": hi, "mu": mu, "sd": np.where(sd > 0, sd, 1.0)}


def escalar(X, e):
    return np.nan_to_num((np.clip(X, e["lo"], e["hi"]) - e["mu"]) / e["sd"])


def secuencias(Z, filas):
    pad = np.vstack([np.zeros((L - 1, Z.shape[1])), Z])
    return np.stack([pad[i:i + L] for i in filas]).astype(np.float32)


class RedLSTM(nn.Module):
    def __init__(self, k):
        super().__init__()
        self.lstm = nn.LSTM(k, HIDDEN, batch_first=True)
        self.drop = nn.Dropout(DROPOUT)
        self.out = nn.Linear(HIDDEN, 1)

    def forward(self, x):
        h, _ = self.lstm(x)
        return self.out(self.drop(h[:, -1])).squeeze(-1)


def entrenar_lstm(Xa, ya, wa, Xv, yv, wv, semilla):
    """Early stopping con pérdida de validación ponderada (wa, wv = pesos por observación)."""
    torch.manual_seed(semilla); np.random.seed(semilla)
    red = RedLSTM(Xa.shape[2]).to(DISP)
    opt = torch.optim.Adam(red.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    bce = nn.BCEWithLogitsLoss(reduction="none")
    t = lambda a: torch.tensor(a, device=DISP)
    Xa_t, ya_t, wa_t, Xv_t, yv_t, wv_t = map(t, (Xa, ya, wa, Xv, yv, wv))
    mejor, estado, sin_mejora = np.inf, None, 0
    for _ in range(EPOCAS):
        red.train()
        orden = torch.randperm(len(Xa_t), device=DISP)
        for i in range(0, len(orden), BATCH):
            b = orden[i:i + BATCH]
            opt.zero_grad()
            ((bce(red(Xa_t[b]), ya_t[b]) * wa_t[b]).sum() / wa_t[b].sum()).backward()
            nn.utils.clip_grad_norm_(red.parameters(), 1.0)
            opt.step()
        red.eval()
        with torch.no_grad():
            pv = ((bce(red(Xv_t), yv_t) * wv_t).sum() / wv_t.sum()).item()
        if pv < mejor - 1e-5:
            mejor, sin_mejora = pv, 0
            estado = {k: v.detach().clone() for k, v in red.state_dict().items()}
        else:
            sin_mejora += 1
            if sin_mejora >= PACIENCIA:
                break
    red.load_state_dict(estado); red.eval()
    return red


def logits_red(red, X):
    with torch.no_grad():
        return red(torch.tensor(X, device=DISP)).cpu().numpy()


def conjunto_entrenamiento(r, ventana, vida_media):
    """Filas de entrenamiento para el bloque que empieza en r, y su peso."""
    fin = r - EMBARGO                                   # embargo: los últimos 5 días no entran
    tr = np.where(VALIDO[:fin])[0]
    if ventana:
        tr = tr[-ventana:]
    w = np.ones(len(tr))
    if vida_media:
        w = 0.5 ** ((tr[-1] - tr) / vida_media)
        w = w / w.mean()
    return tr, w, fin


def entrenar_bloque(r, ventana, vida_media, con_lstm=True):
    tr, w, fin = conjunto_entrenamiento(r, ventana, vida_media)
    esc = escalador(Z_RAW[tr[0]:fin])
    Z = escalar(Z_RAW, esc)
    lr = LogisticRegression(C=C_LOGIT, max_iter=1000).fit(Z[tr], Y[tr], sample_weight=w)
    if not con_lstm:
        return esc, lr, [], None, len(tr)
    n_val = max(int(len(tr) * VAL_FRAC), MIN_VAL)
    i_fit, i_val = np.arange(len(tr) - n_val - L), np.arange(len(tr) - n_val, len(tr))   # brecha L
    Xa, Xv = secuencias(Z, tr[i_fit]), secuencias(Z, tr[i_val])
    ya, yv = Y[tr[i_fit]].astype(np.float32), Y[tr[i_val]].astype(np.float32)
    wa, wv = w[i_fit].astype(np.float32), w[i_val].astype(np.float32)
    redes, zv = [], []
    for s in range(SEMILLAS):
        red = entrenar_lstm(Xa, ya, wa, Xv, yv, wv, semilla=1000 * s + r)
        zv.append(logits_red(red, Xv))
        redes.append(red)
    platt = LogisticRegression(C=1.0).fit(np.mean(zv, 0).reshape(-1, 1), yv, sample_weight=wv)
    return esc, lr, redes, platt, len(tr)


def walkforward(nombre, ventana=None, vida_media=None, reajuste=126, con_lstm=True):
    """p_lstm y p_logit fuera de muestra día a día, con avance guardado en disco."""
    ruta = f"{CACHE}/{nombre}{'' if con_lstm else '_sololog'}{'_estricta' if ESTRICTA else ''}.pkl"
    hecho = pickle.load(open(ruta, "rb")) if os.path.exists(ruta) else {}
    inicio = max(np.searchsorted(FECHAS, pd.Timestamp(PRED_DESDE)),
                 np.searchsorted(np.cumsum(VALIDO), MIN_TRAIN) + EMBARGO + 1)
    bloques = list(range(inicio, T, reajuste))
    t0, nuevos = time.time(), 0
    for j, r in enumerate(bloques):
        clave = str(FECHAS[r].date())
        n_train_hoy = int(VALIDO[:r - EMBARGO].sum())
        if clave in hecho and hecho[clave]["n_disp"] == n_train_hoy and hecho[clave]["T"] >= min(r + reajuste, T):
            continue                                       # bloque ya calculado con los mismos datos
        esc, lr, redes, platt, n = entrenar_bloque(r, ventana, vida_media, con_lstm)
        filas = np.arange(r, min(r + reajuste, T))
        Z = escalar(Z_RAW, esc)
        p_logit = lr.predict_proba(Z[filas])[:, 1]
        p_lstm = np.full(len(filas), np.nan)
        if con_lstm:
            z = np.mean([logits_red(red, secuencias(Z, filas)) for red in redes], 0)
            p_lstm = platt.predict_proba(z.reshape(-1, 1))[:, 1]
        hecho[clave] = {"filas": filas, "p_lstm": p_lstm, "p_logit": p_logit, "coef": lr.coef_[0],
                        "n_train": n, "n_disp": n_train_hoy, "T": min(r + reajuste, T)}
        nuevos += 1
        if nuevos % 10 == 0 or j == len(bloques) - 1:
            pickle.dump(hecho, open(ruta, "wb"))
            el = time.time() - t0
            print(f"  [{nombre}] {j + 1}/{len(bloques)} bloques · {el / 60:.1f} min")
    pickle.dump(hecho, open(ruta, "wb"))
    P = pd.DataFrame(index=FECHAS, columns=["p_lstm", "p_logit"], dtype=float)
    coefs = {}
    for clave, b in hecho.items():
        if clave not in {str(FECHAS[r].date()) for r in bloques}:
            continue
        P.iloc[b["filas"], 0], P.iloc[b["filas"], 1] = b["p_lstm"], b["p_logit"]
        coefs[pd.Timestamp(clave)] = b["coef"]
    P["p"] = P[["p_lstm", "p_logit"]].mean(axis=1, skipna=False)
    return P, pd.DataFrame(coefs, index=VARS_NUCLEO).T.sort_index()


# %% 3 · modelo 1: walk-forward adaptativo (y base)
def correr(modo, con_lstm):
    if modo == "ventana":
        return walkforward(f"adaptativo_v{VENTANA_M1}_r{REAJUSTE_M1}", ventana=VENTANA_M1, reajuste=REAJUSTE_M1, con_lstm=con_lstm)
    if modo == "exponencial":
        return walkforward(f"adaptativo_vm{VIDA_MEDIA}_r{REAJUSTE_M1}", vida_media=VIDA_MEDIA, reajuste=REAJUSTE_M1, con_lstm=con_lstm)
    return walkforward("base_expansiva_r126", reajuste=126, con_lstm=con_lstm)


P_lstm_src, _ = correr(MODO_LSTM, con_lstm=True)
P_logit_src, COEF_ad = (P_lstm_src, _) if MODO_LOGIT == MODO_LSTM else correr(MODO_LOGIT, con_lstm=False)
P_ad = pd.DataFrame({"p_lstm": P_lstm_src.p_lstm, "p_logit": P_logit_src.p_logit})
P_ad["p"] = P_ad[["p_lstm", "p_logit"]].mean(axis=1, skipna=False)
SENALES = {"Adaptativo": P_ad}
if COMPARAR_BASE:
    P_base, COEF_base = correr("expansiva", con_lstm=True)
    SENALES["Base (control)"] = P_base
print("Modelo 1 listo.")
pd.concat({k: v for k, v in SENALES.items()}, axis=1).to_csv(f"{SALIDA}/predicciones_modelo1.csv", float_format="%.6g")
pd.concat({"Adaptativo": COEF_ad, **({"Base (control)": COEF_base} if COMPARAR_BASE else {})}, axis=1).to_csv(
    f"{SALIDA}/coeficientes_logistica.csv", float_format="%.6g")

# %% 4 · modelo 2: GARCH(1,1) + percentil de confianza (igual para ambos sistemas)


def garch_walkforward(r):
    x = (r / 100).to_numpy()
    sig2 = np.full(len(x), np.nan)
    w = a = b = s2 = None
    for t in range(VENTANA_GARCH, len(x)):
        if (t - VENTANA_GARCH) % REAJUSTE_GARCH == 0:
            res = arch_model(x[t - VENTANA_GARCH + 1:t + 1], mean="Zero", vol="GARCH", p=1, q=1,
                             dist="normal").fit(disp="off")
            w, a, b = res.params["omega"], res.params["alpha[1]"], res.params["beta[1]"]
            s2 = res.conditional_volatility[-1] ** 2
        s2 = w + a * x[t] ** 2 + b * s2
        sig2[t] = s2
    return pd.Series(np.sqrt(sig2) * 100, index=r.index)


SIG = garch_walkforward(m["x_usdclp_ret"].fillna(0.0)).reindex(FECHAS)
VOL_REL = SIG / SIG.rolling(VENTANA_PCT, min_periods=120).median().shift(1)
YRET = d["y_ret_neto_pb"]


def sistema(p):
    """Exposición y resultado diario a partir de la probabilidad del modelo 1."""
    p = p.dropna()
    p = p[VOL_REL.reindex(p.index).notna()]
    conf = (p - 0.5).abs()
    pct = conf.rolling(VENTANA_PCT + 1, min_periods=120).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    vr = VOL_REL.reindex(p.index)
    tam = pd.Series(np.where(pct >= U3, 3.0, np.where(pct >= U1, 1.0, 0.0)), index=p.index).where(pct.notna(), 0.0)
    tam = tam.where(~((tam == 3) & (vr > TOPE_VOL)), 1.0)        # tope GARCH: 3 → 1
    tam = tam.where(vr <= VOL_CERO, 0.0)                          # estricta: fuera si vol. relativa > 2
    e = np.sign(p - 0.5) * tam
    y = YRET.reindex(p.index)
    g = (e * y - COSTO * e.diff().abs().fillna(e.abs())).where(y.notna())
    return pd.DataFrame({"p": p, "pct_conf": pct, "vol_rel": vr, "exposicion": e, "y_ret_neto_pb": y, "resultado_pb": g})


def metricas(S):
    g = S.resultado_pb.dropna()
    if len(g) == 0:
        return {}
    eq = g.cumsum()
    ok = S.y_ret_neto_pb.notna()
    op = ok & (S.exposicion != 0)
    return {"ret_%": round((np.exp(g.sum() / 1e4) - 1) * 100, 1),
            "sharpe": round(g.mean() / g.std() * np.sqrt(252), 2) if g.std() > 0 else 0.0,
            "max_caida_%": round((np.exp((eq - eq.cummax()).min() / 1e4) - 1) * 100, 1),
            "acierto_dir_%": round((np.sign(S.p[ok] - 0.5) == np.sign(S.y_ret_neto_pb[ok])).mean() * 100, 1),
            "acierto_operado_%": round((np.sign(S.exposicion[op]) == np.sign(S.y_ret_neto_pb[op])).mean() * 100, 1) if op.any() else np.nan,
            "dias": int(ok.sum()), "%_operado": round(op.sum() / ok.sum() * 100, 0),
            "dias_±3": int((S.exposicion[ok].abs() == 3).sum())}


SIS, filas = {}, []
for nombre, P in SENALES.items():
    for comp in ("p", "p_logit", "p_lstm"):
        etiqueta = nombre + {"p": "", "p_logit": " · solo logística", "p_lstm": " · solo LSTM"}[comp]
        S = sistema(P[comp])
        SIS[etiqueta] = S
        for t, (a, b) in TRAMOS.items():
            filas.append({"senal": etiqueta, "tramo": t, **metricas(S.loc[a:b])})
R = pd.DataFrame(filas)
pd.set_option("display.width", 250)
for c in ("ret_%", "sharpe", "max_caida_%", "acierto_dir_%"):
    print(f"\n{c}")
    print(R.pivot(index="senal", columns="tramo", values=c)[list(TRAMOS)].to_string())
R.to_csv(f"{SALIDA}/resultados_adaptativo{'_estricta' if ESTRICTA else ''}.csv", index=False)

# %% 5 · gráficos
TIT = "versión estricta" if ESTRICTA else "versión reglas"


def sombrear(ax):
    for (t, (a, b)), col in zip(TRAMOS.items(), ["#fcfcfb", "#f4f3f0", "#e8f0fb", "#fbeee6", "#fde2e1"]):
        ax.axvspan(pd.Timestamp(a), min(pd.Timestamp(b), FECHAS[-1]), color=col, lw=0, zorder=0)


def estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color=C["rejilla"], lw=0.6)


# g1: retorno acumulado
fig, ax = plt.subplots(figsize=(13, 5))
sombrear(ax)
for nombre, col in zip(SENALES, [C["azul"], C["gris"]]):
    g = SIS[nombre].resultado_pb.loc[TRAMOS["desarrollo_p1"][0]:].fillna(0)
    ax.plot(g.index, (np.exp(g.cumsum() / 1e4) - 1) * 100, color=col, lw=1.8 if nombre == "Adaptativo" else 1.4, label=nombre)
ax.axhline(0, color=C["tinta2"], lw=0.8)
ax.set_ylabel("Retorno acumulado (%)")
ax.set_title(f"Gráfico A1 · Retorno acumulado neto, adaptativo vs base ({TIT}) · fondos: desarrollo p1 y p2, validación, test, datos nuevos",
             loc="left", fontweight="bold", fontsize=11)
ax.legend(frameon=False)
estilo(ax)
fig.tight_layout(); fig.savefig(f"{SALIDA}/a1_retorno_acumulado.png", dpi=150); plt.show()

# g2: cómo se mueven los pesos de la logística
claves = ["x_usdzar_ret", "x_cobre_lme_ret", "x_dxy_ret", "x_mxef_ret", "cal_viernes", "x_vol_em_dif"]
fig, axes = plt.subplots(2, 3, figsize=(14, 6.5), sharex=True)
for ax, v in zip(axes.flat, claves):
    ax.step(COEF_ad.index, COEF_ad[v], where="post", color=C["azul"], lw=1.4, label="Adaptativo")
    if COMPARAR_BASE:
        ax.step(COEF_base.index, COEF_base[v], where="post", color=C["gris"], lw=1.4, label="Base (control)")
    ax.axhline(0, color=C["tinta2"], lw=0.8)
    ax.set_title(v, fontsize=10)
    estilo(ax)
axes[0, 0].legend(frameon=False, fontsize=8)
fig.suptitle("Gráfico A2 · Coeficiente de la logística en cada reentrenamiento (variables estandarizadas)",
             x=0.01, ha="left", fontweight="bold")
fig.tight_layout(); fig.savefig(f"{SALIDA}/a2_coeficientes.png", dpi=150); plt.show()

# g3: último año — volatilidad GARCH y exposición del adaptativo
S = SIS["Adaptativo"].iloc[-250:]
fig, (a0, a1) = plt.subplots(2, 1, figsize=(13, 6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
a0.plot(S.index, SIG.reindex(S.index), color=C["naranjo"], lw=1.4, label="σ GARCH pronosticada (%)")
a0.plot(S.index, m["x_usdclp_ret"].abs().reindex(S.index), color=C["gris"], lw=0, marker=".", ms=3, label="|retorno| realizado (%)")
a0.legend(frameon=False, fontsize=9); a0.set_title("Volatilidad", loc="left", fontsize=10); estilo(a0)
col = {-3: "#c23b3a", -1: "#f2a6a5", 0: "#d9d8d4", 1: "#86b6ef", 3: "#1c5cab"}
a1.bar(S.index, S.exposicion, color=[col[int(v)] for v in S.exposicion], width=1)
a1.set_yticks([-3, -1, 0, 1, 3]); a1.set_title("Exposición del adaptativo (azul compra, rojo venta)", loc="left", fontsize=10); estilo(a1)
fig.suptitle("Gráfico A3 · Último año: GARCH y posiciones", x=0.01, ha="left", fontweight="bold")
fig.tight_layout(); fig.savefig(f"{SALIDA}/a3_ultimo_anio.png", dpi=150); plt.show()

# g4: zoom oct-nov 2026 día a día
a, b = TRAMOS["datos_nuevos"]
fig, ax = plt.subplots(figsize=(12, 4.5))
for nombre, cl in zip(SENALES, [C["azul"], C["gris"]]):
    g = SIS[nombre].resultado_pb.loc[a:b].dropna()
    ax.plot(g.index, g.cumsum(), color=cl, lw=2 if nombre == "Adaptativo" else 1.4, marker="o", ms=3, label=nombre)
ax.axhline(0, color=C["tinta2"], lw=0.8)
ax.set_ylabel("pb acumulados"); ax.legend(frameon=False)
ax.set_title("Gráfico A4 · Datos nuevos (desde el 6-oct-2026), resultado acumulado", loc="left", fontweight="bold")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b")); estilo(ax)
fig.tight_layout(); fig.savefig(f"{SALIDA}/a4_oct_nov.png", dpi=150); plt.show()

# %% 6 · señal para la próxima jornada


def siguiente_dia_habil(f):
    try:
        import holidays
        fer = holidays.Chile(years=[f.year, f.year + 1])
    except Exception:
        fer = {}
    x = f + timedelta(days=1)
    while x.weekday() >= 5 or x.date() in fer:
        x += timedelta(days=1)
    return x


for nombre in SENALES:
    S, P = SIS[nombre], SENALES[nombre]
    hoy = S.index[-1]
    e = int(S.exposicion.iloc[-1])
    print(f"\n{nombre} — cierre {hoy.date()} → jornada {siguiente_dia_habil(hoy).date()}")
    print(f"  p = {S.p.iloc[-1]:.3f}  (LSTM {P.p_lstm.loc[hoy]:.3f} · logística {P.p_logit.loc[hoy]:.3f})")
    print(f"  percentil de confianza = {S.pct_conf.iloc[-1]:.2f}  ·  vol. relativa GARCH = {S.vol_rel.iloc[-1]:.2f}")
    print(f"  EXPOSICIÓN = {e:+d}  ({'compra' if e > 0 else 'venta' if e < 0 else 'fuera'} USD)")
pd.concat({k: v for k, v in SIS.items() if " · " not in k}, axis=1).to_csv(
    f"{SALIDA}/posiciones_adaptativo{'_estricta' if ESTRICTA else ''}.csv", float_format="%.5f")
print(f"\nGuardado en {SALIDA}/: resultados_adaptativo.csv, posiciones_adaptativo.csv, predicciones_modelo1.csv, "
      f"coeficientes_logistica.csv y gráficos a1-a4.")
