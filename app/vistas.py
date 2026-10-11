"""Datos que necesita cada pantalla, ya calculados. Respeta los perfiles con perfiles.puede_ver."""
from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import perfiles
from .db import Aviso, Correo, Documento, Empleado, LineaDocumento, Producto, Proveedor

ETIQUETAS_CORREO = {"factura": ("Factura", "c-fact"), "reserva": ("Reserva", "c-res"), "consulta": ("Consulta", "c-con"), "queja": ("Queja", "c-queja"),
                    "nomina": ("Nóminas", "c-nom"), "gasto": ("Gasto", "c-gasto"), "publicidad": ("Publicidad", "c-pub"), "cierre": ("Cierre de caja", "c-con"),
                    "etiqueta": ("Etiqueta", "c-est"), "raro": ("Raro: no sé clasificarlo", "c-rev"), "otro": ("Otro", "c-est"), "leyendo": ("Leyendo…", "c-est"),
                    "sin_clasificar": ("Sin clasificar", "c-est")}
COLORES = ["#2d6a4f", "#2c4f9e", "#c0392b", "#9a6200", "#7a3fa0", "#1d6f7d", "#6b6b66"]


def eur(x, dec=2):
    if x is None:
        return "—"
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if x < 0 else "") + s


def bandeja(s: Session, categoria: str | None, correo_id: int | None, perfil: str = perfiles.DUENO) -> dict:
    cuenta = dict(s.execute(select(Correo.categoria, func.count()).group_by(Correo.categoria)).all())
    q = select(Correo).order_by(Correo.recibido.desc())
    if categoria:
        q = q.where(Correo.categoria == categoria)
    correos = list(s.scalars(q.limit(60)))
    sel = s.get(Correo, correo_id) if correo_id else next((c for c in correos if c.categoria == "reserva" and not c.respuesta_enviada), correos[0] if correos else None)
    docs = [documento_json(d, perfil) for d in s.scalars(select(Documento).where(Documento.correo_id == sel.id))] if sel else []
    filas = []
    for c in correos:
        et, cls = ETIQUETAS_CORREO.get(c.categoria, (c.categoria, "c-est"))
        iniciales = "".join(w[0] for w in c.remitente.split()[:2]).upper() or "?"
        filas.append({"c": c, "etiqueta": et, "clase": cls, "iniciales": iniciales, "color": COLORES[sum(map(ord, c.remitente)) % len(COLORES)]})
    return {"cuenta": cuenta, "total": sum(cuenta.values()), "filas": filas, "sel": sel, "docs_sel": docs, "categoria": categoria,
            "etiquetas": ETIQUETAS_CORREO}


def documento_json(d: Documento, perfil: str) -> dict:
    ver_precios = perfiles.puede_ver(perfil, "precios_compra")
    out = {"id": d.id, "tipo": d.tipo, "fecha": d.fecha.isoformat() if d.fecha else None, "numero": d.numero, "estado": d.estado,
           "motivo": d.motivo_revisar, "archivo": d.archivo.rsplit("/", 1)[-1] if d.archivo else "", "correo_id": d.correo_id,
           "pagado": d.pagado_fecha.isoformat() if d.pagado_fecha else None, "vence": d.vencimiento.isoformat() if d.vencimiento else None,
           "proveedor": d.proveedor.nombre if d.proveedor else None, "grupo": d.proveedor.grupo if d.proveedor else None,
           "categoria": d.categoria_gasto, "datos": {k: v for k, v in (d.datos or {}).items() if k in ("comercio", "bruto", "neto", "mes")}}
    if d.tipo == "nomina" and not perfiles.puede_ver(perfil, "salarios_por_persona"):
        out["datos"] = {"mes": (d.datos or {}).get("mes")}
        return out
    if ver_precios or d.tipo != "factura":
        out.update({"base": d.base, "iva": d.iva, "total": d.total})
    return out


def documentos(s: Session, perfil: str, desde: date | None, hasta: date | None) -> dict:
    q = select(Documento).where(Documento.tipo.in_(["factura", "gasto", "nomina", "cierre", "otro"]))
    if desde:
        q = q.where(Documento.fecha >= desde)
    if hasta:
        q = q.where(Documento.fecha <= hasta)
    if not perfiles.puede_ver(perfil, "nominas"):
        q = q.where(Documento.tipo != "nomina")
    docs = list(s.scalars(q.order_by(Documento.fecha.desc())))
    empleados = {e.id: e.nombre for e in s.scalars(select(Empleado))}
    lista = []
    for d in docs:
        j = documento_json(d, perfil)
        if d.tipo == "nomina":
            j["empleado"] = empleados.get(d.empleado_id, "")
        lista.append(j)
    # días con documentos para el calendario (todo el histórico)
    dias = defaultdict(int)
    for f, n in s.execute(select(Documento.fecha, func.count()).where(Documento.fecha.is_not(None)).group_by(Documento.fecha)):
        dias[f.isoformat()] = n
    return {"documentos": lista, "dias": dias, "leyendo": s.scalar(select(func.count(Documento.id)).where(Documento.estado == "leyendo"))}


def lineas_factura(s: Session, doc_id: int, perfil: str) -> dict:
    d = s.get(Documento, doc_id)
    if not d:
        return {}
    precios = perfiles.puede_ver(perfil, "precios_compra")
    lineas = []
    for l in s.scalars(select(LineaDocumento).where(LineaDocumento.documento_id == doc_id)):
        p = s.get(Producto, l.producto_id) if l.producto_id else None
        lineas.append({"descripcion": l.descripcion, "cantidad": l.cantidad, "unidad": l.unidad,
                       "precio": l.precio_unitario if precios else None, "mercabarna": p.codigo_mercabarna if p else "",
                       "producto": p.nombre if p else None})
    prov = d.proveedor
    return {"id": d.id, "titulo": f"{prov.nombre if prov else ''} · {d.numero or 'sin número'}", "lineas": lineas,
            "entregas_mes": prov.entregas_al_mes if prov else 0}


def avisos(s: Session, hoy: date, limite=10) -> list:
    return list(s.scalars(select(Aviso).where(Aviso.fecha <= hoy).order_by(Aviso.fecha.desc(), Aviso.id.desc()).limit(limite)))
