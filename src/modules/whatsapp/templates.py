"""
Plantillas de WhatsApp Business por estado del lead en el CRM.

Las plantillas siguen el formato HSM (Highly Structured Messages) de Meta:
variables posicionales entre dobles llaves {{ n }} para aprobación de negocio.
El texto aquí corresponde a mensajes aprobados que se envían ANTES de iniciar
una conversación (ventana de 24 horas cerrada).
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from jinja2 import Environment, StrictUndefined

from ...domain.entities import EstadoProspecto


@dataclass
class WAContext:
    nombre_contacto: str
    razon_social: str
    ciudad: str
    num_estandares: int
    articulo_resolucion: str
    nivel_riesgo: str
    empresa_remitente: str
    email_remitente: str
    valor_cotizacion: Optional[Decimal] = None
    fecha_vencimiento: Optional[str] = None


# Cada entrada: estado CRM → texto de la plantilla (Jinja2)
# Se mapean a template_name de Meta; en Twilio se usan como body directo.
_PLANTILLAS: dict[str, str] = {

    EstadoProspecto.NUEVO.value: (
        "Hola {{ nombre_contacto }}, soy del equipo de *{{ empresa_remitente }}*. 👋\n\n"
        "Notamos que *{{ razon_social }}* en {{ ciudad }} puede necesitar el diseño de su "
        "SG-SST bajo la *Resolución 0312/2019*.\n\n"
        "Le aplican *{{ num_estandares }} estándares mínimos* ({{ articulo_resolucion }} – "
        "Riesgo ARL {{ nivel_riesgo }}).\n\n"
        "¿Le interesa conocer cómo podemos ayudarle a cumplir esta obligación? 🤝"
    ),

    EstadoProspecto.EN_SEGUIMIENTO.value: (
        "Hola de nuevo, {{ nombre_contacto }} 👋\n\n"
        "Hacemos seguimiento a nuestra consulta para *{{ razon_social }}* sobre el "
        "cumplimiento de los *{{ num_estandares }} estándares* de la Res. 0312/2019.\n\n"
        "¿Podemos coordinar una llamada de 15 minutos esta semana para resolver sus dudas? 📞\n\n"
        "_{{ empresa_remitente }} · {{ email_remitente }}_"
    ),

    EstadoProspecto.COTIZACION_ENVIADA.value: (
        "Hola {{ nombre_contacto }},\n\n"
        "¿Pudo revisar la propuesta SG-SST que enviamos a *{{ razon_social }}*? 📋\n\n"
        "{% if valor_cotizacion %}"
        "Valor del proyecto: *$ {{ '{:,.0f}'.format(valor_cotizacion).replace(',','.') }} COP*"
        "{% if fecha_vencimiento %} (válida hasta el {{ fecha_vencimiento }}){% endif %}.\n\n"
        "{% endif %}"
        "Podemos ajustar el alcance o la forma de pago. ¿Tiene alguna pregunta? 🤝"
    ),

    EstadoProspecto.NEGOCIACION.value: (
        "{{ nombre_contacto }}, queremos ayudarle a *{{ razon_social }}* a cumplir el "
        "*{{ articulo_resolucion }}* de la Res. 0312 antes de la próxima visita del "
        "Ministerio del Trabajo. 💼\n\n"
        "Podemos iniciar con la documentación base esta misma semana. "
        "¿Cerramos la propuesta hoy? ✅\n\n"
        "_{{ empresa_remitente }}_"
    ),
}

_jinja = Environment(undefined=StrictUndefined, autoescape=False)


class WhatsAppTemplateEngine:

    ESTADOS_DISPONIBLES = list(_PLANTILLAS.keys())

    def renderizar(self, estado_crm: str, ctx: WAContext) -> str:
        """Retorna el mensaje renderizado para el estado CRM dado."""
        if estado_crm not in _PLANTILLAS:
            raise ValueError(
                f"No hay plantilla para el estado '{estado_crm}'. "
                f"Disponibles: {self.ESTADOS_DISPONIBLES}"
            )
        return _jinja.from_string(_PLANTILLAS[estado_crm]).render(**ctx.__dict__)
