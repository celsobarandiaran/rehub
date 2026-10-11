"""Gmail por la vía oficial de Google (OAuth). La app lee la bandeja, baja los adjuntos y envía respuestas.

Necesita tres variables de entorno: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET y GMAIL_REFRESH_TOKEN
(esta última la crea herramientas/autorizar_gmail.py cuando el dueño pulsa "Permitir" una vez).
"""
import base64
import re
import time
from email.message import EmailMessage
from email.utils import formataddr

import httpx

from . import config

API = "https://gmail.googleapis.com/gmail/v1/users/me"
ETIQUETA = "ReHub"  # los correos ya procesados llevan esta etiqueta
_token = {"valor": "", "caduca": 0.0}


class GmailNoConectado(Exception):
    pass


def conectado() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.GOOGLE_CLIENT_SECRET and config.GMAIL_REFRESH_TOKEN)


def _acceso() -> str:
    if not conectado():
        raise GmailNoConectado("Gmail no está conectado")
    if time.time() < _token["caduca"] - 60:
        return _token["valor"]
    r = httpx.post("https://oauth2.googleapis.com/token", data={"client_id": config.GOOGLE_CLIENT_ID, "client_secret": config.GOOGLE_CLIENT_SECRET,
                                                                "refresh_token": config.GMAIL_REFRESH_TOKEN, "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    d = r.json()
    _token.update(valor=d["access_token"], caduca=time.time() + d.get("expires_in", 3600))
    return _token["valor"]


def _get(ruta: str, **params):
    r = httpx.get(f"{API}/{ruta}", params=params, headers={"Authorization": f"Bearer {_acceso()}"}, timeout=60)
    r.raise_for_status()
    return r.json()


def _post(ruta: str, json: dict):
    r = httpx.post(f"{API}/{ruta}", json=json, headers={"Authorization": f"Bearer {_acceso()}"}, timeout=60)
    r.raise_for_status()
    return r.json()


def _etiqueta_id() -> str:
    for l in _get("labels")["labels"]:
        if l["name"] == ETIQUETA:
            return l["id"]
    return _post("labels", {"name": ETIQUETA, "labelListVisibility": "labelShow", "messageListVisibility": "show"})["id"]


def _cabecera(msg: dict, nombre: str) -> str:
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == nombre.lower():
            return h["value"]
    return ""


def _partes(parte: dict):
    yield parte
    for p in parte.get("parts", []) or []:
        yield from _partes(p)


def _texto(msg: dict) -> str:
    for p in _partes(msg["payload"]):
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", "replace")
    for p in _partes(msg["payload"]):
        if p.get("mimeType") == "text/html" and p.get("body", {}).get("data"):
            html = base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8", "replace")
            return re.sub(r"<[^>]+>", " ", html)
    return msg.get("snippet", "")


def nuevos(desde_epoch: int | None = None, maximo=50) -> list[dict]:
    """Correos de la bandeja que aún no llevan la etiqueta ReHub. Cada uno con sus adjuntos ya descargados."""
    q = f"-label:{ETIQUETA} in:inbox" + (f" after:{desde_epoch}" if desde_epoch else "")
    ids = _get("messages", q=q, maxResults=maximo).get("messages", []) or []
    out = []
    for m in reversed(ids):  # de más antiguo a más nuevo
        msg = _get(f"messages/{m['id']}", format="full")
        para = _cabecera(msg, "To") + " " + _cabecera(msg, "Delivered-To")
        de = _cabecera(msg, "From")
        # El alias (+proveedor, +cliente…) va en el destinatario; en los correos de demo que la propia cuenta
        # se manda a sí misma va en el remitente.
        alias = re.search(r"\+(\w+)@", para) or re.search(r"\+(\w+)@", de)
        nombre = re.sub(r"\s*<.*>", "", de).strip().strip('"') or de
        adjuntos = []
        for p in _partes(msg["payload"]):
            fn = p.get("filename")
            if fn and p.get("body", {}).get("attachmentId"):
                datos = _get(f"messages/{m['id']}/attachments/{p['body']['attachmentId']}")["data"]
                adjuntos.append((fn, base64.urlsafe_b64decode(datos)))
        out.append({"gmail_id": m["id"], "de_nombre": nombre, "de": de, "alias": alias.group(1) if alias else "", "asunto": _cabecera(msg, "Subject"),
                    "cuerpo": _texto(msg), "fecha": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(msg["internalDate"]) / 1000)),
                    "adjuntos": adjuntos})
    return out


def marcar_procesado(gmail_id: str) -> None:
    _post(f"messages/{gmail_id}/modify", {"addLabelIds": [_etiqueta_id()]})


def enviar(para: str, asunto: str, cuerpo: str, desde_nombre: str = "", alias: str = "", adjuntos: list | None = None, responde_a: str = "") -> str:
    """Envía un correo. Con `alias`, sale desde cuenta+alias@gmail.com (los correos de demo)."""
    cuenta = config.GMAIL_CUENTA
    m = EmailMessage()
    m["To"] = para
    m["Subject"] = asunto
    remitente = cuenta.replace("@", f"+{alias}@") if alias else cuenta
    m["From"] = formataddr((desde_nombre or config.NOMBRE_RESTAURANTE, remitente))
    if responde_a:
        m["In-Reply-To"] = responde_a
        m["References"] = responde_a
    m.set_content(cuerpo)
    for nombre, datos in adjuntos or []:
        tipo = "application/pdf" if nombre.lower().endswith(".pdf") else "image/jpeg"
        m.add_attachment(datos, maintype=tipo.split("/")[0], subtype=tipo.split("/")[1], filename=nombre)
    raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
    return _post("messages/send", {"raw": raw})["id"]


def revocar() -> bool:
    """Autodestruir: quita el permiso que la app tiene sobre la cuenta de Gmail."""
    if not config.GMAIL_REFRESH_TOKEN:
        return False
    r = httpx.post("https://oauth2.googleapis.com/revoke", params={"token": config.GMAIL_REFRESH_TOKEN}, timeout=30)
    return r.status_code == 200
