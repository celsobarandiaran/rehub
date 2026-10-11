"""Arranca ReHub en este ordenador, en http://localhost:8510

Lee las claves de los archivos que están fuera del proyecto (nunca del código):
  ~/.spotscout/claves.env  -> GEMINI_API_KEY (la misma que usa SpotScout)
  ~/.rehub/claves.env      -> HF_TOKEN, SUPABASE_TOKEN y lo que haga falta
y las pone como variables de entorno solo para este proceso.

Uso:  .venv\\Scripts\\python.exe herramientas\\iniciar_local.py  [--sin-recarga]
"""
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVOS = [Path.home() / ".spotscout" / "claves.env", Path.home() / ".rehub" / "claves.env"]


def cargar_claves():
    puestas = []
    for archivo in ARCHIVOS:
        if not archivo.exists():
            continue
        for linea in archivo.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave, valor = clave.strip(), valor.strip().strip('"').strip("'")
            if valor and clave not in os.environ:
                os.environ[clave] = valor
                puestas.append(clave)
    return puestas


if __name__ == "__main__":
    puestas = cargar_claves()
    print("Claves cargadas en el entorno:", ", ".join(puestas) or "ninguna")
    os.environ.setdefault("REHUB_ENTORNO", "local")
    orden = [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8510"]
    if "--sin-recarga" not in sys.argv:
        orden += ["--reload", "--reload-dir", "app"]
    sys.exit(subprocess.call(orden, cwd=RAIZ))
