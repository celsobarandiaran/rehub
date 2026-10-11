"""Preparación común de las pruebas: carpeta de datos propia (base y archivos) y sin IA.

Se ejecuta antes de importar la app, así que la configuración ya nace apuntando aquí.
Importante: las pruebas borran archivos (Reiniciar demo); por eso nunca deben usar la carpeta
datos_locales de verdad.
"""
import os
import shutil
from pathlib import Path

_CARPETA = Path(__file__).resolve().parent / "_datos_pruebas"
shutil.rmtree(_CARPETA, ignore_errors=True)
_CARPETA.mkdir(parents=True, exist_ok=True)
os.environ["REHUB_CARPETA_LOCAL"] = str(_CARPETA)
os.environ["DATABASE_URL"] = f"sqlite:///{_CARPETA / 'pruebas.db'}"
os.environ["REHUB_ENTORNO"] = "local"
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_SERVICE_KEY", None)
