"""Cargar demo (línea de tiempo: 1 día = 1 segundo), Reiniciar y Autodestruir."""
import json
import threading
import time
from collections import deque
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select

from . import almacen, config, db, ia, procesar
from .db import (Ajuste, Aviso, Cierre, Competidor, Correo, Documento, Empleado, Entrada, Evento, LineaDocumento, LineaReceta,
                 MovimientoBanco, PagoFijo, Plato, Producto, Proveedor, Recuento, SesionDB, Turno)

DEMO = config.RAIZ / "datos_demo"
INICIO, FIN = date(2026, 8, 1), date(2026, 10, 11)  # el 11 solo llega el cierre de caja del 10


class Estado:
    def __init__(self):
        self.reset()

    def reset(self):
        self.en_marcha = False
        self.pausa = False
        self.dia = None
        self.n_dia = 0
        self.total_dias = (FIN - INICIO).days + 1
        self.segundos_por_dia = 1.0
        self.ticker = deque(maxlen=12)
        self.contadores = {"facturas": 0, "gastos": 0, "nominas": 0, "cierres": 0, "correos": 0, "ventas": 0.0}
        self.ia_pendientes = 0
        self.ia_estado = ""
        self.ia_ultimo = ""
        self.terminado = False
        self.error = ""

    def json(self):
        return {"en_marcha": self.en_marcha, "pausa": self.pausa, "dia": self.dia.isoformat() if self.dia else None, "n_dia": self.n_dia,
                "total_dias": self.total_dias, "ticker": list(self.ticker), "contadores": self.contadores, "ia_pendientes": self.ia_pendientes,
                "ia_estado": self.ia_estado, "terminado": self.terminado, "error": self.error, "segundos_por_dia": self.segundos_por_dia,
                "ia_activa": _hilo_ia is not None and _hilo_ia.is_alive(), "ia_ultimo": self.ia_ultimo}


ESTADO = Estado()
_hilo = None
_hilo_ia = None
_cerrojo = threading.Lock()


def hoy_demo() -> date:
    with SesionDB() as s:
        a = s.get(Ajuste, "hoy_demo")
        return date.fromisoformat(a.valor) if a and a.valor else date.today()


def hay_datos() -> bool:
    with SesionDB() as s:
        return s.scalar(select(Correo.id).limit(1)) is not None or s.scalar(select(Plato.id).limit(1)) is not None


# ---------------------------------------------------------------- configuración inicial (como si el dueño la hubiera puesto)
def cargar_configuracion(s):
    d = json.loads((DEMO / "datos.json").read_text(encoding="utf-8"))
    s.merge(Ajuste(clave="hoy_demo", valor=d["hoy_demo"]))
    s.merge(Ajuste(clave="dias_apertura_mes", valor="26"))
    s.merge(Ajuste(clave="minimo_caja", valor="3000"))
    s.merge(Ajuste(clave="margen_objetivo", valor="0.70"))
    for p in d["proveedores_info"]:
        if not s.scalar(select(Proveedor).where(Proveedor.nombre == p["nombre"])):
            s.add(Proveedor(nombre=p["nombre"], grupo=p["grupo"], tipo=p["tipo"]))
    s.flush()
    for p in d["productos"]:
        if not s.scalar(select(Producto).where(Producto.nombre == p["nombre"])):
            s.add(Producto(nombre=p["nombre"], tipo=p["tipo"], unidad=p["unidad"], rendimiento=p["rendimiento"],
                           codigo_mercabarna=p["codigo_mercabarna"], alergenos=p["alergenos"]))
    s.flush()
    prods = {p.nombre: p for p in s.scalars(select(Producto))}
    for pl in d["carta"]:
        plato = Plato(nombre=pl["nombre"], parte=pl["parte"], precio_carta=pl["precio_carta"], clave_competencia=pl["clave_competencia"])
        plato.receta = [LineaReceta(producto_id=prods[r["producto"]].id, cantidad=r["cantidad"]) for r in pl["receta"]]
        s.add(plato)
    emps = {}
    for e in d["empleados"]:
        emp = Empleado(nombre=e["nombre"], puesto=e["puesto"], horas_semana=e["horas_semana"])
        s.add(emp)
        emps[e["nombre"]] = emp
    s.flush()
    for t in d["cuadrante"]:
        s.add(Turno(empleado_id=emps[t["empleado"]].id, fecha=date.fromisoformat(t["fecha"]), tramos=t["tramos"]))
    for e in d["eventos"]:
        s.add(Evento(fecha=date.fromisoformat(e["fecha"]), nombre=e["nombre"], efecto=e["efecto"]))
    for p in d["pagos_fijos"]:
        s.add(PagoFijo(concepto=p["concepto"], dia=p["dia"], importe=p["importe"], cada=p["cada"], aproximado=p["aproximado"]))
    for c in d["competidores"]:
        s.add(Competidor(nombre=c["nombre"], distancia_m=c["distancia_m"], valoracion=c["valoracion"], opiniones=c["opiniones"], carta=c["carta"]))


