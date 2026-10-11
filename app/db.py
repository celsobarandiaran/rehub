"""Base de datos de ReHub: tablas y conexión.

En tu PC usa SQLite; en la nube, la base de Supabase (Postgres, Frankfurt).
Importes de compras y ventas se guardan SIN IVA en `base` y con IVA en `total`.
"""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text,
                        create_engine, select)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from . import config


class Base(DeclarativeBase):
    pass


def _ahora():
    return datetime.utcnow()


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    perfil: Mapped[str] = mapped_column(String(20))  # dueno / oficina / trabajador
    clave_hash: Mapped[str] = mapped_column(String(200), default="")
    empleado_id: Mapped[int | None] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado: Mapped[datetime] = mapped_column(DateTime, default=_ahora)


class Ajuste(Base):
    __tablename__ = "ajustes"
    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(Text, default="")


class Proveedor(Base):
    __tablename__ = "proveedores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    grupo: Mapped[str] = mapped_column(String(20), default="comida")  # comida / local
    tipo: Mapped[str] = mapped_column(String(60), default="")
    telefono: Mapped[str] = mapped_column(String(40), default="")
    correo: Mapped[str] = mapped_column(String(120), default="")
    cif: Mapped[str] = mapped_column(String(20), default="")
    direccion: Mapped[str] = mapped_column(String(200), default="")
    entregas_al_mes: Mapped[float] = mapped_column(Float, default=0)


class Correo(Base):
    __tablename__ = "correos"
    id: Mapped[int] = mapped_column(primary_key=True)
    gmail_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    remitente: Mapped[str] = mapped_column(String(200), default="")
    alias: Mapped[str] = mapped_column(String(40), default="")  # +proveedor, +cliente...
    asunto: Mapped[str] = mapped_column(String(300), default="")
    cuerpo: Mapped[str] = mapped_column(Text, default="")
    recibido: Mapped[datetime] = mapped_column(DateTime, default=_ahora)
    categoria: Mapped[str] = mapped_column(String(30), default="sin_clasificar")
    datos: Mapped[dict] = mapped_column(JSON, default=dict)  # fecha/hora/personas de una reserva...
    respuesta_propuesta: Mapped[str] = mapped_column(Text, default="")
    respuesta_enviada: Mapped[bool] = mapped_column(Boolean, default=False)


class Documento(Base):
    """Factura, gasto (ticket), nómina, cierre de TPV u otro."""
    __tablename__ = "documentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)  # factura / gasto / nomina / cierre / otro
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedores.id"), nullable=True)
    numero: Mapped[str] = mapped_column(String(60), default="")
    base: Mapped[float | None] = mapped_column(Float, nullable=True)
    iva: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    categoria_gasto: Mapped[str] = mapped_column(String(60), default="")
    empleado_id: Mapped[int | None] = mapped_column(ForeignKey("empleados.id"), nullable=True)
    archivo: Mapped[str] = mapped_column(String(300), default="")  # ruta en el almacén
    origen: Mapped[str] = mapped_column(String(20), default="correo")  # correo / foto / subida / demo
    correo_id: Mapped[int | None] = mapped_column(ForeignKey("correos.id"), nullable=True)
    estado: Mapped[str] = mapped_column(String(30), default="correcto")  # correcto / revisar / duplicada
    motivo_revisar: Mapped[str] = mapped_column(String(300), default="")
    pagado_fecha: Mapped[date | None] = mapped_column(Date, nullable=True)  # sale del extracto del banco
    datos: Mapped[dict] = mapped_column(JSON, default=dict)
    creado: Mapped[datetime] = mapped_column(DateTime, default=_ahora)
    proveedor: Mapped[Proveedor | None] = relationship()
    lineas: Mapped[list["LineaDocumento"]] = relationship(back_populates="documento", cascade="all, delete-orphan")


class LineaDocumento(Base):
    __tablename__ = "lineas_documento"
    id: Mapped[int] = mapped_column(primary_key=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos.id"))
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("productos.id"), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(200), default="")
    cantidad: Mapped[float | None] = mapped_column(Float, nullable=True)
    unidad: Mapped[str] = mapped_column(String(20), default="kg")
    precio_unitario: Mapped[float | None] = mapped_column(Float, nullable=True)  # sin IVA
    documento: Mapped[Documento] = relationship(back_populates="lineas")


class Producto(Base):
    __tablename__ = "productos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    tipo: Mapped[str] = mapped_column(String(30), default="seco")  # pescado / carne / verdura / seco / congelado / bebida
    unidad: Mapped[str] = mapped_column(String(20), default="kg")
    rendimiento: Mapped[float] = mapped_column(Float, default=1.0)  # lo que queda tras limpiar (0-1)
    codigo_mercabarna: Mapped[str] = mapped_column(String(20), default="")
    alergenos: Mapped[str] = mapped_column(String(200), default="")


