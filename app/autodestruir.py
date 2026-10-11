"""Autodestruir: borra todo lo que la app creó y enseña los enlaces para lo que solo puede borrar el dueño.

Orden: datos y archivos (base y almacén) → permiso de Gmail → proyecto de Supabase (API) → servicio de Render (API).
Cada paso apunta si se hizo o por qué no. Nunca borra la cuenta de Gmail ni las cuentas de los alojamientos:
eso lo hace el dueño con los enlaces de abajo.
"""
import os

import httpx

from . import almacen, config, demo, gmail

ENLACES_MANUALES = [
    ("Cuenta de Gmail de la demo", "https://myaccount.google.com/deleteaccount", "Borrar la cuenta laplazarehub@gmail.com (pide la contraseña)."),
    ("Proyecto de Google Cloud", "https://console.cloud.google.com/iam-admin/settings", "Apagar el proyecto ReHub (se borra a los 30 días)."),
    ("Cuenta de Supabase", "https://supabase.com/dashboard/account/me", "Al final de la página: Delete account."),
    ("Cuenta de Render", "https://dashboard.render.com/u/settings", "Al final de la página: Delete account."),
    ("Repositorio de GitHub", "https://github.com/settings/repositories", "Abrir el repositorio rehub → Settings → Delete this repository."),
    ("Cuenta de Hugging Face (no se usa)", "https://huggingface.co/settings/account", "Al final de la página: Delete account."),
]


def ejecutar() -> dict:
    pasos = []

    def paso(nombre, fn):
        try:
            r = fn()
            pasos.append({"paso": nombre, "ok": True, "detalle": r})
        except Exception as e:
            pasos.append({"paso": nombre, "ok": False, "detalle": f"{type(e).__name__}: {e}"})

    paso("Borrar datos y archivos", lambda: demo.reiniciar())
    paso("Quitar el permiso de Gmail", lambda: "quitado" if gmail.revocar() else "no estaba conectado")
    paso("Borrar el proyecto de Supabase", _borrar_supabase)
    paso("Borrar el servicio de Render", _borrar_render)
    return {"pasos": pasos, "manual": ENLACES_MANUALES}


def _borrar_supabase():
    token, ref = os.environ.get("SUPABASE_TOKEN"), os.environ.get("SUPABASE_PROJECT_REF")
    if not token or not ref:
        return "sin proyecto que borrar (faltan SUPABASE_TOKEN o SUPABASE_PROJECT_REF)"
    r = httpx.delete(f"https://api.supabase.com/v1/projects/{ref}", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    r.raise_for_status()
    return f"proyecto {ref} borrado"


def _borrar_render():
    token, sid = os.environ.get("RENDER_API_KEY"), os.environ.get("RENDER_SERVICE_ID")
    if not token or not sid:
        return "sin servicio que borrar (faltan RENDER_API_KEY o RENDER_SERVICE_ID)"
    r = httpx.delete(f"https://api.render.com/v1/services/{sid}", headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code not in (200, 202, 204):
        r.raise_for_status()
    return f"servicio {sid} borrado (la app dejará de responder en un minuto)"
