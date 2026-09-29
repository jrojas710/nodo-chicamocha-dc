#!/usr/bin/env python3
"""gen_dtdl.py — genera las 8 plantillas DTDL v2 a partir de docs/catalogo.py.
Importe cada JSON en IoT Central: Device templates > + New > IoT device > Import a model."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "docs"))
from catalogo import COMMON_PROPS, TEMPLATES  # noqa: E402


def content(name, kind, schema, sem, desc):
    base = {"name": name, "displayName": {"es": desc}}
    if kind == "T":
        t = ["Telemetry"] + ([sem[0]] if sem else [])
        base.update({"@type": t if len(t) > 1 else "Telemetry", "schema": schema})
        if sem:
            base["unit"] = sem[1]
    elif kind in ("P", "W"):
        t = ["Property"] + ([sem[0]] if sem else [])
        base.update({"@type": t if len(t) > 1 else "Property", "schema": schema,
                     "writable": kind == "W"})
        if sem:
            base["unit"] = sem[1]
    elif kind == "C":
        base["@type"] = "Command"
        if schema:
            base["request"] = {"name": "value", "schema": schema,
                               "displayName": {"es": "Parámetro"}}
    return base


for key, tpl in TEMPLATES.items():
    names = {i[0] for i in tpl["items"]}
    items = list(tpl["items"]) + [p for p in COMMON_PROPS if p[0] not in names]
    model = {
        "@context": "dtmi:dtdl:context;2",
        "@id": tpl["model"],
        "@type": "Interface",
        "displayName": {"es": tpl["display"]},
        "description": {"es": "Nodo Chicamocha DC · Parcial 1 IoT Central · UNAB 2026-II"},
        "contents": [content(*i) for i in items],
    }
    out = HERE / f"{key}.json"
    out.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    print("escrito", out.name, len(model["contents"]), "elementos")
