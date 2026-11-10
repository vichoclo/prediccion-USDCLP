"""
preparar_base_v2.py — Base USD/CLP desde 2001-08 para modelar (Torneo Itaú-FEN).

Lee la base cruda de Bloomberg (hoja 'datos'), la limpia y construye las variables del
modelo (x_*), el calendario (cal_*), el objetivo (y_*) y el carry. Detalle: informe, sección 1.

Uso:
    python src/preparar_base_v2.py "datos/base_usdclp 2.xlsx" datos/procesados/ [--ipsa ipsa.csv]

Salida: modelo_usdclp_desde_{2001,2010,2018}.csv y .xlsx en la carpeta indicada.
El sistema usa modelo_usdclp_desde_2001.
"""
import argparse
import warnings
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

INICIO = "2001-08-09"
CORTES = {"2001": "2001-08-09", "2010": "2010-01-01", "2018": "2018-01-17"}
LIM_FFILL = 10

PERIODOS = [
    ("calentamiento", "2001-08-09", "2001-11-30"),
    ("entrenamiento_inicial", "2001-12-01", "2004-12-31"),
    ("desarrollo", "2005-01-01", "2021-12-31"),
    ("validacion", "2022-01-01", "2024-12-31"),
    ("test", "2025-01-01", "2099-12-31"),
]

CONFIABLE_DESDE = {
    "USDCLPV1M Curncy": "2009-01-01",
    "USDCLPV3M Curncy": "2009-01-01",
    "CHNI1M Curncy": "2010-01-01",
    "CHNI3M Curncy": "2010-01-01",
    "CHNI6M Curncy": "2010-01-01",
    "CHSWP1 Curncy": "2007-01-01",
    "CHSWP2 Curncy": "2007-01-01",
    "CHSWP5 Curncy": "2007-01-01",
    "CHSWP10 Curncy": "2007-01-01",
    "CHSWC2 Curncy": "2007-01-01",
}
COTIZADAS = list(CONFIABLE_DESDE) + ["JPMVXYEM Index", "MOVE Index"]

FERIADOS = holidays.Chile(years=range(2000, 2028), categories=("public", "bank"))


def es_habil(d):
    return d.weekday() < 5 and d not in FERIADOS


def proximo_habil(d):
    d = d + pd.Timedelta(days=1)
    while not es_habil(d.date()):
        d += pd.Timedelta(days=1)
    return d


COLUMNA_CLAVE = "USDCLP Curncy|PX_LAST"


def leer_base_cruda(ruta):
    """Lee la base cruda de Bloomberg. Busca la hoja 'datos'; si no existe, usa la hoja que
    tenga la columna 'fecha' y el cierre del USD/CLP, y avisa. Si el archivo es una base ya
    tratada (salida de este script), lo dice en vez de fallar con un error de pandas."""
    import sys
    if not Path(ruta).exists():
        sys.exit(f"No encuentro '{ruta}'. Súbalo al panel de archivos de Colab o revise el nombre "
                 f"(si tiene espacios, va entre comillas).")
    if str(ruta).lower().endswith(".csv"):
        raw = pd.read_csv(ruta)
    else:
        hojas = pd.ExcelFile(ruta).sheet_names
        if "datos" in hojas:
            hoja = "datos"
        elif "modelo" in hojas:
            sys.exit(f"'{ruta}' es una base YA TRATADA (hoja 'modelo'), no la base cruda de Bloomberg.\n"
                     f"No hace falta volver a prepararla: úsela directo con senal_del_dia.py.\n"
                     f"preparar_base_v2.py necesita la base cruda (por ejemplo, 'base_usdclp 2.xlsx', hoja 'datos').")
        else:
            hoja = None
            for h in hojas:
                cols = pd.read_excel(ruta, sheet_name=h, nrows=0).columns
                if "fecha" in cols and COLUMNA_CLAVE in cols:
                    hoja = h
                    break
            if hoja is None:
                sys.exit(f"'{ruta}' no tiene una hoja 'datos' ni otra con las columnas 'fecha' y '{COLUMNA_CLAVE}'.\n"
                         f"Hojas del archivo: {hojas}.\n"
                         f"La base cruda debe tener el formato de 'base_usdclp 2.xlsx': una fila por fecha y "
                         f"columnas 'TICKER|CAMPO'.")
            print(f"Aviso: no hay hoja 'datos'; uso la hoja '{hoja}'.")
        raw = pd.read_excel(ruta, sheet_name=hoja)
    if "fecha" not in raw.columns or COLUMNA_CLAVE not in raw.columns:
        sys.exit(f"'{ruta}' no tiene las columnas 'fecha' y '{COLUMNA_CLAVE}'.")
    return raw


