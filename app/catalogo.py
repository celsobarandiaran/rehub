"""Categorías de la carta, familias de proveedores y colores de los platos.

Todo lo que es "poner nombre a las cosas" para que las pantallas lo enseñen igual.
"""
import re
import unicodedata

# Orden en que se enseñan. Las que no tengan platos no salen.
CATEGORIAS = {
    "comida": ["entrantes", "paellas y arroces", "pastas", "carnes", "pescados", "platos combinados", "bocadillos", "postres"],
    "bebida": ["cervezas", "vinos", "aguas", "refrescos", "cafés e infusiones", "licores"],
}
NOMBRE_CATEGORIA = {"entrantes": "Entrantes", "paellas y arroces": "Paellas y arroces", "pastas": "Pastas", "carnes": "Carnes", "pescados": "Pescados",
                    "platos combinados": "Platos combinados", "bocadillos": "Bocadillos", "postres": "Postres", "cervezas": "Cervezas", "vinos": "Vinos",
                    "aguas": "Aguas", "refrescos": "Refrescos", "cafés e infusiones": "Cafés e infusiones", "licores": "Licores"}

# Se mira el nombre del plato (y su clave de competencia). La primera regla que encaja, manda.
_REGLAS = {
    "bebida": [("cervezas", r"cerveza|cana\b|canya|birra|clara\b"), ("aguas", r"\bagua"), ("cafes e infusiones", r"\bcaf|\bte\b|infusi|cortado|carajillo|descafe"),
               ("licores", r"gin|ron\b|whisk|licor|chupito|coctel|mojito|vermut|cubata|brandy|orujo|tonic"),
               ("vinos", r"vino|cava|copa|tinto|blanco|rosado|sangria|champ"), ("refrescos", r"refresc|cola|zumo|nestea|aquarius|limonada|fanta|tonica")],
    "comida": [("postres", r"crema catalana|flan|arroz con leche|tarta|helado|postre|brownie|coulant|fruta|yogur|tiramis|mel i mato|pastel|sorbete"),
               ("entrantes", r"brava|croqueta|pan con tomate|tortilla|ensalada|escalivada|jamon|huevos|mejillon|nacho|tabla|anchoa|boqueron|pimiento|esqueixada|queso|patatas|aceituna|hummus|sopa|crema de"),
               ("paellas y arroces", r"arroz|paella|fideu|risotto"), ("pastas", r"canelon|pasta|macarron|espaguet|lasan|noqui|raviol|tallarin|fideos"),
               ("bocadillos", r"bocadillo|bocata|entrepa|sandwich|montadito|burger|hamburguesa"), ("platos combinados", r"combinado|menu del dia|plato del dia"),
               ("carnes", r"entrecot|solomillo|pollo|butifarra|carne|cerdo|ternera|cordero|chuleta|costilla|secreto|presa|pato|conejo|lomo|escalopa|magret|galta|pies de"),
               ("pescados", r"lubina|bacalao|merluza|calamar|gamba|pulpo|sepia|dorada|salmon|atun|rape|marisco|almeja|langostino|pescado|sardina|chipiron|navaja|cigala|bogavante")],
}
# Las claves de las reglas van sin acento para comparar; aquí se traducen al nombre oficial.
_SIN_ACENTO = {"cafes e infusiones": "cafés e infusiones"}

TIPO_COLOR = {"estrella": ("verde", "#2e7d4f", "Vende mucho y deja mucho: mantener"),
              "vaca": ("azul", "#2c4f9e", "Vende mucho pero deja poco: subir precio o bajar coste"),
              "puzle": ("amarillo", "#d9a441", "Deja mucho pero vende poco: darle visibilidad"),
              "perro": ("rojo", "#c0392b", "Vende poco y deja poco: cambiar o quitar")}


def _plano(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def categoria_de(nombre: str, clave: str = "", parte: str = "comida") -> str:
    texto = _plano(f"{nombre} {clave}")
    for cat, patron in _REGLAS.get(parte, _REGLAS["comida"]):
        if re.search(patron, texto):
            return _SIN_ACENTO.get(cat, cat)
    return "entrantes" if parte == "comida" else "refrescos"


def categoria_clave(clave: str) -> tuple[str, str]:
    """Para un plato de la competencia (solo tenemos su clave): (parte, categoría)."""
    texto = _plano(clave)
    for cat, patron in _REGLAS["bebida"]:
        if re.search(patron, texto):
            return "bebida", _SIN_ACENTO.get(cat, cat)
    return "comida", categoria_de(clave, "", "comida")


def parte_de_categoria(categoria: str) -> str:
    return "bebida" if categoria in CATEGORIAS["bebida"] else "comida"


def familia_de(grupo: str, tipo: str) -> str:
    """comida / bebida / local / servicios, a partir del grupo de coste y de lo que suministra."""
    t = _plano(tipo)
    if grupo == "comida":
        return "bebida" if re.search(r"bebida|vino|caf|cerveza|refresc|licor|agua|cava", t) else "comida"
    if re.search(r"limpieza|gestor|asesor|program|software|public|marketing|tpv|internet|telef|movil|segur(idad)?\b.*alarma|alarma|web|informat", t):
        return "servicios"
    return "local"


NOMBRE_FAMILIA = {"comida": "🍽️ Comida", "bebida": "🍷 Bebida", "local": "🏠 Local", "servicios": "🧾 Servicios"}
FAMILIAS = ["comida", "bebida", "local", "servicios"]
