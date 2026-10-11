"""Caché de lecturas de la IA.

Una foto o un correo que ya se leyó una vez no se vuelve a mandar a la IA: se guarda
el resultado (tal cual lo devolvió Gemini) junto a la huella del contenido. Así
"Cargar demo" no gasta el tope gratuito con las mismas 45 fotos, y en la vida real
un archivo reenviado dos veces solo se lee una.

El archivo datos_demo/lecturas_ia.json lo rellena una vez herramientas/preleer_demo.py
con la IA de verdad. La app solo lo lee; lo nuevo que lea en caliente se guarda en
memoria (y en disco solo si REHUB_GUARDAR_LECTURAS=1, para no tocar el repositorio
desde la nube).
"""
import hashlib
import json
import os
import threading
from pathlib import Path

from . import config

ARCHIVO = config.RAIZ / "datos_demo" / "lecturas_ia.json"
_cerrojo = threading.Lock()
_datos: dict | None = None


def huella(contenido: bytes | str) -> str:
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")
    return hashlib.sha256(contenido).hexdigest()


def _cargar() -> dict:
    global _datos
    if _datos is None:
        try:
            _datos = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else {}
        except ValueError:
            _datos = {}
    return _datos


def buscar(clave: str) -> dict | None:
    with _cerrojo:
        return _cargar().get(clave)


def guardar(clave: str, resultado: dict) -> None:
    with _cerrojo:
        d = _cargar()
        d[clave] = resultado
        if os.environ.get("REHUB_GUARDAR_LECTURAS") == "1":
            ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
            ARCHIVO.write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def cuantas() -> int:
    with _cerrojo:
        return len(_cargar())