# ---------------------------------------------------------------- línea de tiempo
def _correos_por_dia():
    por_dia = {}
    for c in json.loads((DEMO / "correos.json").read_text(encoding="utf-8")):
        por_dia.setdefault(datetime.fromisoformat(c["fecha"]).date(), []).append(c)
    return por_dia


def _etiquetas_por_dia():
    verdad = json.loads((DEMO / "verdad.json").read_text(encoding="utf-8"))
    por_dia = {}
    for e in verdad["etiquetas"]:
        por_dia.setdefault(date.fromisoformat(e["recibido"]), []).append(e["archivo"])
    return por_dia


def _ticker(texto, alerta=False):
    ESTADO.ticker.appendleft({"dia": ESTADO.dia.strftime("%d/%m") if ESTADO.dia else "", "texto": texto, "alerta": alerta})


def _bucle_demo():
    try:
        correos = _correos_por_dia()
        etiquetas = _etiquetas_por_dia()
        restaurante = config.NOMBRE_RESTAURANTE
        with SesionDB() as s:
            cargar_configuracion(s)
            s.commit()
        d = INICIO
        while d <= FIN:
            while ESTADO.pausa:
                time.sleep(0.2)
            t0 = time.time()
            ESTADO.dia = d
            ESTADO.n_dia = (d - INICIO).days + 1
            with SesionDB() as s:
                avisos_antes = s.scalar(select(Aviso.id).order_by(Aviso.id.desc()).limit(1)) or 0
                for c in correos.get(d, []):
                    adj = [(Path(a).name, (DEMO / a).read_bytes()) for a in c["adjuntos"]]
                    co = procesar.procesar_correo(s, c, adj, d, restaurante, origen="demo")
                    ESTADO.contadores["correos"] += 1
                    tipo = c.get("tipo_esperado")
                    if tipo == "factura":
                        ESTADO.contadores["facturas"] += 1
                        _ticker(f"📄 {c['asunto']} · {c['de_nombre']}")
                    elif tipo == "gasto":
                        ESTADO.contadores["gastos"] += 1
                        _ticker(f"🧾 {c['asunto']}")
                    elif tipo == "nomina":
                        ESTADO.contadores["nominas"] += len(c["adjuntos"])
                        _ticker(f"👥 {c['asunto']}")
                    elif tipo == "cierre":
                        ESTADO.contadores["cierres"] += 1
                        cierre = s.scalar(select(Cierre).where(Cierre.fecha == d - timedelta(days=1)))
                        if cierre:
                            ESTADO.contadores["ventas"] += cierre.ventas_total
                            _ticker(f"📊 Cierre de caja del {cierre.fecha.strftime('%d/%m')} · {cierre.ventas_total:,.0f} €".replace(",", "."))
                    else:
                        _ticker(f"✉️ {c['de_nombre']}: {c['asunto']}")
                for archivo in etiquetas.get(d, []):
                    ruta = almacen.guardar(f"entrada/recepcion/{Path(archivo).name}", (DEMO / archivo).read_bytes(), "image/jpeg")
                    s.add(Documento(tipo="pendiente", archivo=ruta, origen="demo", estado="leyendo", fecha=d, datos={"recepcion": True}))
                    _ticker(f"📸 Foto de etiqueta en Recepción: {Path(archivo).stem.split(' ', 1)[1].rsplit(' ', 1)[0]}")
                if not abierto(d):
                    _ticker("🔒 Lunes: cerrado")
                for a in s.scalars(select(Aviso).where(Aviso.id > avisos_antes)):
                    _ticker(f"⚠ {a.texto}", alerta=True)
                s.commit()
            ESTADO.ia_pendientes = _contar_pendientes()
            _asegurar_hilo_ia()
            d += timedelta(days=1)
            time.sleep(max(0, ESTADO.segundos_por_dia - (time.time() - t0)))
        with SesionDB() as s:
            cargar_banco(s, (DEMO / "banco" / "extracto_2026-08-01_2026-10-10.n43").read_bytes())
            s.commit()
        _ticker("🏦 Extracto del banco subido y casado con las facturas")
        ESTADO.terminado = True
    except Exception as e:  # se muestra en Ajustes; la app sigue funcionando
        ESTADO.error = f"{type(e).__name__}: {e}"
    finally:
        ESTADO.en_marcha = False


