"""ReHub: la app web. Arranca con:  python -m uvicorn app.main:app"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from datetime import date

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response

from . import almacen, auth, config, db, demo, ia, perfiles, procesar, vistas

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
    return JSONResponse({"ok": True, "base_de_datos": db.base_responde(), "ia": ia.disponible(), "almacen": config.ALMACEN,
                         "version": config.VERSION})


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
    contexto = {"menu": perfiles.menu_para(perfil), "actual": pantalla_id, "pantalla": info, "perfil": perfil, "eur": vistas.eur,
                "hay_datos": demo.hay_datos()}
    with db.SesionDB() as s:
        if pantalla_id == "bandeja":
            q = request.query_params
            contexto.update(vistas.bandeja(s, q.get("cat"), int(q["id"]) if q.get("id", "").isdigit() else None, perfil))
        if pantalla_id == "ajustes":
            contexto["estado_demo"] = demo.ESTADO.json()
    plantilla = f"pantallas/{pantalla_id}.html"
    if not (AQUI / "plantillas" / plantilla).exists():
        plantilla = "pantallas/vacia.html"
    return plantillas.TemplateResponse(request, plantilla, contexto)


def _solo_dueno(request: Request):
    if request.state.perfil != perfiles.DUENO:
        raise HTTPException(403, "Solo el dueño puede hacer esto")


# ---------------------------------------------------------------- demo
@app.post("/api/demo/empezar")
def api_demo_empezar(request: Request, velocidad: float = Form(1.0)):
    _solo_dueno(request)
    try:
        demo.empezar(segundos_por_dia=1.0 / max(0.2, velocidad))
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=409)
    return demo.ESTADO.json()


@app.post("/api/demo/pausa")
def api_demo_pausa(request: Request):
    _solo_dueno(request)
    demo.ESTADO.pausa = not demo.ESTADO.pausa
    return demo.ESTADO.json()


@app.post("/api/demo/velocidad")
def api_demo_velocidad(request: Request, velocidad: float = Form(1.0)):
    _solo_dueno(request)
    demo.ESTADO.segundos_por_dia = 1.0 / max(0.2, velocidad) if velocidad < 100 else 0
    return demo.ESTADO.json()


@app.get("/api/demo/estado")
def api_demo_estado():
    e = demo.ESTADO.json()
    if not demo.ESTADO.en_marcha:
        e["ia_pendientes"] = demo._contar_pendientes()
    return e


@app.post("/api/demo/reiniciar")
def api_demo_reiniciar(request: Request):
    _solo_dueno(request)
    try:
        return demo.reiniciar()
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=409)


# ---------------------------------------------------------------- documentos
@app.get("/api/documentos")
def api_documentos(request: Request, desde: str = "", hasta: str = ""):
    with db.SesionDB() as s:
        return vistas.documentos(s, request.state.perfil, date.fromisoformat(desde) if desde else None, date.fromisoformat(hasta) if hasta else None)


@app.get("/api/factura/{doc_id}")
def api_factura(request: Request, doc_id: int):
    with db.SesionDB() as s:
        return vistas.lineas_factura(s, doc_id, request.state.perfil)


@app.get("/archivo/{doc_id}")
def archivo(request: Request, doc_id: int):
    with db.SesionDB() as s:
        d = s.get(db.Documento, doc_id)
        if not d or not d.archivo:
            raise HTTPException(404)
        if d.tipo == "nomina" and not perfiles.puede_ver(request.state.perfil, "nominas"):
            raise HTTPException(403)
        contenido = almacen.leer(d.archivo)
        nombre = d.archivo.rsplit("/", 1)[-1]
    mime = "application/pdf" if nombre.lower().endswith(".pdf") else "image/jpeg"
    return Response(contenido, media_type=mime, headers={"Content-Disposition": f'inline; filename="{nombre.encode("ascii", "replace").decode()}"'})


@app.post("/api/subir")
async def subir(request: Request, archivo: UploadFile):
    """Subir a mano un PDF o una foto (factura, ticket o etiqueta)."""
    contenido = await archivo.read()
    if len(contenido) > 15 * 1024 * 1024:
        return JSONResponse({"error": "El archivo es demasiado grande (máximo 15 MB)."}, status_code=413)
    with db.SesionDB() as s:
        c = procesar.procesar_correo(s, {"de_nombre": "Subido a mano", "alias": "subida", "asunto": archivo.filename or "Archivo",
                                         "cuerpo": ""}, [(archivo.filename or "archivo.jpg", contenido)], demo.hoy_demo(), config.NOMBRE_RESTAURANTE, origen="subida")
        s.commit()
        cid = c.id
    demo._asegurar_hilo_ia()
    return {"ok": True, "correo_id": cid}


@app.get("/manifest.json")
def manifiesto():
    """Para 'Añadir a pantalla de inicio' en el móvil y la tablet, con icono."""
    return JSONResponse({
        "name": "ReHub", "short_name": "ReHub", "start_url": "/", "display": "standalone",
        "background_color": "#faf7f2", "theme_color": "#1f4d3a",
        "icons": [{"src": "/static/icono-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/icono-512.png", "sizes": "512x512", "type": "image/png"}],
    })
