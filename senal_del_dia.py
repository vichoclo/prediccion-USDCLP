# -*- coding: utf-8 -*-
"""
senal_del_dia.py — Señal diaria del sistema ADAPTATIVO para el monitoreo en vivo.
Torneo Itaú-FEN · USD/CLP.

Sistema adaptativo (oficial):
  modelo 1 = promedio de dos componentes, 11 variables núcleo
             · LSTM de 20 días (5 semillas): toda la historia, con peso exponencial
               0,5^(antigüedad / 250 días), reentrenado cada 21 días
             · logística (C = 0,05): solo los últimos 500 días, reentrenada cada 21 días
  modelo 2 = percentil de confianza (u1 = 0,6; u3 = 0,8) + tope GARCH(1,1) 1,5
Con SISTEMA = "base" reproduce el sistema anterior (control): ambos componentes con
toda la historia y el mismo peso, reentrenados cada 126 días.

QUÉ HACE
  Toma la base tratada (preparar_base_v2.py) y entrega, para el ÚLTIMO día de la base,
  la dirección, la probabilidad, la confianza, la volatilidad relativa y la exposición
  sugerida para la jornada siguiente. Usa los mismos parámetros, semillas y calendario
  de reentrenamiento que el walk-forward del informe (modelo_adaptativo_colab.py), así
  que la señal es la misma que habría dado el backtest ese día.

  El percentil de confianza necesita las probabilidades de los 250 días anteriores, así
  que el script usa los modelos de los bloques que cubren esos días (~13 bloques de 21).

  MODELOS GUARDADOS (modelos_vigentes.pt)
  La primera corrida entrena esos bloques (~3 minutos en CPU) y los guarda. Las
  siguientes los cargan y solo predicen el día nuevo. Cada 21 días hábiles la base
  llega a un bloque nuevo y el script entrena solo ese bloque (~15 segundos). Si cambian
  los datos de entrenamiento de un bloque (se corrige un cierre antiguo), se reentrena.

CÓMO USARLO
  Colab:  !python senal_del_dia.py modelo_usdclp_desde_2001.xlsx
  Local:  python senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
  Opcional: --hasta AAAA-MM-DD  calcula la señal como si ese fuera el último día
            --sistema base      señal del sistema anterior (control)
  Cada corrida agrega una fila a bitacora_senales.csv.

PROCEDIMIENTO DIARIO (sección 9.4 del informe)
  1. Agregar los cierres del día a la base cruda.
  2. python preparar_base_v2.py "base_usdclp 2.xlsx" datos/procesados/
  3. python senal_del_dia.py datos/procesados/modelo_usdclp_desde_2001.csv
"""
import argparse
import hashlib
import os
import sys
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from arch import arch_model
from sklearn.linear_model import LogisticRegression

warnings.filterwarnings("ignore")

# ============================================================== CONFIGURACIÓN (si se pega en una celda de Colab)
ARCHIVO = "modelo_usdclp_desde_2001.xlsx"   # base TRATADA (salida de preparar_base_v2.py)
HASTA = None                                # None = último día de la base; o "AAAA-MM-DD"
SISTEMA = "adaptativo"                      # "adaptativo" (oficial) o "base" (control)

# ============================================================== parámetros (iguales a modelo_adaptativo_colab.py)
VARS_NUCLEO = ["x_cobre_lme_ret", "x_cobre_comex_ret", "x_oro_ret", "x_dxy_ret", "x_bbdxy_ret",
               "x_dxy_mom20", "x_usdzar_ret", "x_mxef_ret", "x_vol_em_dif",
               "cal_viernes", "cal_dias_corridos_sig"]
DESDE, PRED_DESDE = "2001-08-09", "2005-01-01"
L, EMBARGO, MIN_TRAIN, VAL_FRAC, MIN_VAL, SEMILLAS = 20, 5, 750, 0.15, 100, 5
HIDDEN, DROPOUT, LR, WEIGHT_DECAY, BATCH, EPOCAS, PACIENCIA = 16, 0.2, 1e-3, 1e-3, 128, 60, 8
C_LOGIT = 0.05
# Cómo aprende cada componente: ventana (días) o vida_media (días) y cada cuántos días se reentrena
COMPONENTES = {
    "adaptativo": {"lstm": {"ventana": None, "vida_media": 250, "reajuste": 21},
                   "logit": {"ventana": 500, "vida_media": None, "reajuste": 21}},
    "base": {"lstm": {"ventana": None, "vida_media": None, "reajuste": 126},
             "logit": {"ventana": None, "vida_media": None, "reajuste": 126}},
}
VENTANA_GARCH, REAJUSTE_GARCH, VENTANA_PCT = 1000, 21, 250
U1, U3, TOPE_VOL = 0.6, 0.8, 1.5

