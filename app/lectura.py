"""Leer documentos: PDF con texto (sin IA) y fotos (con IA).

Regla de oro: lo que no está claro se marca "revisar" y se deja vacío; nunca se inventa.
Cada lectura devuelve un dict con "tipo", los datos y "revisar" (lista de motivos).
"""
import io
import re
from datetime import date

from pypdf import PdfReader

from . import cache_ia, ia

FECHA = r"(\d{2})/(\d{2})/(\d{4})"
IMPORTE = r"(-?[\d.]+,\d{2})"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def numero_es(s: str | None) -> float | None:
    """'1.234,56' -> 1234.56 ; '8,8' -> 8.8"""
    if s is None:
        return None
    s = s.strip().replace("€", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def fecha_es(s: str | None) -> date | None:
    if not s:
        return None
    m = re.search(FECHA, s)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def texto_pdf(contenido: bytes) -> str:
    try:
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(contenido)).pages)
    except Exception:
        return ""


def leer_pdf(contenido: bytes) -> dict:
    t = texto_pdf(contenido)
    if len(t.strip()) < 30:
        return {"tipo": "sin_texto", "revisar": ["el PDF no tiene texto: hay que leerlo como imagen"]}
    if "INFORME Z" in t or "CIERRE DE CAJA" in t:
        return leer_cierre(t)
    if "RECIBO INDIVIDUAL DE SALARIOS" in t or "LÍQUIDO A PERCIBIR" in t:
        return leer_nomina(t)
    if re.search(r"\bFACTURA\b|Factura", t):
        return leer_factura(t)
    return {"tipo": "otro", "texto": t[:2000], "revisar": []}


def _busca(patron, t, grupo=1):
    m = re.search(patron, t, re.I | re.M)
    return m.group(grupo).strip() if m else None


def leer_factura(t: str) -> dict:
    revisar = []
    lineas_txt = [l for l in t.splitlines() if l.strip()]
    proveedor = lineas_txt[0].strip() if lineas_txt else None
    cif = _busca(r"^CIF:\s*([A-Z0-9-]+|\(ejemplo\))", t)
    tel = _busca(r"Tel\.\s*([\d ]{9,15})", t)
    numero = _busca(r"(?:Nº factura|Número|Factura nº)\s*:\s*(\S+)", t)
    fecha = fecha_es(_busca(r"Fecha(?: de emisión)?\s*:\s*(\d{2}/\d{2}/\d{4})", t))
    venc_txt = _busca(r"(?:Fecha de vencimiento|Vencimiento|Pago)\s*:\s*(\d{2}/\d{2}/\d{4}|al contado)", t)
    vencimiento = fecha if venc_txt == "al contado" else fecha_es(venc_txt)
    bases = [numero_es(x) for x in re.findall(r"Base imponible [\d]+ %\s+" + IMPORTE, t)]
    ivas = [numero_es(x) for x in re.findall(r"^(?:IVA [\d]+ %|Exento de IVA)\s+" + IMPORTE, t, re.M)]
    total = numero_es(_busca(r"^TOTAL\s+" + IMPORTE, t))
    base = round(sum(bases), 2) if bases else None
    iva = round(sum(ivas), 2) if ivas else None
    lineas = []
    for m in re.finditer(r"^(.+?) ([\d.,]+) (\S+) " + IMPORTE + r" € (\d+) % " + IMPORTE + " €$", t, re.M):
        lineas.append({"descripcion": m.group(1).strip(), "cantidad": numero_es(m.group(2)), "unidad": m.group(3),
                       "precio_unitario": numero_es(m.group(4)), "iva": int(m.group(5)) / 100, "importe": numero_es(m.group(6))})
    for campo, valor in (("número", numero), ("fecha", fecha), ("base", base), ("IVA", iva), ("total", total)):
        if valor is None:
            revisar.append(f"no se lee {campo}")
    if base is not None and iva is not None and total is not None and abs(base + iva - total) > 0.02:
        revisar.append("base + IVA no da el total")
    if lineas and base is not None and abs(sum(l["importe"] for l in lineas) - base) > 0.05:
        revisar.append("las líneas no suman la base")
    return {"tipo": "factura", "proveedor": proveedor, "cif": cif, "telefono": tel, "numero": numero, "fecha": fecha, "vencimiento": vencimiento,
            "base": base, "iva": iva, "total": total, "lineas": lineas, "revisar": revisar}


