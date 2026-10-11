"""Carga la demo entera muy rápido (sin IA) y comprueba lo que exige el criterio de éxito."""
import time

from sqlalchemy import func, select

from app import db, demo


def test_cargar_demo_completa():
    db.Base.metadata.drop_all(db.motor)
    db.crear_tablas()
    demo.reiniciar()
    t0 = time.time()
    demo.empezar(segundos_por_dia=0)
    while demo.ESTADO.en_marcha:
        time.sleep(0.2)
    assert not demo.ESTADO.error, demo.ESTADO.error
    assert time.time() - t0 < 600
    # Sin clave de IA, las fotos que están en la caché (datos_demo/lecturas_ia.json: escaneadas, tickets y etiquetas)
    # se leen igual. Se espera a que el hilo de la IA termine.
    for _ in range(300):
        if demo._hilo_ia is None or not demo._hilo_ia.is_alive():
            break
        time.sleep(0.2)
    with db.SesionDB() as s:
        n = lambda q: s.scalar(select(func.count()).select_from(q.subquery()))  # noqa: E731
        assert n(select(db.Documento).where(db.Documento.tipo == "factura")) == 70
        assert n(select(db.Documento).where(db.Documento.tipo == "gasto")) == 20
        assert n(select(db.Documento).where(db.Documento.tipo == "nomina")) == 12
        assert n(select(db.Cierre)) == 61
        assert n(select(db.Documento).where(db.Documento.estado == "leyendo")) == 0  # todo está en la caché
        etiquetas = list(s.scalars(select(db.Entrada).where(db.Entrada.caducidad_estimada.is_(False))))
        assert len(etiquetas) >= 12 and all(e.caduca and e.lote for e in etiquetas)  # fecha y lote leídos de la etiqueta
        revisar = list(s.scalars(select(db.Documento).where(db.Documento.estado == "revisar")))
        # La escaneada con el número ilegible y los tickets de la farmacia (la IA avisa de que la descripción está cortada)
        assert any(r.tipo == "factura" and "numero" in r.motivo_revisar.lower().replace("ú", "u") for r in revisar), [r.motivo_revisar for r in revisar]
        assert all(r.tipo in ("factura", "gasto") for r in revisar) and len(revisar) <= 4, [(r.tipo, r.motivo_revisar) for r in revisar]
        dup = list(s.scalars(select(db.Documento).where(db.Documento.estado == "duplicada")))
        assert len(dup) == 1 and dup[0].proveedor.nombre == "Carnes Vallès"
        subidas = [a.texto for a in s.scalars(select(db.Aviso).where(db.Aviso.tipo == "subida_precio"))]
        assert any(t.startswith("Entrecot de vaca") for t in subidas), subidas
        assert any(t.startswith("Lubina fresca") for t in subidas), subidas
        assert len(subidas) == 2, subidas
        pagadas = n(select(db.Documento).where(db.Documento.pagado_fecha.is_not(None)))
        assert pagadas > 30
        mv = list(s.scalars(select(db.MovimientoBanco).order_by(db.MovimientoBanco.id.desc()).limit(1)))[0]
        assert abs(mv.saldo - 10528.60) < 0.01
        pescados = s.scalar(select(db.Proveedor).where(db.Proveedor.nombre == "Pescados Mar Nou"))
        assert pescados.telefono == "93 000 56 78" and pescados.cif == "B-00000002"
        archivo = s.scalar(select(db.Documento.archivo).where(db.Documento.numero == "C-8403"))
        # Sin acentos a propósito: el almacén de la nube no los admite en los nombres
        assert archivo.startswith("2026/08/facturas/2026-08-03 Carnes Valles 406,74"), archivo
    demo.reiniciar()
    with db.SesionDB() as s:
        assert s.scalar(select(func.count(db.Documento.id))) == 0