DISP = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================== datos
COLUMNAS_NECESARIAS = VARS_NUCLEO[:9] + ["cal_dias_corridos_sig", "cal_dia_semana", "x_usdclp_ret",
                                         "y_sube_neto", "y_ret_neto_pb"]


def cargar(archivo, hasta=None):
    if not os.path.exists(archivo):
        raise SystemExit(f"No encuentro el archivo '{archivo}'. Súbalo al panel de archivos de Colab "
                         f"(ícono de carpeta) o escriba su ruta.")
    if archivo.lower().endswith((".xlsx", ".xls")):
        m = pd.read_excel(archivo, index_col=0, parse_dates=True)
    else:
        m = pd.read_csv(archivo, index_col=0, parse_dates=True)
    faltan = [c for c in COLUMNAS_NECESARIAS if c not in m.columns]
    if faltan:
        raise SystemExit(f"'{archivo}' no es la base tratada: le faltan {faltan[:4]}{'...' if len(faltan) > 4 else ''}.\n"
                         f"Use modelo_usdclp_desde_2001.xlsx, la que genera preparar_base_v2.py "
                         f"(no la base cruda de Bloomberg).")
    m["cal_viernes"] = (m["cal_dia_semana"] == 4).astype(float)
    if hasta is not None:
        m = m.loc[:hasta].copy()
        # el último día se trata como en vivo: su resultado todavía no se conoce
        m.loc[m.index[-1], ["y_sube_neto", "y_ret_neto_pb"]] = np.nan
    return m


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


# ============================================================== modelo 1
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
    """Adam + early stopping con pérdida ponderada por observación (peso 1 = sin ponderar)."""
    torch.manual_seed(semilla)
    np.random.seed(semilla)
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
    red.load_state_dict(estado)
    red.eval()
    return red


def logits(red, X):
    with torch.no_grad():
        return red(torch.tensor(X, device=DISP)).cpu().numpy()


def huella(*arrs):
    """Identifica los datos de entrenamiento de un bloque: si la base cambia, se reentrena."""
    h = hashlib.md5()
    for a in arrs:
        h.update(np.ascontiguousarray(np.nan_to_num(a, nan=-9e9)).tobytes())
    return h.hexdigest()


def filas_entrenamiento(valido, r, ventana, vida_media):
    fin = r - EMBARGO                                   # embargo: los últimos 5 días no entran
    tr = np.where(valido[:fin])[0]
    if ventana:
        tr = tr[-ventana:]
    w = np.ones(len(tr))
    if vida_media:
        w = 0.5 ** ((tr[-1] - tr) / vida_media)
        w = w / w.mean()
    return tr, w, fin


def entrenar_bloque(comp, cfg, Z_raw, y, valido, r, fecha):
    tr, w, fin = filas_entrenamiento(valido, r, cfg["ventana"], cfg["vida_media"])
    esc = escalador(Z_raw[tr[0]:fin])
    Z = escalar(Z_raw, esc)
    mod = {"comp": comp, "fecha": str(fecha.date()), "n_train": len(tr), "escalador": esc,
           "huella": huella(Z_raw[tr[0]:fin], y[:fin], np.array([cfg["ventana"] or 0, cfg["vida_media"] or 0]))}
    if comp == "logit":
        mod["logit"] = LogisticRegression(C=C_LOGIT, max_iter=1000).fit(Z[tr], y[tr], sample_weight=w)
    else:
        n_val = max(int(len(tr) * VAL_FRAC), MIN_VAL)
        i_fit, i_val = np.arange(len(tr) - n_val - L), np.arange(len(tr) - n_val, len(tr))   # brecha de L días
        Xa, Xv = secuencias(Z, tr[i_fit]), secuencias(Z, tr[i_val])
        ya, yv = y[tr[i_fit]].astype(np.float32), y[tr[i_val]].astype(np.float32)
        wa, wv = w[i_fit].astype(np.float32), w[i_val].astype(np.float32)
        redes, zv = [], []
        for s in range(SEMILLAS):
            red = entrenar_lstm(Xa, ya, wa, Xv, yv, wv, semilla=1000 * s + r)
            zv.append(logits(red, Xv))
            redes.append({k: v.cpu() for k, v in red.state_dict().items()})
        mod["redes"] = redes
        mod["platt"] = LogisticRegression(C=1.0).fit(np.mean(zv, 0).reshape(-1, 1), yv, sample_weight=wv)
    print(f"  {comp} · bloque desde {fecha.date()}: ENTRENADO con {len(tr)} días")
    return mod