def abierto(d: date) -> bool:
    return d.weekday() != 0


def _contar_pendientes():
    """Fotos por leer más correos de clientes por entender (sin contar dos veces el correo de una foto)."""
    with SesionDB() as s:
        fotos = list(s.scalars(select(Documento.correo_id).where(Documento.estado == "leyendo")))
        con_foto = {c for c in fotos if c is not None}
        correos = [c for c in s.scalars(select(Correo.id).where(Correo.categoria == "leyendo")) if c not in con_foto]
        return len(fotos) + len(correos)


def _bucle_ia():
    """Lee con la IA las fotos y los correos de clientes que esperan. Si se acaba el tope, espera y reintenta."""
    while True:
        try:
            with SesionDB() as s:
                n = procesar.procesar_pendientes(s, hoy_demo(), config.NOMBRE_RESTAURANTE, maximo=2)
                s.commit()
            ESTADO.ia_estado = "" if n else ESTADO.ia_estado
            if n:
                ESTADO.ia_ultimo = f"{n} leídos a las {time.strftime('%H:%M:%S')}"
        except ia.CuotaAgotada:
            ESTADO.ia_estado = "Se ha acabado el tope diario de la IA gratuita: lo pendiente se leerá cuando se renueve."
            time.sleep(300)
            continue
        except ia.SinIA:
            ESTADO.ia_estado = "Sin clave de IA: las fotos quedan pendientes."
            return
        except Exception as e:
            ESTADO.ia_estado = f"Error leyendo con IA: {e}"
            time.sleep(10)
            n = 0
        ESTADO.ia_pendientes = _contar_pendientes()
        if not n:
            if not ESTADO.en_marcha and ESTADO.ia_pendientes == 0:
                return
            time.sleep(1)


def _asegurar_hilo_ia():
    global _hilo_ia
    with _cerrojo:
        if _hilo_ia is None or not _hilo_ia.is_alive():
            _hilo_ia = threading.Thread(target=_bucle_ia, daemon=True)
            _hilo_ia.start()


def empezar(segundos_por_dia=1.0):
    global _hilo
    with _cerrojo:
        if ESTADO.en_marcha:
            ESTADO.pausa = False
            return
        if hay_datos():
            raise RuntimeError("Ya hay datos: pulsa Reiniciar demo antes de volver a cargarla.")
        ESTADO.reset()
        ESTADO.en_marcha = True
        ESTADO.segundos_por_dia = segundos_por_dia
        _hilo = threading.Thread(target=_bucle_demo, daemon=True)
        _hilo.start()


