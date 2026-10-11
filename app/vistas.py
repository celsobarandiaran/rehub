"""Datos que necesita cada pantalla, ya calculados. Respeta los perfiles con perfiles.puede_ver."""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import calculos, catalogo, perfiles
from .db import Aviso, Cierre, Competidor, Correo, Documento, Empleado, Entrada, LineaDocumento, Producto, Proveedor, Recuento

ETIQUETAS_CORREO = {"factura": ("Factura", "c-fact"), "reserva": ("Reserva", "c-res"), "consulta": ("Consulta", "c-con"), "queja": ("Queja", "c-queja"),
                    "nomina": ("Nóminas", "c-nom"), "gasto": ("Gasto", "c-gasto"), "publicidad": ("Publicidad", "c-pub"), "cierre": ("Cierre de caja", "c-con"),
                    "etiqueta": ("Etiqueta", "c-est"), "albaran": ("Albarán", "c-est"), "raro": ("Raro: no sé clasificarlo", "c-rev"), "otro": ("Otro", "c-est"), "leyendo": ("Leyendo…", "c-est"),
                    "sin_clasificar": ("Sin clasificar", "c-est")}
COLORES = ["#2d6a4f", "#2c4f9e", "#c0392b", "#9a6200", "#7a3fa0", "#1d6f7d", "#6b6b66"]


def eur(x, dec=2):
    if x is None:
        return "—"
    s = f"{abs(x):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if x < 0 else "") + s


