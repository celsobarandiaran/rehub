"""El asistente: un chat en castellano que responde con los datos del propio restaurante.

Solo responde y propone; no cambia ningún dato. Cada respuesta dice de qué pantalla sale.
Sin IA (o con el tope agotado) contesta con los datos de la pantalla que mejor encaja.
"""
import re
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import calculos, catalogo, config, ia, perfiles, vistas
from .db import Charla, Cierre, Competidor, Correo, Documento, Empleado, Proveedor

EJEMPLOS = ["¿Cuánto vendí el sábado pasado?", "¿Qué proveedor me ha subido más los precios este año?", "¿Qué platos quito de la carta?",
            "¿Me llega la caja para pagar el alquiler el día 5?", "¿Qué caduca mañana?", "¿Cómo subo un extracto del banco?"]

PANTALLAS = {"bandeja": "Bandeja", "documentos": "Documentos", "proveedores": "Proveedores", "recepcion": "Recepción", "hoy": "Hoy", "cuadro": "Cuadro del día",
             "carta": "Carta", "competencia": "Competencia", "personal": "Personal", "dueno": "Dueño", "ajustes": "Ajustes", "ayuda": "Cómo se usa"}

MANUAL = """CÓMO SE USA LA APP (pantalla "ayuda"):
- Subir un extracto del banco: Ajustes → "Subir extracto del banco" (archivo Norma 43 o CSV del banco). La app casa cada cargo con su factura y las marca como pagadas.
- Subir una factura, un ticket o una foto a mano: Ajustes → "Subir PDF o foto", o en Recepción con los botones "Foto del albarán" y "Foto de etiqueta".
- Leer el correo ahora: Bandeja → "Revisar correo". Los correos se leen solos cada minuto.
- Responder a un cliente: Bandeja → abrir el correo → revisar la respuesta propuesta → "Enviar". Nada se envía sin pulsar Enviar.
- Cambiar el precio o la receta de un plato: Carta → pulsar el plato → cambiar y "Guardar". Añadir una receta: Carta → Recetas → "Añadir receta".
- Recuento de la cámara: Recepción → "Recuento de la cámara" → escribir lo contado → "Guardar recuento".
- Cambiar un turno: Personal → pulsar la casilla del día → escribir las horas.
- Apuntar el efectivo contado: Cuadro del día → "Efectivo contado" → se ve el descuadre.
- Añadir un competidor: Competencia → "Añadir competidor" (nombre, distancia, valoración y foto de su carta).
- Cargar o reiniciar la demo, enviar los correos de prueba, autodestruir: Ajustes.
- Días de apertura, caja mínima, fondo de caja: Ajustes."""


def _d(x: date | None) -> str:
    return x.strftime("%d/%m/%Y") if x else "—"


def _dia(x: date) -> str:
    return ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][x.weekday()]


