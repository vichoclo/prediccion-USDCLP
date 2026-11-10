# -*- coding: utf-8 -*-
"""
verificar_senal.py — Comprueba que senal_del_dia.py entrega la misma señal que el
walk-forward del informe (modelo_adaptativo_colab.py), en todo un periodo o en días puntuales.

QUÉ COMPARA
  1. Probabilidades: senal_del_dia.py reentrena los bloques que cubren los últimos días del
     archivo de posiciones y compara día a día su p con la del walk-forward.
  2. Exposiciones: aplica el modelo 2 a las probabilidades del script y cuenta en cuántos
     días coincide la exposición con la del walk-forward.
  3. Días puntuales: para cada fecha pedida corre la señal completa del script como si
     esa fecha fuera el último día de la base (lo mismo que se hará en vivo).

CÓMO USARLO (en la misma carpeta que senal_del_dia.py)
  !python verificar_senal.py modelo_usdclp_desde_2001.xlsx posiciones_adaptativo.csv
  !python verificar_senal.py modelo_usdclp_desde_2001.xlsx posiciones_adaptativo.csv \\
        --fechas 2025-03-14,2026-06-15 --sistema adaptativo

  posiciones_adaptativo.csv es la salida de modelo_adaptativo_colab.py (celda 6). Trae el
  sistema adaptativo y la base; --sistema base verifica la base.
  Tarda unos 5 minutos en CPU, más ~3 minutos por fecha puntual.
"""
import argparse
import hashlib
import sys

import numpy as np
import pandas as pd

import senal_del_dia as S

ARCHIVO = "modelo_usdclp_desde_2001.xlsx"      # base tratada
ARCHIVO_POS = "posiciones_adaptativo.csv"      # salida de modelo_adaptativo_colab.py
FECHAS = None                                  # opcional: ["2025-03-14", "2026-06-15"]
SISTEMA = "adaptativo"
COLUMNA = {"adaptativo": "Adaptativo", "base": "Base (sistema final)"}
DIAS_A_COMPARAR = 300


def exposicion(p, vol_rel):                    # modelo 2 de modelo_adaptativo_colab.py
    p = p.dropna()
    p = p[vol_rel.reindex(p.index).notna()]
    pct = (p - 0.5).abs().rolling(S.VENTANA_PCT + 1, min_periods=120).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    vr = vol_rel.reindex(p.index)
    tam = pd.Series(np.where(pct >= S.U3, 3.0, np.where(pct >= S.U1, 1.0, 0.0)), index=p.index).where(pct.notna(), 0.0)
    tam = tam.where(~((tam == 3) & (vr > S.TOPE_VOL)), 1.0)
    return (np.sign(p - 0.5) * tam).where(pct.notna())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?", default=ARCHIVO)
    ap.add_argument("posiciones", nargs="?", default=ARCHIVO_POS)
    ap.add_argument("--sistema", default=SISTEMA, choices=list(COLUMNA))
    ap.add_argument("--fechas", default=",".join(FECHAS) if FECHAS else None, help="AAAA-MM-DD separadas por coma")
    a = ap.parse_args([] if "ipykernel" in sys.modules else None)   # en una celda se usan las constantes

    print(f"Base: {a.archivo} (md5 {hashlib.md5(open(a.archivo, 'rb').read()).hexdigest()[:10]})")
    print(f"Walk-forward: {a.posiciones} · sistema {a.sistema}\n")
    bt = pd.read_csv(a.posiciones, header=[0, 1], index_col=0, parse_dates=True)[COLUMNA[a.sistema]]
    fin = bt["p"].dropna().index.max()
    m = S.cargar(a.archivo).loc[:fin]
    print(f"El walk-forward llega hasta {fin.date()}.")

    # ---------------------------------------------------------------- 1. probabilidades
    print("\n1. Reentrenando con senal_del_dia.py...")
    P = S.probabilidades_recientes(m, dias_necesarios=DIAS_A_COMPARAR + S.VENTANA_PCT + 1, sistema=a.sistema)
    p_sc = P[["p_lstm", "p_logit"]].mean(axis=1, skipna=False).dropna()
    comun = p_sc.index.intersection(bt["p"].dropna().index)
    dif = (p_sc[comun] - bt.loc[comun, "p"]).abs()
    print(f"\n   {len(comun)} días comparados ({comun[0].date()} a {comun[-1].date()})")
    print(f"   diferencia máxima de p: {dif.max():.2e}")

    # ---------------------------------------------------------------- 2. exposiciones
    print("\n2. Exposiciones")
    sig = S.garch_walkforward(m["x_usdclp_ret"].fillna(0.0))
    vol_rel = sig / sig.rolling(S.VENTANA_PCT, min_periods=120).median().shift(1)
    e_sc = exposicion(p_sc, vol_rel).iloc[S.VENTANA_PCT:]       # solo días con 250 días previos completos
    e_bt = bt["exposicion"]
    dias = e_sc.dropna().index.intersection(e_bt.dropna().index)
    iguales = int((e_sc[dias] == e_bt[dias]).sum())
    print(f"   coinciden {iguales} de {len(dias)} días ({dias[0].date()} a {dias[-1].date()})")
    if iguales < len(dias):
        t = pd.DataFrame({"walk-forward": e_bt[dias], "script": e_sc[dias]})
        print(t[t["walk-forward"] != t.script].to_string())

    # ---------------------------------------------------------------- 3. días puntuales
    pruebas = [pd.Timestamp(f) for f in a.fechas.split(",")] if a.fechas else [dias[-1]]
    print("\n3. Señal completa del script en días puntuales (como si cada uno fuera el último día de la base)")
    ok_vivo = n_vivo = 0
    for f in pruebas:
        if f not in e_bt.dropna().index:
            print(f"   {f.date()}: sin señal en el walk-forward (no es día hábil de la base o está fuera del archivo); se omite")
            continue
        s = S.calcular_senal(S.cargar(a.archivo, hasta=f.strftime("%Y-%m-%d")), verbose=False, sistema=a.sistema)
        igual = s["exposicion"] == int(e_bt[f])
        ok_vivo, n_vivo = ok_vivo + igual, n_vivo + 1
        print(f"   {f.date()}: script {s['exposicion']:+d} (p = {s['p']:.4f}, percentil {s['percentil_confianza']:.2f}) · "
              f"walk-forward {int(e_bt[f]):+d} (p = {bt.loc[f, 'p']:.4f}) · {'OK' if igual else 'DISTINTA'}")

    todo_ok = dif.max() < 1e-3 and iguales == len(dias) and ok_vivo == n_vivo
    print("\n" + "=" * 70)
    print("RESULTADO:", "la señal del script es la misma del walk-forward" if todo_ok else
          "hay diferencias: revisar base, versiones de librerías o entorno (CPU/GPU)")
    print("=" * 70)


if __name__ == "__main__":
    main()
