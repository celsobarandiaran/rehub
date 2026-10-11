"""Crea el proyecto de Supabase de la demo (base de datos + almacén de archivos) en Frankfurt, plan gratuito.

Uso:  .venv\\Scripts\\python.exe herramientas\\crear_supabase.py
Necesita SUPABASE_TOKEN en ~/.rehub/claves.env. Guarda ahí: SUPABASE_PROJECT_REF, SUPABASE_URL,
SUPABASE_SERVICE_KEY, SUPABASE_DB_PASSWORD y DATABASE_URL. Si el proyecto ya existe, solo rellena lo que falte.
Autodestruir lo borra con DELETE /v1/projects/{ref}.
"""
import os
import secrets
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()
API = "https://api.supabase.com/v1"
CLAVES = Path.home() / ".rehub" / "claves.env"
NOMBRE, REGION, CUBO = "rehub", "eu-central-1", "documentos"


def guardar(clave, valor):
    t = CLAVES.read_text(encoding="utf-8") if CLAVES.exists() else ""
    lineas = [l for l in t.splitlines() if not l.startswith(clave + "=")]
    lineas.append(f"{clave}={valor}")
    CLAVES.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    os.environ[clave] = valor


def main():
    token = os.environ.get("SUPABASE_TOKEN")
    if not token:
        sys.exit("Falta SUPABASE_TOKEN en claves.env")
    h = {"Authorization": f"Bearer {token}"}
    c = httpx.Client(headers=h, timeout=60)
    orgs = c.get(f"{API}/organizations").json()
    org = orgs[0]
    proyectos = c.get(f"{API}/projects").json()
    p = next((x for x in proyectos if x["name"] == NOMBRE), None)
    if p:
        print("El proyecto ya existe:", p["id"], p.get("region"), p.get("status"))
        pw = os.environ.get("SUPABASE_DB_PASSWORD", "")
    else:
        pw = secrets.token_urlsafe(24).replace("-", "x").replace("_", "y")
        r = c.post(f"{API}/projects", json={"name": NOMBRE, "organization_id": org["id"], "region": REGION, "db_pass": pw, "desired_instance_size": "micro"})
        if r.status_code >= 400:
            r = c.post(f"{API}/projects", json={"name": NOMBRE, "organization_id": org["id"], "region": REGION, "db_pass": pw})
        r.raise_for_status()
        p = r.json()
        guardar("SUPABASE_DB_PASSWORD", pw)
        print("Proyecto creado:", p["id"], "en", REGION)
    ref = p["id"]
    guardar("SUPABASE_PROJECT_REF", ref)
    guardar("SUPABASE_URL", f"https://{ref}.supabase.co")
    for _ in range(60):
        estado = c.get(f"{API}/projects/{ref}").json().get("status")
        print("  estado:", estado)
        if estado == "ACTIVE_HEALTHY":
            break
        time.sleep(10)
    claves = c.get(f"{API}/projects/{ref}/api-keys", params={"reveal": "true"}).json()
    servicio = next((k for k in claves if k.get("name") == "service_role"), None)
    if not servicio:
        servicio = next((k for k in claves if k.get("type") == "secret"), None)
    if not servicio:
        sys.exit(f"No encuentro la clave de servicio: {[k.get('name') for k in claves]}")
    guardar("SUPABASE_SERVICE_KEY", servicio["api_key"])
    # Conexión a la base por el "pooler" (Render solo tiene IPv4 y el host directo es solo IPv6)
    pooler = c.get(f"{API}/projects/{ref}/config/database/pooler").json()
    item = next((x for x in pooler if x.get("database_type") == "PRIMARY"), pooler[0] if pooler else None)
    if not item:
        sys.exit("Sin datos del pooler")
    url = item["connection_string"].replace("[YOUR-PASSWORD]", pw)
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    guardar("DATABASE_URL", url)
    # Cubo de archivos privado
    r = c.post(f"https://{ref}.supabase.co/storage/v1/bucket", headers={"Authorization": f"Bearer {servicio['api_key']}", "apikey": servicio["api_key"]},
               json={"id": CUBO, "name": CUBO, "public": False})
    print("Cubo de archivos:", "creado" if r.status_code in (200, 201) else r.text[:120])
    print("Listo. Guardado en", CLAVES, "· host del pooler:", item.get("db_host"))


if __name__ == "__main__":
    main()