def contexto(s: Session, hoy: date, perfil: str) -> str:
    """Los datos de todas las pantallas, resumidos, con el id de la pantalla delante de cada bloque."""
    L = [f"Restaurante: {config.NOMBRE_RESTAURANTE}. Hoy es {_dia(hoy)} {_d(hoy)}. Todo el análisis va sin IVA salvo ventas de caja y banco (con IVA).", ""]
    ver = lambda dato: perfiles.puede_ver(perfil, dato)  # noqa: E731
    # Cuadro del día: últimos cierres
    L.append("PANTALLA cuadro (Cuadro del día: cierres de caja con IVA):")
    for c in s.scalars(select(Cierre).where(Cierre.fecha <= hoy).order_by(Cierre.fecha.desc()).limit(14)):
        desc = f", efectivo contado {c.efectivo_contado:.2f} €" if c.efectivo_contado is not None else ""
        L.append(f"- {_dia(c.fecha)} {_d(c.fecha)}: ventas {c.ventas_total:.2f} € ({c.cubiertos} cubiertos; tarjeta {c.tarjeta:.2f}, efectivo {c.efectivo:.2f}{desc})")
    vpm = calculos.ventas_por_mes(s)
    for m in sorted(vpm):
        v = vpm[m]
        L.append(f"- Mes {calculos.nombre_mes(m[1])} {m[0]}: ventas {v['con_iva']:.2f} € con IVA ({v['sin_iva']:.2f} sin IVA), {v['cubiertos']} cubiertos, {v['dias']} días abiertos")
    # Dueño
    if ver("costes_y_margenes"):
        d = calculos.dueno(s, hoy)
        L.append("\nPANTALLA dueno (Dueño: cómo va el negocio, sin IVA):")
        if not d.get("sin_datos"):
            for m in d["meses"]:
                cm = m["comida"]
                L.append(f"- {m['nombre']}: ventas {m['ventas']:.2f} €, coste de comida real {cm['real']:.2f} € ({(cm['pct_real'] or 0) * 100:.1f} %; teórico {cm['teorico']:.2f} €), "
                         f"personal {m['personal']:.2f} € ({(m['pct_personal'] or 0) * 100:.1f} %), local {m['local']:.2f} €, otros fijos {m['otros']:.2f} €, beneficio antes del sueldo del dueño {m['beneficio']:.2f} €")
            pe = d["punto_equilibrio"]
            L.append(f"- Punto de equilibrio: {pe['dia'] or 0:.2f} €/día sin IVA ({pe['mes'] or 0:.2f} €/mes) abriendo {d['dias_apertura']} días; media real {pe['media_dia'] or 0:.2f} €/día")
    if ver("banco"):
        b = calculos.banco(s, hoy)
        caja = calculos.caja_30_dias(s, hoy)
        if b["hay"]:
            L.append(f"- Banco: saldo {b['saldo']:.2f} € el {_d(b['fecha'])}. Caja a 30 días: punto más bajo {caja['minimo_val']:.2f} € el {_d(caja['minimo_dia'])} (mínimo deseado {caja['minimo']:.0f} €); dentro de 30 días {caja['final']:.2f} €")
            for p in caja["pagos"][:12]:
                L.append(f"  · pago el {_d(p['dia'])}: {p['concepto']} {p['importe']:.2f} €{' (aprox.)' if p['aprox'] else ''}")
    # Hoy
    L.append("\nPANTALLA hoy (Hoy: avisos, caducidades, previsión):")
    for a in vistas.avisos(s, hoy, 8):
        L.append(f"- Aviso {_d(a.fecha)} [{a.titulo}]: {a.texto}")
    st = calculos.stock(s, hoy)
    for c in st["caducan"]:
        L.append(f"- Caduca {c['cuando']} ({_d(c['caduca'])}): {c['producto']}, quedan {c['queda']} {c['unidad']} ({'estimada' if c['estimada'] else 'etiqueta'})")
    for f in calculos.faltas(s, hoy):
        L.append(f"- Se acaba: {f['producto']}, quedan {f['queda']} {f['unidad']}, para {f['dias']} días; pedir a {f['proveedor'] or 'su proveedor'}")
    pv = calculos.prevision(s, hoy)
    if pv["hay"]:
        L.append(f"- Previsión de hoy: entre {pv['bajo']} y {pv['alto']} € con IVA (un {pv['dia_nombre']} normal da {pv['media']} €)")
    for e in pv["eventos"]:
        L.append(f"- Evento {_d(e.fecha)}: {e.nombre} ({e.efecto})")
    for e in calculos.platos_a_empujar(s, hoy):
        L.append(f"- Plato a empujar hoy: {e['plato']} ({e['motivo']})")
    # Recepción
    L.append("\nPANTALLA recepcion (Recepción: lo que hay en cámara, stock teórico):")
    for f in st["filas"][:15]:
        L.append(f"- {f['producto']}: quedan {f['queda']} {f['unidad']}" + (f" ({f['valor']:.2f} €)" if ver("precios_compra") else ""))
    L.append(f"- Mermas del mes (caducado sin vender): {st['mermas_mes']:.2f} €")
    # Proveedores
    if ver("precios_compra"):
        L.append("\nPANTALLA proveedores (Proveedores: compras sin IVA de los últimos 3 meses y subidas de precio):")
        pr = calculos.proveedores(s, hoy)
        for x in pr["todos"]:
            sub = "; ".join(a.texto for a in x["subidas"][:2])
            L.append(f"- {x['p'].nombre} ({catalogo.NOMBRE_FAMILIA[calculos.familia_proveedor(x['p'])][2:]}; {x['suministra']}): {x['total']:.2f} € en {x['n_facturas']} facturas"
                     + (f". Subidas: {sub}" if sub else "") + (f". Tel. {x['p'].telefono}" if x['p'].telefono else ""))
    # Carta
    if ver("costes_y_margenes"):
        c = calculos.carta(s, hoy)
        L.append("\nPANTALLA carta (Carta: precio de carta con IVA, coste y lo que deja por unidad sin IVA, unidades vendidas en 3 meses, color):")
        for f in c["filas"]:
            L.append(f"- {f['nombre']} [{f['categoria']}]: carta {f['precio_carta']:.2f} €, coste {f['coste']:.2f} €, deja {f['margen']:.2f} € ({f['margen_pct'] * 100:.0f} %), {f['unidades']} vendidos, color {f['color']} ({f['que_hacer']}); competencia: {f['comp_texto']}")
        L.append("- Verde = vende mucho y deja mucho (mantener); azul = vende mucho y deja poco (subir precio o bajar coste); amarillo = deja mucho y vende poco (darle visibilidad); rojo = vende poco y deja poco (cambiar o quitar).")
        if c["ellos"]:
            L.append("- Tienen ellos y tú no: " + "; ".join(f"{e['clave']} ({e['texto']})" for e in c["ellos"][:8]))
    # Competencia
    L.append("\nPANTALLA competencia (Competencia: cartas públicas de los restaurantes de al lado, precios con IVA):")
    for comp in s.scalars(select(Competidor).order_by(Competidor.distancia_m)):
        L.append(f"- {comp.nombre}: a {comp.distancia_m} m, valoración {comp.valoracion or '—'}, {len(comp.carta)} productos; carta leída el {_d(comp.leida)}")
    # Personal
    L.append("\nPANTALLA personal (Personal: horarios y coste frente a ventas por franja):")
    lunes = hoy - timedelta(days=hoy.weekday())
    ps = calculos.personal_semana(s, lunes)
    for e in ps["empleados"]:
        ch = f", coste {ps['coste_hora'].get(e.id, 0):.2f} €/hora" if ver("salarios_por_persona") else ""
        L.append(f"- {e.nombre} ({e.puesto}): {ps['horas'].get(e.id, 0):.0f} h esta semana{ch}")
    for a in ps["avisos"]:
        L.append(f"- Aviso: {a}")
    for f, fr in ps["sobran"][:4]:
        L.append(f"- Sobran manos el {_dia(f)} {_d(f)} de {fr['franja']} h: personal {fr['coste']:.0f} € frente a ventas {fr['ventas']:.0f} €")
    for f, fr in ps["faltan"][:4]:
        L.append(f"- Faltan manos el {_dia(f)} {_d(f)} de {fr['franja']} h: {fr['personas']} personas para {fr['ventas']:.0f} € de ventas")
    # Documentos
    L.append("\nPANTALLA documentos (Documentos: facturas, gastos, nóminas y cierres archivados):")
    for tipo, n in s.execute(select(Documento.tipo, func.count()).group_by(Documento.tipo)):
        L.append(f"- {n} documentos de tipo {tipo}")
    for d in s.scalars(select(Documento).where(Documento.estado == "revisar").limit(6)):
        L.append(f"- Para revisar: {d.tipo} {d.numero or ''} de {d.proveedor.nombre if d.proveedor else (d.datos or {}).get('comercio', '')} ({d.motivo_revisar})")
    for d in s.scalars(select(Documento).where(Documento.tipo == "factura", Documento.pagado_fecha.is_(None), Documento.estado != "duplicada", Documento.vencimiento.is_not(None)).order_by(Documento.vencimiento).limit(8)):
        L.append(f"- Pendiente de pago: {d.proveedor.nombre if d.proveedor else ''} {d.numero} {d.total or 0:.2f} € vence el {_d(d.vencimiento)}")
    # Bandeja
    L.append("\nPANTALLA bandeja (Bandeja: correos leídos y clasificados):")
    for cat, n in s.execute(select(Correo.categoria, func.count()).group_by(Correo.categoria)):
        L.append(f"- {n} correos de tipo {cat}")
    for c in s.scalars(select(Correo).order_by(Correo.recibido.desc()).limit(10)):
        L.append(f"- {c.recibido.strftime('%d/%m %H:%M')} {c.remitente}: «{c.asunto}» ({c.categoria}{'; respuesta lista' if c.respuesta_propuesta and not c.respuesta_enviada else ''})")
    L.append("\n" + MANUAL)
    return "\n".join(L)


