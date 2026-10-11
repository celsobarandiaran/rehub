"""Llamadas a la IA (Gemini). La clave se lee de la variable de entorno GEMINI_API_KEY.

Si se acaba el tope gratuito del día, se lanza CuotaAgotada y el documento queda
en cola ("leyendo…") para reintentarlo más tarde. Nunca se inventa un dato.
"""
import base64
import json
import os
import time

import httpx

from . import config

MODELO = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
# Si un modelo agota su tope gratuito del día, se prueba el siguiente (cada modelo tiene su propio tope).
MODELOS = [m.strip() for m in os.environ.get("GEMINI_MODELOS", "").split(",") if m.strip()] or [MODELO, "gemini-flash-lite-latest"]
URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
_agotados: dict[str, float] = {}  # modelo -> hora en que se agotó (se reintenta pasada una hora)


class CuotaAgotada(Exception):
    pass


class SinIA(Exception):
    pass


def disponible() -> bool:
    return bool(config.GEMINI_API_KEY)


def _llamar(partes: list, esquema: dict | None, temperatura=0.1, reintentos=3) -> str:
    if not disponible():
        raise SinIA("Falta la clave de Gemini")
    modelos = [MODELO] if MODELO not in MODELOS else []
    modelos += MODELOS
    for modelo in modelos:
        if time.time() - _agotados.get(modelo, 0) < 3600:
            continue
        try:
            return _llamar_modelo(modelo, partes, esquema, temperatura, reintentos)
        except CuotaAgotada:
            _agotados[modelo] = time.time()
    raise CuotaAgotada("Tope de la IA gratuita alcanzado en todos los modelos")


def _llamar_modelo(modelo: str, partes: list, esquema: dict | None, temperatura: float, reintentos: int) -> str:
    cuerpo = {"contents": [{"parts": partes}], "generationConfig": {"temperature": temperatura}}
    if esquema:
        cuerpo["generationConfig"].update({"responseMimeType": "application/json", "responseSchema": esquema})
    espera = 4
    for intento in range(reintentos):
        try:
            r = httpx.post(URL.format(modelo=modelo), params={"key": config.GEMINI_API_KEY}, json=cuerpo, timeout=httpx.Timeout(150, connect=20))
        except (httpx.TimeoutException, httpx.TransportError):
            # La IA tarda demasiado o se cae la conexión: se reintenta; si persiste, el documento sigue en cola.
            if intento == reintentos - 1:
                raise
            time.sleep(espera)
            espera *= 2
            continue
        if r.status_code == 429:
            texto = r.text.lower()
            if "per day" in texto or "perday" in texto or intento == reintentos - 1:
                raise CuotaAgotada("Tope de la IA gratuita alcanzado")
            time.sleep(espera)
            espera *= 2
            continue
        if r.status_code >= 500 and intento < reintentos - 1:
            time.sleep(espera)
            continue
        r.raise_for_status()
        datos = r.json()
        try:
            return datos["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ValueError("La IA no ha devuelto respuesta")
    raise CuotaAgotada("Tope de la IA gratuita alcanzado")


def leer_imagen(contenido: bytes, mime: str, instrucciones: str, esquema: dict) -> dict:
    partes = [{"inline_data": {"mime_type": mime, "data": base64.b64encode(contenido).decode()}}, {"text": instrucciones}]
    return json.loads(_llamar(partes, esquema))


def preguntar_json(instrucciones: str, esquema: dict, temperatura=0.2) -> dict:
    return json.loads(_llamar([{"text": instrucciones}], esquema, temperatura))


def preguntar_texto(instrucciones: str, temperatura=0.3) -> str:
    """Respuesta en texto libre (el asistente)."""
    return _llamar([{"text": instrucciones}], None, temperatura).strip()
