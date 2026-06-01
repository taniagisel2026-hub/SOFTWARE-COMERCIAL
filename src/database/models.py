from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class EmpresaProspecto(Base):
    __tablename__ = "empresa_prospecto"

    id_empresa: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    sector_economico: Mapped[Optional[str]] = mapped_column(String(100))
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    departamento: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[Optional[str]] = mapped_column(String(300))
    telefono: Mapped[Optional[str]] = mapped_column(String(30))
    email_contacto: Mapped[Optional[str]] = mapped_column(String(150))
    nombre_contacto: Mapped[Optional[str]] = mapped_column(String(150))
    cargo_contacto: Mapped[Optional[str]] = mapped_column(String(100))
    # Riesgo ARL según clasificación Decreto 1607/2002: I, II, III, IV, V
    nivel_riesgo_arl: Mapped[str] = mapped_column(String(5), nullable=False)
    num_empleados: Mapped[int] = mapped_column(Integer, nullable=False)
    estado_prospecto: Mapped[str] = mapped_column(String(30), nullable=False, default="NUEVO")
    fuente_origen: Mapped[Optional[str]] = mapped_column(String(50))
    fecha_registro: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_ultima_actualizacion: Mapped[date] = mapped_column(Date, nullable=False)
    # Ley 1581 de 2012 – Habeas Data
    opt_out: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_opt_out: Mapped[Optional[date]] = mapped_column(Date)
    motivo_opt_out: Mapped[Optional[str]] = mapped_column(String(300))

    cotizaciones: Mapped[list["Cotizacion"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    interacciones: Mapped[list["HistorialInteracciones"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")


class Cotizacion(Base):
    __tablename__ = "cotizacion"

    id_cotizacion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresa_prospecto.id_empresa"), nullable=False)
    codigo_cotizacion: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0")
    num_empleados_cotizados: Mapped[int] = mapped_column(Integer, nullable=False)
    nivel_riesgo: Mapped[str] = mapped_column(String(5), nullable=False)
    # NIVEL_7 | NIVEL_21 | NIVEL_60 — según Resolución 0312/2019
    nivel_estandares: Mapped[str] = mapped_column(String(20), nullable=False)
    servicios_incluidos: Mapped[Optional[dict]] = mapped_column(JSON)
    valor_servicios: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    valor_viaticos: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    valor_total_proyecto: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    valor_total_mensual: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    valor_total_anual: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(5), nullable=False, default="COP")
    estado_cotizacion: Mapped[str] = mapped_column(String(20), nullable=False, default="BORRADOR")
    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date)
    url_documento_pdf: Mapped[Optional[str]] = mapped_column(String(500))
    creado_por: Mapped[str] = mapped_column(String(100), nullable=False)

    empresa: Mapped["EmpresaProspecto"] = relationship(back_populates="cotizaciones")
    interacciones: Mapped[list["HistorialInteracciones"]] = relationship(back_populates="cotizacion")


class HistorialInteracciones(Base):
    __tablename__ = "historial_interacciones"

    id_interaccion: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_empresa: Mapped[int] = mapped_column(ForeignKey("empresa_prospecto.id_empresa"), nullable=False)
    id_cotizacion: Mapped[Optional[int]] = mapped_column(ForeignKey("cotizacion.id_cotizacion"))
    tipo_interaccion: Mapped[str] = mapped_column(String(50), nullable=False)
    canal: Mapped[Optional[str]] = mapped_column(String(30))
    asunto: Mapped[Optional[str]] = mapped_column(String(300))
    cuerpo_mensaje: Mapped[Optional[str]] = mapped_column(Text)
    estado_respuesta: Mapped[Optional[str]] = mapped_column(String(30))
    fecha_interaccion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    responsable: Mapped[Optional[str]] = mapped_column(String(100))
    notas_seguimiento: Mapped[Optional[str]] = mapped_column(Text)

    empresa: Mapped["EmpresaProspecto"] = relationship(back_populates="interacciones")
    cotizacion: Mapped[Optional["Cotizacion"]] = relationship(back_populates="interacciones")


class ContenidoRedes(Base):
    __tablename__ = "contenido_redes"

    id_contenido: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo_contenido: Mapped[str] = mapped_column(String(30), nullable=False)
    plataforma_destino: Mapped[str] = mapped_column(String(50), nullable=False)
    texto_publicacion: Mapped[Optional[str]] = mapped_column(Text)
    url_imagen_1: Mapped[Optional[str]] = mapped_column(String(500))
    url_imagen_2: Mapped[Optional[str]] = mapped_column(String(500))
    url_imagen_3: Mapped[Optional[str]] = mapped_column(String(500))
    url_articulo: Mapped[Optional[str]] = mapped_column(String(500))
    tema_sst: Mapped[Optional[str]] = mapped_column(String(150))
    estado_publicacion: Mapped[str] = mapped_column(String(30), nullable=False, default="BORRADOR")
    fecha_generacion: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_publicacion: Mapped[Optional[date]] = mapped_column(Date)
    generado_por_ia: Mapped[Optional[str]] = mapped_column(String(50))
    engagement_likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
