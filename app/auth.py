"""Entrada con contraseña y sesión firmada en una cookie."""
import hashlib
import hmac
import os

from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import config
from .perfiles import DUENO

COOKIE = "rehub_sesion"
DURACION_SEGUNDOS = 60 * 60 * 24 * 30  # 30 días: el dueño no tiene que entrar cada vez

_firmador = URLSafeTimedSerializer(config.CLAVE_SESION or "sin-clave", salt="rehub-sesion")


def hash_clave(clave: str) -> str:
    sal = os.urandom(16)
    h = hashlib.scrypt(clave.encode(), salt=sal, n=2**14, r=8, p=1)
    return sal.hex() + ":" + h.hex()


def clave_correcta(clave: str, guardado: str) -> bool:
    try:
        sal_hex, h_hex = guardado.split(":")
        h = hashlib.scrypt(clave.encode(), salt=bytes.fromhex(sal_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(h.hex(), h_hex)
    except ValueError:
        return False


def comprobar_dueno(clave: str) -> bool:
    """El dueño entra con la contraseña de la variable de entorno REHUB_CONTRASENA."""
    return bool(config.CONTRASENA_DUENO) and hmac.compare_digest(clave.encode(), config.CONTRASENA_DUENO.encode())


def crear_sesion(usuario_id: int, perfil: str) -> str:
    return _firmador.dumps({"u": usuario_id, "p": perfil})


def leer_sesion(valor: str | None) -> dict | None:
    if not valor:
        return None
    try:
        datos = _firmador.loads(valor, max_age=DURACION_SEGUNDOS)
    except BadSignature:
        return None
    if datos.get("p") not in (DUENO, "oficina", "trabajador"):
        return None
    return datos