def leer_nomina(t: str) -> dict:
    revisar = []
    empleado = _busca(r"Trabajador/a:\s*(.+)", t)
    periodo = _busca(r"Periodo de liquidación:\s*(\w+) de (\d{4})", t)
    m = re.search(r"Periodo de liquidación:\s*(\w+) de (\d{4})", t)
    mes = MESES.index(m.group(1).lower()) + 1 if m and m.group(1).lower() in MESES else None
    anio = int(m.group(2)) if m else None
    bruto = numero_es(_busca(r"TOTAL DEVENGADO.*?" + IMPORTE, t))
    neto = numero_es(_busca(r"LÍQUIDO A PERCIBIR\s+" + IMPORTE, t))
    coste = numero_es(_busca(r"Coste total para la empresa\s+" + IMPORTE, t))
    for campo, valor in (("empleado", empleado), ("mes", mes), ("total", coste or neto)):
        if not valor:
            revisar.append(f"no se lee {campo}")
    return {"tipo": "nomina", "empleado": empleado, "mes": mes, "anio": anio, "periodo": periodo, "bruto": bruto, "neto": neto,
            "coste_empresa": coste, "total": coste, "revisar": revisar}


def leer_cierre(t: str) -> dict:
    revisar = []
    fecha = fecha_es(t)
    ventas = numero_es(_busca(r"VENTAS TOTALES\s+" + IMPORTE, t))
    tarjeta = numero_es(_busca(r"^\s*Tarjeta\s+" + IMPORTE, t))
    efectivo = numero_es(_busca(r"^\s*Efectivo\s+" + IMPORTE, t))
    cub = _busca(r"Cubiertos\s+(\d+)", t)
    franjas = {m.group(1): numero_es(m.group(2)) for m in re.finditer(r"^\s+(\d{1,2}-\d{1,2})\s+" + IMPORTE, t, re.M)}
    bloque = t.split("UNIDADES POR ARTÍCULO")[-1] if "UNIDADES POR ARTÍCULO" in t else ""
    unidades = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"^\s+(.+?)\s+(\d+)\s*$", bloque, re.M)}
    if None in (fecha, ventas, tarjeta, efectivo):
        revisar.append("faltan datos del cierre")
    elif abs(tarjeta + efectivo - ventas) > 0.02:
        revisar.append("tarjeta + efectivo no da las ventas")
    return {"tipo": "cierre", "fecha": fecha, "total": ventas, "tarjeta": tarjeta, "efectivo": efectivo, "cubiertos": int(cub) if cub else 0,
            "franjas": franjas, "unidades": unidades, "revisar": revisar}


