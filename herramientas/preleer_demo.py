"""Lee UNA VEZ con la IA de verdad las fotos y los correos de clientes de la demo y guarda
los resultados en datos_demo/lecturas_ia.json (la caché que usa la app).

Uso:  .venv\\Scripts\\python.exe herramientas\\preleer_demo.py
Se puede repetir: salta lo que ya está leído. Si se acaba el tope gratuito del día,
guarda lo hecho y para; se vuelve a lanzar al día siguiente.
"""
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.environ["REHUB_GUARDAR_LECTURAS"] = "1"
os.environ.setdefault("REHUB_CARPETA_LOCAL", str(RAIZ / "datos_locales"))

from iniciar_local import cargar_claves  # noqa: E402

cargar_claves()

from app import cache_ia, ia, lectura, procesar  # noqa: E402

DEMO = RAIZ / "datos_demo"


def fotos():
    for carpeta in ("facturas_escaneadas", "tickets", "etiquetas", "en_directo"):
        for f in sorted((DEMO / carpeta).glob("*.jpg")):
            yield f


def correos_clientes():
    for archivo in ("correos.json", "envio_en_directo.json"):
        for c in json.loads((DEMO / archivo).read_text(encoding="utf-8")):
            if c["alias"] in ("cliente", "oficina") and not c.get("adjuntos"):
                yield c


if __name__ == "__main__":
    hoy = date(2026, 10, 11)
    hechas = saltadas = 0
    try:
        for f in fotos():
            contenido = f.read_bytes()
            if cache_ia.buscar("foto:" + cache_ia.huella(contenido)) is not None:
                saltadas += 1
                continue
            t = time.time()
            d = lectura.leer_foto(contenido)
            hechas += 1
            print(f"{f.name}: {d['tipo']} · total {d.get('total')} · caduca {d.get('caducidad')} · revisar {d['revisar'][:1]} ({time.time() - t:.0f} s)")
        for c in correos_clientes():
            clave = "correo:" + cache_ia.huella(f"{c['de_nombre']}\n{c['asunto']}\n{c['cuerpo']}")
            if cache_ia.buscar(clave) is not None:
                saltadas += 1
                continue
            r = procesar.entender_cliente(c["asunto"], c["cuerpo"], c["de_nombre"], hoy, "Restaurante La Plaza")
            if r.get("sin_ia"):
                raise ia.CuotaAgotada("sin IA")
            hechas += 1
            print(f"{c['de_nombre']} · {c['asunto']}: {r['categoria']} · {r.get('fecha')} {r.get('hora')} {r.get('personas')}")
    except ia.CuotaAgotada:
        print("Se ha acabado el tope gratuito de hoy. Vuelve a lanzarlo mañana: seguirá donde lo dejó.")
    print(f"Leídas ahora: {hechas} · ya estaban: {saltadas} · total en caché: {cache_ia.cuantas()}")
