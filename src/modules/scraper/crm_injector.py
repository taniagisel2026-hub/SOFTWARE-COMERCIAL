"""
CRMInjectorService — inyecta prospectos extraídos en la tabla EMPRESA_PROSPECTO.

Lógica de deduplicación (en orden):
  1. Busca por NIT exacto (si existe y no es temporal)
  2. Busca por nombre normalizado + ciudad (elimina sufijos legales antes de comparar)
  3. Si no existe → inserta como NUEVO
  4. Si existe → actualiza solo campos vacíos (no sobreescribe datos mejores previos)
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func

from ...database.connection import get_session
from ...database.models import EmpresaProspecto
from .base import ProspectoExtraido, _normalizar_nombre_empresa, _normalizar_texto


def _generar_nit_temporal(razon_social: str, ciudad: str) -> str:
    """NIT de marcador para empresas sin NIT conocido; nunca coincide con el formato colombiano."""
    clave = f"{razon_social.lower()}|{ciudad.lower()}"
    return f"TEMP-{abs(hash(clave)):012d}"


@dataclass
class InyeccionLoteResult:
    insertadas: int = 0
    actualizadas: int = 0
    omitidas: int = 0
    ids_nuevos: list[int] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)

    @property
    def total_procesadas(self) -> int:
        return self.insertadas + self.actualizadas + self.omitidas


class CRMInjectorService:

    def inyectar(self, prospecto: ProspectoExtraido) -> tuple[int, bool]:
        """
        Inserta o actualiza un prospecto.
        Retorna (id_empresa, fue_creado: bool).
        """
        with get_session() as session:
            existente = self._buscar_existente(session, prospecto)

            if existente:
                self._actualizar_campos_vacios(existente, prospecto)
                return existente.id_empresa, False

            nuevo = self._crear_orm(prospecto)
            session.add(nuevo)
            session.flush()
            return nuevo.id_empresa, True

    def inyectar_lote(self, prospectos: list[ProspectoExtraido]) -> InyeccionLoteResult:
        resultado = InyeccionLoteResult()

        for prospecto in prospectos:
            if not prospecto.email and not prospecto.whatsapp:
                resultado.omitidas += 1
                print(f"  [CRM] Omitido (sin email ni WhatsApp): {prospecto.razon_social[:50]}")
                continue

            try:
                id_empresa, fue_creado = self.inyectar(prospecto)
                if fue_creado:
                    resultado.insertadas += 1
                    resultado.ids_nuevos.append(id_empresa)
                else:
                    resultado.actualizadas += 1
            except Exception as exc:
                resultado.omitidas += 1
                resultado.errores.append(
                    f"{prospecto.razon_social}: {exc}"
                )

        return resultado

    # ── Búsqueda de duplicados ────────────────────────────────────────────────

    def _buscar_existente(self, session, p: ProspectoExtraido) -> EmpresaProspecto | None:
        # 1. NIT exacto (solo si no es temporal y no está vacío)
        if p.nit and not p.nit.startswith("TEMP-"):
            encontrado = session.query(EmpresaProspecto).filter_by(nit=p.nit).first()
            if encontrado:
                return encontrado

        # 2. Email exacto — evita duplicados de fichas distintas con el mismo contacto
        if p.email:
            por_email = session.query(EmpresaProspecto).filter_by(email_contacto=p.email).first()
            if por_email:
                return por_email

        # 3. Nombre normalizado + ciudad — cubre la misma empresa reaparecida (otro
        # sector/día) con un email distinto al ya guardado. El NIT temporal se genera
        # solo a partir de nombre+ciudad, así que sin este paso el insert choca contra
        # el NIT temporal ya existente (UNIQUE) y ese contacto se pierde en vez de
        # fusionarse con el registro existente.
        nombre_norm = _normalizar_nombre_empresa(p.razon_social)
        ciudad_norm = _normalizar_texto(p.ciudad)

        candidatos = (
            session.query(EmpresaProspecto)
            .filter(
                func.lower(EmpresaProspecto.ciudad).contains(ciudad_norm[:15])
            )
            .all()
        )
        for candidato in candidatos:
            if _normalizar_nombre_empresa(candidato.razon_social)[:25] == nombre_norm[:25]:
                return candidato

        return None

    # ── Actualización de campos vacíos ────────────────────────────────────────

    @staticmethod
    def _actualizar_campos_vacios(existente: EmpresaProspecto, p: ProspectoExtraido) -> None:
        """Enriquece el registro existente con datos nuevos sin sobreescribir datos previos."""
        if p.telefono and not existente.telefono:
            existente.telefono = p.telefono
        if p.whatsapp and not existente.whatsapp:
            existente.whatsapp = p.whatsapp
        if p.email and not existente.email_contacto:
            existente.email_contacto = p.email
        if p.direccion and not existente.direccion:
            existente.direccion = p.direccion
        if p.sitio_web and not existente.fuente_origen:
            existente.fuente_origen = p.fuente
        if p.nombre_contacto and not existente.nombre_contacto:
            existente.nombre_contacto = p.nombre_contacto
        if p.cargo_contacto and not existente.cargo_contacto:
            existente.cargo_contacto = p.cargo_contacto
        if p.sector_economico and not existente.sector_economico:
            existente.sector_economico = p.sector_economico
        if p.num_empleados > 0 and existente.num_empleados == 0:
            existente.num_empleados = p.num_empleados
        existente.fecha_ultima_actualizacion = date.today()

    # ── Creación ORM ──────────────────────────────────────────────────────────

    @staticmethod
    def _crear_orm(p: ProspectoExtraido) -> EmpresaProspecto:
        return EmpresaProspecto(
            razon_social=p.razon_social[:200],
            nit=p.nit or _generar_nit_temporal(p.razon_social, p.ciudad),
            sector_economico=p.sector_economico[:100] if p.sector_economico else None,
            ciudad=p.ciudad[:100],
            departamento=p.departamento[:100] if p.departamento else "",
            direccion=p.direccion[:300] if p.direccion else None,
            telefono=p.telefono[:30] if p.telefono else None,
            whatsapp=p.whatsapp[:30] if p.whatsapp else None,
            email_contacto=p.email[:150] if p.email else None,
            nombre_contacto=p.nombre_contacto[:150] if p.nombre_contacto else None,
            cargo_contacto=p.cargo_contacto[:100] if p.cargo_contacto else None,
            nivel_riesgo_arl=p.nivel_riesgo_arl or "I",
            num_empleados=p.num_empleados or 0,
            estado_prospecto="NUEVO",
            fuente_origen=p.fuente[:50],
            opt_out=False,
            fecha_registro=date.today(),
            fecha_ultima_actualizacion=date.today(),
        )