# ---------------------------------------------------------------- fotos (IA)
ESQUEMA_FOTO = {
    "type": "OBJECT",
    "properties": {
        "tipo": {"type": "STRING", "enum": ["factura", "albaran", "ticket", "etiqueta", "otro"]},
        "comercio_o_proveedor": {"type": "STRING", "nullable": True},
        "numero": {"type": "STRING", "nullable": True, "description": "Número de factura o ticket tal cual. null si no se lee bien."},
        "fecha": {"type": "STRING", "nullable": True, "description": "Fecha del documento en formato AAAA-MM-DD"},
        "base": {"type": "NUMBER", "nullable": True},
        "iva": {"type": "NUMBER", "nullable": True},
        "total": {"type": "NUMBER", "nullable": True},
        "lineas": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "descripcion": {"type": "STRING"}, "cantidad": {"type": "NUMBER", "nullable": True}, "unidad": {"type": "STRING", "nullable": True},
            "precio_unitario": {"type": "NUMBER", "nullable": True}, "importe": {"type": "NUMBER", "nullable": True}}}},
        "producto": {"type": "STRING", "nullable": True, "description": "Solo etiquetas: nombre del producto"},
        "peso_kg": {"type": "NUMBER", "nullable": True},
        "lote": {"type": "STRING", "nullable": True},
        "caducidad": {"type": "STRING", "nullable": True, "description": "Solo etiquetas: fecha de caducidad AAAA-MM-DD"},
        "dudas": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Qué no se lee bien"},
    },
    "required": ["tipo", "lineas", "dudas"],
}

INSTRUCCIONES_FOTO = """Eres el lector de documentos de la oficina de un restaurante en España. Mira la foto y devuelve los datos en JSON.
- "tipo": factura (de un proveedor, con base, IVA y total), albaran (nota de entrega del repartidor: líneas con cantidades, normalmente sin IVA ni total; pone "albarán" o "nota de entrega"), ticket (de un gasto en una tienda), etiqueta (de un producto fresco con caducidad) u otro.
- En albaranes: proveedor, fecha, número del albarán y cada línea con cantidad y unidad (el precio si aparece).
- Copia los datos exactamente como aparecen. Importes en euros como número (1234.56). Fechas como AAAA-MM-DD.
- Si un dato no se lee con seguridad (borroso, tapado, ilegible), pon null y explica en "dudas". NUNCA inventes ni deduzcas un dato que no se ve.
- En facturas: base imponible, IVA y total; y cada línea de producto con cantidad, unidad, precio unitario e importe.
- En tickets: comercio, fecha, número de ticket, total y líneas.
- En etiquetas: producto, proveedor si aparece, peso en kg, lote y fecha de caducidad."""


def leer_foto(contenido: bytes, mime: str = "image/jpeg") -> dict:
    clave = "foto:" + cache_ia.huella(contenido)
    d = cache_ia.buscar(clave)
    if d is None:
        d = ia.leer_imagen(contenido, mime, INSTRUCCIONES_FOTO, ESQUEMA_FOTO)
        cache_ia.guardar(clave, d)
    revisar = list(d.get("dudas") or [])
    def f(x):
        try:
            return date.fromisoformat(x) if x else None
        except ValueError:
            return None
    out = {"tipo": {"ticket": "gasto"}.get(d["tipo"], d["tipo"]), "proveedor": d.get("comercio_o_proveedor"), "numero": d.get("numero"),
           "fecha": f(d.get("fecha")), "base": d.get("base"), "iva": d.get("iva"), "total": d.get("total"),
           "lineas": [{"descripcion": l.get("descripcion", ""), "cantidad": l.get("cantidad"), "unidad": l.get("unidad") or "",
                       "precio_unitario": l.get("precio_unitario"), "importe": l.get("importe"), "iva": None} for l in d.get("lineas") or []],
           "producto": d.get("producto"), "peso": d.get("peso_kg"), "lote": d.get("lote"), "caducidad": f(d.get("caducidad")), "revisar": revisar}
    if out["tipo"] == "factura":
        for campo in ("numero", "fecha", "total"):
            if out[campo] in (None, ""):
                revisar.append(f"no se lee {campo}")
        if out["base"] is not None and out["iva"] is not None and out["total"] is not None and abs(out["base"] + out["iva"] - out["total"]) > 0.02:
            revisar.append("base + IVA no da el total")
    if out["tipo"] == "gasto" and out["total"] is None:
        revisar.append("no se lee el total")
    if out["tipo"] == "etiqueta" and out["caducidad"] is None:
        revisar.append("no se lee la caducidad: repite la foto o escríbela")
    return out
