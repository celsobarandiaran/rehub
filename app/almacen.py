"""Almacén de archivos (PDF y fotos).

En tu PC guarda en `datos_locales/archivos`. En la nube usa Supabase Storage.
Las rutas siguen el orden pedido: año/mes/tipo/"fecha proveedor total.pdf".
"""
import re
from datetime import date

import httpx

from . import config

CARPETA = config.CARPETA_LOCAL / "archivos"


def ruta_documento(fecha: date | None, tipo: str, proveedor: str, total: float | None, extension: str) -> str:
    """Ejemplo: 2026/10/facturas/2026-10-10 Pescados Mar Nou 412,30.pdf"""
    carpetas = {"factura": "facturas", "gasto": "gastos", "nomina": "nominas", "cierre": "cierres"}
    f = fecha or date.today()
    importe = f"{total:.2f}".replace(".", ",") if total is not None else "sin-importe"
    nombre = re.sub(r"[\\/:*?\"<>|]", "", f"{f.isoformat()} {proveedor} {importe}").strip()
    return f"{f.year}/{f.month:02d}/{carpetas.get(tipo, 'otros')}/{nombre}.{extension.lstrip('.')}"


def _cabeceras() -> dict:
    return {"Authorization": f"Bearer {config.SUPABASE_CLAVE_SERVICIO}", "apikey": config.SUPABASE_CLAVE_SERVICIO}


def guardar(ruta: str, contenido: bytes, tipo_mime: str = "application/pdf") -> str:
    if config.ALMACEN == "supabase":
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_CUBO}/{ruta}"
        r = httpx.post(url, content=contenido, headers={**_cabeceras(), "Content-Type": tipo_mime, "x-upsert": "true"}, timeout=60)
        r.raise_for_status()
    else:
        destino = CARPETA / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
    return ruta


def leer(ruta: str) -> bytes:
    if config.ALMACEN == "supabase":
        url = f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_CUBO}/{ruta}"
        r = httpx.get(url, headers=_cabeceras(), timeout=60)
        r.raise_for_status()
        return r.content
    return (CARPETA / ruta).read_bytes()


def borrar_todo() -> int:
    """Para Reiniciar demo y Autodestruir. Devuelve cuántos archivos ha borrado."""
    if config.ALMACEN == "supabase":
        borrados = 0
        while True:
            rutas = _listar_recursivo("")
            if not rutas:
                return borrados
            httpx.request("DELETE", f"{config.SUPABASE_URL}/storage/v1/object/{config.SUPABASE_CUBO}",
                          json={"prefixes": rutas}, headers=_cabeceras(), timeout=60).raise_for_status()
            borrados += len(rutas)
    n = 0
    if CARPETA.exists():
        for f in sorted(CARPETA.rglob("*"), reverse=True):
            if f.is_file():
                f.unlink()
                n += 1
            else:
                f.rmdir()
    return n


def _listar_recursivo(prefijo: str) -> list[str]:
    r = httpx.post(f"{config.SUPABASE_URL}/storage/v1/object/list/{config.SUPABASE_CUBO}",
                   json={"prefix": prefijo, "limit": 1000}, headers=_cabeceras(), timeout=60)
    r.raise_for_status()
    rutas = []
    for item in r.json():
        ruta = f"{prefijo}/{item['name']}".lstrip("/")
        if item.get("id"):
            rutas.append(ruta)
        else:
            rutas.extend(_listar_recursivo(ruta))
    return rutas
