"""Publica (o actualiza) ReHub en Render: servicio web Docker, región Frankfurt, plan gratuito.

Uso:  .venv\\Scripts\\python.exe herramientas\\desplegar_render.py
Necesita en ~/.rehub/claves.env: RENDER_API_KEY, GITHUB_REPO_URL y las claves de la app
(REHUB_CONTRASENA, REHUB_CLAVE_SESION, GEMINI_API_KEY, DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY,
y las de Gmail cuando existan). Las claves viajan a Render como variables de entorno del servicio.
Si el servicio ya existe, actualiza las variables y lanza un despliegue nuevo.
"""
import os
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()
API = "https://api.render.com/v1"
NOMBRE = os.environ.get("RENDER_SERVICE_NAME", "rehub")
CLAVES_APP = ["REHUB_CONTRASENA", "REHUB_CLAVE_SESION", "GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_MODELOS", "DATABASE_URL", "SUPABASE_URL",
              "SUPABASE_SERVICE_KEY", "SUPABASE_BUCKET", "SUPABASE_TOKEN", "SUPABASE_PROJECT_REF", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
              "GMAIL_REFRESH_TOKEN", "GMAIL_CUENTA", "RENDER_API_KEY"]


def guardar(clave, valor):
    f = Path.home() / ".rehub" / "claves.env"
    t = f.read_text(encoding="utf-8") if f.exists() else ""
    lineas = [l for l in t.splitlines() if not l.startswith(clave + "=")]
    lineas.append(f"{clave}={valor}")
    f.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.environ[clave] = valor


def main():
    token, repo = os.environ.get("RENDER_API_KEY"), os.environ.get("GITHUB_REPO_URL")
    if not token or not repo:
        sys.exit("Faltan RENDER_API_KEY o GITHUB_REPO_URL en claves.env")
    c = httpx.Client(headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, timeout=60)
    owner = next(o["owner"] for o in c.get(f"{API}/owners").json())
    print("Cuenta de Render:", owner.get("name"), owner.get("email", ""))
    env = [{"key": k, "value": os.environ[k]} for k in CLAVES_APP if os.environ.get(k)]
    env += [{"key": "REHUB_ENTORNO", "value": "nube"}, {"key": "REHUB_RESTAURANTE", "value": "Restaurante La Plaza"}, {"key": "RENDER_SERVICE_NAME", "value": NOMBRE}]
    servicios = [s["service"] for s in c.get(f"{API}/services", params={"name": NOMBRE, "limit": 20}).json()]
    servicio = next((s for s in servicios if s["name"] == NOMBRE), None)
    if not servicio:
        r = c.post(f"{API}/services", json={
            "type": "web_service", "name": NOMBRE, "ownerId": owner["id"], "repo": repo, "branch": "main", "autoDeploy": "yes",
            "serviceDetails": {"env": "docker", "region": "frankfurt", "plan": "free", "healthCheckPath": "/salud",
                               "envSpecificDetails": {"dockerfilePath": "./Dockerfile", "dockerContext": "."}},
            "envVars": env})
        if r.status_code >= 400:
            sys.exit(f"Render no ha creado el servicio: {r.status_code} {r.text[:400]}")
        servicio = r.json()["service"]
        print("Servicio creado:", servicio["id"])
    else:
        print("Servicio existente:", servicio["id"])
        c.put(f"{API}/services/{servicio['id']}/env-vars", json=env).raise_for_status()
        c.post(f"{API}/services/{servicio['id']}/deploys", json={"clearCache": "do_not_clear"}).raise_for_status()
        print("Despliegue nuevo lanzado")
    sid = servicio["id"]
    guardar("RENDER_SERVICE_ID", sid)
    c.put(f"{API}/services/{sid}/env-vars", json=[*env, {"key": "RENDER_SERVICE_ID", "value": sid}]).raise_for_status()
    url = servicio.get("serviceDetails", {}).get("url") or f"https://{NOMBRE}.onrender.com"
    guardar("REHUB_URL", url)
    print("Dirección:", url)
    for _ in range(90):
        d = c.get(f"{API}/services/{sid}/deploys", params={"limit": 1}).json()
        estado = d[0]["deploy"]["status"] if d else "?"
        print("  despliegue:", estado)
        if estado == "live":
            break
        if estado in ("build_failed", "update_failed", "canceled", "deactivated"):
            sys.exit("El despliegue ha fallado: mira los registros en https://dashboard.render.com")
        time.sleep(20)
    try:
        print("Salud:", httpx.get(f"{url}/salud", timeout=120).text)
    except Exception as e:
        print("La app aún no responde:", e)


if __name__ == "__main__":
    main()