# ---------------------------------------------------------------- banco (Norma 43 o CSV)
def leer_norma43(contenido: bytes) -> list[dict]:
    movs, actual = [], None
    for linea in contenido.decode("latin-1").splitlines():
        if linea.startswith("22"):
            fecha = date(2000 + int(linea[10:12]), int(linea[12:14]), int(linea[14:16]))
            signo = -1 if linea[27] == "1" else 1
            actual = {"fecha": fecha, "importe": signo * int(linea[28:42]) / 100, "concepto": "", "ref": linea[52:64].strip()}
            movs.append(actual)
        elif linea.startswith("23") and actual is not None:
            actual["concepto"] = (actual["concepto"] + " " + linea[4:].strip()).strip()
        elif linea.startswith("11"):
            saldo_ini = int(linea[33:47]) / 100 * (-1 if linea[32] == "1" else 1)
    s = saldo_ini
    for m in movs:
        s = round(s + m["importe"], 2)
        m["saldo"] = s
    return movs


def cargar_banco(s, contenido: bytes, nombre="extracto.n43") -> dict:
    """Casa cada cargo con su factura (pagada) y clasifica el resto. No pide ni guarda contraseñas del banco."""
    if nombre.lower().endswith(".csv"):
        movs = []
        for i, fila in enumerate(contenido.decode("utf-8").splitlines()[1:]):
            f, concepto, imp, saldo = fila.split(";")
            movs.append({"fecha": date(int(f[6:10]), int(f[3:5]), int(f[0:2])), "concepto": concepto, "ref": "",
                         "importe": float(imp.replace(".", "").replace(",", ".")), "saldo": float(saldo.replace(".", "").replace(",", "."))})
    else:
        movs = leer_norma43(contenido)
    s.execute(delete(MovimientoBanco))
    facturas = list(s.scalars(select(Documento).where(Documento.tipo == "factura", Documento.estado != "duplicada")))
    casados = 0
    for m in movs:
        mv = MovimientoBanco(fecha=m["fecha"], concepto=m["concepto"], importe=m["importe"], saldo=m["saldo"])
        c = m["concepto"].upper()
        if m["importe"] > 0:
            mv.tipo = "abono_tarjeta" if "TPV" in c else ("ingreso_efectivo" if "EFECTIVO" in c else "otro_ingreso")
        elif "NOMINA" in c:
            mv.tipo = "nomina"
        elif "SEGURIDAD SOCIAL" in c or "TGSS" in c:
            mv.tipo = "seguridad_social"
        elif "PRESTAMO" in c:
            mv.tipo = "prestamo"
        elif "TRASPASO" in c:
            mv.tipo = "retirada_dueno"
        else:
            f = next((f for f in facturas if f.numero and (f.numero == m["ref"] or f.numero in c) and f.total and abs(f.total + m["importe"]) < 0.02), None)
            if f:
                f.pagado_fecha = m["fecha"]
                mv.documento_id = f.id
                mv.tipo = "pago_factura"
                casados += 1
            elif "FACTURA JULIO" in c:
                mv.tipo = "pago_factura_anterior"
            else:
                mv.tipo = "recibo_sin_factura"
        s.add(mv)
    s.merge(Ajuste(clave="extracto_hasta", valor=movs[-1]["fecha"].isoformat() if movs else ""))
    return {"movimientos": len(movs), "casados": casados}


# ---------------------------------------------------------------- reiniciar y autodestruir
TABLAS = [Aviso, MovimientoBanco, Entrada, Recuento, LineaDocumento, Cierre, Documento, Correo, LineaReceta, Plato, Turno, Empleado,
          Evento, PagoFijo, Competidor, Producto, Proveedor]


def reiniciar() -> dict:
    if ESTADO.en_marcha:
        raise RuntimeError("Espera a que termine la carga de la demo (o páusala) antes de reiniciar.")
    with SesionDB() as s:
        for t in TABLAS:
            s.execute(delete(t))
        s.execute(delete(Ajuste).where(Ajuste.clave != "gmail_token"))
        s.commit()
    archivos = almacen.borrar_todo()
    ESTADO.reset()
    return {"archivos_borrados": archivos}
