"""Sube el código de ReHub a un repositorio público de GitHub (de donde Render lo despliega).

Uso:  .venv\\Scripts\\python.exe herramientas\\publicar_github.py
Necesita GITHUB_TOKEN (clave "classic" con permiso repo, o fine-grained con contenido y administración
de repositorios) en ~/.rehub/claves.env. Crea el repositorio si no existe y hace push de la rama main.
La clave se pasa al push en una cabecera de un solo uso: no se guarda en .git/config.
"""
import base64
import os
import subprocess
import sys
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()
GIT = os.environ.get("GIT_EXE", r"C:\Program Files\Git\cmd\git.exe")
REPO = os.environ.get("GITHUB_REPO", "rehub")


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Falta GITHUB_TOKEN en claves.env")
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    yo = httpx.get("https://api.github.com/user", headers=h, timeout=30)
    yo.raise_for_status()
    usuario = yo.json()["login"]
    r = httpx.get(f"https://api.github.com/repos/{usuario}/{REPO}", headers=h, timeout=30)
    if r.status_code == 404:
        r = httpx.post("https://api.github.com/user/repos", headers=h, timeout=30,
                       json={"name": REPO, "description": "ReHub: demo de oficina de restaurante (datos inventados)", "private": False, "auto_init": False})
        r.raise_for_status()
        print("Repositorio creado:", r.json()["html_url"])
    else:
        r.raise_for_status()
        print("Repositorio existente:", r.json()["html_url"])
    url = f"https://github.com/{usuario}/{REPO}.git"
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    subprocess.run([GIT, "remote", "remove", "github"], cwd=RAIZ, capture_output=True)
    subprocess.run([GIT, "remote", "add", "github", url], cwd=RAIZ, check=True)
    subprocess.run([GIT, "-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}", "push", "-u", "github", "main", "--force"],
                   cwd=RAIZ, check=True)
    print("Código subido a", url)
    guardar("GITHUB_REPO_URL", url)


def guardar(clave, valor):
    f = Path.home() / ".rehub" / "claves.env"
    t = f.read_text(encoding="utf-8") if f.exists() else ""
    lineas = [l for l in t.splitlines() if not l.startswith(clave + "=")]
    lineas.append(f"{clave}={valor}")
    f.write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
