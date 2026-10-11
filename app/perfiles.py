"""Perfiles de usuario: qué pantalla y qué dato ve cada uno.

En la demo solo existe el dueño. Las reglas de oficina y trabajador ya están
aquí: para activarlas basta con crear el usuario desde Ajustes (o con
`crear_usuario`) y la app oculta lo que no le toca, sin reprogramar nada.
"""
DUENO = "dueno"
OFICINA = "oficina"
TRABAJADOR = "trabajador"
TODOS = (DUENO, OFICINA, TRABAJADOR)

NOMBRES_PERFIL = {DUENO: "Dueño", OFICINA: "Oficina", TRABAJADOR: "Trabajador"}

# Pantallas en el orden del menú. "perfiles": quién la ve.
PANTALLAS = [
    {"id": "bandeja", "titulo": "Bandeja", "icono": "✉️", "perfiles": {DUENO, OFICINA}},
    {"id": "documentos", "titulo": "Documentos", "icono": "📄", "perfiles": {DUENO, OFICINA}},
    {"id": "proveedores", "titulo": "Proveedores", "icono": "🚚", "perfiles": {DUENO, OFICINA}},
    {"id": "recepcion", "titulo": "Recepción", "icono": "📦", "perfiles": {DUENO, OFICINA, TRABAJADOR}},
    {"id": "hoy", "titulo": "Hoy", "icono": "☀️", "perfiles": {DUENO, OFICINA, TRABAJADOR}},
    {"id": "cuadro", "titulo": "Cuadro del día", "icono": "💶", "perfiles": {DUENO, OFICINA}},
    {"id": "carta", "titulo": "Carta", "icono": "🍽️", "perfiles": {DUENO, OFICINA}},
    {"id": "competencia", "titulo": "Competencia", "icono": "🔎", "perfiles": {DUENO}},
    {"id": "personal", "titulo": "Personal", "icono": "👥", "perfiles": {DUENO, OFICINA, TRABAJADOR}},
    {"id": "dueno", "titulo": "Dueño", "icono": "📊", "perfiles": {DUENO}},
    {"id": "asistente", "titulo": "Asistente", "icono": "💬", "perfiles": {DUENO, OFICINA}},
    {"id": "ajustes", "titulo": "Ajustes", "icono": "⚙️", "perfiles": {DUENO}},
]
PANTALLA_INICIO = {DUENO: "hoy", OFICINA: "bandeja", TRABAJADOR: "hoy"}

# Datos sensibles: quién los ve. Cada plantilla y cada consulta pregunta con `puede_ver`.
DATOS_SENSIBLES = {
    "salarios_por_persona": {DUENO},          # nóminas, coste por hora de cada persona
    "nominas": {DUENO},                      # documentos de nómina
    "precios_compra": {DUENO, OFICINA},      # lo que cobra cada proveedor
    "costes_y_margenes": {DUENO, OFICINA},   # coste y margen de platos
    "precios_venta": {DUENO, OFICINA},       # el trabajador no ve ningún precio
    "banco": {DUENO},                        # saldo y movimientos
    "cuadrante_de_todos": {DUENO, OFICINA},  # el trabajador solo ve su turno
}

# Perfiles que se pueden usar ahora mismo. En la demo, solo el dueño.
PERFILES_ACTIVOS = {DUENO}


def puede_ver_pantalla(perfil: str, pantalla_id: str) -> bool:
    return any(p["id"] == pantalla_id and perfil in p["perfiles"] for p in PANTALLAS)


def puede_ver(perfil: str, dato: str) -> bool:
    if dato not in DATOS_SENSIBLES:
        raise KeyError(f"Dato sensible sin regla: {dato}")
    return perfil in DATOS_SENSIBLES[dato]


def menu_para(perfil: str) -> list[dict]:
    return [p for p in PANTALLAS if perfil in p["perfiles"]]


def perfil_activo(perfil: str) -> bool:
    return perfil in PERFILES_ACTIVOS
