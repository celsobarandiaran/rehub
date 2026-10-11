"""Procesar lo que llega: correos, adjuntos y fotos de Recepción.

Clasifica, saca los datos, archiva el archivo con su nombre ordenado y guarda
todo en la base. Detecta facturas duplicadas y subidas de precio.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import almacen, ia, lectura
from .db import (Aviso, Cierre, Correo, Documento, Empleado, Entrada, LineaDocumento, Plato, Producto, Proveedor)

VIDA_DIAS = {"pescado": 2, "carne": 6, "verdura": 6, "lacteo": 7, "pan": 2, "seco": 180, "bebida": 365, "congelado": 90}
SUBIDA_MINIMA = 0.05  # avisa si un precio sube más de un 5 %
CATEGORIAS_GASTO = [("boqueria|mercat|mercado|fruter", "Mercado (compras sueltas)"), ("hielo", "Hielo y bebida"),
                    ("ferreter|reparac|fontaner", "Reparaciones y mantenimiento"), ("makro|menaje|bazar", "Material y menaje"),
                    ("parking|aparcam|gasolin|taxi", "Transporte y aparcamiento")]


def normal(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", " ", s).split("(")[0].strip()


def _sin_espacios(s):
    return re.sub(r"\s+", " ", normal(s)).strip()


# ---------------------------------------------------------------- proveedores y productos
def buscar_proveedor(s: Session, nombre: str | None, cif: str | None = None, crear=True) -> Proveedor | None:
    if cif and cif != "(ejemplo)":
        p = s.scalar(select(Proveedor).where(Proveedor.cif == cif))
        if p:
            return p
    n = _sin_espacios(nombre)
    if not n:
        return None
    for p in s.scalars(select(Proveedor)):
        pn = _sin_espacios(p.nombre)
        if pn == n or (len(n) > 4 and (pn.startswith(n) or n.startswith(pn))):
            return p
    if not crear:
        return None
    p = Proveedor(nombre=(nombre or "").strip().title() if (nombre or "").isupper() else (nombre or "").strip())
    s.add(p)
    s.flush()
    return p


def completar_contacto(p: Proveedor, firma: str):
    """Teléfono, correo, CIF y dirección sacados de la firma del correo (si faltan)."""
    if not firma:
        return
    tel = re.search(r"Tel\.?\s*([\d ]{9,15})", firma)
    correo = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", firma)
    cif = re.search(r"CIF\s*([A-Z]-?\d{7,8}[A-Z0-9]?)", firma)
    lineas = [l.strip() for l in firma.split("\n") if l.strip() and l.strip() != "--"]
    p.telefono = p.telefono or (tel.group(1).strip() if tel else "")
    p.correo = p.correo or (correo.group(0) if correo else "")
    p.cif = p.cif or (cif.group(1) if cif else "")
    if not p.direccion and len(lineas) >= 2 and not lineas[1].lower().startswith("tel"):
        p.direccion = lineas[1]


def buscar_producto(s: Session, descripcion: str, tipo_por_defecto="seco") -> Producto:
    n = _sin_espacios(descripcion)
    for p in s.scalars(select(Producto)):
        pn = _sin_espacios(p.nombre)
        if pn == n or n.startswith(pn) or pn.startswith(n):
            return p
    p = Producto(nombre=descripcion.strip()[:120], tipo=tipo_por_defecto)
    s.add(p)
    s.flush()
    return p


TIPO_POR_PROVEEDOR = {"carne": "carne", "pescado": "pescado", "verdura": "verdura", "pan": "pan", "bebida": "bebida"}


# ---------------------------------------------------------------- clasificar correos sin adjunto
REGLAS = [
    ("publicidad", r"\b(baja|descuento|oferta|regalamos|gratis|únete|unete|promoci|rebajas|última oportunidad|invitación a la feria)\b"),
    ("reserva", r"\b(reserv|mesa para|taula per|tenéis mesa|teneis mesa|para \d+ personas|per a (dues|\d+) persones|somos \d+)"),
    ("queja", r"(esperamos \d+ minutos|no se puede|nos cobraron|estaba mal|queja|fatal|muy mal)"),
    ("consulta", r"\?|¿"),
]


def clasificar_texto(asunto: str, cuerpo: str) -> str:
    t = f"{asunto}\n{cuerpo}".lower()
    if re.search(r"^re:", asunto.lower()) and len(cuerpo) < 120:
        return "otro"
    for cat, patron in REGLAS:
        if re.search(patron, t):
            return cat
    return "raro"


ESQUEMA_CLIENTE = {"type": "OBJECT", "properties": {
    "categoria": {"type": "STRING", "enum": ["reserva", "consulta", "queja", "publicidad", "otro"]},
    "fecha": {"type": "STRING", "nullable": True, "description": "Fecha de la reserva AAAA-MM-DD"},
    "hora": {"type": "STRING", "nullable": True, "description": "HH:MM"},
    "personas": {"type": "INTEGER", "nullable": True},
    "respuesta": {"type": "STRING", "description": "Respuesta propuesta en castellano, firmada por el restaurante. Vacía si es publicidad u otro."}},
    "required": ["categoria", "respuesta"]}


def entender_cliente(asunto: str, cuerpo: str, remitente: str, hoy: date, restaurante: str) -> dict:
    """Con IA: tipo de mensaje, datos de la reserva y respuesta propuesta. Sin IA: reglas y plantilla."""
    try:
        return ia.preguntar_json(
            f"Eres la oficina de {restaurante}. Hoy es {hoy.isoformat()}. Lee este correo de un cliente y devuelve JSON.\n"
            "Si es una reserva, saca fecha, hora y número de personas; la respuesta debe confirmar fecha, hora y personas "
            "(si falta algún dato, pídelo en la respuesta en vez de inventarlo). Si es una queja, pide disculpas sin excusas y ofrece algo sencillo. "
            "Si es una consulta, contesta solo con lo que se sabe y si no lo sabes di que lo consultas. Escribe en castellano, cercano y breve.\n\n"
            f"De: {remitente}\nAsunto: {asunto}\n\n{cuerpo}", ESQUEMA_CLIENTE)
    except (ia.SinIA, ia.CuotaAgotada):
        cat = clasificar_texto(asunto, cuerpo)
        nombre = remitente.split()[0] if remitente else ""
        plantillas = {"reserva": f"Hola, {nombre}:\n\nGracias por escribirnos. Revisamos la disponibilidad y te confirmamos enseguida la fecha, la hora y el número de personas.\n\nUn saludo,\n{restaurante}",
                      "queja": f"Hola, {nombre}:\n\nSentimos mucho lo que pasó. Tienes toda la razón y lo vamos a corregir. Nos encantaría que nos dieras otra oportunidad.\n\nUn saludo,\n{restaurante}",
                      "consulta": f"Hola, {nombre}:\n\nGracias por escribirnos. Te contestamos en cuanto lo consultemos.\n\nUn saludo,\n{restaurante}"}
        return {"categoria": cat, "respuesta": plantillas.get(cat, ""), "sin_ia": True}


# ---------------------------------------------------------------- guardar documentos
def _ruta_entrada(correo_id, nombre):
    limpio = re.sub(r"[^\w. -]", "", nombre)[-80:]
    return f"entrada/{correo_id or 'manual'}/{limpio}"


def _avisar(s, fecha, tipo, nivel, titulo, texto, **kw):
    s.add(Aviso(fecha=fecha, tipo=tipo, nivel=nivel, titulo=titulo, texto=texto, **kw))


def guardar_factura(s: Session, d: dict, ruta_tmp: str, origen: str, correo: Correo | None, firma: str = "") -> Documento:
    prov = buscar_proveedor(s, d.get("proveedor"), d.get("cif"))
    if prov and firma:
        completar_contacto(prov, firma)
    if prov and d.get("telefono") and not prov.telefono:
        prov.telefono = d["telefono"]
    doc = Documento(tipo="factura", fecha=d.get("fecha"), proveedor=prov, numero=d.get("numero") or "", base=d.get("base"), iva=d.get("iva"),
                    total=d.get("total"), vencimiento=d.get("vencimiento"), origen=origen, correo_id=correo.id if correo else None,
                    estado="revisar" if d.get("revisar") else "correcto", motivo_revisar="; ".join(d.get("revisar") or []))
    s.add(doc)
    s.flush()
    # ¿Duplicada? mismo proveedor y número (o mismo proveedor, fecha y total si no hay número)
    q = select(Documento).where(Documento.tipo == "factura", Documento.id != doc.id, Documento.proveedor_id == doc.proveedor_id, Documento.estado != "duplicada")
    q = q.where(Documento.numero == doc.numero) if doc.numero else q.where(Documento.fecha == doc.fecha, Documento.total == doc.total)
    orig = s.scalars(q).first()
    if orig and doc.numero:
        doc.estado = "duplicada"
        doc.motivo_revisar = f"Duplicada de {orig.numero} (llegó el {orig.creado.strftime('%d/%m') if orig.creado else ''})"
        _avisar(s, (correo.recibido.date() if correo else doc.fecha) or doc.fecha, "duplicada", "r", "No pagar",
                f"Factura duplicada de {prov.nombre} {doc.numero}: ya llegó antes. No la pagues dos veces.", documento_id=doc.id)
    tipo_prod = TIPO_POR_PROVEEDOR.get((prov.tipo or "").lower(), "seco") if prov else "seco"
    for l in d.get("lineas") or []:
        prod = buscar_producto(s, l["descripcion"], tipo_prod) if prov and prov.grupo == "comida" else None
        ln = LineaDocumento(documento_id=doc.id, producto_id=prod.id if prod else None, descripcion=l["descripcion"], cantidad=l.get("cantidad"),
                            unidad=l.get("unidad") or "", precio_unitario=l.get("precio_unitario"))
        s.add(ln)
        if prod and doc.estado != "duplicada" and l.get("precio_unitario"):
            _mirar_subida(s, doc, prod, l["precio_unitario"])
            _entrada_estimada(s, doc, prod, l.get("cantidad"))
    _archivar(doc, ruta_tmp, prov.nombre if prov else "Sin proveedor")
    return doc


def _mirar_subida(s, doc, prod, precio):
    anterior = s.execute(
        select(LineaDocumento.precio_unitario, Documento.numero, Documento.fecha).join(Documento)
        .where(LineaDocumento.producto_id == prod.id, Documento.proveedor_id == doc.proveedor_id, Documento.fecha < doc.fecha,
               Documento.estado != "duplicada").order_by(Documento.fecha.desc())).first()
    if anterior and anterior[0] and precio > anterior[0] * (1 + SUBIDA_MINIMA):
        pct = round((precio / anterior[0] - 1) * 100)
        _avisar(s, doc.fecha, "subida_precio", "a", "Subida de precio",
                f"{prod.nombre}: de {anterior[0]:.2f} a {precio:.2f} €/{prod.unidad} (+{pct} %) en {doc.proveedor.nombre}, factura {doc.numero}.".replace(".", ",", 2),
                documento_id=doc.id, producto_id=prod.id, datos={"antes": anterior[0], "ahora": precio, "factura_antes": anterior[1]})


def _entrada_estimada(s, doc, prod, cantidad):
    """Todo lo fresco entra en cámara con caducidad estimada; la foto de la etiqueta la corrige."""
    if not cantidad or prod.tipo not in ("pescado", "carne", "verdura", "lacteo", "pan") or not doc.fecha:
        return
    s.add(Entrada(producto_id=prod.id, documento_id=doc.id, fecha=doc.fecha, cantidad=cantidad,
                  caduca=doc.fecha + timedelta(days=VIDA_DIAS.get(prod.tipo, 7)), caducidad_estimada=True))


def _archivar(doc: Documento, ruta_tmp: str, quien: str):
    if not ruta_tmp:
        return
    ext = ruta_tmp.rsplit(".", 1)[-1].lower()
    nueva = almacen.ruta_documento(doc.fecha, doc.tipo, quien, doc.total, ext)
    try:
        doc.archivo = almacen.mover(ruta_tmp, nueva)
    except Exception:
        doc.archivo = ruta_tmp


def guardar_nomina(s, d, ruta_tmp, origen, correo) -> Documento:
    nombre = d.get("empleado") or ""
    emp = next((e for e in s.scalars(select(Empleado)) if normal(e.nombre) == normal(nombre)), None)
    if not emp and nombre:
        emp = Empleado(nombre=nombre)
        s.add(emp)
        s.flush()
    fecha = date(d["anio"], d["mes"], 28) if d.get("anio") and d.get("mes") else None
    if fecha:
        fecha = (fecha.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    doc = Documento(tipo="nomina", fecha=fecha, empleado_id=emp.id if emp else None, total=d.get("coste_empresa"), base=d.get("bruto"),
                    origen=origen, correo_id=correo.id if correo else None, estado="revisar" if d.get("revisar") else "correcto",
                    motivo_revisar="; ".join(d.get("revisar") or []), datos={"bruto": d.get("bruto"), "neto": d.get("neto"), "mes": d.get("mes")})
    s.add(doc)
    s.flush()
    _archivar(doc, ruta_tmp, f"Nomina {nombre.split(' (')[0]}")
    return doc


def guardar_cierre(s, d, ruta_tmp, origen, correo) -> Documento:
    doc = Documento(tipo="cierre", fecha=d.get("fecha"), total=d.get("total"), origen=origen, correo_id=correo.id if correo else None,
                    estado="revisar" if d.get("revisar") else "correcto", motivo_revisar="; ".join(d.get("revisar") or []))
    s.add(doc)
    s.flush()
    platos = list(s.scalars(select(Plato)))
    unidades = {}
    for nombre, n in (d.get("unidades") or {}).items():
        p = next((p for p in platos if p.nombre.startswith(nombre) or normal(p.nombre).startswith(normal(nombre))), None)
        unidades[p.nombre if p else nombre] = unidades.get(p.nombre if p else nombre, 0) + n
    if d.get("fecha") and not s.scalar(select(Cierre).where(Cierre.fecha == d["fecha"])):
        s.add(Cierre(fecha=d["fecha"], ventas_total=d.get("total") or 0, tarjeta=d.get("tarjeta") or 0, efectivo=d.get("efectivo") or 0,
                     cubiertos=d.get("cubiertos") or 0, unidades=unidades, franjas=d.get("franjas") or {}, documento_id=doc.id))
    _archivar(doc, ruta_tmp, "Cierre TPV")
    return doc


def categoria_gasto(comercio: str) -> str:
    c = normal(comercio)
    for patron, cat in CATEGORIAS_GASTO:
        if re.search(patron, c):
            return cat
    return "Otros"


def guardar_gasto(s, d, ruta_tmp, origen, correo) -> Documento:
    doc = Documento(tipo="gasto", fecha=d.get("fecha"), numero=d.get("numero") or "", total=d.get("total"), origen=origen,
                    correo_id=correo.id if correo else None, categoria_gasto=categoria_gasto(d.get("proveedor") or ""),
                    estado="revisar" if d.get("revisar") else "correcto", motivo_revisar="; ".join(d.get("revisar") or []),
                    datos={"comercio": d.get("proveedor"), "lineas": d.get("lineas")})
    s.add(doc)
    s.flush()
    _archivar(doc, ruta_tmp, d.get("proveedor") or "Gasto")
    return doc


def guardar_etiqueta(s, d, ruta_tmp, hoy: date) -> Entrada | None:
    """Foto de Recepción: casa el producto con la última factura de ese proveedor y corrige la caducidad."""
    prod = buscar_producto(s, d.get("producto") or "", "pescado") if d.get("producto") else None
    if not prod:
        return None
    prov = buscar_proveedor(s, d.get("proveedor"), crear=False)
    q = (select(Entrada).join(Documento).where(Entrada.producto_id == prod.id, Entrada.caducidad_estimada.is_(True))
         .order_by(Documento.fecha.desc()))
    if prov:
        q = q.where(Documento.proveedor_id == prov.id)
    if d.get("fecha"):
        q = q.where(Documento.fecha <= d["fecha"] + timedelta(days=1), Documento.fecha >= d["fecha"] - timedelta(days=7))
    e = s.scalars(q).first()
    if not e:
        e = Entrada(producto_id=prod.id, fecha=d.get("fecha") or hoy, cantidad=d.get("peso") or 0)
        s.add(e)
    if d.get("caducidad"):
        e.caduca = d["caducidad"]
        e.caducidad_estimada = False
    e.lote = d.get("lote") or e.lote
    if d.get("peso"):
        e.cantidad = d["peso"]
    e.foto = ruta_tmp
    s.flush()
    return e


# ---------------------------------------------------------------- entrada principal
def procesar_correo(s: Session, c: dict, adjuntos: list[tuple[str, bytes]], hoy: date, restaurante: str, origen="correo") -> Correo:
    """c: {de_nombre, alias, asunto, cuerpo, fecha (iso), gmail_id?}. adjuntos: [(nombre, bytes)]."""
    correo = Correo(gmail_id=c.get("gmail_id", ""), remitente=c.get("de_nombre", ""), alias=c.get("alias", ""), asunto=c.get("asunto", ""),
                    cuerpo=c.get("cuerpo", ""), recibido=datetime.fromisoformat(c["fecha"]) if c.get("fecha") else datetime.now())
    s.add(correo)
    s.flush()
    firma = c.get("cuerpo", "").split("\n--\n", 1)[1] if "\n--\n" in c.get("cuerpo", "") else ""
    tipos = []
    for nombre, contenido in adjuntos:
        tmp = almacen.guardar(_ruta_entrada(correo.id, nombre), contenido, "application/pdf" if nombre.lower().endswith(".pdf") else "image/jpeg")
        if nombre.lower().endswith(".pdf"):
            d = lectura.leer_pdf(contenido)
            if d["tipo"] == "factura":
                guardar_factura(s, d, tmp, origen, correo, firma)
            elif d["tipo"] == "nomina":
                guardar_nomina(s, d, tmp, origen, correo)
            elif d["tipo"] == "cierre":
                guardar_cierre(s, d, tmp, origen, correo)
            else:
                s.add(Documento(tipo="otro", archivo=tmp, origen=origen, correo_id=correo.id, estado="revisar", motivo_revisar="no sé qué documento es",
                                fecha=correo.recibido.date()))
            tipos.append(d["tipo"])
        else:  # foto: la lee la IA más tarde (cola)
            s.add(Documento(tipo="pendiente", archivo=tmp, origen=origen, correo_id=correo.id, estado="leyendo", fecha=correo.recibido.date(),
                            datos={"firma": firma, "remitente": correo.remitente}))
            tipos.append("pendiente")
    if tipos:
        orden = ["factura", "nomina", "cierre", "pendiente", "otro", "sin_texto"]
        correo.categoria = {"factura": "factura", "nomina": "nomina", "cierre": "cierre", "pendiente": "leyendo"}.get(sorted(tipos, key=orden.index)[0], "raro")
    else:
        cat = clasificar_texto(correo.asunto, correo.cuerpo)
        correo.categoria = cat
        if cat in ("reserva", "consulta", "queja"):
            correo.categoria = "leyendo"  # la IA lo entiende y propone respuesta en la cola
    return correo


def procesar_pendientes(s: Session, hoy: date, restaurante: str, maximo=3) -> int:
    """Lee con IA unas pocas fotos o correos de clientes pendientes. Devuelve cuántos ha hecho."""
    hechos = 0
    for doc in s.scalars(select(Documento).where(Documento.estado == "leyendo").order_by(Documento.id).limit(maximo)):
        try:
            contenido = almacen.leer(doc.archivo)
        except Exception:
            # El archivo ya no está (se borró el almacén, fallo de red…): no se intenta eternamente.
            doc.tipo, doc.estado, doc.motivo_revisar = "otro", "revisar", "no se encuentra el archivo de la foto"
            hechos += 1
            continue
        d = lectura.leer_foto(contenido)  # puede lanzar CuotaAgotada: se queda en cola
        correo = s.get(Correo, doc.correo_id) if doc.correo_id else None
        ruta = doc.archivo
        s.delete(doc)
        s.flush()
        if d["tipo"] == "factura":
            guardar_factura(s, d, ruta, doc.origen, correo, (doc.datos or {}).get("firma", ""))
            cat = "factura"
        elif d["tipo"] == "gasto":
            guardar_gasto(s, d, ruta, doc.origen, correo)
            cat = "gasto"
        elif d["tipo"] == "etiqueta":
            guardar_etiqueta(s, d, ruta, hoy)
            cat = "etiqueta"
        else:
            s.add(Documento(tipo="otro", archivo=ruta, origen=doc.origen, correo_id=doc.correo_id, estado="revisar", motivo_revisar="foto que no es factura ni ticket"))
            cat = "raro"
        if correo and correo.categoria == "leyendo":
            correo.categoria = cat
        hechos += 1
    for correo in s.scalars(select(Correo).where(Correo.categoria == "leyendo").order_by(Correo.id).limit(maximo)):
        if s.scalar(select(func.count(Documento.id)).where(Documento.correo_id == correo.id, Documento.estado == "leyendo")):
            continue
        r = entender_cliente(correo.asunto, correo.cuerpo, correo.remitente, hoy, restaurante)
        correo.categoria = r["categoria"] if r["categoria"] != "otro" else "otro"
        correo.respuesta_propuesta = r.get("respuesta") or ""
        correo.datos = {k: r.get(k) for k in ("fecha", "hora", "personas", "sin_ia") if r.get(k) is not None}
        hechos += 1
    return hechos
