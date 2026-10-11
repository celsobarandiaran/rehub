"""Autoriza UNA VEZ a ReHub a leer y enviar correo de la cuenta de la demo (vía oficial de Google).

Antes hace falta, en Google Cloud (con la cuenta laplazarehub@gmail.com):
  1. Un proyecto, con la API de Gmail activada.
  2. Una "pantalla de consentimiento" en modo prueba con esa cuenta como usuario de prueba.
  3. Un "ID de cliente OAuth" de tipo "Aplicación de escritorio": su ID y su secreto van en
     ~/.rehub/claves.env como GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET.

Uso:  .venv\\Scripts\\python.exe herramientas\\autorizar_gmail.py
Abre el navegador; el dueño elige la cuenta y pulsa "Permitir" (verá un aviso de "app no verificada":
"Configuración avanzada" > "Ir a ReHub"). El permiso (refresh token) se guarda en claves.env.
"""
import http.server
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()
CLAVES = Path.home() / ".rehub" / "claves.env"
ALCANCES = "https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/gmail.send"
PUERTO = 8599
codigo = {}


class Recibir(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        codigo.update(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write("<h2 style='font-family:sans-serif'>ReHub ya tiene permiso. Puedes cerrar esta pestaña.</h2>".encode())

    def log_message(self, *a):
        pass


def guardar(clave, valor):
    t = CLAVES.read_text(encoding="utf-8") if CLAVES.exists() else ""
    lineas = [l for l in t.splitlines() if not l.startswith(clave + "=")]
    lineas.append(f"{clave}={valor}")
    CLAVES.write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    cid, sec = os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET")
    if not cid or not sec:
        sys.exit("Faltan GOOGLE_CLIENT_ID y GOOGLE_CLIENT_SECRET en ~/.rehub/claves.env")
    estado = secrets.token_urlsafe(16)
    redir = f"http://localhost:{PUERTO}/"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redir, "response_type": "code", "scope": ALCANCES, "access_type": "offline", "prompt": "consent",
        "state": estado, "login_hint": os.environ.get("GMAIL_CUENTA", "laplazarehub@gmail.com")})
    srv = http.server.HTTPServer(("localhost", PUERTO), Recibir)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print("Se abre el navegador. Elige la cuenta de la demo y pulsa Permitir.")
    webbrowser.open(url)
    import time
    for _ in range(600):
        if codigo:
            break
        time.sleep(0.5)
    srv.server_close()
    if codigo.get("state", [""])[0] != estado or not codigo.get("code"):
        sys.exit("No se recibió el permiso.")
    r = httpx.post("https://oauth2.googleapis.com/token", data={"code": codigo["code"][0], "client_id": cid, "client_secret": sec,
                                                                "redirect_uri": redir, "grant_type": "authorization_code"}, timeout=30)
    r.raise_for_status()
    rt = r.json().get("refresh_token")
    if not rt:
        sys.exit("Google no devolvió el permiso permanente. Quita el acceso en myaccount.google.com/permissions y repite.")
    guardar("GMAIL_REFRESH_TOKEN", rt)
    print("Permiso guardado en", CLAVES)
