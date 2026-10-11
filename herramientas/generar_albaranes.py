"""Dos fotos de albarán inventadas para la demo (botón "Foto del albarán" de Recepción).

Uso:  .venv\\Scripts\\python.exe herramientas\\generar_albaranes.py
Crea datos_demo/albaranes/*.jpg. Casan con las facturas F-2026-0290 (08/10) y F-2026-0291 (10/10)
de Pescados Mar Nou; en el del 10/10 faltan 0,5 kg de mejillón a propósito (la app debe avisar).
"""
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos_demo" / "albaranes"
FUENTE, FUENTE_N, FUENTE_M = "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/consola.ttf"

ALBARANES = [
    {"numero": "ALB-26-0290", "fecha": date(2026, 10, 8), "factura": "F-2026-0290",
     "lineas": [("Merluza", 1.9, "kg"), ("Gamba roja", 1.0, "kg"), ("Bacalao desalado", 1.3, "kg"), ("Mejillón", 6.2, "kg")]},
    {"numero": "ALB-26-0291", "fecha": date(2026, 10, 10), "factura": "F-2026-0291",
     "lineas": [("Merluza", 1.8, "kg"), ("Gamba roja", 1.2, "kg"), ("Bacalao desalado", 1.4, "kg"), ("Mejillón", 4.9, "kg"), ("Calamar limpio", 5.3, "kg"), ("Lubina fresca", 1.7, "kg")]},
]


def num(x):
    return f"{x:.1f}".replace(".", ",")


def img_albaran(a: dict, ruta: Path):
    W, H = 980, 760 + 44 * len(a["lineas"])
    im = Image.new("RGB", (W, H), (253, 252, 248))
    d = ImageDraw.Draw(im)
    fb, f, fm = ImageFont.truetype(FUENTE_N, 40), ImageFont.truetype(FUENTE, 28), ImageFont.truetype(FUENTE_M, 28)
    d.rectangle((20, 20, W - 20, H - 20), outline=(60, 60, 60), width=3)
    d.text((50, 45), "PESCADOS MAR NOU, S.L.", font=fb, fill=(10, 40, 80))
    d.text((50, 95), "Mercabarna, pabellón del pescado · Barcelona · CIF B-00000002 (inventado)", font=ImageFont.truetype(FUENTE, 22), fill=(70, 70, 70))
    d.text((50, 160), "ALBARÁN DE ENTREGA", font=fb, fill=(10, 10, 10))
    d.text((50, 220), f"Albarán nº: {a['numero']}", font=f, fill=(20, 20, 20))
    d.text((520, 220), f"Fecha: {a['fecha'].strftime('%d/%m/%Y')}", font=f, fill=(20, 20, 20))
    d.text((50, 262), "Cliente: Restaurante La Plaza · Barcelona", font=f, fill=(20, 20, 20))
    y = 330
    d.line((40, y, W - 40, y), fill=(60, 60, 60), width=2)
    d.text((50, y + 12), "Producto", font=f, fill=(20, 20, 20))
    d.text((700, y + 12), "Cantidad", font=f, fill=(20, 20, 20))
    y += 58
    d.line((40, y, W - 40, y), fill=(60, 60, 60), width=2)
    y += 14
    for nombre, cant, ud in a["lineas"]:
        d.text((50, y), nombre, font=fm, fill=(20, 20, 20))
        d.text((700, y), f"{num(cant)} {ud}", font=fm, fill=(20, 20, 20))
        y += 44
    d.line((40, y + 6, W - 40, y + 6), fill=(60, 60, 60), width=2)
    d.text((50, y + 24), "Género fresco. Conservar entre 0 y 4 °C. Los precios van en la factura.", font=ImageFont.truetype(FUENTE, 22), fill=(70, 70, 70))
    d.text((50, y + 60), "Recibí conforme:", font=f, fill=(20, 20, 20))
    d.line((260, y + 120, 560, y + 120), fill=(30, 30, 30), width=2)
    d.text((50, H - 60), "Documento de ejemplo para la demo de ReHub (inventado).", font=ImageFont.truetype(FUENTE, 20), fill=(140, 140, 140))
    im = im.rotate(-2.2, expand=True, fillcolor=(150, 140, 125), resample=Image.BICUBIC)
    fondo = Image.new("RGB", (im.width + 80, im.height + 80), (150, 140, 125))
    fondo.paste(im, (40, 40))
    fondo = fondo.filter(ImageFilter.GaussianBlur(0.7)).resize((fondo.width * 2 // 3, fondo.height * 2 // 3))
    fondo.save(ruta, quality=72)


if __name__ == "__main__":
    SALIDA.mkdir(parents=True, exist_ok=True)
    for a in ALBARANES:
        ruta = SALIDA / f"{a['fecha'].isoformat()} Albaran Pescados Mar Nou {a['numero']}.jpg"
        img_albaran(a, ruta)
        print("creado", ruta.name)
