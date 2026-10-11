"""Comprueba que la lectura de los PDF de la demo saca exactamente los datos correctos (verdad.json)."""
import json
from datetime import date
from pathlib import Path

from app import lectura

DEMO = Path(__file__).resolve().parent.parent / "datos_demo"
VERDAD = json.loads((DEMO / "verdad.json").read_text(encoding="utf-8"))


def test_facturas_pdf_se_leen_bien():
    fallos = []
    for v in VERDAD["facturas"]:
        if v["escaneada"]:
            continue
        d = lectura.leer_pdf((DEMO / v["archivo"]).read_bytes())
        esperado = {"numero": v["numero"], "fecha": date.fromisoformat(v["fecha"]), "base": v["base"], "iva": v["iva"], "total": v["total"],
                    "vencimiento": date.fromisoformat(v["vencimiento"])}
        for k, x in esperado.items():
            if d.get(k) != x:
                fallos.append((v["archivo"], k, d.get(k), x))
        if len(d["lineas"]) != len(v["lineas"]) or d["revisar"]:
            fallos.append((v["archivo"], "lineas/revisar", len(d["lineas"]), d["revisar"]))
    assert not fallos, fallos[:5]


def test_nominas_y_cierres_se_leen_bien():
    for v in VERDAD["nominas"]:
        d = lectura.leer_pdf((DEMO / v["archivo"]).read_bytes())
        assert (d["tipo"], d["mes"], d["bruto"], d["neto"], d["coste_empresa"]) == ("nomina", v["mes"], v["bruto"], v["neto"], v["coste_empresa"]), v["archivo"]
    for v in VERDAD["cierres"]:
        d = lectura.leer_pdf((DEMO / v["archivo"]).read_bytes())
        assert d["tipo"] == "cierre" and d["fecha"] == date.fromisoformat(v["fecha"]) and d["total"] == v["total"], v["archivo"]
        # El TPV corta los nombres a 24 letras, como muchas cajas reales: la app los casa con la carta por el principio.
        assert d["tarjeta"] == v["tarjeta"] and d["cubiertos"] == v["cubiertos"], v["archivo"]
        assert d["unidades"] == {k[:24].strip(): n for k, n in v["unidades"].items()}, v["archivo"]
        assert abs(sum(d["franjas"].values()) - v["total"]) < 0.05


def test_numeros_espanoles():
    assert lectura.numero_es("1.234,56") == 1234.56
    assert lectura.numero_es("8,8") == 8.8
    assert lectura.numero_es("") is None