def cargar(ruta, ipsa_ext=None):
    raw = leer_base_cruda(ruta)
    raw["fecha"] = pd.to_datetime(raw["fecha"])
    raw = raw.set_index("fecha").sort_index()
    if ipsa_ext is not None:
        raw = completar_ipsa(raw, ipsa_ext)
    habil = np.array([es_habil(d.date()) for d in raw.index])
    d = raw[(raw.index >= INICIO) & habil].copy()
    return raw, d


def completar_ipsa(raw, ruta):
    ext = pd.read_csv(ruta, parse_dates=["fecha"]).set_index("fecha")["valor"].sort_index()
    base = raw["IPSA Index|PX_LAST"]
    comun = base.dropna().index.intersection(ext.index)
    if len(comun) < 5:
        raise ValueError("El archivo del IPSA necesita al menos 5 días en común con la base para empalmar")
    ultimo = base.last_valid_index()
    k = (base.loc[comun] / ext.loc[comun]).iloc[-20:].median()
    nuevo = ext.loc[ext.index > ultimo] * k
    raw = raw.reindex(raw.index.union(nuevo.index))
    raw.loc[nuevo.index, "IPSA Index|PX_LAST"] = nuevo.values
    raw["flag_ipsa_externo_raw"] = 0
    raw.loc[nuevo.index, "flag_ipsa_externo_raw"] = 1
    print(f"IPSA externo: {len(nuevo)} días agregados desde {ultimo.date()} (factor de empalme {k:.4f})")
    return raw


def col(d, ticker, campo="PX_LAST"):
    return d[f"{ticker}|{campo}"]


def depurar_cotizadas(d):
    edades = {}
    for t in COTIZADAS:
        c = f"{t}|PX_LAST"
        s = d[c].copy()
        if t in CONFIABLE_DESDE:
            s[s.index < CONFIABLE_DESDE[t]] = np.nan
        prev = s.ffill()
        repetido = s.notna() & (s == prev.shift(1))
        fresco = s.notna() & ~repetido
        s[repetido] = np.nan
        d[c] = s
        grupo = fresco.cumsum()
        edad = grupo.groupby(grupo).cumcount().astype(float)
        edad[grupo == 0] = np.nan
        edades[t] = edad
    return d, pd.DataFrame(edades, index=d.index)


def ffill(s):
    return s.ffill(limit=LIM_FFILL)


def ret_pb(s):
    s = ffill(s)
    return np.log(s).diff() * 1e4


def dif_pb(s):
    return ffill(s).diff() * 100


REZ_MAX = {}
REZ_FIJO = {"CLIMMOMS Index": 38, "CLIMYOYN Index": 50, "CLINNSYO Index": 8, "CHUETOTL Index": 34}
REZ_MIN = {"CLIMMOMS Index": 25, "CLIMYOYN Index": 25, "CLINNSYO Index": 5, "CHUETOTL Index": 25}


def macro_pit(raw, idx, ticker):
    v = col(raw, ticker).dropna()
    rel = pd.to_datetime(col(raw, ticker, "FECHA_RELEASE").reindex(v.index))
    rez = REZ_FIJO[ticker]
    REZ_MAX[ticker] = rez
    lag = (rel - v.index).dt.days
    rel = rel.where(lag >= REZ_MIN[ticker])
    rel = rel.fillna(pd.Series(v.index + pd.Timedelta(days=rez), index=v.index))
    t = pd.DataFrame({"release": rel.values, "ref": v.index, "valor": v.values,
                      "cambio": v.diff().values}).sort_values(["release", "ref"], kind="mergesort")
    out = pd.merge_asof(pd.DataFrame({"fecha": idx}), t, left_on="fecha",
                        right_on="release", direction="backward")
    return out.set_index("fecha")[["valor", "cambio"]]