class Entrada(Base):
    """Lo que entra en cámara: viene del albarán y, si hay, de la etiqueta."""
    __tablename__ = "entradas"
    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id"), nullable=True)
    fecha: Mapped[date] = mapped_column(Date)
    cantidad: Mapped[float] = mapped_column(Float)
    caduca: Mapped[date | None] = mapped_column(Date, nullable=True)
    caducidad_estimada: Mapped[bool] = mapped_column(Boolean, default=True)
    lote: Mapped[str] = mapped_column(String(60), default="")
    foto: Mapped[str] = mapped_column(String(300), default="")


class Recuento(Base):
    __tablename__ = "recuentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad_contada: Mapped[float] = mapped_column(Float)


class Plato(Base):
    __tablename__ = "platos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    parte: Mapped[str] = mapped_column(String(20), default="comida")  # comida / bebida
    precio_carta: Mapped[float] = mapped_column(Float)  # con IVA, como en la carta
    clave_competencia: Mapped[str] = mapped_column(String(60), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    receta: Mapped[list["LineaReceta"]] = relationship(cascade="all, delete-orphan")


class LineaReceta(Base):
    __tablename__ = "lineas_receta"
    id: Mapped[int] = mapped_column(primary_key=True)
    plato_id: Mapped[int] = mapped_column(ForeignKey("platos.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("productos.id"))
    cantidad: Mapped[float] = mapped_column(Float)  # ya limpia, en la unidad del producto
    producto: Mapped[Producto] = relationship()


class Cierre(Base):
    """Cierre diario del TPV."""
    __tablename__ = "cierres"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, unique=True)
    ventas_total: Mapped[float] = mapped_column(Float)  # con IVA
    tarjeta: Mapped[float] = mapped_column(Float, default=0)
    efectivo: Mapped[float] = mapped_column(Float, default=0)
    cubiertos: Mapped[int] = mapped_column(Integer, default=0)
    efectivo_contado: Mapped[float | None] = mapped_column(Float, nullable=True)
    unidades: Mapped[dict] = mapped_column(JSON, default=dict)  # plato -> unidades
    franjas: Mapped[dict] = mapped_column(JSON, default=dict)   # "12-14" -> ventas
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id"), nullable=True)


class Empleado(Base):
    __tablename__ = "empleados"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))
    puesto: Mapped[str] = mapped_column(String(60), default="")
    horas_semana: Mapped[float] = mapped_column(Float, default=40)


class Turno(Base):
    __tablename__ = "turnos"
    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleados.id"))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    tramos: Mapped[list] = mapped_column(JSON, default=list)  # [["12:30","16:30"],["20:00","24:00"]]


class Evento(Base):
    __tablename__ = "eventos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    nombre: Mapped[str] = mapped_column(String(200))
    efecto: Mapped[str] = mapped_column(String(60), default="")


class PagoFijo(Base):
    __tablename__ = "pagos_fijos"
    id: Mapped[int] = mapped_column(primary_key=True)
    concepto: Mapped[str] = mapped_column(String(120))
    dia: Mapped[int] = mapped_column(Integer)
    importe: Mapped[float] = mapped_column(Float)
    cada: Mapped[str] = mapped_column(String(20), default="mes")  # mes / trimestre
    aproximado: Mapped[bool] = mapped_column(Boolean, default=False)


class MovimientoBanco(Base):
    __tablename__ = "movimientos_banco"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    concepto: Mapped[str] = mapped_column(String(300))
    importe: Mapped[float] = mapped_column(Float)  # + entra, - sale
    saldo: Mapped[float | None] = mapped_column(Float, nullable=True)
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(String(30), default="")  # pago_factura / abono_tarjeta / recibo_sin_factura...


class Competidor(Base):
    __tablename__ = "competidores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    distancia_m: Mapped[int] = mapped_column(Integer, default=0)
    valoracion: Mapped[float | None] = mapped_column(Float, nullable=True)
    opiniones: Mapped[int] = mapped_column(Integer, default=0)
    carta: Mapped[dict] = mapped_column(JSON, default=dict)  # clave -> precio con IVA


motor = create_engine(config.URL_BASE_DATOS, pool_pre_ping=True)
SesionDB = sessionmaker(bind=motor, expire_on_commit=False)


def crear_tablas() -> None:
    if config.URL_BASE_DATOS.startswith("sqlite"):
        config.CARPETA_LOCAL.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(motor)


def base_responde() -> bool:
    try:
        with Session(motor) as s:
            s.execute(select(1))
        return True
    except Exception:
        return False