def _sin_ia(pregunta: str, ctx: str) -> tuple[str, str]:
    """Sin IA: elige la pantalla por palabras clave y devuelve sus primeras líneas."""
    q = pregunta.lower()
    reglas = [("ayuda", r"cómo|como (subo|cambio|pongo|hago|añado|anado)|dónde|donde"), ("cuadro", r"vend|caja de|cierre|cubiertos|efectivo"), ("dueno", r"benefici|gano|equilibrio|banco|caja|alquiler|pagar|llega"),
              ("hoy", r"caduc|aviso|hoy|previs|empuj|recomend"), ("proveedores", r"proveedor|subido|precio|compr|pedir|acaba"), ("carta", r"plato|carta|quito|margen|deja|receta|cuesta"),
              ("personal", r"personal|turno|horario|empleado|camarer|cocin"), ("competencia", r"competen|al lado|cerca"), ("bandeja", r"correo|reserva|queja|cliente"),
              ("documentos", r"factura|documento|nómina|nomina|pendiente")]
    pantalla = next((p for p, patron in reglas if re.search(patron, q)), "hoy")
    marca = "PANTALLA " + pantalla if pantalla != "ayuda" else "CÓMO SE USA"
    i = ctx.find(marca)
    bloque = ctx[i:].split("\n\nPANTALLA", 1)[0] if i >= 0 else ""
    lineas = [l for l in bloque.split("\n")[1:] if l.strip()][:8]
    texto = "La IA no está disponible ahora mismo, así que te dejo los datos tal cual de la pantalla " + PANTALLAS[pantalla] + ":\n" + "\n".join(lineas)
    return texto, pantalla


