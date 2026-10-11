"""Los cálculos de ReHub. Todo el análisis se hace SIN IVA; la caja y el banco, con IVA (dinero real).

Cada función recibe una sesión de base de datos y devuelve diccionarios listos para pintar.
Las reglas vienen del informe de diseño: platos por euros de margen, coste de comida real
(con recuento) frente al teórico (según recetas), punto de equilibrio con días de apertura,
caja a 30 días desde el saldo real del banco, previsión como margen y no como cifra exacta.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import (Ajuste, Aviso, Cierre, Competidor, Documento, Empleado, Entrada, Evento, LineaDocumento, LineaReceta, MovimientoBanco,
                 PagoFijo, Plato, Producto, Proveedor, Recuento, Turno)

IVA_VENTAS = 0.10
NORMAL = {"comida": (0.28, 0.35), "personal": (0.30, 0.35)}
FRANJAS = ["12-14", "14-16", "16-19", "19-21", "21-23", "23-24"]
TIPOS = {"estrella": "⭐ Estrella · gana y se vende", "vaca": "🐄 Vaca · se vende pero gana poco",
         "puzle": "🧩 Puzle · gana pero no se vende", "perro": "🐕 Perro · ni gana ni se vende"}
QUE_HACER = {"estrella": "Que no falte y que se vea.", "vaca": "Se vende mucho pero deja poco: ajustar ración o subir un poco.",
             "puzle": "Deja mucho pero se vende poco: recomendarlo, mejor foto o mejor nombre.", "perro": "Ni deja ni se vende: cambiarlo o quitarlo."}


def ajuste(s: Session, clave: str, por_defecto):
    a = s.get(Ajuste, clave)
    if not a or a.valor in (None, ""):
        return por_defecto
    try:
        return type(por_defecto)(a.valor) if not isinstance(por_defecto, date) else date.fromisoformat(a.valor)
    except (TypeError, ValueError):
        return por_defecto


def mes_de(d: date):
    return (d.year, d.month)


def nombre_mes(m: int) -> str:
    return ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"][m]


# ---------------------------------------------------------------- precios y costes
def precios_actuales(s: Session) -> dict[int, tuple[float, date, int]]:
    """Último precio sin IVA de cada producto: producto_id -> (precio, fecha, documento_id). Ignora duplicadas."""
    out = {}
    q = (select(LineaDocumento.producto_id, LineaDocumento.precio_unitario, Documento.fecha, Documento.id)
         .join(Documento).where(Documento.estado != "duplicada", LineaDocumento.producto_id.is_not(None), LineaDocumento.precio_unitario.is_not(None))
         .order_by(Documento.fecha))
    for pid, precio, fecha, did in s.execute(q):
        out[pid] = (precio, fecha, did)
    return out


def coste_receta(receta: list, precios: dict, productos: dict) -> tuple[float, list]:
    total, detalle = 0.0, []
    for l in receta:
        p = productos[l.producto_id]
        precio = precios.get(l.producto_id, (0.0, None, None))[0]
        coste = l.cantidad / (p.rendimiento or 1.0) * precio
        total += coste
        detalle.append({"producto": p.nombre, "cantidad": l.cantidad, "unidad": p.unidad, "rendimiento": p.rendimiento, "precio": precio, "coste": round(coste, 2),
                        "alergenos": p.alergenos})
    return round(total, 2), detalle


def unidades_vendidas(s: Session, desde: date | None = None, hasta: date | None = None) -> dict[str, int]:
    q = select(Cierre.unidades)
    if desde:
        q = q.where(Cierre.fecha >= desde)
    if hasta:
        q = q.where(Cierre.fecha <= hasta)
    out = defaultdict(int)
    for u in s.scalars(q):
        for k, n in (u or {}).items():
            out[k] += n
    return out


def carta(s: Session, hoy: date, dias=92) -> dict:
    """Cada plato con precio sin IVA, coste, margen, unidades, tipo y competencia."""
    precios = precios_actuales(s)
    productos = {p.id: p for p in s.scalars(select(Producto))}
    vendidas = unidades_vendidas(s, hoy - timedelta(days=dias), hoy)
    comps = list(s.scalars(select(Competidor)))
    platos = list(s.scalars(select(Plato).where(Plato.activo.is_(True))))
    filas = []
    for p in platos:
        coste, detalle = coste_receta(p.receta, precios, productos)
        pv = round(p.precio_carta / (1 + IVA_VENTAS), 2)
        u = vendidas.get(p.nombre, 0)
        suyos = [c.carta.get(p.clave_competencia) for c in comps if c.carta.get(p.clave_competencia)]
        media = round(sum(suyos) / len(suyos), 2) if suyos else None
        dif = round(p.precio_carta / media - 1, 3) if media else None
        filas.append({"id": p.id, "nombre": p.nombre, "parte": p.parte, "precio_carta": p.precio_carta, "pv": pv, "coste": coste, "margen": round(pv - coste, 2),
                      "margen_pct": round((pv - coste) / pv, 3) if pv else 0, "unidades": u, "receta": detalle, "comp_n": len(suyos), "comp_media": media,
                      "comp_dif": dif, "alergenos": sorted({a.strip() for d in detalle for a in d["alergenos"].split(",") if a.strip()}),
                      "clave": p.clave_competencia})
    resumen = {}
    for parte in ("comida", "bebida"):
        fs = [f for f in filas if f["parte"] == parte]
        tot = sum(f["unidades"] for f in fs) or 1
        media = sum(f["margen"] * f["unidades"] for f in fs) / tot
        umbral = 0.7 * tot / max(1, len(fs))
        for f in fs:
            gana, vende = f["margen"] >= media, f["unidades"] >= umbral
            f["tipo"] = "estrella" if gana and vende else "vaca" if vende else "puzle" if gana else "perro"
            f["que_hacer"] = QUE_HACER[f["tipo"]]
            if f["comp_dif"] is not None and f["comp_dif"] < -0.05 and f["tipo"] in ("estrella", "vaca"):
                f["que_hacer"] += f" Estás más barato que la competencia: podrías subir a {f['comp_media']:.2f} €.".replace(".", ",")
            f["margen_total"] = round(f["margen"] * f["unidades"], 2)
        resumen[parte] = {"margen_medio": round(media, 2), "umbral": round(umbral), "margen_total": round(sum(f["margen_total"] for f in fs), 2), "platos": len(fs)}
    filas.sort(key=lambda f: -f["margen_total"])
    mias = {f["clave"] for f in filas}
    suyas = defaultdict(list)
    for c in comps:
        for k, v in c.carta.items():
            if k not in mias:
                suyas[k].append(v)
    ellos = [{"clave": k, "n": len(v), "media": round(sum(v) / len(v), 2)} for k, v in sorted(suyas.items(), key=lambda x: -len(x[1]))]
    yo = [f for f in filas if f["comp_n"] == 0 and f["parte"] == "comida"]
    return {"filas": filas, "resumen": resumen, "ellos": ellos, "yo": yo, "n_comp": len(comps),
            "mas_caro": sum(1 for f in filas if f["comp_dif"] is not None and f["comp_dif"] > 0.03),
            "mas_barato": sum(1 for f in filas if f["comp_dif"] is not None and f["comp_dif"] < -0.03)}


# ---------------------------------------------------------------- ventas, compras, personal por mes
def ventas_por_mes(s: Session) -> dict:
    out = defaultdict(lambda: {"con_iva": 0.0, "sin_iva": 0.0, "cubiertos": 0, "dias": 0, "tarjeta": 0.0})
    for c in s.scalars(select(Cierre)):
        m = out[mes_de(c.fecha)]
        m["con_iva"] += c.ventas_total
        m["sin_iva"] += c.ventas_total / (1 + IVA_VENTAS)
        m["cubiertos"] += c.cubiertos
        m["dias"] += 1
        m["tarjeta"] += c.tarjeta
    return dict(out)


def compras_por_mes(s: Session) -> dict:
    """Base (sin IVA) de las facturas por mes y grupo (comida / local), sin duplicadas."""
    out = defaultdict(lambda: {"comida": 0.0, "local": 0.0, "por_proveedor": defaultdict(float)})
    for d in s.scalars(select(Documento).where(Documento.tipo == "factura", Documento.estado != "duplicada", Documento.fecha.is_not(None))):
        g = d.proveedor.grupo if d.proveedor else "local"
        out[mes_de(d.fecha)][g] += d.base or 0.0
        if d.proveedor:
            out[mes_de(d.fecha)]["por_proveedor"][d.proveedor.nombre] += d.base or 0.0
    return dict(out)


def personal_por_mes(s: Session) -> dict:
    out = defaultdict(float)
    for d in s.scalars(select(Documento).where(Documento.tipo == "nomina", Documento.fecha.is_not(None))):
        out[mes_de(d.fecha)] += d.total or 0.0
    return dict(out)


def coste_hora(s: Session) -> dict[int, float]:
    """Coste para la empresa por hora de cada empleado: última nómina (coste empresa) / horas del mes."""
    ultima = {}
    for d in s.scalars(select(Documento).where(Documento.tipo == "nomina", Documento.empleado_id.is_not(None)).order_by(Documento.fecha)):
        ultima[d.empleado_id] = d.total or 0.0
    out = {}
    for e in s.scalars(select(Empleado)):
        horas_mes = (e.horas_semana or 40) * 52 / 12
        out[e.id] = round(ultima.get(e.id, 0.0) / horas_mes, 2) if horas_mes else 0.0
    return out


# ---------------------------------------------------------------- stock, caducidades y coste de comida
def stock(s: Session, hoy: date) -> dict:
    """Stock teórico por producto (FIFO): entradas menos lo consumido según recetas y ventas."""
    productos = {p.id: p for p in s.scalars(select(Producto))}
    precios = precios_actuales(s)
    recetas = defaultdict(list)
    platos = {p.nombre: p for p in s.scalars(select(Plato))}
    for p in platos.values():
        for l in p.receta:
            recetas[p.nombre].append((l.producto_id, l.cantidad / (productos[l.producto_id].rendimiento or 1.0)))
    entradas = defaultdict(list)
    primera = {}
    for e in s.scalars(select(Entrada).order_by(Entrada.fecha, Entrada.id)):
        entradas[e.producto_id].append(e)
        primera.setdefault(e.producto_id, e.fecha)
    consumo = defaultdict(float)
    for c in s.scalars(select(Cierre).where(Cierre.fecha <= hoy)):
        for nombre, n in (c.unidades or {}).items():
            for pid, cant in recetas.get(nombre, []):
                if pid in primera and c.fecha >= primera[pid]:
                    consumo[pid] += n * cant
    # último recuento manda sobre lo teórico
    ultimo_recuento = {}
    for r in s.scalars(select(Recuento).order_by(Recuento.fecha)):
        ultimo_recuento[r.producto_id] = r
    filas, caducan, mermas = [], [], 0.0
    inicio_mes = hoy.replace(day=1)
    for pid, lista in entradas.items():
        p = productos[pid]
        queda = consumo[pid]
        restantes = []
        for e in lista:
            usado = min(e.cantidad, queda)
            queda -= usado
            resto = round(e.cantidad - usado, 3)
            if resto > 0:
                restantes.append((e, resto))
        total = round(sum(r for _, r in restantes), 3)
        precio = precios.get(pid, (0.0, None, None))[0]
        for e, resto in restantes:
            if e.caduca and hoy <= e.caduca <= hoy + timedelta(days=1):
                caducan.append({"producto": p.nombre, "queda": resto, "unidad": p.unidad, "caduca": e.caduca, "estimada": e.caducidad_estimada,
                                "cuando": "hoy" if e.caduca == hoy else "mañana", "lote": e.lote, "valor": round(resto * precio, 2)})
            elif e.caduca and e.caduca < hoy and e.caduca >= inicio_mes:
                mermas += resto * precio
        filas.append({"producto": p.nombre, "tipo": p.tipo, "unidad": p.unidad, "queda": total, "valor": round(total * precio, 2),
                      "recuento": ultimo_recuento.get(pid)})
    caducan.sort(key=lambda x: (x["caduca"], -x["valor"]))
    filas.sort(key=lambda f: -f["valor"])
    return {"filas": filas, "caducan": caducan, "mermas_mes": round(mermas, 2), "productos_en_camara": sum(1 for f in filas if f["queda"] > 0),
            "valor_total": round(sum(f["valor"] for f in filas), 2)}


def coste_comida_mes(s: Session, anio: int, mes: int, hoy: date) -> dict:
    """Coste de comida real (con recuentos si los hay) y teórico (recetas × ventas) de un mes."""
    compras = compras_por_mes(s).get((anio, mes), {"comida": 0.0})["comida"]
    ventas = ventas_por_mes(s).get((anio, mes), {"sin_iva": 0.0})["sin_iva"]
    precios = precios_actuales(s)
    productos = {p.id: p for p in s.scalars(select(Producto))}
    platos = {p.nombre: p for p in s.scalars(select(Plato))}
    inicio, fin = date(anio, mes, 1), (date(anio, mes, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    teorico = 0.0
    for c in s.scalars(select(Cierre).where(Cierre.fecha >= inicio, Cierre.fecha <= fin)):
        for nombre, n in (c.unidades or {}).items():
            p = platos.get(nombre)
            if p:
                teorico += n * coste_receta(p.receta, precios, productos)[0]

    def valor_recuento(fecha_limite):
        ultimo = {}
        for r in s.scalars(select(Recuento).where(Recuento.fecha <= fecha_limite).order_by(Recuento.fecha)):
            ultimo[r.producto_id] = r.cantidad_contada
        return round(sum(c * precios.get(pid, (0.0,))[0] for pid, c in ultimo.items()), 2) if ultimo else None

    inv_ini, inv_fin = valor_recuento(inicio - timedelta(days=1)), valor_recuento(fin)
    con_recuento = inv_ini is not None and inv_fin is not None
    real = round(inv_ini + compras - inv_fin, 2) if con_recuento else round(compras, 2)
    return {"compras": round(compras, 2), "ventas": round(ventas, 2), "teorico": round(teorico, 2), "real": real, "con_recuento": con_recuento,
            "inv_ini": inv_ini, "inv_fin": inv_fin, "pct_real": round(real / ventas, 3) if ventas else None, "pct_teorico": round(teorico / ventas, 3) if ventas else None,
            "diferencia": round(real - teorico, 2)}


# ---------------------------------------------------------------- dueño
def semaforo(valor: float | None, rango: tuple) -> str:
    if valor is None:
        return "gris"
    return "v" if valor <= rango[1] else ("a" if valor <= rango[1] + 0.03 else "r")


def dueno(s: Session, hoy: date) -> dict:
    """Cuadro mensual: el último mes completo con datos."""
    ventas, compras, personal = ventas_por_mes(s), compras_por_mes(s), personal_por_mes(s)
    meses = sorted(m for m in ventas if m < mes_de(hoy)) or sorted(ventas)
    if not meses:
        return {"sin_datos": True}
    filas = []
    for m in meses:
        v = ventas[m]
        comida = coste_comida_mes(s, m[0], m[1], hoy)
        per = personal.get(m, 0.0)
        local = compras.get(m, {"local": 0.0})["local"]
        otros = sum(p.importe for p in s.scalars(select(PagoFijo).where(PagoFijo.cada == "mes")) if "sin factura" in p.concepto or "autónomo" in p.concepto or "Préstamo" in p.concepto)
        gastos = comida["real"] + per + local + otros
        luz_gas = sum(v_ for k, v_ in compras.get(m, {"por_proveedor": {}})["por_proveedor"].items() if k in ("Endesa", "Naturgy"))
        filas.append({"mes": m, "nombre": f"{nombre_mes(m[1])} {m[0]}", "ventas": round(v["sin_iva"], 2), "ventas_iva": round(v["con_iva"], 2), "cubiertos": v["cubiertos"],
                      "dias": v["dias"], "comida": comida, "personal": round(per, 2), "pct_personal": round(per / v["sin_iva"], 3) if v["sin_iva"] else None,
                      "local": round(local, 2), "otros": round(otros, 2), "gastos": round(gastos, 2), "beneficio": round(v["sin_iva"] - gastos, 2),
                      "luz_gas": round(luz_gas, 2), "luz_gas_cubierto": round(luz_gas / v["cubiertos"], 2) if v["cubiertos"] else None,
                      "ticket": round(v["sin_iva"] / v["cubiertos"], 2) if v["cubiertos"] else None})
    actual = filas[-1]
    anterior = filas[-2] if len(filas) > 1 else None
    dias_apertura = ajuste(s, "dias_apertura_mes", 26)
    pct_comida = actual["comida"]["pct_real"] or 0.3
    fijos = actual["personal"] + actual["local"] + actual["otros"]
    pe_mes = fijos / (1 - pct_comida) if pct_comida < 1 else None
    actual["semaforos"] = {"comida": semaforo(actual["comida"]["pct_real"], NORMAL["comida"]), "personal": semaforo(actual["pct_personal"], NORMAL["personal"])}
    return {"meses": filas, "actual": actual, "anterior": anterior, "dias_apertura": dias_apertura,
            "punto_equilibrio": {"fijos": round(fijos, 2), "pct_comida": pct_comida, "mes": round(pe_mes, 2) if pe_mes else None,
                                 "dia": round(pe_mes / dias_apertura, 2) if pe_mes else None, "media_dia": round(actual["ventas"] / actual["dias"], 2) if actual["dias"] else None},
            "variacion": round(actual["ventas"] / anterior["ventas"] - 1, 3) if anterior and anterior["ventas"] else None}


def banco(s: Session, hoy: date) -> dict:
    movs = list(s.scalars(select(MovimientoBanco).order_by(MovimientoBanco.fecha, MovimientoBanco.id)))
    if not movs:
        return {"hay": False}
    saldo = movs[-1].saldo
    sin_factura = [m for m in movs if m.tipo == "recibo_sin_factura"][-6:]
    tarjeta = defaultdict(float)
    for m in movs:
        if m.tipo == "abono_tarjeta":
            tarjeta[mes_de(m.fecha - timedelta(days=1))] += m.importe
    tpv = {m: v["tarjeta"] for m, v in ventas_por_mes(s).items()}
    comparacion = [{"mes": f"{nombre_mes(m[1])} {m[0]}", "tpv": round(tpv.get(m, 0), 2), "banco": round(tarjeta[m], 2), "diferencia": round(tpv.get(m, 0) - tarjeta[m], 2)}
                   for m in sorted(tarjeta) if m in tpv]
    return {"hay": True, "saldo": saldo, "fecha": movs[-1].fecha, "sin_factura": sin_factura, "tarjeta": comparacion, "movimientos": len(movs)}


def caja_30_dias(s: Session, hoy: date) -> dict:
    """Dinero en el banco cada día durante 30 días: saldo real + ventas previstas − pagos conocidos."""
    b = banco(s, hoy)
    saldo = b["saldo"] if b["hay"] else 0.0
    minimo = ajuste(s, "minimo_caja", 3000.0)
    # entradas: media de ventas por día de la semana (últimas 8 semanas), tarjeta llega al día siguiente
    por_dia = defaultdict(list)
    for c in s.scalars(select(Cierre).where(Cierre.fecha > hoy - timedelta(days=56), Cierre.fecha <= hoy)):
        por_dia[c.fecha.weekday()].append(c.ventas_total)
    media = {wd: (sum(v) / len(v) if v else 0.0) for wd, v in por_dia.items()}
    cerrado = {wd for wd in range(7) if wd not in por_dia}
    # compras diarias aproximadas con IVA (se pagan al vencimiento, pero las de proveedores futuras no están en facturas: se estiman)
    compras = compras_por_mes(s)
    ult = compras.get(max(compras), {"comida": 0.0}) if compras else {"comida": 0.0}
    compras_dia = (ult["comida"] * 1.1 / 30) if compras else 0.0
    pagos = []
    for d in s.scalars(select(Documento).where(Documento.tipo == "factura", Documento.estado != "duplicada", Documento.pagado_fecha.is_(None), Documento.vencimiento.is_not(None))):
        if d.vencimiento >= hoy:
            pagos.append({"dia": d.vencimiento, "concepto": f"{d.proveedor.nombre if d.proveedor else 'Factura'} {d.numero}", "importe": d.total or 0, "aprox": False, "tipo": "factura"})
    iva_confirmado = ajuste(s, "iva_trimestre_confirmado", 0.0)
    for p in s.scalars(select(PagoFijo)):
        for k in range(2):
            m = (hoy.month - 1 + k) % 12 + 1
            a = hoy.year + (hoy.month - 1 + k) // 12
            if p.cada == "trimestre" and m not in (1, 4, 7, 10):
                continue
            dia = ((date(a, m, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day if p.dia == -1 else p.dia
            f = date(a, m, dia)
            if hoy <= f <= hoy + timedelta(days=30):
                importe = p.importe
                aprox = p.aproximado
                if p.concepto.startswith("IVA") and iva_confirmado:
                    importe, aprox = iva_confirmado, False
                if p.concepto.startswith("IVA") and not iva_confirmado:
                    importe = iva_estimado(s, hoy)
                pagos.append({"dia": f, "concepto": p.concepto, "importe": importe, "aprox": aprox, "tipo": "fijo"})
    pagos.sort(key=lambda x: x["dia"])
    serie, minimo_dia, minimo_val = [], hoy, saldo
    sal = saldo
    for i in range(31):
        d = hoy + timedelta(days=i)
        if i:
            ayer = d - timedelta(days=1)
            sal += media.get(ayer.weekday(), 0.0) * 0.75 * 0.997  # tarjeta de ayer, menos comisión
            if d.weekday() == 1:  # el martes se ingresa el efectivo de la semana anterior
                sal += sum(media.get(wd, 0.0) * 0.25 for wd in range(7)) - compras_dia * 2
            sal -= compras_dia * 0.6  # parte de las compras se paga al contado o por recibo corto
            for p in pagos:
                if p["dia"] == d:
                    sal -= p["importe"]
        serie.append({"dia": d, "saldo": round(sal, 2)})
        if sal < minimo_val:
            minimo_val, minimo_dia = sal, d
    grandes = [p for p in pagos if p["importe"] >= 500]
    return {"saldo_hoy": round(saldo, 2), "fecha_saldo": b.get("fecha"), "serie": serie, "pagos": pagos, "grandes": grandes, "minimo": minimo,
            "minimo_dia": minimo_dia, "minimo_val": round(minimo_val, 2), "final": serie[-1]["saldo"], "falta": minimo_val < minimo,
            "entra_dia": round(sum(media.values()) / 7, 2), "iva_confirmado": bool(iva_confirmado), "cerrado": cerrado}


def iva_estimado(s: Session, hoy: date) -> float:
    """IVA del trimestre anterior: cobrado en ventas menos pagado en compras (aproximado)."""
    tri = (hoy.month - 1) // 3  # trimestre actual (0-3); el que se paga es el anterior
    meses = [((tri - 1) * 3 + i) if tri else (9 + i) for i in (1, 2, 3)]
    anio = hoy.year if tri else hoy.year - 1
    rep = sum(v["con_iva"] - v["sin_iva"] for m, v in ventas_por_mes(s).items() if m[0] == anio and m[1] in meses)
    sop = sum(d.iva or 0 for d in s.scalars(select(Documento).where(Documento.tipo == "factura", Documento.estado != "duplicada"))
              if d.fecha and d.fecha.year == anio and d.fecha.month in meses)
    # si faltan meses del trimestre en los datos, se extrapola con la media de los que hay
    presentes = {m[1] for m in ventas_por_mes(s) if m[0] == anio and m[1] in meses}
    factor = 3 / len(presentes) if presentes else 1
    return round(max(0.0, (rep - sop) * factor), 2)


# ---------------------------------------------------------------- hoy
def prevision(s: Session, dia: date) -> dict:
    mismos = [c.ventas_total for c in s.scalars(select(Cierre).where(Cierre.fecha < dia, Cierre.fecha > dia - timedelta(days=70)))
              if c.fecha.weekday() == dia.weekday()]
    eventos = list(s.scalars(select(Evento).where(Evento.fecha >= dia, Evento.fecha <= dia + timedelta(days=7)).order_by(Evento.fecha)))
    if not mismos:
        return {"hay": False, "eventos": eventos}
    media = sum(mismos) / len(mismos)
    bajo, alto = min(mismos), max(mismos)
    ticket = 0.0
    cierres = list(s.scalars(select(Cierre).where(Cierre.fecha > dia - timedelta(days=28), Cierre.fecha < dia)))
    if cierres:
        ticket = sum(c.ventas_total for c in cierres) / max(1, sum(c.cubiertos for c in cierres))
    hoy_ev = [e for e in eventos if e.fecha == dia]
    return {"hay": True, "media": round(media), "bajo": round(bajo), "alto": round(alto), "n": len(mismos), "ticket": round(ticket, 2),
            "cubiertos": (round(bajo / ticket), round(alto / ticket)) if ticket else None, "eventos": eventos, "hoy_eventos": hoy_ev,
            "dia_nombre": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][dia.weekday()]}


def platos_a_empujar(s: Session, hoy: date, n=3) -> list:
    """Por margen en euros, por lo que caduca y por lo que suele venderse ese día."""
    c = carta(s, hoy)
    st = stock(s, hoy)
    caducan = {x["producto"] for x in st["caducan"]}
    vendidas_dia = defaultdict(int)
    for ci in s.scalars(select(Cierre).where(Cierre.fecha < hoy, Cierre.fecha > hoy - timedelta(days=70))):
        if ci.fecha.weekday() == hoy.weekday():
            for k, u in (ci.unidades or {}).items():
                vendidas_dia[k] += u
    out = []
    for f in c["filas"]:
        if f["parte"] != "comida":
            continue
        usa = [d["producto"] for d in f["receta"] if d["producto"] in caducan]
        puntos = f["margen"] * (2.0 if usa else 1.0) * (1 + min(vendidas_dia.get(f["nombre"], 0), 60) / 60)
        motivo = []
        if usa:
            motivo.append(f"usa {', '.join(usa).lower()}, que caduca hoy o mañana")
        motivo.append(f"deja {f['margen']:.2f} € por ración".replace(".", ","))
        if f["tipo"] == "puzle":
            motivo.append("deja mucho pero se pide poco: hay que recomendarlo")
        frase = {"puzle": f"«Os recomiendo {f['nombre'].lower()}, es de lo mejor de la casa y poca gente lo conoce.»",
                 "estrella": f"«{f['nombre']} es el plato de la casa, para compartir sale perfecto.»"}.get(f["tipo"], f"«Hoy {f['nombre'].lower()} está en su punto, ¿os lo pongo?»")
        out.append({"plato": f["nombre"], "puntos": puntos, "motivo": "; ".join(motivo), "frase": frase, "tipo": f["tipo"], "margen": f["margen"]})
    out.sort(key=lambda x: -x["puntos"])
    return out[:n]


# ---------------------------------------------------------------- personal
def _horas_en_franja(tramos: list, franja: str) -> float:
    a, b = [int(x) for x in franja.split("-")]
    total = 0.0
    for ini, fin in tramos:
        h1 = int(ini[:2]) + int(ini[3:5]) / 60
        h2 = int(fin[:2]) + int(fin[3:5]) / 60
        total += max(0.0, min(h2, b) - max(h1, a))
    return total


def personal_semana(s: Session, lunes: date) -> dict:
    empleados = {e.id: e for e in s.scalars(select(Empleado))}
    ch = coste_hora(s)
    turnos = list(s.scalars(select(Turno).where(Turno.fecha >= lunes, Turno.fecha <= lunes + timedelta(days=6))))
    cuadrante = {e.id: {} for e in empleados.values()}
    horas = defaultdict(float)
    for t in turnos:
        cuadrante[t.empleado_id][t.fecha.weekday()] = t.tramos
        horas[t.empleado_id] += sum(_horas_en_franja(t.tramos, "0-24") for _ in [0])
    avisos = []
    for t in turnos:
        if _horas_en_franja(t.tramos, "0-24") > 9:
            avisos.append(f"{empleados[t.empleado_id].nombre.split(' (')[0]} pasa de 9 h el {t.fecha.strftime('%d/%m')}.")
    for eid, h in horas.items():
        if h > 40.01:
            avisos.append(f"{empleados[eid].nombre.split(' (')[0]} pasa de 40 h esta semana ({h:.0f} h).")
    # coste frente a ventas por franja: media de los mismos días de la semana de las últimas 8 semanas
    ventas_franja = defaultdict(lambda: defaultdict(list))
    for c in s.scalars(select(Cierre).where(Cierre.fecha >= lunes - timedelta(days=56), Cierre.fecha < lunes)):
        for fr, v in (c.franjas or {}).items():
            ventas_franja[c.fecha.weekday()][fr].append(v)
    dias = []
    for wd in range(7):
        franjas = []
        for fr in FRANJAS:
            coste = sum(_horas_en_franja(cuadrante[eid].get(wd, []), fr) * ch.get(eid, 0) for eid in empleados)
            vs = ventas_franja[wd][fr]
            ventas = (sum(vs) / len(vs) / (1 + IVA_VENTAS)) if vs else 0.0
            pct = coste / ventas if ventas else None
            franjas.append({"franja": fr, "coste": round(coste, 2), "ventas": round(ventas, 2), "pct": round(pct, 2) if pct is not None else None,
                            "personas": sum(1 for eid in empleados if _horas_en_franja(cuadrante[eid].get(wd, []), fr) > 0)})
        dias.append({"wd": wd, "fecha": lunes + timedelta(days=wd), "franjas": franjas, "cerrado": not any(f["ventas"] for f in franjas) and not any(cuadrante[e].get(wd) for e in empleados)})
    sobran = [(d["fecha"], f) for d in dias for f in d["franjas"] if f["pct"] is not None and f["pct"] > 0.6 and f["coste"] > 0]
    faltan = [(d["fecha"], f) for d in dias for f in d["franjas"] if f["ventas"] > 300 and f["personas"] <= 2 and f["pct"] is not None and f["pct"] < 0.2]
    return {"empleados": list(empleados.values()), "cuadrante": cuadrante, "horas": dict(horas), "coste_hora": ch, "avisos": avisos, "dias": dias,
            "sobran": sobran, "faltan": faltan, "lunes": lunes}


# ---------------------------------------------------------------- proveedores
def proveedores(s: Session, hoy: date) -> list:
    compras = compras_por_mes(s)
    meses = sorted(compras)[-3:]
    avisos = {a.documento_id: a for a in s.scalars(select(Aviso).where(Aviso.tipo == "subida_precio"))}
    out = []
    for p in s.scalars(select(Proveedor).order_by(Proveedor.nombre)):
        por_mes = [round(compras.get(m, {"por_proveedor": {}})["por_proveedor"].get(p.nombre, 0.0), 2) for m in meses]
        subidas = [a for a in s.scalars(select(Aviso).join(Documento, Aviso.documento_id == Documento.id).where(Aviso.tipo == "subida_precio", Documento.proveedor_id == p.id))]
        out.append({"p": p, "meses": [f"{nombre_mes(m[1])}" for m in meses], "compras": por_mes, "subidas": subidas, "ultimo_mes": por_mes[-1] if por_mes else 0})
    out.sort(key=lambda x: -(x["compras"][-2] if len(x["compras"]) > 1 else x["ultimo_mes"]))
    return out


def ficha_proveedor(s: Session, prov_id: int) -> dict:
    p = s.get(Proveedor, prov_id)
    if not p:
        return {}
    docs = list(s.scalars(select(Documento).where(Documento.proveedor_id == prov_id, Documento.tipo == "factura").order_by(Documento.fecha.desc())))
    historial = defaultdict(list)
    for d in sorted(docs, key=lambda d: d.fecha or date.min):
        if d.estado == "duplicada":
            continue
        for l in d.lineas:
            if l.producto_id and l.precio_unitario:
                historial[l.producto_id].append({"fecha": d.fecha, "precio": l.precio_unitario, "doc": d.id, "numero": d.numero})
    productos = {pid: s.get(Producto, pid) for pid in historial}
    series = []
    for pid, puntos in historial.items():
        subida = None
        for i in range(1, len(puntos)):
            if puntos[i]["precio"] > puntos[i - 1]["precio"] * 1.05:
                subida = {"i": i, "antes": puntos[i - 1], "ahora": puntos[i], "pct": round((puntos[i]["precio"] / puntos[i - 1]["precio"] - 1) * 100)}
        series.append({"producto": productos[pid].nombre, "unidad": productos[pid].unidad, "puntos": puntos, "subida": subida, "codigo_mercabarna": productos[pid].codigo_mercabarna})
    series.sort(key=lambda x: (x["subida"] is None, x["producto"]))
    # mismo producto en otro proveedor
    comparaciones = []
    precios_otros = defaultdict(dict)
    for pid in historial:
        q = (select(Documento.proveedor_id, LineaDocumento.precio_unitario, Documento.fecha).join(Documento)
             .where(LineaDocumento.producto_id == pid, Documento.proveedor_id != prov_id, Documento.estado != "duplicada").order_by(Documento.fecha))
        for opid, precio, fecha in s.execute(q):
            precios_otros[pid][opid] = (precio, fecha)
    for pid, otros in precios_otros.items():
        mio = historial[pid][-1]["precio"]
        for opid, (precio, fecha) in otros.items():
            comparaciones.append({"producto": productos[pid].nombre, "mio": mio, "otro": s.get(Proveedor, opid).nombre, "otro_precio": precio, "fecha": fecha,
                                  "diferencia_pct": round((mio / precio - 1) * 100) if precio else None})
    compras = compras_por_mes(s)
    meses = sorted(compras)[-3:]
    return {"p": p, "facturas": docs, "series": series, "comparaciones": comparaciones,
            "compras": [(f"{nombre_mes(m[1])}", round(compras[m]["por_proveedor"].get(p.nombre, 0.0), 2)) for m in meses]}


def hoy_demo(s: Session) -> date:
    return ajuste(s, "hoy_demo", date.today())