def predecir_bloque(mod, Z_raw, filas):
    Z = escalar(Z_raw, mod["escalador"])
    if mod["comp"] == "logit":
        return mod["logit"].predict_proba(Z[filas])[:, 1]
    Xp = secuencias(Z, filas)
    zp = []
    for estado in mod["redes"]:
        red = RedLSTM(Z.shape[1]).to(DISP)
        red.load_state_dict(estado)
        red.eval()
        zp.append(logits(red, Xp))
    return mod["platt"].predict_proba(np.mean(zp, 0).reshape(-1, 1))[:, 1]


def cargar_modelos(ruta):
    if ruta and os.path.exists(ruta):
        try:
            return torch.load(ruta, weights_only=False)
        except TypeError:                      # versiones antiguas de torch
            return torch.load(ruta)
    return {}


def probabilidades_recientes(m, dias_necesarios, ruta_modelos=None, sistema=None):
    """Probabilidades del LSTM y de la logística en los últimos `dias_necesarios` días, con
    el mismo calendario de reentrenamiento, pesos y semillas que el walk-forward del informe.
    Con ruta_modelos, los modelos de cada bloque se guardan y se reutilizan."""
    sistema = sistema or SISTEMA
    d = m.loc[DESDE:]
    Z_raw = d[VARS_NUCLEO].to_numpy(float)
    y = d["y_sube_neto"].to_numpy(float)
    fechas, valido, T = d.index, ~np.isnan(y), len(d)
    inicio = max(np.searchsorted(fechas, pd.Timestamp(PRED_DESDE)),
                 np.searchsorted(np.cumsum(valido), MIN_TRAIN) + EMBARGO + 1)

    guardados = cargar_modelos(ruta_modelos)
    vigentes, cambio = {}, False
    salida = {"p_lstm": np.full(T, np.nan), "p_logit": np.full(T, np.nan)}
    for comp, cfg in COMPONENTES[sistema].items():
        R = cfg["reajuste"]
        for r in [r for r in range(inicio, T, R) if r + R > T - dias_necesarios]:
            clave = f"{sistema}|{comp}|{fechas[r].date()}"
            tr, _, fin = filas_entrenamiento(valido, r, cfg["ventana"], cfg["vida_media"])
            h = huella(Z_raw[tr[0]:fin], y[:fin], np.array([cfg["ventana"] or 0, cfg["vida_media"] or 0]))
            mod = guardados.get(clave)
            if mod is None or mod["huella"] != h:
                mod, cambio = entrenar_bloque(comp, cfg, Z_raw, y, valido, r, fechas[r]), True
            vigentes[clave] = mod
            filas = np.arange(r, min(r + R, T))
            salida[f"p_{comp}"][filas] = predecir_bloque(mod, Z_raw, filas)
    if ruta_modelos and (cambio or set(vigentes) != set(guardados)):
        torch.save(vigentes, ruta_modelos)
        print(f"  modelos guardados en {ruta_modelos}")
    return pd.DataFrame(salida, index=fechas)


# ============================================================== modelo 2
def garch_walkforward(r):
    x = (r / 100).to_numpy()
    n = len(x)
    sig2 = np.full(n, np.nan)
    w = a = b = s2 = None
    for t in range(VENTANA_GARCH, n):
        if (t - VENTANA_GARCH) % REAJUSTE_GARCH == 0:
            res = arch_model(x[t - VENTANA_GARCH + 1:t + 1], mean="Zero", vol="GARCH",
                             p=1, q=1, dist="normal").fit(disp="off")
            w, a, b = res.params["omega"], res.params["alpha[1]"], res.params["beta[1]"]
            s2 = res.conditional_volatility[-1] ** 2
        s2 = w + a * x[t] ** 2 + b * s2
        sig2[t] = s2
    return pd.Series(np.sqrt(sig2) * 100, index=r.index)


def siguiente_dia_habil(fecha):
    try:
        import holidays
        feriados = holidays.Chile(years=[fecha.year, fecha.year + 1])
    except Exception:
        feriados = {}
    d = fecha + timedelta(days=1)
    while d.weekday() >= 5 or d.date() in feriados:
        d += timedelta(days=1)
    return d


def fmt(x, dec=3):
    return f"{x:.{dec}f}".replace(".", ",")


