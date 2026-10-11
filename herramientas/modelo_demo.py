"""Modelo de datos de la demo "Restaurante La Plaza" (1 ago - 10 oct 2026).

Es la ÚNICA fuente de todas las cifras de la demo: facturas, ventas, nóminas,
banco... se calculan aquí y los archivos (PDF, fotos, correos) se dibujan a
partir de esto. Así todo cuadra entre sí.

Todo es inventado. Importes de compras: precio sin IVA por unidad.
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

INICIO = date(2026, 8, 1)
FIN = date(2026, 10, 10)
HOY_DEMO = date(2026, 10, 11)  # el "hoy" de la demo
CORREO = "laplaza.rehub@gmail.com"
RESTAURANTE = {"nombre": "Restaurante La Plaza", "razon": "La Plaza Restauració, S.L. (ejemplo)", "cif": "B-99999999",
               "direccion": "Plaça de l'Exemple, 1 · 08002 Barcelona (inventada)"}

rng = random.Random(20261011)


def dias(desde=INICIO, hasta=FIN):
    d = desde
    while d <= hasta:
        yield d
        d += timedelta(days=1)


def abierto(d: date) -> bool:
    return d.weekday() != 0  # cierra los lunes


# ---------------------------------------------------------------- productos
@dataclass
class Prod:
    nombre: str
    proveedor: str
    unidad: str
    precio: float          # sin IVA, por unidad
    iva: float             # 0.04 / 0.10 / 0.21
    tipo: str              # pescado / carne / verdura / seco / bebida / lacteo / pan
    rendimiento: float = 1.0
    mercabarna: str = ""   # código en las estadísticas de Mercabarna
    alergenos: str = ""


PRODUCTOS = {p.nombre: p for p in [
    # Carnes Vallès
    Prod("Entrecot de vaca", "Carnes Vallès", "kg", 21.50, 0.10, "carne", 0.90),
    Prod("Solomillo de cerdo", "Carnes Vallès", "kg", 11.90, 0.10, "carne", 0.95),
    Prod("Pollo de corral", "Carnes Vallès", "kg", 4.35, 0.10, "carne", 0.70),
    Prod("Jamón ibérico loncheado", "Carnes Vallès", "kg", 26.93, 0.10, "carne"),
    Prod("Carne picada mixta", "Carnes Vallès", "kg", 8.40, 0.10, "carne"),
    Prod("Butifarra", "Carnes Vallès", "kg", 9.80, 0.10, "carne"),
    # Pescados Mar Nou
    Prod("Lubina fresca", "Pescados Mar Nou", "kg", 12.80, 0.10, "pescado", 1.0, "2411921", "pescado"),
    Prod("Calamar limpio", "Pescados Mar Nou", "kg", 11.50, 0.10, "pescado", 1.0, "243101", "moluscos"),
    Prod("Mejillón", "Pescados Mar Nou", "kg", 4.20, 0.10, "pescado", 1.0, "2452021", "moluscos"),
    Prod("Bacalao desalado", "Pescados Mar Nou", "kg", 21.90, 0.10, "pescado", 0.95, "", "pescado"),
    Prod("Gamba roja", "Pescados Mar Nou", "kg", 56.38, 0.10, "pescado", 1.0, "", "crustáceos"),
    Prod("Merluza", "Pescados Mar Nou", "kg", 13.20, 0.10, "pescado", 0.85, "", "pescado"),
    Prod("Tinta de calamar", "Pescados Mar Nou", "kg", 65.00, 0.10, "seco", 1.0, "", "moluscos"),
    # Hortalizas del Prat (verdura fresca: IVA 4 %)
    Prod("Tomate maduro", "Hortalizas del Prat", "kg", 1.45, 0.04, "verdura", 0.95, "326GBZ"),
    Prod("Cebolla seca", "Hortalizas del Prat", "kg", 0.85, 0.04, "verdura", 0.90, "322BAA"),
    Prod("Patata", "Hortalizas del Prat", "kg", 0.95, 0.04, "verdura", 0.85, "320BBA"),
    Prod("Pimiento rojo", "Hortalizas del Prat", "kg", 3.20, 0.04, "verdura", 0.85, "326EBB"),
    Prod("Limón", "Hortalizas del Prat", "kg", 1.60, 0.04, "verdura", 1.0, "310AAA"),
    Prod("Lechuga", "Hortalizas del Prat", "ud", 0.70, 0.04, "verdura"),
    Prod("Ajo", "Hortalizas del Prat", "kg", 4.20, 0.04, "verdura", 0.85),
    Prod("Perejil", "Hortalizas del Prat", "manojo", 0.52, 0.04, "verdura"),
    Prod("Rúcula", "Hortalizas del Prat", "kg", 9.50, 0.04, "verdura"),
    Prod("Calabacín", "Hortalizas del Prat", "kg", 1.30, 0.04, "verdura", 0.95),
    # Bebidas Sol
    Prod("Cerveza de barril", "Bebidas Sol", "l", 2.98, 0.21, "bebida", 0.90, "", "gluten"),
    Prod("Agua mineral 0,5 l", "Bebidas Sol", "ud", 0.24, 0.10, "bebida"),
    Prod("Refresco lata", "Bebidas Sol", "ud", 0.93, 0.10, "bebida"),
    Prod("Tónica", "Bebidas Sol", "ud", 0.60, 0.10, "bebida"),
    # Vins i Cafès Roca
    Prod("Vino de la casa", "Vins i Cafès Roca", "botella", 4.20, 0.21, "bebida", 1.0, "", "sulfitos"),
    Prod("Café en grano", "Vins i Cafès Roca", "kg", 18.00, 0.10, "seco"),
    Prod("Ginebra", "Vins i Cafès Roca", "botella", 14.50, 0.21, "bebida"),
    Prod("Cava", "Vins i Cafès Roca", "botella", 6.50, 0.21, "bebida", 1.0, "", "sulfitos"),
    # Distribuciones Olivé
    Prod("Aceite de oliva", "Distribuciones Olivé", "l", 7.05, 0.04, "seco"),
    Prod("Arroz bomba", "Distribuciones Olivé", "kg", 3.80, 0.04, "seco"),
    Prod("Harina", "Distribuciones Olivé", "kg", 0.90, 0.04, "seco", 1.0, "", "gluten"),
    Prod("Huevos", "Distribuciones Olivé", "docena", 2.90, 0.04, "lacteo", 1.0, "", "huevo"),
    Prod("Leche", "Distribuciones Olivé", "l", 0.95, 0.04, "lacteo", 1.0, "", "leche"),
    Prod("Azúcar", "Distribuciones Olivé", "kg", 1.10, 0.10, "seco"),
    Prod("Queso de cabra", "Distribuciones Olivé", "kg", 14.00, 0.04, "lacteo", 1.0, "", "leche"),
    Prod("Pasta de canelones", "Distribuciones Olivé", "kg", 4.50, 0.04, "seco", 1.0, "", "gluten, huevo"),
    Prod("Nata", "Distribuciones Olivé", "l", 3.60, 0.10, "lacteo", 1.0, "", "leche"),
    # Forn de Pa Sant Jaume
    Prod("Pan de barra", "Forn de Pa Sant Jaume", "ud", 0.55, 0.04, "pan", 1.0, "", "gluten"),
    Prod("Pan de cristal", "Forn de Pa Sant Jaume", "ud", 1.20, 0.04, "pan", 1.0, "", "gluten"),
]}

# Subidas de precio a propósito (fecha desde la que se aplican)
SUBIDAS = {"Entrecot de vaca": (date(2026, 9, 14), 24.20), "Lubina fresca": (date(2026, 10, 1), 14.90)}


def precio(prod: str, d: date) -> float:
    if prod in SUBIDAS and d >= SUBIDAS[prod][0]:
        return SUBIDAS[prod][1]
    return PRODUCTOS[prod].precio


# ---------------------------------------------------------------- proveedores
PROVEEDORES = {
    "Carnes Vallès": dict(grupo="comida", tipo="Carne", serie="C-", num=8402, tel="93 000 12 34", correo="pedidos@carnesvalles.example",
                         cif="B-00000001", dir="C/ de l'Exemple, 12 · 08014 Barcelona", vence=30, estilo=1),
    "Pescados Mar Nou": dict(grupo="comida", tipo="Pescado", serie="F-2026-0", num=270, tel="93 000 56 78", correo="pedidos@marnou.example",
                            cif="B-00000002", dir="Mercabarna, pabellón de pescado, parada 0 (ejemplo)", vence=30, estilo=2),
    "Hortalizas del Prat": dict(grupo="comida", tipo="Verdura", serie="HP-", num=301, tel="93 000 34 56", correo="hortalizasprat@ejemplo.example",
                               cif="B-00000004", dir="Camí de l'Horta, s/n · El Prat de Llobregat", vence=0, estilo=3, escaneada=True),
    "Bebidas Sol": dict(grupo="comida", tipo="Bebida", serie="BS-", num=2101, tel="93 000 90 12", correo="comercial@bebidassol.example",
                       cif="B-00000003", dir="Pol. Ind. Exemple, nave 3 · L'Hospitalet", vence=30, estilo=1),
    "Vins i Cafès Roca": dict(grupo="comida", tipo="Vino y café", serie="VR-", num=1120, tel="93 000 44 55", correo="pedidos@vinsroca.example",
                             cif="B-00000008", dir="C/ del Vi, 8 · 08003 Barcelona", vence=30, estilo=2),
    "Distribuciones Olivé": dict(grupo="comida", tipo="Aceite, arroz y básicos", serie="DO-", num=890, tel="93 000 66 77", correo="olive@distribuciones.example",
                                cif="B-00000009", dir="Av. de l'Exemple, 40 · Badalona", vence=30, estilo=1),
    "Forn de Pa Sant Jaume": dict(grupo="comida", tipo="Pan", serie="FP-", num=7, tel="93 000 78 90", correo="forn@santjaume.example",
                                 cif="B-00000005", dir="C/ Sant Jaume, 3 · 08002 Barcelona", vence=2, estilo=3),
    "Fincas Ronda": dict(grupo="local", tipo="Alquiler", serie="A-", num=8, tel="93 000 11 22", correo="admin@fincasronda.example",
                        cif="B-00000006", dir="Ronda de l'Exemple, 20 · Barcelona", vence=5, estilo=2),
    "Seguros Previsora": dict(grupo="local", tipo="Seguro", serie="SP-26-", num=1041, tel="93 000 33 44", correo="clientes@previsora.example",
                             cif="A-00000007", dir="Pg. de l'Exemple, 100 · Barcelona", vence=5, estilo=1),
    "Endesa": dict(grupo="local", tipo="Luz", serie="LZ-", num=77118, tel="", correo="facturas@luz.example",
                  cif="(ejemplo)", dir="", vence=15, estilo=2),
    "Naturgy": dict(grupo="local", tipo="Gas", serie="NG-", num=55100, tel="", correo="facturas@gas.example",
                   cif="(ejemplo)", dir="", vence=15, estilo=1),
    "Neteges Brillant": dict(grupo="local", tipo="Limpieza", serie="NB-", num=410, tel="93 000 88 99", correo="neteges@brillant.example",
                            cif="B-00000010", dir="C/ de la Neteja, 5 · Barcelona", vence=30, estilo=3),
}


@dataclass
class Linea:
    producto: str
    cantidad: float
    unidad: str
    precio: float
    iva: float

    @property
    def importe(self):
        return round(self.cantidad * self.precio, 2)


@dataclass
class Factura:
    proveedor: str
    numero: str
    fecha: date
    lineas: list
    vence: date
    escaneada: bool = False
    duplicada_de: str = ""
    archivo: str = ""
    correo_fecha: date | None = None
    pagada: date | None = None
    forma_pago: str = "domiciliación"
    nota_revisar: str = ""

    @property
    def base(self):
        return round(sum(l.importe for l in self.lineas), 2)

    @property
    def ivas(self):
        tipos = {}
        for l in self.lineas:
            tipos[l.iva] = round(tipos.get(l.iva, 0) + l.importe, 2)
        return {t: (b, round(b * t, 2)) for t, b in sorted(tipos.items())}

    @property
    def iva(self):
        return round(sum(c for _, c in self.ivas.values()), 2)

    @property
    def total(self):
        return round(self.base + self.iva, 2)


def _numero(prov):
    p = PROVEEDORES[prov]
    p["num"] += 1
    return f"{p['serie']}{p['num']}"


def _l(prod, cant, d):
    p = PRODUCTOS[prod]
    return Linea(prod, cant, p.unidad, precio(prod, d), p.iva)


def _var(x, pct=0.15):
    return round(x * (1 + rng.uniform(-pct, pct)), 1)


def generar_facturas() -> list[Factura]:
    fs = []

    def nueva(prov, d, lineas, **kw):
        info = PROVEEDORES[prov]
        f = Factura(prov, _numero(prov), d, lineas, d + timedelta(days=info["vence"]), escaneada=info.get("escaneada", False), **kw)
        fs.append(f)
        return f

    for d in dias():
        wd = d.weekday()
        if wd == 0:  # lunes: carne de toda la semana
            nueva("Carnes Vallès", d, [_l("Entrecot de vaca", _var(8.5, .08), d), _l("Solomillo de cerdo", _var(3), d), _l("Pollo de corral", _var(6.5), d),
                                       _l("Jamón ibérico loncheado", 3, d), _l("Carne picada mixta", _var(1), d), _l("Butifarra", _var(2.5), d)])
        if wd in (3, 5):  # jueves y sábado: pescado
            nueva("Pescados Mar Nou", d, [_l("Lubina fresca", _var(2.0), d), _l("Calamar limpio", _var(5.8), d), _l("Mejillón", _var(6.0, .1), d),
                                          _l("Bacalao desalado", _var(1.2), d), _l("Gamba roja", _var(1.1), d), _l("Merluza", _var(1.8), d)]
                  + ([_l("Tinta de calamar", 0.25, d)] if wd == 3 else []))
        if wd == 2:  # miércoles: verdura (papel escaneado)
            nueva("Hortalizas del Prat", d, [_l("Tomate maduro", _var(13), d), _l("Cebolla seca", _var(5), d), _l("Patata", _var(40), d),
                                             _l("Pimiento rojo", _var(3.6), d), _l("Limón", _var(2), d), _l("Lechuga", 10, d), _l("Ajo", 1, d),
                                             _l("Perejil", 4, d), _l("Rúcula", 0.3, d), _l("Calabacín", _var(1.1), d)], forma_pago="efectivo")
        if d.day in (7, 21):
            nueva("Bebidas Sol", d, [_l("Cerveza de barril", 120, d), _l("Agua mineral 0,5 l", 240, d), _l("Refresco lata", 150, d), _l("Tónica", 24, d)])
        if d.day in (2, 16):
            nueva("Vins i Cafès Roca", d, [_l("Vino de la casa", 30, d), _l("Café en grano", 3, d), _l("Ginebra", 2, d), _l("Cava", 2, d)])
        if d.day == 15:
            nueva("Distribuciones Olivé", d, [_l("Aceite de oliva", 60, d), _l("Arroz bomba", 20, d), _l("Harina", 18, d), _l("Huevos", 65, d),
                                              _l("Leche", 85, d), _l("Azúcar", 12, d), _l("Queso de cabra", 1.5, d), _l("Pasta de canelones", 2, d), _l("Nata", 3, d)])
            if d.month in (8, 9):
                nueva("Neteges Brillant", d, [Linea("Servicio de limpieza de campana y extractores", 1, "servicio", 80.00, 0.21)])
        if (d + timedelta(days=1)).month != d.month:
            nueva("Forn de Pa Sant Jaume", d, [_l("Pan de barra", 100, d), _l("Pan de cristal", 170, d)])
        if d.day == 1:
            nueva("Fincas Ronda", d, [Linea(f"Alquiler del local, {d.strftime('%m/%Y')}", 1, "mes", 2000.00, 0.21)])
            nueva("Seguros Previsora", d, [Linea(f"Seguro multirriesgo de hostelería, {d.strftime('%m/%Y')}", 1, "mes", 186.40, 0.0)])
        if d.day == 5:
            kwh = {8: 4630, 9: 4390, 10: 4420}[d.month]
            nueva("Endesa", d, [Linea(f"Energía consumida ({kwh} kWh)", kwh, "kWh", round({8: 640.0, 9: 607.36, 10: 607.36}[d.month] / kwh, 5), 0.21)])
        if d.day == 6:
            kwh = {8: 2010, 9: 2080, 10: 2080}[d.month]
            nueva("Naturgy", d, [Linea(f"Gas natural ({kwh} kWh)", kwh, "kWh", round({8: 330.0, 9: 345.70, 10: 345.70}[d.month] / kwh, 5), 0.21)])

    # La factura de Carnes Vallès del 5 de octubre llega otra vez el 9 (duplicada a propósito)
    orig = next(f for f in fs if f.proveedor == "Carnes Vallès" and f.fecha == date(2026, 10, 5))
    dup = Factura(orig.proveedor, orig.numero, orig.fecha, orig.lineas, orig.vence, duplicada_de=orig.numero, correo_fecha=date(2026, 10, 9))
    fs.append(dup)
    # Una escaneada con el número ilegible
    ileg = next(f for f in fs if f.proveedor == "Hortalizas del Prat" and f.fecha == date(2026, 10, 7))
    ileg.nota_revisar = "número de factura ilegible en el escaneo"
    for f in fs:
        f.correo_fecha = f.correo_fecha or f.fecha
    fs.sort(key=lambda f: (f.correo_fecha, f.proveedor))
    return fs


# ---------------------------------------------------------------- carta
# nombre, parte, precio de carta (con IVA), receta {producto: cantidad limpia}, uso por cubierto, clave competencia
CARTA = [
    ("Arroz negro", "comida", 16.50, {"Arroz bomba": .10, "Calamar limpio": .12, "Tinta de calamar": .008, "Aceite de oliva": .03, "Cebolla seca": .05, "Ajo": .005, "Tomate maduro": .05, "Merluza": .03}, .115, "arroz negro"),
    ("Calamares a la andaluza", "comida", 13.00, {"Calamar limpio": .18, "Harina": .04, "Aceite de oliva": .05, "Limón": .03}, .145, "calamares"),
    ("Patatas bravas", "comida", 6.50, {"Patata": .30, "Aceite de oliva": .05, "Tomate maduro": .05, "Ajo": .003}, .25, "bravas"),
    ("Entrecot a la brasa", "comida", 22.00, {"Entrecot de vaca": .30, "Pan de barra": .2, "Patata": .20, "Pimiento rojo": .08, "Aceite de oliva": .02}, .10, "entrecot"),
    ("Lubina a la sal", "comida", 21.00, {"Lubina fresca": .45, "Pan de barra": .2, "Limón": .05, "Aceite de oliva": .02}, .03, "lubina"),
    ("Canelones de la abuela", "comida", 12.00, {"Pasta de canelones": .06, "Carne picada mixta": .12, "Leche": .15, "Harina": .02, "Cebolla seca": .05}, .03, "canelones"),
    ("Ensalada de queso de cabra", "comida", 11.50, {"Queso de cabra": .08, "Rúcula": .06, "Tomate maduro": .08, "Lechuga": .5, "Aceite de oliva": .02}, .015, "ensalada cabra"),
    ("Mejillones a la marinera", "comida", 11.00, {"Mejillón": .50, "Pan de barra": .2, "Tomate maduro": .06, "Cebolla seca": .04, "Ajo": .005, "Aceite de oliva": .02}, .08, "mejillones"),
    ("Croquetas caseras (6)", "comida", 9.00, {"Jamón ibérico loncheado": .03, "Leche": .15, "Harina": .06, "Huevos": .08, "Aceite de oliva": .06}, .17, "croquetas"),
    ("Crema catalana", "comida", 5.50, {"Leche": .15, "Huevos": .15, "Azúcar": .04, "Limón": .01}, .085, "crema catalana"),
    ("Bacalao a la llauna", "comida", 18.50, {"Bacalao desalado": .22, "Pan de barra": .2, "Ajo": .01, "Aceite de oliva": .03, "Perejil": .1}, .04, "bacalao"),
    ("Gambas a la plancha", "comida", 19.00, {"Gamba roja": .20, "Aceite de oliva": .01}, .03, "gambas"),
    ("Pan con tomate", "comida", 3.20, {"Pan de cristal": .5, "Tomate maduro": .06, "Aceite de oliva": .01, "Ajo": .002}, .28, "pan con tomate"),
    ("Tortilla de patatas", "comida", 8.50, {"Patata": .20, "Huevos": .25, "Cebolla seca": .05, "Aceite de oliva": .04}, .07, "tortilla"),
    ("Pollo al ajillo", "comida", 12.50, {"Pollo de corral": .35, "Pan de barra": .2, "Ajo": .02, "Aceite de oliva": .03, "Perejil": .1}, .055, "pollo"),
    ("Solomillo a la pimienta", "comida", 17.50, {"Solomillo de cerdo": .20, "Pan de barra": .2, "Nata": .05, "Patata": .15}, .05, "solomillo"),
    ("Butifarra con patatas", "comida", 11.00, {"Butifarra": .25, "Pan de barra": .2, "Patata": .15, "Aceite de oliva": .01}, .04, "butifarra"),
    ("Merluza a la vasca", "comida", 17.00, {"Merluza": .20, "Pan de barra": .2, "Perejil": .2, "Ajo": .01, "Aceite de oliva": .03}, .045, "merluza"),
    ("Ensalada verde", "comida", 7.50, {"Lechuga": .5, "Tomate maduro": .10, "Cebolla seca": .03, "Aceite de oliva": .02}, .06, "ensalada verde"),
    ("Escalivada", "comida", 8.00, {"Pimiento rojo": .15, "Calabacín": .15, "Cebolla seca": .10, "Aceite de oliva": .03}, .03, "escalivada"),
    ("Jamón ibérico (ración)", "comida", 16.00, {"Jamón ibérico loncheado": .08, "Pan de cristal": .5}, .045, "jamón"),
    ("Huevos rotos con jamón", "comida", 11.50, {"Huevos": .17, "Patata": .25, "Jamón ibérico loncheado": .04, "Aceite de oliva": .04}, .07, "huevos rotos"),
    ("Arroz con leche", "comida", 5.00, {"Arroz bomba": .04, "Leche": .20, "Azúcar": .03, "Limón": .01}, .03, "arroz con leche"),
    ("Flan casero", "comida", 4.50, {"Huevos": .17, "Leche": .15, "Azúcar": .04}, .055, "flan"),
    ("Paella de marisco", "comida", 19.50, {"Arroz bomba": .10, "Gamba roja": .06, "Mejillón": .15, "Calamar limpio": .08, "Tomate maduro": .05, "Aceite de oliva": .03}, .055, "paella"),
    ("Caña de cerveza", "bebida", 2.80, {"Cerveza de barril": .25}, .75, "caña"),
    ("Copa de vino de la casa", "bebida", 3.50, {"Vino de la casa": 1 / 6}, .33, "copa vino"),
    ("Agua mineral 0,5 l", "bebida", 2.20, {"Agua mineral 0,5 l": 1}, .45, "agua"),
    ("Refresco", "bebida", 2.90, {"Refresco lata": 1}, .29, "refresco"),
    ("Café solo", "bebida", 1.50, {"Café en grano": .007, "Azúcar": .006}, .62, "café"),
    ("Café con leche", "bebida", 1.80, {"Café en grano": .007, "Leche": .12, "Azúcar": .006}, .22, "café con leche"),
    ("Gin tonic", "bebida", 8.50, {"Ginebra": .05 / .7, "Tónica": 1, "Limón": .01}, .05, "gin tonic"),
    ("Copa de cava", "bebida", 4.00, {"Cava": 1 / 6}, .03, "copa cava"),
]


def coste_plato(receta: dict, d: date) -> float:
    return round(sum(c / PRODUCTOS[p].rendimiento * precio(p, d) for p, c in receta.items()), 2)


# ---------------------------------------------------------------- ventas (cierres del TPV)
BASE_DIA = {6: 1160, 0: 0, 1: 690, 2: 745, 3: 845, 4: 1220, 5: 1430}  # domingo=6 en weekday()
FRANJAS = {"12-14": .22, "14-16": .33, "16-19": .04, "19-21": .12, "21-23": .24, "23-24": .05}


@dataclass
class CierreTPV:
    fecha: date
    unidades: dict
    franjas: dict
    cubiertos: int
    tarjeta: float
    efectivo: float
    efectivo_contado: float
    numero: int

    @property
    def total(self):
        return round(self.tarjeta + self.efectivo, 2)


def generar_cierres(eventos) -> list[CierreTPV]:
    efecto = {e["fecha"]: e["factor"] for e in eventos}
    cierres, n = [], 4100
    descuadres = {date(2026, 8, 22): -35.0, date(2026, 10, 10): -20.0}
    for d in dias():
        if not abierto(d):
            continue
        objetivo = BASE_DIA[d.weekday()] * (1.13 if d.month == 8 else 1.0) * (0.9 + rng.random() * 0.2) * efecto.get(d, 1.0)
        ticket = 28.0
        cub = max(15, round(objetivo / ticket))
        uds = {}
        for nombre, parte, pc, receta, uso, _ in CARTA:
            u = int(cub * uso + rng.random())
            if u:
                uds[nombre] = u
        total = round(sum(uds[nm] * next(c[2] for c in CARTA if c[0] == nm) for nm in uds), 2)
        tarjeta = round(total * rng.uniform(0.70, 0.80), 2)
        efectivo = round(total - tarjeta, 2)
        repartir = {k: round(total * v * rng.uniform(0.85, 1.15), 2) for k, v in FRANJAS.items()}
        ajuste = round(total - sum(repartir.values()), 2)
        repartir["14-16"] = round(repartir["14-16"] + ajuste, 2)
        n += 1
        cierres.append(CierreTPV(d, uds, repartir, cub, tarjeta, efectivo, round(efectivo + descuadres.get(d, 0.0), 2), n))
    return cierres


# ---------------------------------------------------------------- gastos (tickets en foto)
GASTOS_TIPOS = [("Mercat de la Boqueria", "Mercado (compras sueltas)", [("Hierbas frescas", 6.00), ("Fresas", 18.00), ("Limones", 9.00), ("Albahaca", 4.50)]),
                ("Hielo Cubitos BCN", "Hielo y bebida", [("Saco hielo 10 kg", 9.00)]),
                ("Ferretería Sant Pere", "Reparaciones y mantenimiento", [("Grifo monomando", 28.90), ("Juntas y teflón", 6.10), ("Bombillas LED", 7.35)]),
                ("Makro", "Material y menaje", [("Servilletas (pack)", 14.90), ("Film transparente", 9.80), ("Agua 0,5 l (24 ud)", 4.56), ("Bolsas basura", 12.40)]),
                ("Parking Catedral", "Transporte y aparcamiento", [("Aparcamiento 2 h", 12.50)]),
                ("Farmacia Sant Jaume", "Otros", [("Botiquín: tiritas y gasas", 11.20)])]


@dataclass
class Gasto:
    fecha: date
    comercio: str
    categoria: str
    lineas: list
    numero: str

    @property
    def total(self):
        return round(sum(c * p for _, c, p in self.lineas), 2)


def generar_gastos() -> list[Gasto]:
    fechas = [d for d in dias() if abierto(d)]
    elegidas = sorted(rng.sample(fechas[:-2], 18) + [date(2026, 10, 10), date(2026, 10, 10)])
    gs = []
    for i, d in enumerate(elegidas):
        if d == date(2026, 10, 10):
            tipo = GASTOS_TIPOS[1] if not any(g.fecha == d for g in gs) else GASTOS_TIPOS[0]
        else:
            tipo = GASTOS_TIPOS[i % len(GASTOS_TIPOS)]
        com, cat, items = tipo
        sel = items if len(items) <= 2 else rng.sample(items, 2)
        lineas = [(nm, 2 if "hielo" in nm.lower() else 1, p) for nm, p in sel]
        gs.append(Gasto(d, com, cat, lineas, f"T{rng.randint(10000, 99999)}"))
    return gs


# ---------------------------------------------------------------- personal
EMPLEADOS = [  # nombre, puesto, bruto, neto, coste empresa
    ("Laura Puig (ejemplo)", "Camarera", 1750.00, 1412.35, 2301.25),
    ("Óscar Martín (ejemplo)", "Camarero", 1600.00, 1298.60, 2104.00),
    ("Rosa Ferrer (ejemplo)", "Cocinera", 2000.00, 1586.20, 2630.00),
    ("Iván López (ejemplo)", "Ayudante de cocina", 1680.00, 1354.90, 2209.20),
]
NOMINAS_EXTRA = {("Laura Puig (ejemplo)", 8): (1850.00, 1488.40, 2432.75)}  # agosto: horas extra
M, N, P = [["10:00", "18:00"]], [["16:00", "24:00"]], [["12:30", "16:30"], ["20:00", "24:00"]]
PATRON = {  # weekday: tramos por empleado (lunes cerrado)
    "Laura Puig (ejemplo)": {1: M, 2: M, 4: P, 5: P, 6: M},
    "Óscar Martín (ejemplo)": {1: N, 3: N, 4: N, 5: P, 6: N},
    "Rosa Ferrer (ejemplo)": {1: P, 2: P, 3: P, 4: P, 5: P},
    "Iván López (ejemplo)": {1: M, 3: M, 4: N, 5: N, 6: M},
}


def generar_cuadrante() -> list[dict]:
    return [{"empleado": e, "fecha": d.isoformat(), "tramos": PATRON[e][d.weekday()]}
            for d in dias(INICIO, date(2026, 10, 31)) for e in PATRON if d.weekday() in PATRON[e]]


def generar_nominas() -> list[dict]:
    out = []
    for mes, cobro, llega in ((7, date(2026, 7, 31), date(2026, 8, 3)), (8, date(2026, 8, 31), date(2026, 9, 2)), (9, date(2026, 9, 30), date(2026, 10, 2))):
        for nombre, puesto, bruto, neto, coste in EMPLEADOS:
            b, n, c = NOMINAS_EXTRA.get((nombre, mes), (bruto, neto, coste))
            out.append({"empleado": nombre, "puesto": puesto, "mes": mes, "anio": 2026, "bruto": b, "neto": n, "coste_empresa": c,
                        "ss_empresa": round(c - b, 2), "irpf_y_ss_trabajador": round(b - n, 2), "fecha": cobro, "llega": llega})
    return out


# ---------------------------------------------------------------- eventos y pagos fijos
EVENTOS = [
    {"fecha": date(2026, 8, 15), "nombre": "Festivo: la Asunción", "efecto": "más gente", "factor": 1.15},
    {"fecha": date(2026, 8, 22), "nombre": "Fiestas de Gràcia (última noche)", "efecto": "más gente", "factor": 1.10},
    {"fecha": date(2026, 9, 11), "nombre": "Diada de Catalunya (festivo)", "efecto": "más gente", "factor": 1.20},
    {"fecha": date(2026, 9, 24), "nombre": "La Mercè (festivo)", "efecto": "más gente", "factor": 1.25},
    {"fecha": date(2026, 9, 26), "nombre": "Concierto en el Palau Sant Jordi", "efecto": "cenas antes", "factor": 1.10},
    {"fecha": date(2026, 10, 3), "nombre": "Partido de fútbol en casa, 21:00", "efecto": "cena floja", "factor": 0.92},
    {"fecha": date(2026, 10, 11), "nombre": "Fira de la Tardor en la plaza", "efecto": "más gente", "factor": 1.0},
    {"fecha": date(2026, 10, 12), "nombre": "Festivo: Fiesta Nacional", "efecto": "más gente", "factor": 1.0},
    {"fecha": date(2026, 10, 13), "nombre": "Concierto en el Palau de la Música, 21:00", "efecto": "cenas antes", "factor": 1.0},
    {"fecha": date(2026, 10, 17), "nombre": "Partido de fútbol, 18:30", "efecto": "tarde floja", "factor": 1.0},
]

PAGOS_FIJOS = [
    {"concepto": "Alquiler (Fincas Ronda)", "dia": 5, "importe": 2420.00, "cada": "mes", "aproximado": False},
    {"concepto": "Seguro multirriesgo (Seguros Previsora)", "dia": 5, "importe": 186.40, "cada": "mes", "aproximado": False},
    {"concepto": "Alarma (sin factura por correo)", "dia": 5, "importe": 28.60, "cada": "mes", "aproximado": False},
    {"concepto": "Luz (Endesa)", "dia": 20, "importe": 734.90, "cada": "mes", "aproximado": True},
    {"concepto": "Gas (Naturgy)", "dia": 21, "importe": 418.30, "cada": "mes", "aproximado": True},
    {"concepto": "Nóminas (neto)", "dia": -1, "importe": 5652.05, "cada": "mes", "aproximado": False},
    {"concepto": "Seguridad Social de la empresa", "dia": -1, "importe": 2214.45, "cada": "mes", "aproximado": False},
    {"concepto": "Cuota de autónomo del dueño", "dia": -1, "importe": 315.00, "cada": "mes", "aproximado": False},
    {"concepto": "Préstamo ICO (cuota)", "dia": 10, "importe": 1200.00, "cada": "mes", "aproximado": False},
    {"concepto": "Traspaso al dueño (su sueldo)", "dia": 1, "importe": 2500.00, "cada": "mes", "aproximado": False},
    {"concepto": "IVA del trimestre (modelo 303)", "dia": 20, "importe": 0.0, "cada": "trimestre", "aproximado": True},
    {"concepto": "Retenciones IRPF del trimestre (modelo 111)", "dia": 20, "importe": 4134.15, "cada": "trimestre", "aproximado": True},
]

# ---------------------------------------------------------------- competencia
COMPETIDORES = [
    {"nombre": "Bar Nova Plaça (inventado)", "distancia_m": 150, "valoracion": 4.2, "opiniones": 860,
     "carta": {"arroz negro": 17.50, "calamares": 12.00, "bravas": 6.00, "croquetas": 8.50, "mejillones": 10.50, "crema catalana": 5.50, "pan con tomate": 3.00,
               "tortilla": 8.00, "caña": 2.50, "copa vino": 3.20, "agua": 2.20, "refresco": 2.80, "café": 1.40, "café con leche": 1.70, "pulpo": 18.00, "huevos estrellados": 10.50}},
    {"nombre": "Taberna del Arco (inventada)", "distancia_m": 300, "valoracion": 4.5, "opiniones": 1420,
     "carta": {"arroz negro": 17.90, "calamares": 12.50, "bravas": 6.50, "entrecot": 24.00, "croquetas": 9.00, "crema catalana": 6.00, "gambas": 21.00, "jamón": 18.00,
               "pan con tomate": 3.50, "caña": 2.70, "copa vino": 3.50, "agua": 2.30, "refresco": 2.90, "café": 1.50, "café con leche": 1.80, "gin tonic": 9.00,
               "pulpo": 17.50, "menú del día": 15.50, "huevos estrellados": 11.50}},
    {"nombre": "Casa Vidal (inventada)", "distancia_m": 450, "valoracion": 3.9, "opiniones": 310,
     "carta": {"arroz negro": 16.20, "calamares": 12.40, "bravas": 6.10, "entrecot": 23.00, "mejillones": 10.50, "croquetas": 8.30, "crema catalana": 5.90, "paella": 18.50,
               "pan con tomate": 3.20, "tortilla": 8.50, "caña": 2.60, "copa vino": 3.20, "agua": 2.40, "refresco": 2.70, "café": 1.45, "café con leche": 1.75,
               "gin tonic": 9.00, "pulpo": 17.00, "menú del día": 15.50}},
]
