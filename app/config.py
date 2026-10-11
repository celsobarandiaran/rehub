"""Configuración de ReHub.

Todo lo que es secreto o cambia entre tu PC y la nube se lee de variables de
entorno. Nunca se escribe una clave en el código.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# "local" en tu PC, "nube" en el alojamiento
ENTORNO = os.environ.get("REHUB_ENTORNO", "local")
EN_LA_NUBE = ENTORNO == "nube"

NOMBRE_RESTAURANTE = os.environ.get("REHUB_RESTAURANTE", "Restaurante La Plaza")

# Contraseña del dueño. En la nube es obligatoria; en local hay una de prueba.
CONTRASENA_DUENO = os.environ.get("REHUB_CONTRASENA") or ("" if EN_LA_NUBE else "rehub-local")

# Clave para firmar la cookie de sesión. En la nube es obligatoria.
CLAVE_SESION = os.environ.get("REHUB_CLAVE_SESION") or ("" if EN_LA_NUBE else "solo-para-pruebas-en-local")

# Base de datos: SQLite en local; en la nube, la de Supabase (Postgres en Frankfurt).
# Carpeta de datos en local (base SQLite y archivos). Las pruebas usan otra para no borrar la de verdad.
CARPETA_LOCAL = Path(os.environ.get("REHUB_CARPETA_LOCAL") or (RAIZ / "datos_locales"))
URL_BASE_DATOS = os.environ.get("DATABASE_URL") or f"sqlite:///{CARPETA_LOCAL / 'rehub.db'}"

# Almacén de archivos (PDF y fotos): carpeta local o Supabase Storage.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_CLAVE_SERVICIO = os.environ.get("SUPABASE_SERVICE_KEY", "")
SUPABASE_CUBO = os.environ.get("SUPABASE_BUCKET", "documentos")
ALMACEN = "supabase" if (SUPABASE_URL and SUPABASE_CLAVE_SERVICIO) else "local"

# IA y correo (se usan a partir de la sesión 3)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")
GMAIL_CUENTA = os.environ.get("GMAIL_CUENTA", "laplazarehub@gmail.com")  # la cuenta de la demo, creada por Celso el 11/10/2026

VERSION = "0.2"


def problemas_de_configuracion() -> list[str]:
    """Lo que falta para arrancar con seguridad. Vacío si todo está bien."""
    faltan = []
    if not CONTRASENA_DUENO:
        faltan.append("REHUB_CONTRASENA")
    if not CLAVE_SESION:
        faltan.append("REHUB_CLAVE_SESION")
    return faltan
