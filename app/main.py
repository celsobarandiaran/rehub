"""ReHub: la app web. Arranca con:  python -m uvicorn app.main:app"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from datetime import date, timedelta

from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from . import almacen, auth, calculos, config, db, demo, gmail, ia, perfiles, procesar, vistas

AQUI = Path(__file__).resolve().parent


@asynccontextmanager
async def arranque(app: FastAPI):
    faltan = config.problemas_de_configuracion()
    if faltan:
        raise RuntimeError("Faltan variables de entorno: " + ", ".join(faltan))
    db.crear_tablas()
    # Si quedaron fotos o correos por leer (por ejemplo, se acabó el tope de la IA ayer), se retoman al arrancar.
    if demo._contar_pendientes():
        demo._asegurar_hilo_ia()
    if gmail.conectado():
        demo.arrancar_sondeo_gmail()  # mira la bandeja cada minuto
    yield


app = FastAPI(title="ReHub", lifespan=arranque, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
plantillas = Jinja2Templates(directory=AQUI / "plantillas")
plantillas.env.globals.update(config=config, perfiles=perfiles, timedelta=timedelta)

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
    q = request.query_params
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        contexto["hoy"] = hoy
        if pantalla_id == "bandeja":
            contexto.update(vistas.bandeja(s, q.get("cat"), int(q["id"]) if q.get("id", "").isdigit() else None, perfil))
        elif pantalla_id == "ajustes":
            contexto["estado_demo"] = demo.ESTADO.json()
        elif contexto["hay_datos"]:
            if pantalla_id == "hoy":
                st = calculos.stock(s, hoy)
                contexto.update(prevision=calculos.prevision(s, hoy), empujar=calculos.platos_a_empujar(s, hoy), avisos=vistas.avisos(s, hoy),
                                caducan=st["caducan"], caja=calculos.caja_30_dias(s, hoy) if perfiles.puede_ver(perfil, "banco") else None)
            elif pantalla_id == "cuadro":
                contexto.update(vistas.cuadro_del_dia(s, hoy, q.get("fecha")))
            elif pantalla_id == "carta":
                contexto.update(carta=calculos.carta(s, hoy), tipos=calculos.TIPOS, parte=q.get("parte", "comida"))
            elif pantalla_id == "dueno":
                contexto.update(d=calculos.dueno(s, hoy), banco=calculos.banco(s, hoy), caja=calculos.caja_30_dias(s, hoy), normal=calculos.NORMAL)
            elif pantalla_id == "personal":
                lunes = date.fromisoformat(q["semana"]) if q.get("semana") else (hoy + timedelta(days=1) if hoy.weekday() == 6 else hoy - timedelta(days=hoy.weekday()))
                contexto.update(calculos.personal_semana(s, lunes), ver_salarios=perfiles.puede_ver(perfil, "salarios_por_persona"),
                                ver_todos=perfiles.puede_ver(perfil, "cuadrante_de_todos"), usuario_empleado=None)
            elif pantalla_id == "recepcion":
                contexto.update(vistas.recepcion(s, hoy, perfil))
            elif pantalla_id == "proveedores":
                contexto.update(lista=calculos.proveedores(s, hoy))
                sel = int(q["id"]) if q.get("id", "").isdigit() else (contexto["lista"][0]["p"].id if contexto["lista"] else None)
                contexto.update(ficha=calculos.ficha_proveedor(s, sel) if sel else {}, mercabarna=vistas.MERCABARNA)
            elif pantalla_id == "competencia":
                contexto.update(vistas.competencia(s, hoy, int(q["id"]) if q.get("id", "").isdigit() else None))
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


# ---------------------------------------------------------------- acciones de las pantallas
def _num(texto: str) -> float | None:
    t = (texto or "").replace("€", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(t) if t else None
    except ValueError:
        return None


@app.post("/api/cierre/{cierre_id}/contado")
def api_contado(request: Request, cierre_id: int, contado: str = Form("")):
    if not perfiles.puede_ver(request.state.perfil, "costes_y_margenes"):
        raise HTTPException(403)
    with db.SesionDB() as s:
        c = s.get(db.Cierre, cierre_id)
        if not c:
            raise HTTPException(404)
        c.efectivo_contado = _num(contado)
        s.commit()
        fondo = calculos.ajuste(s, "fondo_caja", 150.0)
        gastos = sum(g.total or 0 for g in s.scalars(select(db.Documento).where(db.Documento.tipo == "gasto", db.Documento.fecha == c.fecha)))
        esperada = round(fondo + c.efectivo - gastos, 2)
        return {"descuadre": round(c.efectivo_contado - esperada, 2) if c.efectivo_contado is not None else None}


@app.post("/api/plato/{plato_id}")
async def api_plato(request: Request, plato_id: int):
    """Cambiar precio de carta y cantidades de la receta; el margen se recalcula al momento."""
    if not perfiles.puede_ver(request.state.perfil, "costes_y_margenes"):
        raise HTTPException(403)
    form = await request.form()
    with db.SesionDB() as s:
        p = s.get(db.Plato, plato_id)
        if not p:
            raise HTTPException(404)
        precio = _num(form.get("precio_carta", ""))
        if precio is None or precio <= 0:
            return JSONResponse({"error": "El precio no es válido."}, status_code=400)
        p.precio_carta = precio
        for i, l in enumerate(p.receta):
            c = _num(form.get(f"cantidad_{i}", ""))
            if c is not None and c >= 0:
                l.cantidad = c
        s.commit()
    return {"ok": True}


@app.post("/api/recuento")
async def api_recuento(request: Request):
    """Recuento de la cámara: producto -> cantidad contada. Lo que no se manda no cambia."""
    form = await request.form()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        n = 0
        for k, v in form.items():
            if k.startswith("prod_") and k[5:].isdigit():
                c = _num(v)
                if c is not None:
                    s.add(db.Recuento(fecha=hoy, producto_id=int(k[5:]), cantidad_contada=c))
                    n += 1
        s.commit()
    return {"ok": True, "guardados": n}


@app.post("/api/turno")
def api_turno(request: Request, empleado_id: int = Form(...), fecha: str = Form(...), tramos: str = Form("")):
    """tramos: '10:00-18:00' o '12:30-16:30,20:00-24:00' o vacío (libre)."""
    if not perfiles.puede_ver(request.state.perfil, "cuadrante_de_todos"):
        raise HTTPException(403)
    lista = []
    for t in [x.strip() for x in tramos.split(",") if x.strip()]:
        try:
            a, b = t.split("-")
            lista.append([a.strip(), b.strip()])
        except ValueError:
            return JSONResponse({"error": "Escribe las horas así: 12:30-16:30,20:00-24:00"}, status_code=400)
    with db.SesionDB() as s:
        f = date.fromisoformat(fecha)
        t = s.scalar(select(db.Turno).where(db.Turno.empleado_id == empleado_id, db.Turno.fecha == f))
        if t:
            t.tramos = lista
        else:
            s.add(db.Turno(empleado_id=empleado_id, fecha=f, tramos=lista))
        s.commit()
    return {"ok": True}


# ---------------------------------------------------------------- correo
@app.post("/api/correo/revisar")
def api_correo_revisar(request: Request):
    """Lee ahora mismo lo nuevo de la bandeja de Gmail."""
    try:
        n = demo.revisar_gmail()
    except gmail.GmailNoConectado:
        return JSONResponse({"error": "Gmail no está conectado."}, status_code=409)
    except Exception as e:
        return JSONResponse({"error": f"No se pudo leer el correo: {e}"}, status_code=502)
    return {"ok": True, "nuevos": n}


@app.post("/api/correo/{correo_id}/enviar")
def api_correo_enviar(request: Request, correo_id: int, texto: str = Form("")):
    """Nada se envía sin pulsar Enviar: aquí es donde se pulsa."""
    if request.state.perfil == perfiles.TRABAJADOR:
        raise HTTPException(403)
    with db.SesionDB() as s:
        c = s.get(db.Correo, correo_id)
        if not c:
            raise HTTPException(404)
        texto = texto.strip() or c.respuesta_propuesta
        if not texto:
            return JSONResponse({"error": "No hay texto que enviar."}, status_code=400)
        try:
            # La reserva o consulta llegó desde un alias de la propia cuenta: la respuesta vuelve a esa dirección.
            para = config.GMAIL_CUENTA.replace("@", f"+{c.alias}@") if c.alias else config.GMAIL_CUENTA
            gmail.enviar(para, "Re: " + c.asunto, texto, responde_a=c.gmail_id)
        except gmail.GmailNoConectado:
            return JSONResponse({"error": "Gmail no está conectado: no se puede enviar."}, status_code=409)
        c.respuesta_propuesta, c.respuesta_enviada = texto, True
        s.commit()
    return {"ok": True}


@app.post("/api/demo/enviar_correo")
def api_demo_enviar_correo(request: Request):
    """Manda los 15 correos de demo desde los alias para verlos llegar y clasificarse en directo."""
    _solo_dueno(request)
    try:
        n = demo.enviar_en_directo()
    except gmail.GmailNoConectado:
        return JSONResponse({"error": "Gmail no está conectado."}, status_code=409)
    return {"ok": True, "enviados": n}


@app.post("/api/autodestruir")
def api_autodestruir(request: Request, confirmacion: str = Form("")):
    _solo_dueno(request)
    if confirmacion.strip() != "DESTRUIR":
        return JSONResponse({"error": "Escribe DESTRUIR para confirmar."}, status_code=400)
    from . import autodestruir
    return autodestruir.ejecutar()


@app.post("/api/competidor")
async def api_competidor(request: Request):
    """Añadir un competidor: nombre, distancia, valoración y su carta (foto o enlace, leída por la IA)."""
    _solo_dueno(request)
    form = await request.form()
    nombre = (form.get("nombre") or "").strip()
    if not nombre:
        return JSONResponse({"error": "Falta el nombre."}, status_code=400)
    carta = {}
    archivo = form.get("archivo")
    contenido = await archivo.read() if archivo is not None and getattr(archivo, "filename", "") else b""
    if contenido:
        try:
            carta = procesar.leer_carta_competidor(contenido, archivo.content_type or "image/jpeg")
        except (ia.SinIA, ia.CuotaAgotada):
            return JSONResponse({"error": "La IA no está disponible ahora para leer la carta; prueba más tarde."}, status_code=503)
    with db.SesionDB() as s:
        c = db.Competidor(nombre=nombre, distancia_m=int(_num(form.get("distancia_m", "")) or 0), valoracion=_num(form.get("valoracion", "")),
                          opiniones=0, carta=carta)
        s.add(c)
        s.commit()
        return {"ok": True, "id": c.id, "productos": len(carta)}


@app.post("/api/ajuste")
def api_ajuste(request: Request, clave: str = Form(...), valor: str = Form("")):
    _solo_dueno(request)
    if clave not in ("dias_apertura_mes", "minimo_caja", "margen_objetivo", "fondo_caja", "valoracion_google", "iva_trimestre_confirmado"):
        raise HTTPException(400)
    with db.SesionDB() as s:
        s.merge(db.Ajuste(clave=clave, valor=valor.replace(",", ".")))
        s.commit()
    return {"ok": True}


@app.get("/manifest.json")
def manifiesto():
    """Para 'Añadir a pantalla de inicio' en el móvil y la tablet, con icono."""
    return JSONResponse({
        "name": "ReHub", "short_name": "ReHub", "start_url": "/", "display": "standalone",
        "background_color": "#faf7f2", "theme_color": "#1f4d3a",
        "icons": [{"src": "/static/icono-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/static/icono-512.png", "sizes": "512x512", "type": "image/png"}],
    })
