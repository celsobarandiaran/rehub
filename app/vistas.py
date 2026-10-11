"""Datos que necesita cada pantalla, ya calculados. Respeta los perfiles con perfiles.puede_ver."""
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import calculos, perfiles
from .db import Aviso, Cierre, Competidor, Correo, Documento, Empleado, Entrada, LineaDocumento, Producto, Proveedor, Recuento

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


MERCABARNA = json.loads((Path(__file__).resolve().parent / "static" / "mercabarna.json").read_text(encoding="utf-8"))


def cuadro_del_dia(s: Session, hoy: date, fecha: str | None) -> dict:
    q = select(Cierre).order_by(Cierre.fecha.desc())
    if fecha:
        try:
            f = date.fromisoformat(fecha)
            q = select(Cierre).where(Cierre.fecha <= f).order_by(Cierre.fecha.desc())
        except ValueError:
            pass
    else:
        q = select(Cierre).where(Cierre.fecha < hoy).order_by(Cierre.fecha.desc())
    cierre = s.scalars(q).first()
    if not cierre:
        return {"cierre": None}
    gastos = list(s.scalars(select(Documento).where(Documento.tipo == "gasto", Documento.fecha == cierre.fecha)))
    gastos_total = sum(g.total or 0 for g in gastos)
    fondo = calculos.ajuste(s, "fondo_caja", 150.0)
    esperada = round(fondo + cierre.efectivo - gastos_total, 2)
    descuadre = round(cierre.efectivo_contado - esperada, 2) if cierre.efectivo_contado is not None else None
    meses = []
    ventas = calculos.ventas_por_mes(s)
    desc_mes = defaultdict(float)
    for c in s.scalars(select(Cierre)):
        if c.efectivo_contado is not None:
            desc_mes[calculos.mes_de(c.fecha)] += c.efectivo_contado - c.efectivo
    for m in sorted(ventas):
        meses.append({"nombre": f"{calculos.nombre_mes(m[1])} {m[0]}", "ventas": ventas[m]["con_iva"], "cubiertos": ventas[m]["cubiertos"], "descuadres": round(desc_mes.get(m, 0.0), 2)})
    return {"cierre": cierre, "gastos": [{"categoria": g.categoria_gasto, "total": g.total} for g in gastos], "gastos_total": round(gastos_total, 2),
            "fondo": fondo, "esperada": esperada, "descuadre": descuadre, "banco": calculos.banco(s, hoy), "meses": meses}


def recepcion(s: Session, hoy: date, perfil: str) -> dict:
    st = calculos.stock(s, hoy)
    ver_precios = perfiles.puede_ver(perfil, "precios_compra")
    recientes = []
    for e in s.scalars(select(Entrada).where(Entrada.fecha >= hoy - timedelta(days=7)).order_by(Entrada.fecha.desc(), Entrada.id.desc()).limit(25)):
        p = s.get(Producto, e.producto_id)
        d = s.get(Documento, e.documento_id) if e.documento_id else None
        recientes.append({"fecha": e.fecha, "producto": p.nombre if p else "", "cantidad": e.cantidad, "unidad": p.unidad if p else "", "caduca": e.caduca,
                          "estimada": e.caducidad_estimada, "lote": e.lote, "factura": d.numero if d else "", "proveedor": d.proveedor.nombre if d and d.proveedor else "",
                          "doc_id": d.id if d else None, "foto": bool(e.foto)})
    ultimo = s.scalars(select(Recuento).order_by(Recuento.fecha.desc())).first()
    if not ver_precios:
        for f in st["filas"]:
            f["valor"] = None
        for c in st["caducan"]:
            c["valor"] = None
        st["mermas_mes"] = None
        st["valor_total"] = None
    caros = sorted([f for f in st["filas"] if f["queda"] > 0], key=lambda f: -(f["valor"] or 0))[:12]
    return {"stock": st, "recientes": recientes, "ultimo_recuento": ultimo.fecha if ultimo else None, "caros": caros, "ver_precios": ver_precios,
            "pendientes_foto": s.scalar(select(func.count(Documento.id)).where(Documento.estado == "leyendo", Documento.tipo == "pendiente"))}


def competencia(s: Session, hoy: date, comp_id: int | None) -> dict:
    comps = list(s.scalars(select(Competidor).order_by(Competidor.distancia_m)))
    c = calculos.carta(s, hoy)
    sel = next((x for x in comps if x.id == comp_id), comps[0] if comps else None)
    filas, subir = [], 0
    if sel:
        for f in c["filas"]:
            su = sel.carta.get(f["clave"])
            if not su:
                continue
            d = f["precio_carta"] / su - 1
            if d < -0.05:
                aviso, subir = f"Podrías subir a {su:.2f} €: estás un {round(-d * 100)} % por debajo.".replace(".", ",", 1), subir + 1
            elif d > 0.08:
                aviso = "Estás bastante por encima: si no se vende, revisa precio o ración."
            else:
                aviso = "En línea."
            filas.append({"nombre": f["nombre"], "suyo": su, "mio": f["precio_carta"], "dif": d, "aviso": aviso})
    return {"competidores": comps, "sel": sel, "filas": filas, "subir": subir, "valoracion_propia": calculos.ajuste(s, "valoracion_google", 4.1)}
