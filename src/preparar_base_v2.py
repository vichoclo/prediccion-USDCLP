"""
preparar_base_v2.py — Base USD/CLP desde 2001-08 para modelar (Torneo Itaú-FEN).
 
Uso:
    python preparar_base_v2.py "base_usdclp 2.xlsx" carpeta_salida/ [--ipsa ipsa.csv]
 
    --ipsa: CSV opcional con columnas `fecha,valor` (cierre diario del IPSA) para
            completar los días que faltan desde el 2026-08-31. Se empalma por
            razón en el traslape, así que sirve tanto el índice de precios como
            el de retorno total (mejor el de retorno total, que es el de la base).
 
Cambios respecto de preparar_base.py (v1, desde 2010):
 1. Inicio 2001-08-09: primer dato de la TPM nominal (CHOVCHOV). Antes la TPM se
    fijaba en UF y no hay carry nominal en la base. El peso flota desde sep-1999.
 2. Series cotizadas que vienen RANCIAS (repiten el valor del día anterior porque
    no hubo cotización nueva):
      a. Fecha de confiabilidad por serie (CONFIABLE_DESDE): antes de esa fecha la
         serie se deja vacía. Criterio: año desde el cual la tasa de repetición,
         en días con mercado de EE.UU. abierto, queda bajo ~10-15% y sin huecos
         largos.
      b. Después de esa fecha, el día con valor repetido se trata como "sin
         cotización nueva": el nivel se arrastra (máx. 10 días) y se agrega una
         columna `edad_*` con los días hábiles desde la última cotización fresca.
         El cambio diario de ese día queda en 0 y el día que vuelve a cotizar
         lleva el cambio acumulado (información conocida en t, sin fuga).
    Repeticiones legítimas NO se tocan: TPM, Fed funds, SOFR, UF, CNY (paridad
    fija hasta jul-2005), Tesoro 3M en tasa cero.
 3. IPSA: se puede completar con un archivo externo (--ipsa). Queda marcado con
    flag_ipsa_externo.
 4. Nuevas columnas de control: flag_vol20_contaminada (la ventana de 20 días
    incluye un spot rellenado) y `periodo` (tramo del protocolo de validación).
 5. Cortes de salida: 2001 (larga), 2010 y 2018.
 
Se mantienen las reglas de v1: x_* usa solo información al cierre de t; y_* mira
a t+1; la normalización se hace dentro del walk-forward.
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
 
# Tramos del protocolo (ver claude/base_2001.md en el proyecto)
PERIODOS = [
    ("calentamiento", "2001-08-09", "2001-11-30"),   # ventanas de 60 días
    ("entrenamiento_inicial", "2001-12-01", "2004-12-31"),
    ("desarrollo", "2005-01-01", "2021-12-31"),
    ("validacion", "2022-01-01", "2024-12-31"),
    ("test", "2025-01-01", "2099-12-31"),
]
 
# Desde cuándo se usa cada serie cotizada local (antes: vacía)
CONFIABLE_DESDE = {
    "USDCLPV1M Curncy": "2009-01-01",   # 30-60% repetido hasta 2007, 19-22% en 2008
    "USDCLPV3M Curncy": "2009-01-01",
    "CHNI1M Curncy": "2010-01-01",      # 17-35% repetido y 10-18% vacío 2003-2009
    "CHNI3M Curncy": "2010-01-01",
    "CHNI6M Curncy": "2010-01-01",
    "CHSWP1 Curncy": "2007-01-01",      # sin datos hasta 2003-04, 10-30% repetido 2004-06
    "CHSWP2 Curncy": "2007-01-01",
    "CHSWP5 Curncy": "2007-01-01",
    "CHSWP10 Curncy": "2007-01-01",
    "CHSWC2 Curncy": "2007-01-01",
}
# Series cotizadas en las que un valor repetido = no hubo cotización nueva
COTIZADAS = list(CONFIABLE_DESDE) + ["JPMVXYEM Index", "MOVE Index"]
 
FERIADOS = holidays.Chile(years=range(2000, 2028), categories=("public", "bank"))
 
 
def es_habil(d):
    return d.weekday() < 5 and d not in FERIADOS
 
 
def proximo_habil(d):
    d = d + pd.Timedelta(days=1)
    while not es_habil(d.date()):
        d += pd.Timedelta(days=1)
    return d
 
 
# ---------------------------------------------------------------- carga
def cargar(ruta, ipsa_ext=None):
    raw = pd.read_excel(ruta, sheet_name="datos")
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
    # razón mediana de los últimos 20 días comunes -> lleva el archivo a la escala de la base
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
 
 
# ---------------------------------------------------------------- series rancias
def depurar_cotizadas(d):
    """Aplica fecha de confiabilidad y marca repeticiones como 'sin cotización'.
    Devuelve d modificado y un DataFrame con la edad de la última cotización."""
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
        # días hábiles desde la última cotización fresca
        grupo = fresco.cumsum()
        edad = grupo.groupby(grupo).cumcount().astype(float)
        edad[grupo == 0] = np.nan
        edades[t] = edad
    return d, pd.DataFrame(edades, index=d.index)
 
 
# ---------------------------------------------------------------- helpers
def ffill(s):
    return s.ffill(limit=LIM_FFILL)
 
 
def ret_pb(s):
    """Retorno log en pb sobre serie rellenada (día sin dato => 0, y el
    movimiento completo aparece al reabrir)."""
    s = ffill(s)
    return np.log(s).diff() * 1e4
 
 
def dif_pb(s):
    return ffill(s).diff() * 100  # tasas en % -> pb
 
 
# ---------------------------------------------------------------- macro PIT
REZ_MAX = {}
# PARCHE auditoría 2026-10-26: rezagos FIJOS y documentados (antes: máximo observado en
# toda la muestra, un cálculo global que cambia si se trunca la base) y rezago mínimo
# plausible: una fecha de publicación más temprana que eso se considera error del
# archivo y se reemplaza por el rezago fijo.
REZ_FIJO = {"CLIMMOMS Index": 38, "CLIMYOYN Index": 50, "CLINNSYO Index": 8, "CHUETOTL Index": 34}
REZ_MIN = {"CLIMMOMS Index": 25, "CLIMYOYN Index": 25, "CLINNSYO Index": 5, "CHUETOTL Index": 25}
 
 
def macro_pit(raw, idx, ticker):
    v = col(raw, ticker).dropna()
    rel = pd.to_datetime(col(raw, ticker, "FECHA_RELEASE").reindex(v.index))
    rez = REZ_FIJO[ticker]
    REZ_MAX[ticker] = rez
    lag = (rel - v.index).dt.days
    rel = rel.where(lag >= REZ_MIN[ticker])                    # fechas implausibles → vacías
    rel = rel.fillna(pd.Series(v.index + pd.Timedelta(days=rez), index=v.index))
    t = pd.DataFrame({"release": rel.values, "ref": v.index, "valor": v.values,
                      "cambio": v.diff().values}).sort_values(["release", "ref"], kind="mergesort")
    out = pd.merge_asof(pd.DataFrame({"fecha": idx}), t, left_on="fecha",
                        right_on="release", direction="backward")
    return out.set_index("fecha")[["valor", "cambio"]]
 
 
# ---------------------------------------------------------------- principal
def construir(raw, d):
    d, edades = depurar_cotizadas(d)
    idx = d.index
    m = pd.DataFrame(index=idx)
    dic = []
 
    def add(nombre, serie, desc, fuente, rezago="0"):
        m[nombre] = serie
        dic.append((nombre, desc, fuente, rezago))
 
    # --- control
    per = pd.Series(index=idx, dtype=object)
    for n, a, b in PERIODOS:
        per[(idx >= a) & (idx <= b)] = n
    add("periodo", per, "Tramo del protocolo: calentamiento / entrenamiento_inicial / desarrollo / validacion / test", "protocolo")
 
    # --- calendario
    sig = pd.Series([proximo_habil(t) for t in idx], index=idx)
    dias = (sig - pd.Series(idx, index=idx)).dt.days
    add("cal_dia_semana", pd.Series(idx.dayofweek, index=idx), "0=lunes … 4=viernes", "calendario")
    add("cal_dias_corridos_sig", dias, "Días corridos hasta la próxima jornada hábil (3 un viernes normal)", "calendario")
 
    # --- spot y huecos
    spot = col(d, "USDCLP Curncy")
    obs_sig = col(d, "CLFXDOOB Index").shift(-1)  # observado de t+1 ≈ spot de t
    falta = spot.isna()
    # PARCHE auditoría 2026-10-26: el observado de t+1 se publica la mañana siguiente, así
    # que no se usa para las variables de t. El día sin spot el nivel se arrastra y el
    # movimiento aparece completo el día en que vuelve a haber dato.
    spot_rel = spot.ffill(limit=LIM_FFILL)
    relleno = (falta & spot_rel.notna()).astype(int)
    add("flag_usdclp_falta", falta.astype(int), "1 si Bloomberg no trae USDCLP ese día", "USDCLP")
    add("flag_usdclp_relleno", relleno,
        "1 si el spot usado en variables se arrastró del último día con dato", "USDCLP/CLFXDOOB")
    add("flag_vol20_contaminada", relleno.rolling(21, min_periods=1).max().astype(int),
        "1 si la ventana de 20 retornos incluye un spot rellenado", "USDCLP/CLFXDOOB")
    add("usdclp_cierre", spot, "Cierre USDCLP sin rellenar (referencia, no usar como variable)", "USDCLP")
 
    # --- tasas y carry
    tpm = ffill(col(d, "CHOVCHOV Index"))
    iusd = col(d, "SOFRRATE Index").combine_first(col(d, "FEDL01 Index"))
    iusd = ffill(iusd)
    carry = (tpm - iusd) / 100 * dias / 360 * 1e4  # pb que paga un largo USD
    add("carry_pb", carry, "Carry de t a t+1 en pb: (TPM − SOFR/FedFunds) × días/360. Largo paga, corto recibe", "CHOVCHOV, SOFRRATE, FEDL01", "objetivo")
 
    # --- objetivos
    y = np.log(spot.shift(-1) / spot) * 1e4  # NaN si falta t o t+1
    add("y_ret_pb", y, "Retorno log USDCLP de t a t+1, en pb", "USDCLP", "futuro")
    add("y_ret_neto_pb", y - carry, "Retorno t→t+1 menos carry (lo que gana un largo de 1x antes de costos)", "USDCLP + carry", "futuro")
    add("y_sube", (y > 0).astype(float).where(y.notna()), "1 si el dólar sube de t a t+1", "USDCLP", "futuro")
    add("y_sube_neto", (y - carry > 0).astype(float).where(y.notna() & carry.notna()), "1 si conviene estar comprado (sube más que el carry); 0 si conviene corto", "USDCLP + carry", "futuro")
 
    # --- USDCLP: retornos, momentum, volatilidad, rango
    r = np.log(spot_rel).diff() * 1e4
    add("x_usdclp_ret", r, "Retorno log USDCLP t-1→t (pb)", "USDCLP")
    for k in range(1, 5):
        add(f"x_usdclp_ret_l{k}", r.shift(k), f"Retorno USDCLP rezagado {k} días", "USDCLP")
    for w in (5, 20, 60):
        add(f"x_usdclp_mom{w}", np.log(spot_rel / spot_rel.shift(w)) * 1e4, f"Retorno acumulado {w} días (pb)", "USDCLP")
    for w in (5, 20, 60):
        add(f"x_usdclp_vol{w}", r.rolling(w, min_periods=int(w * .8)).std() * np.sqrt(252) / 100,
            f"Volatilidad realizada {w} días, % anual", "USDCLP")
    o, h, l = (col(d, "USDCLP Curncy", c) for c in ("PX_OPEN", "PX_HIGH", "PX_LOW"))
    add("x_usdclp_rango", (h - l) / spot * 1e4, "Rango alto-bajo del día / cierre (pb)", "USDCLP OHLC")
    add("x_usdclp_cuerpo", np.log(spot / o) * 1e4, "Cierre vs apertura (pb)", "USDCLP OHLC")
    v1m = ffill(col(d, "USDCLPV1M Curncy"))
    add("x_vol_impl_1m", v1m, "Vol implícita USDCLP 1M (% anual). Desde 2009", "USDCLPV1M")
    add("x_vol_impl_1m_dif", v1m.diff(), "Cambio diario vol implícita 1M", "USDCLPV1M")
    add("x_vol_impl_3m", ffill(col(d, "USDCLPV3M Curncy")), "Vol implícita USDCLP 3M (% anual). Desde 2009", "USDCLPV3M")
    add("x_vol_prima", v1m - m["x_usdclp_vol20"], "Vol implícita 1M − realizada 20d", "USDCLPV1M, USDCLP")
 
    # --- carry / tasas locales
    add("x_dif_tasas", tpm - iusd.shift(1), "TPM − tasa USD (USD rezagada 1 día por publicación), % anual", "CHOVCHOV, SOFR/FEDL01", "USD: 1")
    add("x_tpm_dif", tpm.diff() * 100, "Cambio diario TPM (pb)", "CHOVCHOV")
    dias_atras = pd.Series(idx, index=idx).diff().dt.days
    cam = (col(d, "CLICP Index") / col(d, "CLICP Index").shift(1) - 1) * 360 / dias_atras * 100
    add("x_camara", cam, "Tasa de cámara implícita en CLICP, % anual. Desde 2002-11", "CLICP")
    add("x_camara_menos_tpm", cam - tpm, "Cámara − TPM (tensión de liquidez, en %)", "CLICP, CHOVCHOV")
    camr = (col(d, "CLICREAL Index") / col(d, "CLICREAL Index").shift(1) - 1) * 360 / dias_atras * 100
    add("x_camara_real", camr, "Tasa de cámara real (UF), % anual. Desde 2006-11", "CLICREAL")
    for t in ("CHNI1M", "CHNI3M", "CHNI6M"):
        s = ffill(col(d, f"{t} Curncy"))
        add(f"x_{t.lower()}", s, f"Rendimiento implícito NDF {t[4:]} (% anual). Desde 2010", t)
        add(f"x_{t.lower()}_dif", s.diff() * 100, f"Cambio diario {t} (pb)", t)
    add("x_basis_ndf1m", ffill(col(d, "CHNI1M Curncy")) - tpm, "Tasa implícita NDF 1M − TPM (basis offshore/onshore). Desde 2010", "CHNI1M, CHOVCHOV")
    for t in ("CHSWP1", "CHSWP2", "CHSWP5", "CHSWP10", "CHSWC2"):
        add(f"x_{t.lower()}_dif", dif_pb(col(d, f"{t} Curncy")), f"Cambio diario swap {t} (pb). Desde 2007", t)
    add("x_pendiente_swp", ffill(col(d, "CHSWP10 Curncy")) - ffill(col(d, "CHSWP1 Curncy")), "Swap 10a − 1a (% anual)", "CHSWP10, CHSWP1")
    add("x_infl_impl_2a", ffill(col(d, "CHSWP2 Curncy")) - ffill(col(d, "CHSWC2 Curncy")), "Swap CLP 2a − swap UF 2a (inflación implícita)", "CHSWP2, CHSWC2")
    add("x_uf_ret", ret_pb(col(d, "CHUF Index")), "Variación diaria UF (pb; se conoce por anticipado)", "CHUF")
 
    # --- edad de la última cotización fresca (series rancias)
    for t in ("USDCLPV1M Curncy", "CHNI1M Curncy", "CHNI3M Curncy", "CHSWP2 Curncy", "CHSWP5 Curncy"):
        n = t.split()[0].lower()
        add(f"edad_{n}", edades[t], f"Días hábiles desde la última cotización nueva de {t} (0 = cotizó hoy)", t)
 
    # --- tasas EE.UU.
    add("x_tasa_usd_dif", (iusd.diff() * 100).shift(1), "Cambio SOFR/FedFunds (pb), rezagado 1 día", "SOFRRATE, FEDL01", "1")
    for t in ("USGG3M", "USGG2YR", "USGG10YR"):
        add(f"x_{t.lower()}_dif", dif_pb(col(d, f"{t} Index")), f"Cambio diario Tesoro {t} (pb)", t)
    add("x_dif_2a_cl_us", ffill(col(d, "CHSWP2 Curncy")) - ffill(col(d, "USGG2YR Index")), "Swap CLP 2a − Tesoro 2a", "CHSWP2, USGG2YR")
 
    # --- precios: retornos log (pb)
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
        add(f"x_{n}_mom20", np.log(s / s.shift(20)) * 1e4, f"Retorno acumulado 20 días {t} (pb)", t)
    add("flag_ipsa_falta", col(d, "IPSA Index").isna().astype(int), "1 si el IPSA no tiene dato ese día", "IPSA")
    ext = d["flag_ipsa_externo_raw"] if "flag_ipsa_externo_raw" in d else pd.Series(0, index=idx)
    add("flag_ipsa_externo", ext.fillna(0).astype(int), "1 si el IPSA de ese día viene del archivo externo (después del 2026-08-31)", "IPSA externo")
 
    # --- riesgo / volatilidad global
    for n, t in {"vix": "VIX Index", "move": "MOVE Index", "vol_em": "JPMVXYEM Index"}.items():
        s = ffill(col(d, t))
        add(f"x_{n}", s, f"Nivel {t}", t)
        add(f"x_{n}_dif", s.diff(), f"Cambio diario {t}", t)
 
    # --- flujos: empalme en diferencias + rezago 2 días
    def empalme(viejo, nuevo):
        dv, dn = col(d, viejo).diff(), col(d, nuevo).diff()
        corte = pd.Timestamp("2022-01-01")
        return dv.where(idx < corte, dn)
    flujos = {"pos_offshore": ("CLPBODM Index", "CLPBODMB Index"),
              "pos_local": ("CLPBLDM Index", "CLPBLDMB Index")}
    for n, (a, b) in flujos.items():
        dd = empalme(a, b)
        add(f"x_{n}_dif", dd.shift(2), f"Cambio diario posición derivados banca ({n}), MM USD, empalme {a}→{b}, rezago 2 días. Desde 2008-10", f"{a}, {b}", "2")
        add(f"x_{n}_dif20", dd.rolling(20, min_periods=15).sum().shift(2), f"Cambio 20 días posición {n}, rezago 2 días", f"{a}, {b}", "2")
    add("x_pos_spot_dif", col(d, "CLPBSMB Index").diff().shift(2), "Cambio diario posición spot banca (MM USD), rezago 2 días; desde 2022", "CLPBSMB", "2")
 
    # --- macro point-in-time
    for n, t in {"imacec_mm": "CLIMMOMS Index", "imacec_aa": "CLIMYOYN Index",
                 "ipc_aa": "CLINNSYO Index", "desempleo": "CHUETOTL Index"}.items():
        p = macro_pit(raw, idx, t)
        add(f"x_{n}", p["valor"], f"Último {t} publicado a la fecha (point-in-time)", t, "FECHA_RELEASE")
        add(f"x_{n}_cambio", p["cambio"], f"Cambio del último {t} publicado vs el mes anterior", t, "FECHA_RELEASE")
 
    dic = pd.DataFrame(dic, columns=["variable", "descripcion", "fuente", "rezago_dias"])
    dic["primer_dato"] = [m[c].first_valid_index().date() if m[c].notna().any() else None for c in dic.variable]
    for n, a, b in PERIODOS[1:]:
        dic[f"pct_{n}"] = [round(m.loc[a:b, c].notna().mean() * 100, 1) for c in dic.variable]
    return m, dic
 
 
def guardar(m, dic, salida):
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    fer = pd.DataFrame([(pd.Timestamp(k), v) for k, v in sorted(FERIADOS.items())
                        if 2001 <= k.year <= 2026], columns=["fecha", "feriado"])
    per = pd.DataFrame(PERIODOS, columns=["periodo", "desde", "hasta"])
    conf = pd.DataFrame(sorted(CONFIABLE_DESDE.items()), columns=["serie", "se_usa_desde"])
    for nombre, desde in CORTES.items():
        mm = m.loc[desde:]
        mm.to_csv(salida / f"modelo_usdclp_desde_{nombre}.csv", float_format="%.6g")
        with pd.ExcelWriter(salida / f"modelo_usdclp_desde_{nombre}.xlsx", engine="openpyxl") as xw:
            mm.reset_index().to_excel(xw, sheet_name="modelo", index=False)
            dic.to_excel(xw, sheet_name="diccionario_variables", index=False)
            per.to_excel(xw, sheet_name="periodos", index=False)
            conf.to_excel(xw, sheet_name="series_rancias", index=False)
            fer.to_excel(xw, sheet_name="feriados_cl", index=False)
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
    print("rezago máximo macro usado cuando falta FECHA_RELEASE:", REZ_MAX)
