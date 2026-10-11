"""Dibuja todos los archivos de la demo en datos_demo/ a partir de modelo_demo.py.

Uso:  python herramientas/generar_demo.py
Crea PDF de facturas, nóminas y cierres; fotos de facturas escaneadas, tickets y
etiquetas; correos; extracto del banco (Norma 43 y CSV); la carta; y un índice.
También guarda verdad.json con los datos correctos, para comprobar que la app
los saca bien.
"""
import csv
import json
import math
import shutil
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import modelo_demo as m  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos_demo"
FUENTE = "C:/Windows/Fonts/arial.ttf"
FUENTE_N = "C:/Windows/Fonts/arialbd.ttf"
FUENTE_M = "C:/Windows/Fonts/consola.ttf"


def eur(x):
    s = f"{abs(x):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-" if x < 0 else "") + s


def num(x):
    return (f"{x:.3f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)).replace(".", ",")


def fecha_es(d):
    return d.strftime("%d/%m/%Y")


def nombre_archivo(d, quien, total, ext):
    return f"{d.isoformat()} {quien} {eur(total)}.{ext}"


# ---------------------------------------------------------------- PDF de factura
class PDF(FPDF):
    def __init__(self):
        super().__init__(format="A4")
        self.add_font("A", "", FUENTE)
        self.add_font("A", "B", FUENTE_N)
        self.set_auto_page_break(True, 15)


def pdf_factura(f: m.Factura, ruta: Path):
    info = m.PROVEEDORES[f.proveedor]
    pdf = PDF()
    pdf.add_page()
    estilo = info["estilo"]
    color = {1: (31, 77, 58), 2: (44, 79, 158), 3: (120, 70, 30)}[estilo]
    pdf.set_text_color(*color)
    pdf.set_font("A", "B", 18)
    pdf.cell(0, 10, f.proveedor.upper() if estilo == 2 else f.proveedor, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(60, 60, 60)
    pdf.set_font("A", "", 9)
    pdf.multi_cell(0, 4.5, f"{info['dir']}\nCIF: {info['cif']}" + (f"  ·  Tel. {info['tel']}" if info["tel"] else "") + f"\n{info['correo']}")
    pdf.ln(4)
    pdf.set_font("A", "B", 14)
    pdf.set_text_color(0, 0, 0)
    titulo = "FACTURA" if estilo != 3 else "Factura simplificada"
    pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "", 10)
    etiquetas = {1: ("Nº factura", "Fecha", "Vencimiento"), 2: ("Número", "Fecha de emisión", "Fecha de vencimiento"), 3: ("Factura nº", "Fecha", "Pago")}[estilo]
    venc = fecha_es(f.vence) if f.forma_pago != "efectivo" else "al contado"
    pdf.cell(95, 6, f"{etiquetas[0]}: {f.numero}")
    pdf.cell(0, 6, f"Cliente: {m.RESTAURANTE['razon']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"{etiquetas[1]}: {fecha_es(f.fecha)}")
    pdf.cell(0, 6, f"CIF cliente: {m.RESTAURANTE['cif']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"{etiquetas[2]}: {venc}")
    pdf.cell(0, 6, m.RESTAURANTE["direccion"], new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("A", "B", 9)
    pdf.set_fill_color(235, 235, 230)
    anchos = (78, 22, 18, 26, 18, 28)
    for t, w in zip(("Concepto", "Cantidad", "Unidad", "Precio", "IVA", "Importe"), anchos):
        pdf.cell(w, 7, t, border="B", fill=True, align="L" if t in ("Concepto", "Unidad") else "R")
    pdf.ln()
    pdf.set_font("A", "", 9)
    for l in f.lineas:
        pdf.cell(anchos[0], 6, l.producto[:44])
        pdf.cell(anchos[1], 6, num(l.cantidad), align="R")
        pdf.cell(anchos[2], 6, l.unidad)
        pdf.cell(anchos[3], 6, eur(l.precio) + " €", align="R")
        pdf.cell(anchos[4], 6, f"{round(l.iva * 100)} %", align="R")
        pdf.cell(anchos[5], 6, eur(l.importe) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("A", "", 10)
    x = 110
    for tipo, (b, c) in f.ivas.items():
        pdf.set_x(x)
        pdf.cell(55, 6, f"Base imponible {round(tipo * 100)} %")
        pdf.cell(25, 6, eur(b) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x)
        pdf.cell(55, 6, f"IVA {round(tipo * 100)} %" if tipo else "Exento de IVA")
        pdf.cell(25, 6, eur(c) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x)
    pdf.set_font("A", "B", 12)
    pdf.cell(55, 8, "TOTAL")
    pdf.cell(25, 8, eur(f.total) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("A", "", 8)
    pdf.set_text_color(110, 110, 110)
    pago = "Pago al contado." if f.forma_pago == "efectivo" else "Forma de pago: recibo domiciliado al vencimiento."
    pdf.multi_cell(0, 4, pago + "\nDocumento de ejemplo generado para la demo de ReHub. Empresa y datos inventados.")
    pdf.output(str(ruta))


def img_factura_escaneada(f: m.Factura, ruta: Path, numero_ilegible=False):
    """Factura en papel, fotografiada: un poco torcida, con sombra y grano."""
    W, H = 1240, 1754
    im = Image.new("RGB", (W, H), (250, 248, 240))
    d = ImageDraw.Draw(im)
    fb, fn, fm_ = ImageFont.truetype(FUENTE_N, 46), ImageFont.truetype(FUENTE, 30), ImageFont.truetype(FUENTE_M, 28)
    info = m.PROVEEDORES[f.proveedor]
    y = 80
    d.text((80, y), "HORTALIZAS DEL PRAT", font=fb, fill=(40, 40, 40)); y += 70
    d.text((80, y), info["dir"], font=fn, fill=(70, 70, 70)); y += 40
    d.text((80, y), f"CIF {info['cif']}  ·  Tel. {info['tel']}", font=fn, fill=(70, 70, 70)); y += 80
    d.text((80, y), "FACTURA", font=fb, fill=(20, 20, 20))
    d.text((640, y + 8), "Nº " + ("H?-3▒▒" if numero_ilegible else f.numero), font=fn, fill=(20, 20, 20)); y += 70
    d.text((80, y), f"Fecha: {fecha_es(f.fecha)}", font=fn, fill=(20, 20, 20))
    d.text((640, y), f"Cliente: {m.RESTAURANTE['nombre']}", font=fn, fill=(20, 20, 20)); y += 80
    d.line((80, y, W - 80, y), fill=(60, 60, 60), width=3); y += 20
    d.text((80, y), "Producto            Cant.   Ud.    Precio   Importe", font=fm_, fill=(30, 30, 30)); y += 45
    d.line((80, y, W - 80, y), fill=(120, 120, 120), width=1); y += 15
    for l in f.lineas:
        d.text((80, y), f"{l.producto[:18]:18s} {num(l.cantidad):>6s} {l.unidad[:6]:6s} {eur(l.precio):>7s} {eur(l.importe):>9s}", font=fm_, fill=(30, 30, 30))
        y += 44
    y += 30
    b, c = f.ivas[0.04]
    for t, v in (("Base 4 %", b), ("IVA 4 %", c), ("TOTAL", f.total)):
        d.text((640, y), f"{t:10s} {eur(v):>10s} €", font=fb if t == "TOTAL" else fm_, fill=(20, 20, 20)); y += 52
    d.text((80, H - 160), "Pagado al contado. Gracias.", font=fn, fill=(90, 90, 90))
    d.text((80, H - 110), "Documento de ejemplo para la demo de ReHub (inventado).", font=ImageFont.truetype(FUENTE, 22), fill=(140, 140, 140))
    im = im.rotate(-1.6, expand=True, fillcolor=(90, 85, 75), resample=Image.BICUBIC)
    fondo = Image.new("RGB", (im.width + 60, im.height + 60), (95, 88, 78))
    fondo.paste(im, (30, 30))
    sombra = Image.linear_gradient("L").resize(fondo.size).rotate(90)
    fondo = Image.composite(fondo, Image.new("RGB", fondo.size, (60, 55, 50)), sombra.point(lambda v: 200 + v // 5))
    fondo = fondo.filter(ImageFilter.GaussianBlur(0.8)).resize((fondo.width // 2, fondo.height // 2))
    fondo.save(ruta, quality=72)


# ---------------------------------------------------------------- tickets y etiquetas
def img_ticket(g: m.Gasto, ruta: Path):
    W = 560
    alto = 520 + 46 * len(g.lineas)
    im = Image.new("RGB", (W, alto), (252, 252, 247))
    d = ImageDraw.Draw(im)
    f, fb = ImageFont.truetype(FUENTE_M, 26), ImageFont.truetype(FUENTE_N, 30)
    y = 30
    d.text((W // 2, y), g.comercio.upper(), font=fb, fill=(20, 20, 20), anchor="ma"); y += 50
    d.text((W // 2, y), "Barcelona · NIF B-0000000 (ej.)", font=f, fill=(40, 40, 40), anchor="ma"); y += 50
    d.text((40, y), f"Fecha: {fecha_es(g.fecha)}   {['09:12', '11:40', '12:05', '17:30'][g.fecha.day % 4]}", font=f, fill=(20, 20, 20)); y += 38
    d.text((40, y), f"Ticket: {g.numero}", font=f, fill=(20, 20, 20)); y += 40
    d.line((30, y, W - 30, y), fill=(80, 80, 80), width=2); y += 20
    for nombre, c, p in g.lineas:
        d.text((40, y), f"{c} x {nombre[:22]}", font=f, fill=(20, 20, 20))
        d.text((W - 40, y), eur(c * p), font=f, fill=(20, 20, 20), anchor="ra"); y += 46
    d.line((30, y, W - 30, y), fill=(80, 80, 80), width=2); y += 20
    d.text((40, y), "TOTAL EUR", font=fb, fill=(10, 10, 10))
    d.text((W - 40, y), eur(g.total), font=fb, fill=(10, 10, 10), anchor="ra"); y += 60
    d.text((40, y), "IVA incluido · EFECTIVO", font=f, fill=(30, 30, 30)); y += 50
    d.text((W // 2, y), "Gracias por su visita", font=f, fill=(60, 60, 60), anchor="ma")
    im = im.rotate(2.5 if g.fecha.day % 2 else -3, expand=True, fillcolor=(120, 110, 95), resample=Image.BICUBIC)
    fondo = Image.new("RGB", (im.width + 80, im.height + 80), (128, 116, 100))
    fondo.paste(im, (40, 40))
    fondo.filter(ImageFilter.GaussianBlur(0.6)).save(ruta, quality=70)


def img_etiqueta(prov, prod, peso, lote, envasado, caduca, ruta: Path):
    W, H = 900, 560
    im = Image.new("RGB", (W, H), (250, 250, 250))
    d = ImageDraw.Draw(im)
    fb, f, fm_ = ImageFont.truetype(FUENTE_N, 48), ImageFont.truetype(FUENTE, 32), ImageFont.truetype(FUENTE_M, 34)
    d.rectangle((10, 10, W - 10, H - 10), outline=(40, 40, 40), width=4)
    d.text((40, 35), prod.upper(), font=fb, fill=(10, 10, 10))
    d.text((40, 105), prov, font=f, fill=(50, 50, 50))
    filas = [("Peso neto", f"{num(peso)} kg"), ("Lote", lote), ("Envasado", fecha_es(envasado)), ("Fecha de caducidad", fecha_es(caduca))]
    y = 175
    for k, v in filas:
        d.text((40, y), k + ":", font=f, fill=(40, 40, 40))
        d.text((420, y), v, font=fm_ if k != "Fecha de caducidad" else fb, fill=(10, 10, 10))
        y += 70 if k != "Envasado" else 80
    d.text((40, H - 70), "Consérvese entre 0 y 4 °C · Ejemplo para la demo (inventado)", font=ImageFont.truetype(FUENTE, 24), fill=(90, 90, 90))
    for i in range(36):
        d.rectangle((600 + i * 7, 40, 603 + i * 7, 120), fill=(0, 0, 0) if (i * 7) % 3 else (250, 250, 250))
    im = im.rotate(-4, expand=True, fillcolor=(170, 190, 200), resample=Image.BICUBIC)
    fondo = Image.new("RGB", (im.width + 120, im.height + 120), (180, 200, 210))
    fondo.paste(im, (60, 60))
    fondo.filter(ImageFilter.GaussianBlur(1.0)).save(ruta, quality=70)


# ---------------------------------------------------------------- nóminas y cierres
def pdf_nomina(n, ruta: Path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("A", "B", 15)
    pdf.cell(0, 9, "RECIBO INDIVIDUAL DE SALARIOS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "", 10)
    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    pdf.multi_cell(0, 5.5, f"Empresa: {m.RESTAURANTE['razon']} · CIF {m.RESTAURANTE['cif']}\nTrabajador/a: {n['empleado']}\n"
                           f"Categoría: {n['puesto']} · Convenio de hostelería de Cataluña (ejemplo)\n"
                           f"Periodo de liquidación: {meses[n['mes']]} de {n['anio']} (del 1 al {n['fecha'].day})\nElaborado por: Gestoría Albà (inventada)")
    pdf.ln(4)
    sb = round(n["bruto"] * 0.82, 2)
    filas = [("Salario base", sb), ("Plus convenio", round(n["bruto"] * 0.10, 2)), ("Prorrata pagas extra", round(n["bruto"] - sb - round(n["bruto"] * 0.10, 2), 2))]
    pdf.set_font("A", "B", 10)
    pdf.cell(120, 7, "Devengos", border="B")
    pdf.cell(0, 7, "Importe", border="B", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "", 10)
    for k, v in filas:
        pdf.cell(120, 6, k)
        pdf.cell(0, 6, eur(v) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "B", 10)
    pdf.cell(120, 7, "TOTAL DEVENGADO (bruto)")
    pdf.cell(0, 7, eur(n["bruto"]) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    ss = round(n["bruto"] * 0.0635, 2)
    irpf = round(n["irpf_y_ss_trabajador"] - ss, 2)
    pdf.cell(120, 7, "Deducciones", border="B")
    pdf.cell(0, 7, "", border="B", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "", 10)
    for k, v in (("Cotización a la Seguridad Social (6,35 %)", ss), ("Retención IRPF", irpf)):
        pdf.cell(120, 6, k)
        pdf.cell(0, 6, eur(v) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("A", "B", 12)
    pdf.cell(120, 8, "LÍQUIDO A PERCIBIR")
    pdf.cell(0, 8, eur(n["neto"]) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("A", "", 9)
    pdf.cell(120, 6, "Aportación de la empresa a la Seguridad Social")
    pdf.cell(0, 6, eur(n["ss_empresa"]) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(120, 6, "Coste total para la empresa")
    pdf.cell(0, 6, eur(n["coste_empresa"]) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4, "Documento de ejemplo para la demo de ReHub. Persona y datos inventados.")
    pdf.output(str(ruta))


def pdf_cierre(c: m.CierreTPV, ruta: Path):
    pdf = FPDF(format=(80, 297))
    pdf.add_font("M", "", FUENTE_M)
    pdf.set_margins(4, 4)
    pdf.add_page()
    pdf.set_font("M", "", 8)
    dias_s = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    txt = [m.RESTAURANTE["nombre"].upper(), "INFORME Z · CIERRE DE CAJA", f"Nº {c.numero}", f"{dias_s[c.fecha.weekday()]} {fecha_es(c.fecha)}", "-" * 34,
           f"{'VENTAS TOTALES':20s}{eur(c.total):>13s}", f"{'  Tarjeta':20s}{eur(c.tarjeta):>13s}", f"{'  Efectivo':20s}{eur(c.efectivo):>13s}",
           f"{'Base imponible 10%':20s}{eur(round(c.total / 1.1, 2)):>13s}", f"{'IVA 10%':20s}{eur(round(c.total - c.total / 1.1, 2)):>13s}",
           f"{'Cubiertos':20s}{c.cubiertos:>13d}", "-" * 34, "VENTAS POR FRANJA"]
    txt += [f"  {k:18s}{eur(v):>13s}" for k, v in c.franjas.items()]
    txt += ["-" * 34, "UNIDADES POR ARTÍCULO"]
    txt += [f"  {k[:24]:24s}{u:>7d}" for k, u in sorted(c.unidades.items(), key=lambda x: -x[1])]
    txt += ["-" * 34, "Documento de ejemplo (inventado)"]
    for t in txt:
        pdf.cell(0, 4, t, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(ruta))


def pdf_carta_competidor(comp, ruta: Path):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("A", "B", 20)
    pdf.cell(0, 12, comp["nombre"].replace(" (inventado)", "").replace(" (inventada)", ""), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("A", "", 9)
    pdf.cell(0, 6, "Carta (ejemplo inventado para la demo de ReHub)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    nombres = {"arroz negro": "Arròs negre", "calamares": "Calamares a la romana", "bravas": "Bravas de la casa", "entrecot": "Entrecot de ternera",
               "croquetas": "Croquetas de jamón", "crema catalana": "Crema catalana", "mejillones": "Mejillones al vapor", "gambas": "Gambas al ajillo",
               "jamón": "Jamón ibérico", "pan con tomate": "Pa amb tomàquet", "tortilla": "Tortilla española", "paella": "Paella de marisco",
               "caña": "Caña", "copa vino": "Copa de vino tinto", "agua": "Agua mineral", "refresco": "Refrescos", "café": "Café", "café con leche": "Cortado / café con leche",
               "gin tonic": "Gin tonic", "pulpo": "Pulpo a la gallega", "menú del día": "Menú del día (lun-vie)", "huevos estrellados": "Huevos estrellados"}
    pdf.set_font("A", "", 12)
    for k, p in comp["carta"].items():
        pdf.cell(150, 8, nombres.get(k, k.capitalize()))
        pdf.cell(0, 8, eur(p) + " €", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(ruta))


# ---------------------------------------------------------------- banco
def movimientos_banco(facturas, cierres, gastos, nominas, saldo_inicial):
    mov = []

    def add(d, concepto, importe, tipo, ref=""):
        mov.append({"fecha": d, "concepto": concepto, "importe": round(importe, 2), "tipo": tipo, "ref": ref})

    for c in cierres:  # la tarjeta llega al día siguiente
        add(c.fecha + timedelta(days=1), f"ABONO TPV {fecha_es(c.fecha)}", c.tarjeta, "abono_tarjeta", str(c.numero))
    por_mes = defaultdict(float)
    for c in cierres:
        por_mes[c.fecha.month] += c.tarjeta
    for mes, t in por_mes.items():
        d = date(2026, mes + 1, 1)
        if d <= m.FIN:
            add(d, "COMISIONES TPV DATAFONO", -round(t * 0.003, 2), "recibo_sin_factura")
    # efectivo: ingreso los martes de lo cobrado la semana anterior (menos gastos y verdura pagados en efectivo)
    semana = defaultdict(float)
    for c in cierres:
        semana[c.fecha - timedelta(days=c.fecha.weekday())] += c.efectivo_contado
    for g in gastos:
        semana[g.fecha - timedelta(days=g.fecha.weekday())] -= g.total
    for f in facturas:
        if f.forma_pago == "efectivo":
            semana[f.fecha - timedelta(days=f.fecha.weekday())] -= f.total
    for lunes, t in semana.items():
        d = lunes + timedelta(days=8)
        if d <= m.FIN and t > 0:
            add(d, "INGRESO EFECTIVO EN OFICINA", round(t, 2), "ingreso_efectivo")
    for f in facturas:
        if f.duplicada_de or f.forma_pago == "efectivo":
            continue
        if f.fecha.month == 8 and (f.vence - f.fecha).days >= 28:
            # recibos de las facturas de julio (anteriores a la demo), que vencen en agosto
            add(f.fecha + timedelta(days=(f.vence - f.fecha).days - 31), f"RECIBO {f.proveedor.upper()} FACTURA JULIO", -f.total, "pago_factura_anterior")
        if f.vence <= m.FIN:
            f.pagada = f.vence
            add(f.vence, f"RECIBO {f.proveedor.upper()} {f.numero}", -f.total, "pago_factura", f.numero)
    for mes in (8, 9):
        ultimo = date(2026, mes + 1, 1) - timedelta(days=1)
        for n in nominas:
            if n["mes"] == mes:
                add(ultimo, f"TRANSF. NOMINA {n['empleado'].split(' (')[0].upper()}", -n["neto"], "nomina")
        anterior = [n for n in nominas if n["mes"] == mes - 1]
        add(ultimo, "TGSS SEGURIDAD SOCIAL", -round(sum(n["ss_empresa"] + n["bruto"] * 0.0635 for n in anterior), 2), "seguridad_social")
        add(ultimo, "CUOTA AUTONOMOS RETA", -315.00, "recibo_sin_factura")
    for mes in (8, 9, 10):
        add(date(2026, mes, 5), "RECIBO SEGURIDAD 24 ALARMA", -28.60, "recibo_sin_factura")
        add(date(2026, mes, 1), "TRASPASO A CUENTA PERSONAL DEL TITULAR", -2500.00, "retirada_dueno")
        add(date(2026, mes, 10), "PRESTAMO ICO CUOTA MENSUAL", -1200.00, "prestamo")
    mov.sort(key=lambda x: (x["fecha"], -x["importe"]))
    s = saldo_inicial
    for x in mov:
        s = round(s + x["importe"], 2)
        x["saldo"] = s
    return mov


def norma43(mov, saldo_inicial, ruta: Path):
    """Extracto en formato Norma 43 (cuaderno 43 de la AEB), registros de 80 caracteres."""
    def imp(x):
        return f"{round(abs(x) * 100):014d}"
    lineas = ["11" + "0000" + "0000" + "0000000000" + m.INICIO.strftime("%y%m%d") + m.FIN.strftime("%y%m%d") + ("2" if saldo_inicial >= 0 else "1")
              + imp(saldo_inicial) + "978" + "3" + f"{'LA PLAZA RESTAURACIO SL':26s}" + "   "]
    debe = haber = 0
    for x in mov:
        dh = "1" if x["importe"] < 0 else "2"
        debe += x["importe"] < 0
        haber += x["importe"] >= 0
        lineas.append("22" + "    " + "0000" + x["fecha"].strftime("%y%m%d") + x["fecha"].strftime("%y%m%d") + "99" + "000" + dh + imp(x["importe"])
                      + "0000000000" + f"{x['ref'][:12]:12s}" + f"{'':16s}")
        lineas.append("23" + "01" + f"{x['concepto'][:38]:38s}" + f"{'':38s}")
    total_d = sum(-x["importe"] for x in mov if x["importe"] < 0)
    total_h = sum(x["importe"] for x in mov if x["importe"] >= 0)
    final = mov[-1]["saldo"]
    lineas.append("33" + "0000" + "0000" + "0000000000" + f"{debe:05d}" + imp(total_d) + f"{haber:05d}" + imp(total_h) + ("2" if final >= 0 else "1") + imp(final) + "978" + "    ")
    lineas.append("88" + "9" * 18 + f"{len(lineas) - 1:06d}" + " " * 54)
    ruta.write_text("\r\n".join(l[:80].ljust(80) for l in lineas) + "\r\n", encoding="latin-1")


# ---------------------------------------------------------------- correos
FIRMAS = {}


def firma(prov):
    i = m.PROVEEDORES[prov]
    return f"\n\n--\n{prov}\n{i['dir']}\nTel. {i['tel']} · {i['correo']}\nCIF {i['cif']}" if i["tel"] else f"\n\n--\n{prov} · Atención a empresas\n{i['correo']}"


def generar(carpeta=SALIDA):
    if carpeta.exists():
        shutil.rmtree(carpeta)
    for sub in ("facturas", "facturas_escaneadas", "tickets", "nominas", "cierres_tpv", "etiquetas", "banco", "competencia", "en_directo"):
        (carpeta / sub).mkdir(parents=True, exist_ok=True)

    facturas = m.generar_facturas()
    cierres = m.generar_cierres(m.EVENTOS)
    gastos = m.generar_gastos()
    nominas = m.generar_nominas()
    correos, verdad = [], {"facturas": [], "gastos": [], "nominas": [], "cierres": [], "etiquetas": []}

    def hora(d, h):
        return datetime(d.year, d.month, d.day, h, (d.day * 7) % 60).isoformat()

    for f in facturas:
        quien = f.proveedor
        if f.escaneada:
            nombre = f"facturas_escaneadas/{f.fecha.isoformat()} {quien}.jpg"
            img_factura_escaneada(f, carpeta / nombre, bool(f.nota_revisar))
        else:
            nombre = f"facturas/{f.fecha.isoformat()} {quien} {f.numero}{' reenvio' if f.duplicada_de else ''}.pdf"
            if not (carpeta / nombre).exists():
                pdf_factura(f, carpeta / nombre)
        f.archivo = nombre
        cuerpo = ("Buenos días,\n\nOs reenvío la factura " + f.numero + " por si no os llegó." if f.duplicada_de else
                  "Hola,\n\nOs paso foto de la factura de esta semana." if f.escaneada else
                  f"Buenos días,\n\nAdjuntamos la factura {f.numero} de fecha {fecha_es(f.fecha)}.\nImporte: {eur(f.total)} €.") + firma(quien)
        correos.append({"de_nombre": quien, "alias": "proveedor", "asunto": ("RV: " if f.duplicada_de else "") + f"Factura {f.numero}" if not f.escaneada else "Factura semana",
                        "cuerpo": cuerpo, "fecha": hora(f.correo_fecha, 8), "adjuntos": [nombre], "tipo_esperado": "factura"})
        verdad["facturas"].append({"archivo": nombre, "proveedor": quien, "numero": None if f.nota_revisar else f.numero, "fecha": f.fecha.isoformat(),
                                   "base": f.base, "iva": f.iva, "total": f.total, "vencimiento": f.vence.isoformat(), "duplicada": bool(f.duplicada_de),
                                   "escaneada": f.escaneada, "revisar": f.nota_revisar,
                                   "lineas": [{"producto": l.producto, "cantidad": l.cantidad, "unidad": l.unidad, "precio": l.precio, "iva": l.iva} for l in f.lineas]})

    for g in gastos:
        nombre = f"tickets/{g.fecha.isoformat()} {g.comercio} {eur(g.total)}.jpg"
        img_ticket(g, carpeta / nombre)
        correos.append({"de_nombre": "Oficina La Plaza", "alias": "oficina", "asunto": f"Ticket {g.comercio}", "cuerpo": "Foto del ticket de hoy.\n\nMarta (oficina)",
                        "fecha": hora(g.fecha, 13), "adjuntos": [nombre], "tipo_esperado": "gasto"})
        verdad["gastos"].append({"archivo": nombre, "comercio": g.comercio, "categoria": g.categoria, "fecha": g.fecha.isoformat(), "total": g.total})

    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre"]
    for mes in (7, 8, 9):
        del_mes = [n for n in nominas if n["mes"] == mes]
        adj = []
        for n in del_mes:
            nombre = f"nominas/{n['fecha'].isoformat()} Nomina {n['empleado'].split(' (')[0]} {eur(n['coste_empresa'])}.pdf"
            pdf_nomina(n, carpeta / nombre)
            adj.append(nombre)
            verdad["nominas"].append({"archivo": nombre, "empleado": n["empleado"], "mes": mes, "bruto": n["bruto"], "neto": n["neto"], "coste_empresa": n["coste_empresa"]})
        correos.append({"de_nombre": "Gestoría Albà", "alias": "gestoria", "asunto": f"Nóminas de {meses[mes]}",
                        "cuerpo": f"Hola,\n\nOs adjunto las nóminas de {meses[mes]}. El total líquido a transferir es de {eur(sum(n['neto'] for n in del_mes))} € "
                                  f"y la Seguridad Social se cargará a final del mes que viene.\n\nUn saludo,\nGestoría Albà (inventada)",
                        "fecha": hora(del_mes[0]["llega"], 10), "adjuntos": adj, "tipo_esperado": "nomina"})

    for c in cierres:
        nombre = f"cierres_tpv/{c.fecha.isoformat()} Cierre TPV {eur(c.total)}.pdf"
        pdf_cierre(c, carpeta / nombre)
        correos.append({"de_nombre": "TPV La Plaza", "alias": "restaurante", "asunto": f"Cierre de caja {fecha_es(c.fecha)}", "cuerpo": "Informe Z adjunto (envío automático del TPV).",
                        "fecha": hora(c.fecha + timedelta(days=1), 1), "adjuntos": [nombre], "tipo_esperado": "cierre"})
        verdad["cierres"].append({"archivo": nombre, "fecha": c.fecha.isoformat(), "total": c.total, "tarjeta": c.tarjeta, "efectivo": c.efectivo,
                                  "efectivo_contado": c.efectivo_contado, "cubiertos": c.cubiertos, "unidades": c.unidades, "franjas": c.franjas})

    # 15 etiquetas de producto fresco que casan con líneas de las últimas facturas de pescado y carne
    recientes = [f for f in facturas if f.proveedor in ("Pescados Mar Nou", "Carnes Vallès") and not f.duplicada_de and f.fecha >= date(2026, 10, 1)]
    vida = {"pescado": 2, "carne": 5}
    n_et = 0
    for f in sorted(recientes, key=lambda x: x.fecha, reverse=True):
        for l in f.lineas:
            p = m.PRODUCTOS[l.producto]
            if p.tipo not in vida or n_et >= 15:
                continue
            caduca = f.fecha + timedelta(days=vida[p.tipo] + (1 if p.tipo == "carne" and "Jamón" in l.producto else 0) + (20 if "Jamón" in l.producto else 0))
            lote = f"L{f.fecha.strftime('%y%m%d')}-{n_et + 1:02d}"
            nombre = f"etiquetas/{f.fecha.isoformat()} {l.producto} {lote}.jpg"
            img_etiqueta(f.proveedor, l.producto, l.cantidad, lote, f.fecha, caduca, carpeta / nombre)
            verdad["etiquetas"].append({"archivo": nombre, "producto": l.producto, "proveedor": f.proveedor, "factura": f.numero, "peso": l.cantidad,
                                        "lote": lote, "caduca": caduca.isoformat(), "recibido": f.fecha.isoformat()})
            n_et += 1

    # Clientes y publicidad
    clientes = [
        ("Marta García", "Reserva para el sábado, 8 personas", "Hola, queríamos reservar mesa para 8 personas este sábado 17 de octubre a las 21:30. Somos un cumpleaños, ¿podría ser en la planta de arriba? Gracias, Marta.", date(2026, 10, 10), "reserva"),
        ("Pere Soler", "Mesa para dos el viernes", "Bon dia, voldria reservar per a dues persones divendres 16 a les 21:00. Gràcies! Pere", date(2026, 10, 9), "reserva"),
        ("Laia Vidal", "Comida de empresa", "Hola, somos 14 compañeros de trabajo y buscamos sitio para comer el jueves 22 de octubre a las 14:00. ¿Tenéis menú para grupos? Laia", date(2026, 10, 8), "reserva"),
        ("Carlos Ruiz", "Reserva domingo", "Buenas, mesa para 4 el domingo 18 a las 14:30, con una trona para un bebé si puede ser. Carlos", date(2026, 10, 6), "reserva"),
        ("Ana Morales", "Reserva cena", "Hola, ¿tenéis mesa para 3 personas el sábado 3 de octubre a las 22:00? Ana", date(2026, 9, 30), "reserva"),
        ("Julia Fernández", "¿Tenéis opciones sin gluten?", "Hola, mi hija es celíaca. ¿Qué platos de la carta puede comer? Gracias, Julia", date(2026, 9, 18), "consulta"),
        ("Tomás Bru", "Horario de cocina", "¿Hasta qué hora está abierta la cocina los domingos? Tomás", date(2026, 8, 27), "consulta"),
        ("Sofía Navarro", "¿Se puede ir con perro?", "Hola, ¿admitís perros pequeños en la terraza? Sofía", date(2026, 8, 12), "consulta"),
        ("Nerea Gil", "Pago con tarjeta de comida", "Hola, ¿aceptáis tarjetas restaurante (tipo cheque comida)? Nerea", date(2026, 9, 3), "consulta"),
        ("Jordi Ribas", "Esperamos 50 minutos el segundo plato", "Estuvimos el sábado por la noche y esperamos 50 minutos el segundo plato sin que nadie nos dijera nada. La comida buena, pero así no se puede. Jordi Ribas", date(2026, 10, 4), "queja"),
    ]
    for nombre, asunto, cuerpo, d, tipo in clientes:
        correos.append({"de_nombre": nombre, "alias": "cliente", "asunto": asunto, "cuerpo": cuerpo, "fecha": hora(d, 9 + d.day % 10), "adjuntos": [], "tipo_esperado": tipo})
    publi = [("ProMenu Ofertas", "¡Digitaliza tu carta con un 40 % de descuento!"), ("Hostel Supply", "Nuevas vajillas con envío gratis"),
             ("Seguros HoReCa", "Revisa tu seguro: te ahorramos un 20 %"), ("Delivery Rápido", "Únete a nuestra plataforma de reparto"),
             ("Uniformes Pro", "Uniformes de cocina desde 9,90 €"), ("Software TPV Plus", "Cambia de TPV y llévate la impresora gratis"),
             ("Feria Alimentaria", "Invitación a la feria del sector"), ("Café Premium", "Prueba nuestro café de especialidad gratis")]
    for i, (nombre, asunto) in enumerate(publi):
        d = date(2026, 8, 5) + timedelta(days=i * 8)
        correos.append({"de_nombre": nombre, "alias": "cliente", "asunto": asunto, "cuerpo": f"{asunto}. Escríbenos para más información. Para darte de baja, responde BAJA.",
                        "fecha": hora(d, 11), "adjuntos": [], "tipo_esperado": "publicidad"})
    correos.sort(key=lambda c: c["fecha"])

    # Banco: el 1 de agosto había 3.000 € (tras pagar los impuestos y nóminas de julio)
    saldo_ini = 3000.00
    mov = movimientos_banco(facturas, cierres, gastos, nominas, saldo_ini)
    norma43(mov, saldo_ini, carpeta / "banco" / "extracto_2026-08-01_2026-10-10.n43")
    with open(carpeta / "banco" / "extracto_2026-08-01_2026-10-10.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["Fecha", "Concepto", "Importe", "Saldo"])
        for x in mov:
            w.writerow([fecha_es(x["fecha"]), x["concepto"], eur(x["importe"]), eur(x["saldo"])])

    # Carta, competencia, cuadrante, eventos, pagos fijos
    carta = [{"nombre": n, "parte": parte, "precio_carta": pc, "clave_competencia": clave,
              "receta": [{"producto": p, "cantidad": round(c, 4)} for p, c in receta.items()]} for n, parte, pc, receta, _, clave in m.CARTA]
    productos = [{"nombre": p.nombre, "proveedor": p.proveedor, "unidad": p.unidad, "tipo": p.tipo, "rendimiento": p.rendimiento,
                  "codigo_mercabarna": p.mercabarna, "alergenos": p.alergenos} for p in m.PRODUCTOS.values()]
    proveedores = [{"nombre": k, "grupo": v["grupo"], "tipo": v["tipo"]} for k, v in m.PROVEEDORES.items()]
    for comp in m.COMPETIDORES:
        pdf_carta_competidor(comp, carpeta / "competencia" / f"Carta {comp['nombre'].split(' (')[0]}.pdf")
    ventas_trim = sum(c.total for c in cierres if c.fecha.month in (8, 9)) / 1.1
    iva_rep = ventas_trim * 1.5 * 0.10  # julio estimado como la media de agosto y septiembre
    iva_sop = sum(f.iva for f in facturas if not f.duplicada_de and f.fecha.month in (8, 9)) * 1.5
    pagos = [dict(p) for p in m.PAGOS_FIJOS]
    for p in pagos:
        if p["concepto"].startswith("IVA"):
            p["importe"] = round(iva_rep - iva_sop, 2)
    json_out = {
        "restaurante": m.RESTAURANTE, "hoy_demo": m.HOY_DEMO.isoformat(), "carta": carta, "productos": productos, "proveedores_info": proveedores,
        "cuadrante": m.generar_cuadrante(), "empleados": [{"nombre": e[0], "puesto": e[1], "horas_semana": 40} for e in m.EMPLEADOS],
        "eventos": [{"fecha": e["fecha"].isoformat(), "nombre": e["nombre"], "efecto": e["efecto"]} for e in m.EVENTOS],
        "pagos_fijos": pagos, "competidores": m.COMPETIDORES,
    }
    (carpeta / "datos.json").write_text(json.dumps(json_out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (carpeta / "correos.json").write_text(json.dumps(correos, ensure_ascii=False, indent=1), encoding="utf-8")
    verdad["banco"] = {"saldo_inicial": saldo_ini, "saldo_final": mov[-1]["saldo"], "movimientos": len(mov)}
    verdad["proveedores_contacto"] = {k: {"telefono": v["tel"], "correo": v["correo"], "cif": v["cif"], "direccion": v["dir"]} for k, v in m.PROVEEDORES.items()}
    (carpeta / "verdad.json").write_text(json.dumps(verdad, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    iva_303 = next(p["importe"] for p in pagos if p["concepto"].startswith("IVA"))
    envio = generar_en_directo(carpeta, iva_303)
    escribir_indice(carpeta, facturas, gastos, nominas, cierres, verdad, correos, mov, envio, saldo_ini)
    return carpeta


def generar_en_directo(carpeta, iva_303):
    """15 correos para 'Enviar al correo' en la reunión (fechas del 11 de octubre)."""
    d = m.HOY_DEMO
    f1 = m.Factura("Pescados Mar Nou", m._numero("Pescados Mar Nou"), d, [m._l("Lubina fresca", 2.1, d), m._l("Calamar limpio", 5.5, d), m._l("Mejillón", 6.0, d)], d + timedelta(days=30))
    f2 = m.Factura("Bebidas Sol", m._numero("Bebidas Sol"), d, [m._l("Cerveza de barril", 90, d), m._l("Refresco lata", 96, d)], d + timedelta(days=30))
    f3 = m.Factura("Distribuciones Olivé", m._numero("Distribuciones Olivé"), d, [m._l("Aceite de oliva", 20, d), m._l("Huevos", 30, d)], d + timedelta(days=30))
    for f in (f1, f2, f3):
        pdf_factura(f, carpeta / "en_directo" / f"Factura {f.proveedor} {f.numero}.pdf")
    g = m.Gasto(d, "Hielo Cubitos BCN", "Hielo y bebida", [("Saco hielo 10 kg", 2, 9.00)], "T55120")
    img_ticket(g, carpeta / "en_directo" / "Ticket hielo.jpg")
    envio = [
        {"de_nombre": "Pescados Mar Nou", "alias": "proveedor", "asunto": f"Factura {f1.numero}", "cuerpo": f"Buenos días,\n\nAdjuntamos la factura {f1.numero}." + firma("Pescados Mar Nou"), "adjuntos": [f"en_directo/Factura Pescados Mar Nou {f1.numero}.pdf"]},
        {"de_nombre": "Bebidas Sol", "alias": "proveedor", "asunto": f"Factura {f2.numero}", "cuerpo": f"Hola,\n\nOs enviamos la factura {f2.numero}." + firma("Bebidas Sol"), "adjuntos": [f"en_directo/Factura Bebidas Sol {f2.numero}.pdf"]},
        {"de_nombre": "Distribuciones Olivé", "alias": "proveedor", "asunto": f"Factura {f3.numero}", "cuerpo": "Factura adjunta." + firma("Distribuciones Olivé"), "adjuntos": [f"en_directo/Factura Distribuciones Olivé {f3.numero}.pdf"]},
        {"de_nombre": "Gestoría Albà", "alias": "gestoria", "asunto": "IVA y retenciones del 3.er trimestre", "cuerpo": "Hola,\n\nYa tenemos los impuestos del tercer trimestre: IVA (modelo 303) " + eur(iva_303) + " € y retenciones (modelo 111) 4.134,15 €. Se cargarán el 20 de octubre.\n\nUn saludo,\nGestoría Albà (inventada)", "adjuntos": []},
        {"de_nombre": "Oficina La Plaza", "alias": "oficina", "asunto": "Ticket hielo", "cuerpo": "Foto del ticket.", "adjuntos": ["en_directo/Ticket hielo.jpg"]},
        {"de_nombre": "Elena Puig", "alias": "cliente", "asunto": "Reserva para 6 el viernes", "cuerpo": "Hola, ¿tenéis mesa para 6 personas el viernes 16 de octubre a las 21:00? Gracias, Elena", "adjuntos": []},
        {"de_nombre": "Marc Serra", "alias": "cliente", "asunto": "Cena de aniversario", "cuerpo": "Bona tarda, voldríem una taula per a dos dissabte 17 a les 21:30, és el nostre aniversari. Marc", "adjuntos": []},
        {"de_nombre": "Lucía Ramos", "alias": "cliente", "asunto": "¿Tenéis menú del día?", "cuerpo": "Hola, ¿hacéis menú del día entre semana? ¿Qué precio tiene? Lucía", "adjuntos": []},
        {"de_nombre": "David Ortega", "alias": "cliente", "asunto": "Factura de mi comida", "cuerpo": "Hola, comí ayer con mi empresa y necesito factura a nombre de Ortega Consulting SL. Os paso el ticket si hace falta. David", "adjuntos": []},
        {"de_nombre": "Raquel Mas", "alias": "cliente", "asunto": "La cuenta estaba mal", "cuerpo": "Ayer nos cobraron dos cafés que no pedimos. No es mucho, pero que lo sepáis. Raquel", "adjuntos": []},
        {"de_nombre": "ProMenu Ofertas", "alias": "cliente", "asunto": "Última oportunidad: 50 % de descuento", "cuerpo": "Solo hoy. Responde BAJA para no recibir más.", "adjuntos": []},
        {"de_nombre": "Delivery Rápido", "alias": "cliente", "asunto": "Te regalamos 3 meses sin comisión", "cuerpo": "Únete hoy a nuestra plataforma.", "adjuntos": []},
        {"de_nombre": "Hostel Supply", "alias": "cliente", "asunto": "Rebajas de octubre en menaje", "cuerpo": "Descubre nuestras ofertas.", "adjuntos": []},
        {"de_nombre": "Ayuntamiento (notificación)", "alias": "oficina", "asunto": "Renovación de la licencia de terraza", "cuerpo": "Le recordamos que la licencia de terraza vence el 31 de diciembre. Puede renovarla en la sede electrónica.", "adjuntos": []},
        {"de_nombre": "Pere Soler", "alias": "cliente", "asunto": "RE: Mesa para dos el viernes", "cuerpo": "Perfecte, gràcies! Fins divendres. Pere", "adjuntos": []},
    ]
    (carpeta / "envio_en_directo.json").write_text(json.dumps(envio, ensure_ascii=False, indent=1), encoding="utf-8")
    return envio


def escribir_indice(carpeta, facturas, gastos, nominas, cierres, verdad, correos, mov, envio, saldo_ini):
    por_tipo = defaultdict(int)
    for c in correos:
        por_tipo[c["tipo_esperado"]] += 1
    ventas = defaultdict(float)
    for c in cierres:
        ventas[c.fecha.month] += c.total
    t = [
        "# Datos de demo · Restaurante La Plaza (inventado)", "",
        f"Del {fecha_es(m.INICIO)} al {fecha_es(m.FIN)}. El \"hoy\" de la demo es el {fecha_es(m.HOY_DEMO)}. Todo es inventado.",
        "Se generan con `python herramientas/generar_demo.py` a partir de `herramientas/modelo_demo.py` (una sola fuente: todo cuadra).", "",
        "| Qué | Cuántos | Carpeta |", "|---|---|---|",
        f"| Facturas en PDF | {sum(1 for f in facturas if not f.escaneada)} (1 duplicada a propósito) | facturas/ |",
        f"| Facturas escaneadas (foto) | {sum(1 for f in facturas if f.escaneada)} (1 con el número ilegible) | facturas_escaneadas/ |",
        f"| Tickets de gasto (foto) | {len(gastos)} | tickets/ |",
        f"| Nóminas | {len(nominas)} (4 empleados × julio, agosto y septiembre) | nominas/ |",
        f"| Cierres diarios del TPV | {len(cierres)} (los lunes cierra) | cierres_tpv/ |",
        f"| Etiquetas de producto fresco (foto) | {len(verdad['etiquetas'])} | etiquetas/ |",
        f"| Extracto del banco | {len(mov)} movimientos (Norma 43 y CSV) | banco/ |",
        "| Cartas de 3 competidores | 3 PDF | competencia/ |",
        f"| Correos (llegan a la bandeja) | {len(correos)}: " + ", ".join(f"{v} {k}" for k, v in sorted(por_tipo.items())) + " | correos.json |",
        f"| Correos para enviar en directo | {len(envio)} | envio_en_directo.json, en_directo/ |",
        "| Carta (25 platos + 8 bebidas con receta), productos, cuadrante, eventos, pagos fijos, competidores | — | datos.json |",
        "| Datos correctos para comprobar la extracción | — | verdad.json |", "",
        "## Cosas puestas a propósito",
        f"- Subidas de precio: entrecot de 21,50 a 24,20 €/kg desde el {fecha_es(m.SUBIDAS['Entrecot de vaca'][0])}; lubina de 12,80 a 14,90 €/kg desde el {fecha_es(m.SUBIDAS['Lubina fresca'][0])}.",
        "- Factura duplicada: Carnes Vallès del 5/10 reenviada el 9/10.",
        "- Escaneada con el número ilegible: Hortalizas del Prat del 7/10 (debe salir \"revisar\").",
        "- Descuadres de caja: 22/8 (−35 €) y 10/10 (−20 €).",
        "- Recibos en el banco sin factura: comisiones del datáfono, alarma y cuota de autónomo.", "",
        "## Cifras de control (con IVA)",
        f"- Ventas: agosto {eur(ventas[8])} €, septiembre {eur(ventas[9])} €, octubre hasta el día 10 {eur(ventas[10])} €.",
        f"- Banco: saldo el 1/8 {eur(saldo_ini)} €, saldo el 10/10 {eur(mov[-1]['saldo'])} €.", "",
        "Importante: nombres de empresas, personas, CIF, teléfonos y direcciones son inventados (dominios .example).",
    ]
    (carpeta / "INDICE.md").write_text("\n".join(t) + "\n", encoding="utf-8")


if __name__ == "__main__":
    c = generar()
    print("Demo generada en", c)
    print((c / "INDICE.md").read_text(encoding="utf-8"))