def responder(s: Session, pregunta: str, pantalla_actual: str, hoy: date, perfil: str) -> dict:
    pregunta = pregunta.strip()[:500]
    ctx = contexto(s, hoy, perfil)
    sin_ia = False
    try:
        r = ia.preguntar_json(
            "Eres el asistente de ReHub, la oficina de un restaurante. Responde en castellano, cercano y sin tecnicismos, en 2 a 6 frases, con cifras en euros y fechas concretas. "
            "Usa SOLO los datos de abajo; si el dato no está, di claramente que no lo tienes y en qué pantalla se podría mirar o apuntar. No inventes. "
            "Nunca cambies nada ni digas que lo has cambiado: solo respondes y propones; si el usuario quiere cambiar algo, dile en qué pantalla y botón se hace. "
            f"El usuario está mirando la pantalla '{pantalla_actual}'. Devuelve JSON con 'respuesta' y 'fuente' (el id de la pantalla de donde sale el dato principal: "
            + ", ".join(PANTALLAS) + ").\n\nPREGUNTA: " + pregunta + "\n\nDATOS:\n" + ctx,
            {"type": "OBJECT", "properties": {"respuesta": {"type": "STRING"}, "fuente": {"type": "STRING", "enum": list(PANTALLAS)}}, "required": ["respuesta", "fuente"]})
        texto, fuente = r["respuesta"].strip(), r.get("fuente") or pantalla_actual
    except (ia.SinIA, ia.CuotaAgotada, ValueError, KeyError):
        texto, fuente = _sin_ia(pregunta, ctx)
        sin_ia = True
    except Exception as e:  # red caída, etc.
        texto, fuente = _sin_ia(pregunta, ctx)
        texto = texto.replace("La IA no está disponible ahora mismo", f"La IA ha fallado ({type(e).__name__})")
        sin_ia = True
    if fuente not in PANTALLAS:
        fuente = pantalla_actual if pantalla_actual in PANTALLAS else "hoy"
    ch = Charla(pantalla=pantalla_actual, pregunta=pregunta, respuesta=texto, fuente=fuente, sin_ia=sin_ia)
    s.add(ch)
    s.commit()
    return {"respuesta": texto, "fuente": fuente, "fuente_nombre": PANTALLAS[fuente], "enlace": "/p/ajustes" if fuente == "ayuda" else f"/p/{fuente}",
            "sin_ia": sin_ia, "id": ch.id}


def historial(s: Session, limite=40) -> list:
    return list(s.scalars(select(Charla).order_by(Charla.id.desc()).limit(limite)))
