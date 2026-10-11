"""Preparación común de las pruebas: base de datos propia en un archivo y sin IA.

Se ejecuta antes de importar la app, así que la configuración ya nace apuntando aquí.
"""
import os
from pathlib import Path

_BD = Path(__file__).resolve().parent / "_pruebas.db"
if _BD.exists():
    _BD.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_BD}"
os.environ["REHUB_ENTORNO"] = "local"
os.environ.pop("GEMINI_API_KEY", None)
