"""Tanda 3 de cambios: categorías de la carta, proveedores por familias, faltas, albaranes, competencia por categorías, asistente."""
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import asistente, calculos, catalogo, db, demo, procesar, vistas
from app.main import app


def _demo_cargada():
    """Carga la demo entera (sin IA) una sola vez por sesión de pruebas."""
    db.crear_tablas()
    with db.SesionDB() as s:
        if s.scalar(select(db.Plato.id).limit(1)):
            return
    demo.reiniciar()
    demo.empezar(segundos_por_dia=0)
    import time
    while demo.ESTADO.en_marcha:
        time.sleep(0.2)
    for _ in range(300):
        if demo._hilo_ia is None or not demo._hilo_ia.is_alive():
            break
        time.sleep(0.2)


def _dueno():
    c = TestClient(app)
    c.post("/entrar", data={"clave": "rehub-local"}, follow_redirects=False)
    return c


def test_categorias_de_la_carta():
    assert catalogo.categoria_de("Arroz negro", "arroz negro", "comida") == "paellas y arroces"
    assert catalogo.categoria_de("Crema catalana", "", "comida") == "postres"
    assert catalogo.categoria_de("Canelones de la abuela", "", "comida") == "pastas"
    assert catalogo.categoria_de("Entrecot a la brasa", "", "comida") == "carnes"
    assert catalogo.categoria_de("Patatas bravas", "", "comida") == "entrantes"
    assert catalogo.categoria_de("Copa de cava", "", "bebida") == "vinos"
    assert catalogo.categoria_de("Café con leche", "", "bebida") == "cafés e infusiones"
    assert catalogo.categoria_clave("gin tonic") == ("bebida", "licores")
    assert catalogo.categoria_clave("pulpo") == ("comida", "pescados")
    assert catalogo.familia_de("comida", "Vino y café") == "bebida"
    assert catalogo.familia_de("local", "Limpieza") == "servicios"
    assert catalogo.familia_de("local", "Luz") == "local"


def test_carta_por_categorias_colores_y_competencia_en_palabras():
    _demo_cargada()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        c = calculos.carta(s, hoy)
    nombres = [cat["id"] for cat in c["por_categoria"]["comida"]]
    assert nombres == [x for x in catalogo.CATEGORIAS["comida"] if x in nombres]  # orden fijo
    assert {"entrantes", "paellas y arroces", "pastas", "carnes", "pescados", "postres"} <= set(nombres)
    assert [cat["id"] for cat in c["por_categoria"]["bebida"]] == ["cervezas", "vinos", "aguas", "refrescos", "cafés e infusiones", "licores"]
    colores = {f["color"] for f in c["filas"]}
    assert colores <= {"verde", "azul", "amarillo", "rojo"} and len(colores) >= 3
    bravas = next(f for f in c["filas"] if f["nombre"] == "Patatas bravas")
    assert bravas["comp_texto"].startswith("lo tienen todos tus competidores, a ") and "€ de media" in bravas["comp_texto"]
    solo = next(f for f in c["filas"] if f["comp_n"] == 0)
    assert solo["comp_texto"] == "nadie más lo tiene"
    assert any(e["texto"].startswith("lo tienen") or e["texto"].startswith("lo tiene") for e in c["ellos"])
    assert len(c["leyenda"]) == 4


def test_proveedores_por_familias_y_faltas():
    _demo_cargada()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        pr = calculos.proveedores(s, hoy)
        faltas = calculos.faltas(s, hoy)
        ficha = calculos.ficha_proveedor(s, s.scalar(select(db.Proveedor).where(db.Proveedor.nombre == "Pescados Mar Nou")).id)
    grupos = {g["id"]: [x["p"].nombre for x in g["proveedores"]] for g in pr["grupos"]}
    assert "Bebidas Sol" in grupos["bebida"] and "Vins i Cafès Roca" in grupos["bebida"]
    assert "Pescados Mar Nou" in grupos["comida"] and "Endesa" in grupos["local"] and "Neteges Brillant" in grupos["servicios"]
    pescados = next(x for x in pr["todos"] if x["p"].nombre == "Pescados Mar Nou")
    assert pescados["n_facturas"] >= 15 and pescados["total"] > 1000 and "Calamar" in pescados["suministra"]
    assert isinstance(faltas, list) and all({"producto", "dias", "proveedor"} <= set(f) for f in faltas)
    # Vista A: una columna por factura; la lubina sube un 16 % el 01/10
    assert len(ficha["matriz"]["columnas"]) >= 15
    lubina = next(f for f in ficha["matriz"]["filas"] if f["producto"] == "Lubina fresca")
    assert 16 in lubina["cambios"].values() and lubina["mercabarna"]
    assert ficha["familia"] == "comida"


def test_competencia_por_categorias_y_resumen():
    _demo_cargada()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        arco = s.scalar(select(db.Competidor).where(db.Competidor.nombre.like("Taberna del Arco%")))
        v = vistas.competencia(s, hoy, arco.id)
    cats = {(c["parte"], c["id"]) for c in v["por_categoria"]}
    assert ("comida", "entrantes") in cats and ("bebida", "cervezas") in cats
    assert "pastas" in v["sin"]
    r = v["resumen"]
    assert r["tengo_yo"] and r["tienen_ellos"] and isinstance(r["mas_caro"], list)
    assert any("arroz negro" in x and "16,90" in x and "17,90" in x for x in r["cambios"]), r["cambios"]
    assert any("quitado paella" in x for x in r["cambios"])


