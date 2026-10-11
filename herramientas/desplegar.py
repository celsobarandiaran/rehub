"""Publica (o actualiza) ReHub en Hugging Face Spaces.

Uso:  .venv\\Scripts\\python.exe herramientas\\desplegar.py
- Crea el Space si no existe (tipo Docker, público: la app lleva su propia contraseña).
- Pone las claves como SECRETOS del Space (nunca en el código): GEMINI_API_KEY, REHUB_CONTRASENA,
  REHUB_CLAVE_SESION y, si existen, DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_KEY y las de Gmail.
- Sube los archivos del proyecto. Para publicar una versión nueva basta con volver a ejecutarlo.
Las claves se leen de ~/.rehub/claves.env y ~/.spotscout/claves.env.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()

from huggingface_hub import HfApi  # noqa: E402

USUARIO = os.environ.get("HF_USUARIO", "rehub-celso")
SPACE = os.environ.get("HF_SPACE", f"{USUARIO}/rehub")
SECRETOS = ["GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_MODELOS", "REHUB_CONTRASENA", "REHUB_CLAVE_SESION", "DATABASE_URL", "SUPABASE_URL",
            "SUPABASE_SERVICE_KEY", "SUPABASE_BUCKET", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_CUENTA"]
VARIABLES = {"REHUB_ENTORNO": "nube", "REHUB_RESTAURANTE": "Restaurante La Plaza"}
IGNORAR = [".venv/*", ".venv/**", "datos_locales/*", "datos_locales/**", "tests/_datos_pruebas/**", "__pycache__/**", "**/__pycache__/**", ".git/**",
           ".pytest_cache/**", "maqueta/**", "*.md", "!README.md", "datos_demo/competencia/**"]


def main():
    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("Falta HF_TOKEN en ~/.rehub/claves.env")
    api = HfApi(token=token)
    yo = api.whoami()["name"]
    print("Cuenta de Hugging Face:", yo)
    url = api.create_repo(SPACE, repo_type="space", space_sdk="docker", private=False, exist_ok=True)
    print("Space:", url)
    for k in SECRETOS:
        v = os.environ.get(k)
        if v:
            api.add_space_secret(SPACE, k, v)
            print("  secreto puesto:", k)
    for k, v in VARIABLES.items():
        api.add_space_variable(SPACE, k, v)
    print("Subiendo archivos…")
    api.upload_folder(repo_id=SPACE, repo_type="space", folder_path=str(RAIZ), ignore_patterns=IGNORAR,
                      commit_message="Nueva versión de ReHub")
    print(f"Hecho. Dirección: https://huggingface.co/spaces/{SPACE}  ·  app: https://{SPACE.replace('/', '-')}.hf.space")


if __name__ == "__main__":
    main()
