#!/usr/bin/env python3
"""
analisis_4dias.py — Comparativa de los 4 días NO continuos a partir de lo que
exporta IoT Central (Data Explorer > Export, o Data Export a Blob en JSON/CSV).

Calcula por (día, dispositivo, variable): máximo, mínimo, promedio, recuento y
sumatoria (solo donde tiene sentido físico), la hora del máximo y del mínimo, el
intervalo mediano entre muestras (evidencia de ASINCRONÍA) y los huecos mayores a
3× el intervalo mediano (evidencia de DESCONEXIÓN). Cruza cada máximo/mínimo con el
umbral de la Rule para redactar la lectura operativa.

Uso:
  python tools/analisis_4dias.py datos_4dias/*.csv  --dias 2026-10-01 2026-10-03 2026-10-06 2026-10-08
  (opcional) --col-tiempo "Timestamp" --col-dispositivo "Device ID"

Salidas en datos_4dias/resultados/:
  estadisticas.csv   — tabla completa (la inserta docs/build_pdf.py)
  huecos.csv         — desconexiones detectadas
  intervalos.csv     — intervalo mediano por dispositivo
  lectura.md         — lectura operativa automática (revísela y ajústela)
  grafico_<var>.png  — 4 días superpuestos por variable indispensable
Versión: 1.0.0
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "datos_4dias" / "resultados"
TZ = "America/Bogota"

# Variables donde la SUMATORIA tiene significado operativo
SUMMABLE = {"energyKwh": "kWh consumidos en el día", "accessGranted": "accesos concedidos",
            "accessDenied": "intentos rechazados", "leakDetected": "muestras con fuga",
            "smokeAlarm": "muestras en alarma", "overTemp": "muestras en sobretemperatura"}

# Umbrales (coinciden con las Rules R01–R14 del documento)
THRESH = {"tempIntake": (">", 27.0, "R01"), "tempExhaust": (">", 45.0, "tabla"),
          "humidity": (">", 60.0, "R03"), "diffPressure": ("<", 2.0, "R04"),
          "dewPoint": (">", 15.0, "R05"), "smokeObscuration": (">", 1.5, "R07"),
          "ceilingTemp": (">", 57.0, "R08"), "currentA": (">", 25.6, "R09"),
          "powerFactor": ("<", 0.9, "R10"), "doorOpenSeconds": (">", 120, "R11"),
          "pm25": (">", 35.4, "R13"), "aqi": (">", 100, "R13"), "tempOutdoor": (">", 30.0, "R14"),
          "floorHumidity": (">", 80.0, "tabla")}

KEY_VARS = ["tempIntake", "humidity", "diffPressure", "currentA", "tempOutdoor", "pm25"]

TIME_CANDIDATES = ["timestamp", "enqueuedtime", "time", "fecha", "datetime", "eventtime"]
DEV_CANDIDATES = ["deviceid", "device id", "device", "device name", "devicename", "dispositivo"]


def load(paths: list[str], col_t: str | None, col_d: str | None) -> pd.DataFrame:
    frames = []
    for p in paths:
        p = Path(p)
        if p.suffix.lower() in (".json", ".jsonl"):
            rows = []
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    j = json.loads(line)
                    flat = {"timestamp": j.get("enqueuedTime"), "deviceId": j.get("deviceId")}
                    flat.update(j.get("telemetry", {}))
                    rows.append(flat)
            df = pd.DataFrame(rows)
        else:
            df = pd.read_csv(p)
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    lower = {c.lower().strip(): c for c in df.columns}
    ct = col_t or next((lower[c] for c in TIME_CANDIDATES if c in lower), None)
    cd = col_d or next((lower[c] for c in DEV_CANDIDATES if c in lower), None)
    if not ct or not cd:
        sys.exit(f"No se identificaron columnas de tiempo/dispositivo en {list(df.columns)}; "
                 f"use --col-tiempo y --col-dispositivo")
    df = df.rename(columns={ct: "ts", cd: "device"})
    df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce").dt.tz_convert(TZ)
    df = df.dropna(subset=["ts"])
    long = df.melt(id_vars=["ts", "device"], var_name="variable", value_name="valor")
    long["valor"] = long["valor"].replace({True: 1, False: 0, "true": 1, "false": 0,
                                            "True": 1, "False": 0})
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    long = long.dropna(subset=["valor"])
    long["dia"] = long["ts"].dt.date.astype(str)
    return long


def stats(long: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dia, dev, var), g in long.groupby(["dia", "device", "variable"]):
        imax, imin = g["valor"].idxmax(), g["valor"].idxmin()
        rows.append({"dia": dia, "dispositivo": dev, "variable": var,
                     "max": round(g["valor"].max(), 3), "hora_max": g.loc[imax, "ts"].strftime("%H:%M"),
                     "min": round(g["valor"].min(), 3), "hora_min": g.loc[imin, "ts"].strftime("%H:%M"),
                     "promedio": round(g["valor"].mean(), 3), "recuento": int(g["valor"].count()),
                     "sumatoria": round(g["valor"].sum(), 3) if var in SUMMABLE else None})
    return pd.DataFrame(rows)


def gaps_and_intervals(long: pd.DataFrame):
    per_dev = long.drop_duplicates(["device", "ts"])[["device", "dia", "ts"]].sort_values(["device", "ts"])
    gaps, intervals = [], []
    for (dev, _dia), g in per_dev.groupby(["device", "dia"]):   # huecos DENTRO de cada día
        d = g["ts"].diff().dt.total_seconds().dropna()
        if d.empty:
            continue
        med = d.median()
        intervals.append({"dispositivo": dev, "dia": _dia, "intervalo_mediano_s": round(med, 1),
                          "muestras": len(g)})
        for idx in d[d > max(3 * med, 90)].index:
            end = g.loc[idx, "ts"]
            gaps.append({"dispositivo": dev, "desde": (end - pd.Timedelta(seconds=d[idx])).isoformat(),
                         "hasta": end.isoformat(), "duracion_min": round(d[idx] / 60, 1)})
    return pd.DataFrame(gaps), pd.DataFrame(intervals)


def reading(st: pd.DataFrame) -> str:
    lines = ["# Lectura operativa automática (revisar y completar)\n"]
    for var, (op, thr, rule) in THRESH.items():
        sub = st[st["variable"] == var]
        if sub.empty:
            continue
        top = sub.loc[sub["max"].idxmax()] if op == ">" else sub.loc[sub["min"].idxmin()]
        val = top["max"] if op == ">" else top["min"]
        hora = top["hora_max"] if op == ">" else top["hora_min"]
        crossed = (val > thr) if op == ">" else (val < thr)
        verdict = (f"SUPERA el umbral {op} {thr} ({rule}) -> la regla debió dispararse; "
                   f"verifique la alerta en la ventana") if crossed else \
                  f"se mantiene dentro del umbral {op} {thr} ({rule})"
        lines.append(f"- **{var}** · extremo {val} el {top['dia']} a las {hora} en "
                     f"{top['dispositivo']}: {verdict}.")
    for var, label in SUMMABLE.items():
        sub = st[st["variable"] == var]
        for _, r in sub.iterrows():
            lines.append(f"- **{var}** {r['dia']} ({r['dispositivo']}): sumatoria {r['sumatoria']} = {label}.")
    return "\n".join(lines) + "\n"


def charts(long: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for var in KEY_VARS:
        sub = long[long["variable"] == var]
        if sub.empty:
            continue
        fig, ax = plt.subplots(figsize=(8, 3.2), dpi=150)
        for (dia, dev), g in sub.groupby(["dia", "device"]):
            h = g["ts"].dt.hour + g["ts"].dt.minute / 60
            ax.plot(h, g["valor"], lw=1.1, label=f"{dia} · {dev}")
        if var in THRESH:
            ax.axhline(THRESH[var][1], color="#b3261e", ls="--", lw=1, label=f"umbral {THRESH[var][2]}")
        ax.set_xlim(0, 24); ax.set_xlabel("hora local (UTC−5)"); ax.set_title(var, loc="left")
        ax.grid(alpha=.25); ax.legend(fontsize=6, ncol=2, frameon=False)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        fig.tight_layout(); fig.savefig(OUT / f"grafico_{var}.png"); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("archivos", nargs="+")
    ap.add_argument("--dias", nargs="*", help="4 fechas YYYY-MM-DD no continuas")
    ap.add_argument("--col-tiempo"); ap.add_argument("--col-dispositivo")
    ap.add_argument("--salida", help="carpeta de salida (por defecto datos_4dias/resultados)")
    a = ap.parse_args()
    global OUT
    if a.salida:
        OUT = Path(a.salida)
    OUT.mkdir(parents=True, exist_ok=True)
    long = load(a.archivos, a.col_tiempo, a.col_dispositivo)
    if a.dias:
        long = long[long["dia"].isin(a.dias)]
        if len(a.dias) != 4:
            print("AVISO: el parcial exige 4 días no continuos")
    dias = sorted(long["dia"].unique())
    consecutivos = [d for d0, d in zip(dias, dias[1:])
                    if (pd.Timestamp(d) - pd.Timestamp(d0)).days == 1]
    if consecutivos:
        print(f"AVISO: hay días consecutivos {consecutivos}; elija fechas no continuas")
    st = stats(long)
    gaps, ints = gaps_and_intervals(long)
    st.to_csv(OUT / "estadisticas.csv", index=False)
    gaps.to_csv(OUT / "huecos.csv", index=False)
    ints.to_csv(OUT / "intervalos.csv", index=False)
    (OUT / "lectura.md").write_text(reading(st), encoding="utf-8")
    charts(long)
    print(f"Días: {dias}\nFilas estadísticas: {len(st)} · huecos: {len(gaps)}\nSalida: {OUT}")


if __name__ == "__main__":
    main()
