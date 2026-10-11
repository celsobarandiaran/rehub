"""ReHub: la app web. Arranca con:  python -m uvicorn app.main:app"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, config, db, perfiles

AQUI = Path(__file__).resolve().parent


@asynccontextmanager
async def arranque(app: FastAPI):
    faltan = config.problemas_de_configuracion()
    if faltan:
        raise RuntimeError("Faltan variables de entorno: " + ", ".join(faltan))
    db.crear_tablas()
    yield


app = FastAPI(title="ReHub", lifespan=arranque, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
plantillas = Jinja2Templates(directory=AQUI / "plantillas")
plantillas.env.globals.update(config=config, perfiles=perfiles)

LIBRES = ("/entrar", "/salud", "/despertando", "/static", "/favicon.ico", "/manifest.json")


@app.middleware("http")
async def exigir_entrada(request: Request, call_next):
    """Sin sesión válida solo se ven la entrada, la salud y la página de despertar."""
    ruta = request.url.path
    if ruta.startswith(LIBRES):
        return await call_next(request)
    sesion = auth.leer_sesion(request.cookies.get(auth.COOKIE))
    if not sesion or not perfiles.perfil_activo(sesion["p"]):
        return RedirectResponse("/entrar", status_code=303)
    request.state.perfil = sesion["p"]
    request.state.usuario = sesion["u"]
    return await call_next(request)


@app.get("/salud")
def salud():
    """La usa la página de despertar y el aviso diario que mantiene la app despierta."""
    return JSONResponse({"ok": True, "base_de_datos": db.base_responde(), "version": config.VERSION})


@app.get("/despertando", response_class=HTMLResponse)
def despertando(request: Request):
    return plantillas.TemplateResponse(request, "despertando.html")


@app.get("/entrar", response_class=HTMLResponse)
def entrar_form(request: Request):
    return plantillas.TemplateResponse(request, "entrar.html", {"error": ""})


@app.post("/entrar")
def entrar(request: Request, clave: str = Form("")):
    if auth.comprobar_dueno(clave):
        r = RedirectResponse("/", status_code=303)
        r.set_cookie(auth.COOKIE, auth.crear_sesion(0, perfiles.DUENO), max_age=auth.DURACION_SEGUNDOS,
                     httponly=True, samesite="lax", secure=config.EN_LA_NUBE)
        return r
    return plantillas.TemplateResponse(request, "entrar.html", {"error": "Contraseña incorrecta."}, status_code=401)


@app.get("/salir")
def salir():
    r = RedirectResponse("/entrar", status_code=303)
    r.delete_cookie(auth.COOKIE)
    return r


@app.get("/")
def inicio(request: Request):
    return RedirectResponse(f"/p/{perfiles.PANTALLA_INICIO[request.state.perfil]}", status_code=303)


@app.get("/p/{pantalla_id}", response_class=HTMLResponse)
def pantalla(request: Request, pantalla_id: str):
    perfil = request.state.perfil
    if not perfiles.puede_ver_pantalla(perfil, pantalla_id):
        return plantillas.TemplateResponse(request, "no_permitido.html", {"menu": perfiles.menu_para(perfil), "actual": ""}, status_code=403)
    info = next(p for p in perfiles.PANTALLAS if p["id"] == pantalla_id)
    contexto = {"menu": perfiles.menu_para(perfil), "actual": pantalla_id, "pantalla": info, "perfil": perfil}
    plantilla = f"pantallas/{pantalla_id}.html"
    if not (AQUI / "plantillas" / plantilla).exists():
        plantilla = "pantallas/vacia.html"
    return plantillas.TemplateResponse(request, plantilla, contexto)


@app.get("/manifest.json")
def manifiesto():
    """Para 'Añadir a pantalla de inicio' en el móvil y la tablet, con icono."""
    return JSONResponse({
        "name": "ReHub", "short_name": "ReHub", "start_url": "/", "display": "standalone",
        "background_color": "#faf7f2", "theme_color": "#1f4d3a",
        "icons": [{"src": "/static/icono-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/icono-512.png", "sizes": "512x512", "type": "image/png"}],
    })