# ============================================================== principal
def calcular_senal(m, verbose=True, ruta_modelos=None, sistema=None):
    """Señal para el último día de la base m. Devuelve un diccionario con todo lo que
    se imprime y se guarda en la bitácora."""
    sistema = sistema or SISTEMA
    hoy = m.index[-1]
    log = print if verbose else (lambda *a, **k: None)

    log(f"Modelo 1 ({sistema}): modelos vigentes del walk-forward...")
    P = probabilidades_recientes(m, dias_necesarios=VENTANA_PCT + 1, ruta_modelos=ruta_modelos, sistema=sistema)
    P["p"] = P[["p_lstm", "p_logit"]].mean(axis=1, skipna=False)

    log("Modelo 2: GARCH(1,1)...")
    sig = garch_walkforward(m["x_usdclp_ret"].fillna(0.0))
    vol_rel = sig / sig.rolling(VENTANA_PCT, min_periods=120).median().shift(1)

    # mismas filas que el backtest: días con probabilidad y volatilidad relativa
    p = P["p"].dropna()
    p = p[vol_rel.reindex(p.index).notna()]
    conf = (p - 0.5).abs()
    hist = conf.iloc[-(VENTANA_PCT + 1):-1]
    if len(hist) < 120:
        raise SystemExit("Faltan días de historia para el percentil de confianza.")
    pct = float((hist < conf.iloc[-1]).mean())

    p_hoy, vr_hoy = float(p.iloc[-1]), float(vol_rel.loc[hoy])
    tam = 3 if pct >= U3 else (1 if pct >= U1 else 0)
    recorte = tam == 3 and vr_hoy > TOPE_VOL
    if recorte:
        tam = 1
    lado = 1 if p_hoy > 0.5 else (-1 if p_hoy < 0.5 else 0)
    return {
        "sistema": sistema, "fecha_cierre": hoy, "jornada": siguiente_dia_habil(hoy), "p": p_hoy,
        "p_lstm": float(P["p_lstm"].iloc[-1]), "p_logit": float(P["p_logit"].iloc[-1]),
        "percentil_confianza": pct, "vol_relativa": vr_hoy, "sigma_garch_pb": float(sig.loc[hoy]),
        "tope_garch": recorte, "lado": lado, "tamano": tam, "exposicion": lado * tam,
    }


def imprimir(s):
    direccion = "COMPRAR dólar" if s["lado"] > 0 else ("VENDER dólar" if s["lado"] < 0 else "SIN DIRECCIÓN")
    if s["tamano"] == 0:
        motivo = f"   (abstención: confianza bajo el percentil {U1 * 100:.0f})"
    elif s["tope_garch"]:
        motivo = f"   (tope GARCH: 3 → 1 porque la vol. relativa supera {TOPE_VOL})"
    else:
        motivo = ""
    print("\n" + "=" * 78)
    print(f"Señal al cierre del {s['fecha_cierre'].date()} (para la jornada siguiente, {s['jornada'].date()}):")
    print(f"  dirección: {direccion} | p = {fmt(s['p'])} | confianza (percentil) = {fmt(s['percentil_confianza'], 2)} "
          f"| vol. relativa = {fmt(s['vol_relativa'], 2)}")
    print(f"  exposición sugerida: {s['exposicion']:+d}".replace("+0", "0").replace("-", "−") + motivo)
    print(f"  componentes: p LSTM = {fmt(s['p_lstm'])} · p logística = {fmt(s['p_logit'])}   [sistema {s['sistema']}]")
    print("=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?", default=ARCHIVO)
    ap.add_argument("--hasta", default=HASTA, help="AAAA-MM-DD: calcula la señal como si fuera el último día")
    ap.add_argument("--sistema", default=SISTEMA, choices=list(COMPONENTES))
    ap.add_argument("--bitacora", default="bitacora_senales.csv")
    ap.add_argument("--modelos", default=None,
                    help="archivo de modelos guardados (por defecto modelos_vigentes_<sistema>.pt; '' para no guardar)")
    # Pegado en una celda de Colab/Jupyter, sys.argv trae los argumentos del kernel:
    # se ignoran y se usan ARCHIVO, HASTA y SISTEMA de la configuración de arriba.
    en_notebook = "ipykernel" in sys.modules
    args = ap.parse_args([] if en_notebook else None)
    ruta = f"modelos_vigentes_{args.sistema}.pt" if args.modelos is None else (args.modelos or None)

    m = cargar(args.archivo, args.hasta)
    print(f"Base: {args.archivo} · {len(m)} días · último cierre {m.index[-1].date()}")
    # con --hasta no se tocan los modelos guardados de la operación en vivo
    s = calcular_senal(m, ruta_modelos=None if args.hasta else ruta, sistema=args.sistema)
    imprimir(s)

    fila = pd.DataFrame([{
        "sistema": s["sistema"], "fecha_cierre": s["fecha_cierre"].date(), "jornada": s["jornada"].date(),
        "p": round(s["p"], 4), "p_lstm": round(s["p_lstm"], 4), "p_logit": round(s["p_logit"], 4),
        "percentil_confianza": round(s["percentil_confianza"], 3), "vol_relativa": round(s["vol_relativa"], 3),
        "sigma_garch_pb": round(s["sigma_garch_pb"], 1), "tope_garch": s["tope_garch"], "exposicion": s["exposicion"],
    }])
    nuevo = not os.path.exists(args.bitacora)
    fila.to_csv(args.bitacora, mode="a", header=nuevo, index=False)
    print(f"Guardado en {args.bitacora}")


if __name__ == "__main__":
    main()
