"""
Orquestador del canal WhatsApp Business.
Pipeline: Ley 1581 → Rate limit → Delay → Render (por estado CRM) → Twilio → Log
"""
import os
from datetime import datetime
from typing import Optional

from ...database.connection import get_session
from ...database.models import HistorialInteracciones
from ...domain.entities import Cotizacion, EmpresaProspecto
from ...domain.resolution_0312 import ESPECIFICACIONES, clasificar_nivel_estandares
from ..compliance.habeas_data import HabeasDataService
from ..email.rate_limiter import RateLimiter
from .templates import WAContext, WhatsAppTemplateEngine
from .whatsapp_client import BaseWhatsAppClient, TwilioWhatsAppClient


class WhatsAppService:

    def __init__(
        self,
        wa_client: Optional[BaseWhatsAppClient] = None,
        rate_limiter: Optional[RateLimiter] = None,
        template_engine: Optional[WhatsAppTemplateEngine] = None,
        habeas_data: Optional[HabeasDataService] = None,
    ):
        # Instanciación lazy del cliente Twilio para no exigir credenciales en imports
        self._client = wa_client
        self._rate = rate_limiter or RateLimiter()
        self._templates = template_engine or WhatsAppTemplateEngine()
        self._habeas = habeas_data or HabeasDataService()

    def _get_client(self) -> BaseWhatsAppClient:
        if self._client is None:
            self._client = TwilioWhatsAppClient.from_env()
        return self._client

    def enviar(
        self,
        empresa: EmpresaProspecto,
        creado_por: str,
        cotizacion: Optional[Cotizacion] = None,
    ) -> str:
        """
        Selecciona la plantilla según el estado CRM de la empresa y ejecuta el pipeline.
        Retorna el SID del mensaje de Twilio.
        Lanza HabeasDataError o RateLimitExceededError si hay bloqueo.
        """
        if not empresa.telefono:
            raise ValueError(
                f"La empresa '{empresa.razon_social}' no tiene teléfono registrado."
            )

        # 1 ── Verificar Ley 1581
        self._habeas.verificar_opt_out(empresa.id_empresa)

        # 2 ── Verificar límite diario
        self._rate.verificar("WHATSAPP")

        # 3 ── Delay aleatorio
        delay = self._rate.aplicar_delay("WHATSAPP")

        # 4 ── Construir contexto y renderizar según estado CRM
        nivel = clasificar_nivel_estandares(empresa.num_empleados, empresa.nivel_riesgo_arl)
        spec = ESPECIFICACIONES[nivel]
        from ...config import get_config
        cfg = get_config()
        ctx = WAContext(
            nombre_contacto=empresa.nombre_contacto or "Gerente",
            razon_social=empresa.razon_social,
            ciudad=empresa.ciudad,
            num_estandares=spec.num_estandares,
            articulo_resolucion=spec.articulo_resolucion,
            nivel_riesgo=empresa.nivel_riesgo_arl.value,
            empresa_remitente=cfg.empresa_nombre,
            email_remitente=cfg.empresa_email,
            valor_cotizacion=cotizacion.valor_total_proyecto if cotizacion else None,
            fecha_vencimiento=(
                cotizacion.fecha_vencimiento.strftime("%d/%m/%Y")
                if cotizacion and cotizacion.fecha_vencimiento else None
            ),
            nombre_asesora=cfg.asesora_nombre,
        )
        body = self._templates.renderizar(empresa.estado_prospecto.value, ctx)

        # 5 ── Enviar vía Twilio
        numero = empresa.telefono.strip().replace(" ", "")
        if not numero.startswith("+"):
            numero = f"+57{numero}"  # prefijo Colombia por defecto

        mensaje_sid = self._get_client().send_message(to_number=numero, body=body)

        # 6 ── Registrar en HistorialInteracciones
        self._log(
            id_empresa=empresa.id_empresa,
            id_cotizacion=cotizacion.id_cotizacion if cotizacion else None,
            asunto=f"WhatsApp – {empresa.estado_prospecto.value}",
            cuerpo=body,
            responsable=creado_por,
            delay_s=delay,
        )

        return mensaje_sid

    def _log(
        self,
        id_empresa: int,
        id_cotizacion: Optional[int],
        asunto: str,
        cuerpo: str,
        responsable: str,
        delay_s: float,
    ) -> None:
        with get_session() as session:
            session.add(HistorialInteracciones(
                id_empresa=id_empresa,
                id_cotizacion=id_cotizacion if id_cotizacion else None,
                tipo_interaccion="WHATSAPP_SALIENTE",
                canal="WHATSAPP",
                asunto=asunto,
                cuerpo_mensaje=cuerpo,
                estado_respuesta="ENVIADO",
                fecha_interaccion=datetime.now(),
                responsable=responsable,
                notas_seguimiento=f"Delay: {delay_s}s",
            ))