def bandeja(s: Session, categoria: str | None, correo_id: int | None, perfil: str = perfiles.DUENO, desde: date | None = None, hasta: date | None = None) -> dict:
    """Correos del periodo (por defecto, el mes en curso), con el recuento por tipo dentro de ese periodo."""
    filtro = []
    if desde:
        filtro.append(Correo.recibido >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        filtro.append(Correo.recibido <= datetime.combine(hasta, datetime.max.time()))
    cuenta = dict(s.execute(select(Correo.categoria, func.count()).where(*filtro).group_by(Correo.categoria)).all())
    q = select(Correo).where(*filtro).order_by(Correo.recibido.desc())
    if categoria:
        q = q.where(Correo.categoria == categoria)
    correos = list(s.scalars(q.limit(300)))
    if correo_id and not any(c.id == correo_id for c in correos):
        elegido = s.get(Correo, correo_id)
        if elegido:
            correos.insert(0, elegido)
    # La parte derecha arranca cerrada: solo se abre el correo que se pincha
    sel = s.get(Correo, correo_id) if correo_id else None
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
    q = select(Documento).where(Documento.tipo.in_(["factura", "gasto", "nomina", "cierre", "albaran", "otro"]))
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


def contadores(s: Session, hoy: date, perfil: str) -> dict:
    """Lo pendiente de cada pantalla, para las pastillas amarillas del menú."""
    out = {}
    try:
        out["bandeja"] = s.scalar(select(func.count(Correo.id)).where(((Correo.respuesta_propuesta != "") & (Correo.respuesta_enviada.is_(False))) | (Correo.categoria == "raro"))) or 0
        out["documentos"] = s.scalar(select(func.count(Documento.id)).where(Documento.estado.in_(["revisar", "duplicada"]))) or 0
        out["recepcion"] = s.scalar(select(func.count(Documento.id)).where(Documento.estado == "leyendo", Documento.tipo == "pendiente")) or 0
        out["hoy"] = s.scalar(select(func.count(Aviso.id)).where(Aviso.fecha >= hoy - timedelta(days=7), Aviso.nivel == "r")) or 0
    except Exception:
        return {}
    return {k: v for k, v in out.items() if v}


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
    albaranes = [{"id": d.id, "fecha": d.fecha, "numero": d.numero, "proveedor": d.proveedor.nombre if d.proveedor else "", "lineas": (d.datos or {}).get("lineas", 0),
                  "casado": (d.datos or {}).get("casado", ""), "diferencias": (d.datos or {}).get("diferencias", []), "estado": d.estado, "motivo": d.motivo_revisar}
                 for d in s.scalars(select(Documento).where(Documento.tipo == "albaran").order_by(Documento.id.desc()).limit(8))]
    return {"stock": st, "recientes": recientes, "ultimo_recuento": ultimo.fecha if ultimo else None, "caros": caros, "ver_precios": ver_precios,
            "albaranes": albaranes,
            "pendientes_foto": s.scalar(select(func.count(Documento.id)).where(Documento.estado == "leyendo", Documento.tipo == "pendiente"))}


def competencia(s: Session, hoy: date, comp_id: int | None) -> dict:
    comps = list(s.scalars(select(Competidor).order_by(Competidor.distancia_m)))
    c = calculos.carta(s, hoy)
    sel = next((x for x in comps if x.id == comp_id), None)  # arranca cerrado: se abre al pinchar un competidor
    mias = {f["clave"]: f for f in c["filas"]}
    filas, subir = [], 0
    por_categoria, sin, resumen = [], [], {}
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
            filas.append({"nombre": f["nombre"], "suyo": su, "mio": f["precio_carta"], "dif": d, "aviso": aviso, "clave": f["clave"]})
        # Su carta por categorías (bebida y comida), y qué categorías de las mías no tiene
        clasif = {k: catalogo.categoria_clave(k) for k in sel.carta}
        mis_categorias = {(parte, cat["id"]) for parte in ("comida", "bebida") for cat in c["por_categoria"][parte]}
        for parte in ("comida", "bebida"):
            for cat in catalogo.CATEGORIAS[parte]:
                platos = [{"clave": k, "precio": v, "mio": mias[k]["precio_carta"] if k in mias else None, "mio_nombre": mias[k]["nombre"] if k in mias else "",
                           "dif": round(mias[k]["precio_carta"] / v - 1, 3) if k in mias and v else None}
                          for k, v in sorted(sel.carta.items()) if clasif[k] == (parte, cat)]
                if platos:
                    por_categoria.append({"parte": parte, "id": cat, "nombre": catalogo.NOMBRE_CATEGORIA[cat], "platos": platos})
                elif (parte, cat) in mis_categorias:
                    sin.append(catalogo.NOMBRE_CATEGORIA[cat].lower())
        resumen = {
            "tengo_yo": [f["nombre"] for f in c["filas"] if f["clave"] not in sel.carta and f["parte"] == "comida"][:8],
            "tienen_ellos": [k for k in sel.carta if k not in mias][:8],
            "mas_caro": [f"{f['nombre']} (+{round(f['dif'] * 100)} %)" for f in filas if f["dif"] > 0.03],
            "mas_barato": [f"{f['nombre']} ({round(f['dif'] * 100)} %)" for f in filas if f["dif"] < -0.03],
            "cambios": _cambios_carta(sel),
        }
    return {"competidores": comps, "sel": sel, "filas": filas, "subir": subir, "valoracion_propia": calculos.ajuste(s, "valoracion_google", 4.1),
            "por_categoria": por_categoria, "sin": sin, "resumen": resumen}


def _cambios_carta(comp: Competidor) -> list[str]:
    """Qué ha cambiado entre la lectura anterior de su carta y la actual, en frases."""
    ant, act = comp.carta_anterior or {}, comp.carta or {}
    if not ant:
        return []
    out = []
    for k in sorted(set(ant) | set(act)):
        a, b = ant.get(k), act.get(k)
        if a and b and abs(a - b) > 0.01:
            out.append(f"han {'subido' if b > a else 'bajado'} {k} de {eur(a)} a {eur(b)} €")
        elif a and not b:
            out.append(f"han quitado {k}")
        elif b and not a:
            out.append(f"han añadido {k} a {eur(b)} €")
    return out
