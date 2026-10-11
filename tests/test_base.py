"""Pruebas de la base: contraseña, perfiles y pantallas."""
import os

os.environ.setdefault("REHUB_ENTORNO", "local")
os.environ.setdefault("DATABASE_URL", "sqlite://")  # base en memoria para las pruebas

from fastapi.testclient import TestClient  # noqa: E402

from app import auth, perfiles  # noqa: E402
from app.main import app  # noqa: E402


def cliente():
    return TestClient(app)


def test_sin_contrasena_te_manda_a_entrar():
    with cliente() as c:
        r = c.get("/p/hoy", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/entrar"


def test_contrasena_mala_no_entra():
    with cliente() as c:
        r = c.post("/entrar", data={"clave": "mala"}, follow_redirects=False)
        assert r.status_code == 401
        assert auth.COOKIE not in r.cookies


def test_dueno_entra_y_ve_las_11_pantallas():
    with cliente() as c:
        r = c.post("/entrar", data={"clave": "rehub-local"}, follow_redirects=False)
        assert r.status_code == 303
        for p in perfiles.PANTALLAS:
            assert c.get(f"/p/{p['id']}").status_code == 200, p["id"]


def test_salud_responde_sin_contrasena():
    with cliente() as c:
        d = c.get("/salud").json()
        assert d["ok"] and d["base_de_datos"]


def test_reglas_de_perfiles():
    assert perfiles.puede_ver_pantalla("oficina", "bandeja")
    assert not perfiles.puede_ver_pantalla("oficina", "dueno")
    assert not perfiles.puede_ver_pantalla("trabajador", "carta")
    assert perfiles.puede_ver_pantalla("trabajador", "recepcion")
    assert not perfiles.puede_ver("oficina", "salarios_por_persona")
    assert not perfiles.puede_ver("trabajador", "precios_venta")
    assert perfiles.puede_ver("dueno", "banco")


def test_perfil_sin_activar_no_entra_aunque_tenga_cookie():
    with cliente() as c:
        c.cookies.set(auth.COOKIE, auth.crear_sesion(5, "oficina"))
        r = c.get("/p/bandeja", follow_redirects=False)
        assert r.status_code == 303


def test_hash_de_claves():
    h = auth.hash_clave("secreta")
    assert auth.clave_correcta("secreta", h) and not auth.clave_correcta("otra", h)