def construir(raw, d):
    d, edades = depurar_cotizadas(d)
    idx = d.index
    m = pd.DataFrame(index=idx)
    dic = []

    def add(nombre, serie, desc, fuente, rezago="0"):
        m[nombre] = serie
        dic.append((nombre, desc, fuente, rezago))

    per = pd.Series(index=idx, dtype=object)
    for n, a, b in PERIODOS:
        per[(idx >= a) & (idx <= b)] = n
    add("periodo", per, "Tramo del protocolo", "protocolo")

    sig = pd.Series([proximo_habil(t) for t in idx], index=idx)
    dias = (sig - pd.Series(idx, index=idx)).dt.days
    add("cal_dia_semana", pd.Series(idx.dayofweek, index=idx), "0=lunes … 4=viernes", "calendario")
    add("cal_dias_corridos_sig", dias, "Días corridos hasta la próxima jornada hábil", "calendario")

    spot = col(d, "USDCLP Curncy")
    falta = spot.isna()
    spot_rel = spot.ffill(limit=LIM_FFILL)
    relleno = (falta & spot_rel.notna()).astype(int)
    add("flag_usdclp_falta", falta.astype(int), "1 si Bloomberg no trae USDCLP ese día", "USDCLP")
    add("flag_usdclp_relleno", relleno, "1 si el spot se arrastró del último día con dato", "USDCLP")
    add("flag_vol20_contaminada", relleno.rolling(21, min_periods=1).max().astype(int),
        "1 si la ventana de 20 retornos incluye un spot rellenado", "USDCLP")
    add("usdclp_cierre", spot, "Cierre USDCLP sin rellenar", "USDCLP")

    tpm = ffill(col(d, "CHOVCHOV Index"))
    iusd = ffill(col(d, "SOFRRATE Index").combine_first(col(d, "FEDL01 Index")))
    carry = (tpm - iusd) / 100 * dias / 360 * 1e4
    add("carry_pb", carry, "Carry de t a t+1 en pb", "CHOVCHOV, SOFRRATE, FEDL01", "objetivo")

    y = np.log(spot.shift(-1) / spot) * 1e4
    add("y_ret_pb", y, "Retorno log USDCLP de t a t+1, en pb", "USDCLP", "futuro")
    add("y_ret_neto_pb", y - carry, "Retorno t→t+1 menos carry", "USDCLP + carry", "futuro")
    add("y_sube", (y > 0).astype(float).where(y.notna()), "1 si el dólar sube de t a t+1", "USDCLP", "futuro")
    add("y_sube_neto", (y - carry > 0).astype(float).where(y.notna() & carry.notna()),
        "1 si conviene estar comprado", "USDCLP + carry", "futuro")

    r = np.log(spot_rel).diff() * 1e4
    add("x_usdclp_ret", r, "Retorno log USDCLP t-1→t (pb)", "USDCLP")
    for k in range(1, 5):
        add(f"x_usdclp_ret_l{k}", r.shift(k), f"Retorno USDCLP rezagado {k} días", "USDCLP")
    for w in (5, 20, 60):
        add(f"x_usdclp_mom{w}", np.log(spot_rel / spot_rel.shift(w)) * 1e4, f"Retorno acumulado {w} días", "USDCLP")
    for w in (5, 20, 60):
        add(f"x_usdclp_vol{w}", r.rolling(w, min_periods=int(w * .8)).std() * np.sqrt(252) / 100,
            f"Volatilidad realizada {w} días", "USDCLP")
    o, h, l = (col(d, "USDCLP Curncy", c) for c in ("PX_OPEN", "PX_HIGH", "PX_LOW"))
    add("x_usdclp_rango", (h - l) / spot * 1e4, "Rango alto-bajo / cierre (pb)", "USDCLP OHLC")
    add("x_usdclp_cuerpo", np.log(spot / o) * 1e4, "Cierre vs apertura (pb)", "USDCLP OHLC")
    v1m = ffill(col(d, "USDCLPV1M Curncy"))
    add("x_vol_impl_1m", v1m, "Vol implícita 1M", "USDCLPV1M")
    add("x_vol_impl_1m_dif", v1m.diff(), "Cambio vol implícita 1M", "USDCLPV1M")
    add("x_vol_impl_3m", ffill(col(d, "USDCLPV3M Curncy")), "Vol implícita 3M", "USDCLPV3M")
    add("x_vol_prima", v1m - m["x_usdclp_vol20"], "Vol implícita 1M − realizada 20d", "USDCLPV1M, USDCLP")

    add("x_dif_tasas", tpm - iusd.shift(1), "TPM − tasa USD", "CHOVCHOV, SOFR/FEDL01", "USD: 1")
    add("x_tpm_dif", tpm.diff() * 100, "Cambio diario TPM (pb)", "CHOVCHOV")
    dias_atras = pd.Series(idx, index=idx).diff().dt.days
    cam = (col(d, "CLICP Index") / col(d, "CLICP Index").shift(1) - 1) * 360 / dias_atras * 100
    add("x_camara", cam, "Tasa de cámara implícita", "CLICP")
    add("x_camara_menos_tpm", cam - tpm, "Cámara − TPM", "CLICP, CHOVCHOV")
    camr = (col(d, "CLICREAL Index") / col(d, "CLICREAL Index").shift(1) - 1) * 360 / dias_atras * 100
    add("x_camara_real", camr, "Tasa de cámara real", "CLICREAL")
    for t in ("CHNI1M", "CHNI3M", "CHNI6M"):
        s = ffill(col(d, f"{t} Curncy"))
        add(f"x_{t.lower()}", s, f"Rendimiento implícito NDF {t[4:]}", t)
        add(f"x_{t.lower()}_dif", s.diff() * 100, f"Cambio diario {t} (pb)", t)
    add("x_basis_ndf1m", ffill(col(d, "CHNI1M Curncy")) - tpm, "NDF 1M − TPM", "CHNI1M, CHOVCHOV")
    for t in ("CHSWP1", "CHSWP2", "CHSWP5", "CHSWP10", "CHSWC2"):
        add(f"x_{t.lower()}_dif", dif_pb(col(d, f"{t} Curncy")), f"Cambio diario swap {t}", t)
    add("x_pendiente_swp", ffill(col(d, "CHSWP10 Curncy")) - ffill(col(d, "CHSWP1 Curncy")), "Swap 10a − 1a", "CHSWP")
    add("x_infl_impl_2a", ffill(col(d, "CHSWP2 Curncy")) - ffill(col(d, "CHSWC2 Curncy")), "Inflación implícita 2a", "CHSWP2, CHSWC2")
    add("x_uf_ret", ret_pb(col(d, "CHUF Index")), "Variación diaria UF", "CHUF")

    for t in ("USDCLPV1M Curncy", "CHNI1M Curncy", "CHNI3M Curncy", "CHSWP2 Curncy", "CHSWP5 Curncy"):
        n = t.split()[0].lower()
        add(f"edad_{n}", edades[t], f"Días desde la última cotización nueva de {t}", t)

    add("x_tasa_usd_dif", (iusd.diff() * 100).shift(1), "Cambio SOFR/FedFunds, rezagado 1 día", "SOFRRATE, FEDL01", "1")
    for t in ("USGG3M", "USGG2YR", "USGG10YR"):
        add(f"x_{t.lower()}_dif", dif_pb(col(d, f"{t} Index")), f"Cambio diario Tesoro {t}", t)
    add("x_dif_2a_cl_us", ffill(col(d, "CHSWP2 Curncy")) - ffill(col(d, "USGG2YR Index")), "Swap CLP 2a − Tesoro 2a", "CHSWP2, USGG2YR")

    precios = {
        "cobre_lme": "LMCADS03 Comdty", "cobre_comex": "HG1 Comdty", "aluminio": "LMAHDS03 Comdty",
        "brent": "CO1 Comdty", "hierro": "SCO1 Comdty", "oro": "XAU Curncy", "bcom": "BCOM Index",
        "dxy": "DXY Curncy", "bbdxy": "BBDXY Index", "eurusd": "EURUSD Curncy", "usdjpy": "USDJPY Curncy",
        "usdcnh": "USDCNH Curncy", "usdcny": "USDCNY Curncy", "usdbrl": "USDBRL Curncy",
        "usdmxn": "USDMXN Curncy", "usdcop": "USDCOP Curncy", "usdpen": "USDPEN Curncy",
        "usdzar": "USDZAR Curncy", "spx": "SPX Index", "mxef": "MXEF Index", "shcomp": "SHCOMP Index",
        "ipsa": "IPSA Index",
    }
    for n, t in precios.items():
        add(f"x_{n}_ret", ret_pb(col(d, t)), f"Retorno log diario {t} (pb)", t)
    for n in ("cobre_lme", "dxy", "mxef"):
        t = precios[n]
        s = ffill(col(d, t))
        add(f"x_{n}_mom20", np.log(s / s.shift(20)) * 1e4, f"Retorno acumulado 20 días {t}", t)
    add("flag_ipsa_falta", col(d, "IPSA Index").isna().astype(int), "1 si el IPSA no tiene dato", "IPSA")
    ext = d["flag_ipsa_externo_raw"] if "flag_ipsa_externo_raw" in d else pd.Series(0, index=idx)
    add("flag_ipsa_externo", ext.fillna(0).astype(int), "1 si el IPSA viene del archivo externo", "IPSA externo")

    for n, t in {"vix": "VIX Index", "move": "MOVE Index", "vol_em": "JPMVXYEM Index"}.items():
        s = ffill(col(d, t))
        add(f"x_{n}", s, f"Nivel {t}", t)
        add(f"x_{n}_dif", s.diff(), f"Cambio diario {t}", t)

    def empalme(viejo, nuevo):
        dv, dn = col(d, viejo).diff(), col(d, nuevo).diff()
        return dv.where(idx < pd.Timestamp("2022-01-01"), dn)
    for n, (a, b) in {"pos_offshore": ("CLPBODM Index", "CLPBODMB Index"),
                      "pos_local": ("CLPBLDM Index", "CLPBLDMB Index")}.items():
        dd = empalme(a, b)
        add(f"x_{n}_dif", dd.shift(2), f"Cambio diario posición {n}, rezago 2 días", f"{a}, {b}", "2")
        add(f"x_{n}_dif20", dd.rolling(20, min_periods=15).sum().shift(2), f"Cambio 20 días posición {n}", f"{a}, {b}", "2")
    add("x_pos_spot_dif", col(d, "CLPBSMB Index").diff().shift(2), "Cambio posición spot banca, rezago 2 días", "CLPBSMB", "2")

    for n, t in {"imacec_mm": "CLIMMOMS Index", "imacec_aa": "CLIMYOYN Index",
                 "ipc_aa": "CLINNSYO Index", "desempleo": "CHUETOTL Index"}.items():
        p = macro_pit(raw, idx, t)
        add(f"x_{n}", p["valor"], f"Último {t} publicado", t, "FECHA_RELEASE")
        add(f"x_{n}_cambio", p["cambio"], f"Cambio del último {t} publicado", t, "FECHA_RELEASE")

    dic = pd.DataFrame(dic, columns=["variable", "descripcion", "fuente", "rezago_dias"])
    return m, dic


def guardar(m, dic, salida):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    for nombre, desde in CORTES.items():
        mm = m.loc[desde:]
        mm.index.name = "fecha"
        mm.to_csv(salida / f"modelo_usdclp_desde_{nombre}.csv", float_format="%.6g")
        with pd.ExcelWriter(salida / f"modelo_usdclp_desde_{nombre}.xlsx", engine="openpyxl") as xw:
            mm.reset_index().to_excel(xw, sheet_name="modelo", index=False)
            dic.to_excel(xw, sheet_name="diccionario_variables", index=False)
        print(nombre, mm.shape, mm.index.min().date(), mm.index.max().date())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ruta")
    ap.add_argument("salida")
    ap.add_argument("--ipsa", default=None)
    a = ap.parse_args()
    raw, d = cargar(a.ruta, a.ipsa)
    m, dic = construir(raw, d)
    guardar(m, dic, a.salida)