def test_bandeja_por_periodo():
    _demo_cargada()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        mes = vistas.bandeja(s, None, None, "dueno", hoy.replace(day=1), hoy)
        todo = vistas.bandeja(s, None, None, "dueno", None, None)
        sept = vistas.bandeja(s, None, None, "dueno", date(2026, 9, 1), date(2026, 9, 30))
    assert 0 < mes["total"] < todo["total"]
    assert all(date(2026, 9, 1) <= f["c"].recibido.date() <= date(2026, 9, 30) for f in sept["filas"])


def test_albaran_casa_con_la_factura_y_avisa_si_falta_genero():
    _demo_cargada()
    with db.SesionDB() as s:
        hoy = calculos.hoy_demo(s)
        d = {"tipo": "albaran", "proveedor": "Pescados Mar Nou", "numero": "ALB-0291", "fecha": date(2026, 10, 10), "total": None,
             "lineas": [{"descripcion": "Mejillón", "cantidad": 4.9, "unidad": "kg", "precio_unitario": None, "importe": None},
                        {"descripcion": "Lubina fresca", "cantidad": 1.7, "unidad": "kg", "precio_unitario": None, "importe": None}], "revisar": []}
        doc = procesar.guardar_albaran(s, d, "", "subida", None, hoy)
        s.commit()
        assert doc.datos["factura"] == "F-2026-0291"
        assert doc.datos["diferencias"] and doc.datos["diferencias"][0].startswith("Mejillón: te facturan 5.4")
        aviso = s.scalar(select(db.Aviso).where(db.Aviso.tipo == "albaran"))
        assert aviso and "Reclama" in aviso.texto
        entrada = s.scalar(select(db.Entrada).join(db.Documento, db.Entrada.documento_id == db.Documento.id)
                           .where(db.Documento.numero == "F-2026-0291", db.Entrada.producto_id == s.scalar(select(db.Producto.id).where(db.Producto.nombre == "Mejillón"))))
        assert abs(entrada.cantidad - 4.9) < 0.01  # lo que llegó manda sobre lo facturado


def test_api_receta_clave_y_competencia():
    _demo_cargada()
    with _dueno() as c:
        with db.SesionDB() as s:
            calamar = s.scalar(select(db.Producto.id).where(db.Producto.nombre == "Calamar limpio"))
            arroz = s.scalar(select(db.Producto.id).where(db.Producto.nombre == "Arroz bomba"))
        r = c.post("/api/receta", data={"categoria": "paellas y arroces", "nombre": "Arroz de calamar (prueba)", "precio_carta": "15,50",
                                        "producto_0": str(calamar), "cantidad_0": "0,15", "producto_1": str(arroz), "cantidad_1": "0,1"}).json()
        assert r["ok"]
        with db.SesionDB() as s:
            p = s.get(db.Plato, r["id"])
            assert p.categoria == "paellas y arroces" and p.parte == "comida" and len(p.receta) == 2
            hoy = calculos.hoy_demo(s)
            fila = next(f for f in calculos.carta(s, hoy)["filas"] if f["id"] == p.id)
            assert fila["coste"] > 0 and fila["categoria"] == "paellas y arroces"
        assert c.post("/api/receta", data={"categoria": "carnes", "nombre": "", "precio_carta": "10"}).status_code == 400
        assert c.post(f"/api/plato/{r['id']}/clave", data={"clave": "arroz negro"}).json()["ok"]
        assert c.post("/api/competencia/ocultar", data={"clave": "pulpo"}).json()["ok"]
        with db.SesionDB() as s:
            assert "pulpo" in calculos.claves_ocultas(s)
            assert not any(e["clave"] == "pulpo" for e in calculos.carta(s, calculos.hoy_demo(s))["ellos"])
            comp = s.scalar(select(db.Competidor))
        assert c.post("/api/competencia/anadir", data={"competidor_id": comp.id, "clave": "tarta de queso", "precio": "6,50"}).json()["ok"]
        with db.SesionDB() as s:
            assert s.get(db.Competidor, comp.id).carta["tarta de queso"] == 6.5
        assert c.get("/p/carta").status_code == 200 and c.get("/p/competencia").status_code == 200


def test_asistente_sin_ia_responde_con_datos_y_guarda_la_charla():
    _demo_cargada()
    with _dueno() as c:
        r = c.post("/api/asistente", data={"pregunta": "¿Cuánto vendí el sábado pasado?", "pantalla": "hoy"}).json()
        assert r["sin_ia"] and r["fuente"] == "cuadro" and "sábado" in r["respuesta"]
        r2 = c.post("/api/asistente", data={"pregunta": "¿Cómo subo un extracto del banco?", "pantalla": "hoy"}).json()
        assert r2["fuente"] == "ayuda" and "extracto" in r2["respuesta"].lower()
        assert c.get("/p/asistente").status_code == 200
        assert "Conversaciones anteriores" in c.get("/p/asistente").text
    with db.SesionDB() as s:
        assert s.scalar(select(db.Charla.id).where(db.Charla.pregunta.like("%extracto%")))
        ctx = asistente.contexto(s, calculos.hoy_demo(s), "dueno")
        assert "PANTALLA carta" in ctx and "Punto de equilibrio" in ctx and "CÓMO SE USA" in ctx
