"""
Orquestador del canal de correo electrónico.
Pipeline: Ley 1581 → Rate limit → Delay → Render → Gmail → Log
"""
import os
from datetime import datetime
from typing import Optional

from ...database.connection import get_session
from ...database.models import HistorialInteracciones
from ...domain.entities import Cotizacion, EmpresaProspecto
from ...domain.resolution_0312 import ESPECIFICACIONES, clasificar_nivel_estandares
from ..compliance.habeas_data import HabeasDataService
from .gmail_client import GmailClient
from .rate_limiter import RateLimiter
from .templates import EmailContext, EmailTemplateEngine


class EmailService:

    def __init__(
        self,
        gmail_client: Optional[GmailClient] = None,
        rate_limiter: Optional[RateLimiter] = None,
        template_engine: Optional[EmailTemplateEngine] = None,
        habeas_data: Optional[HabeasDataService] = None,
    ):
        self._gmail = gmail_client or GmailClient.from_config()
        self._rate = rate_limiter or RateLimiter()
        self._templates = template_engine or EmailTemplateEngine()
        self._habeas = habeas_data or HabeasDataService()

    def enviar(
        self,
        empresa: EmpresaProspecto,
        tipo_plantilla: str,
        creado_por: str,
        cotizacion: Optional[Cotizacion] = None,
    ) -> str:
        """
        Ejecuta el pipeline completo de envío.
        Retorna el ID de mensaje de Gmail.
        Lanza HabeasDataError o RateLimitExceededError si hay bloqueo.
        """
        # 1 ── Verificar Ley 1581
        self._habeas.verificar_opt_out(empresa.id_empresa)

        # 2 ── Verificar límite diario
        self._rate.verificar("EMAIL")

        # 3 ── Delay aleatorio (simula cadencia humana)
        delay = self._rate.aplicar_delay("EMAIL")

        # 4 ── Construir contexto dinámico con variables de la empresa y la Res. 0312
        nivel = clasificar_nivel_estandares(empresa.num_empleados, empresa.nivel_riesgo_arl)
        spec = ESPECIFICACIONES[nivel]
        ctx = EmailContext(
            razon_social=empresa.razon_social,
            nombre_contacto=empresa.nombre_contacto or "Gerente",
            ciudad=empresa.ciudad,
            departamento=empresa.departamento,
            num_estandares=spec.num_estandares,
            nivel_riesgo=empresa.nivel_riesgo_arl.value,
            articulo_resolucion=spec.articulo_resolucion,
            empresa_remitente=os.getenv("EMPRESA_NOMBRE", "Medina SST Empresarial SAS"),
            email_remitente=os.getenv("EMPRESA_EMAIL", ""),
            opt_out_url=(
                f"mailto:{os.getenv('EMPRESA_EMAIL', '')}?"
                f"subject=Exclusión Base de Datos - {empresa.razon_social}"
            ),
            sector_economico=empresa.sector_economico or "",
            num_empleados=empresa.num_empleados,
            valor_cotizacion=cotizacion.valor_total_proyecto if cotizacion else None,
            fecha_vencimiento_cotizacion=(
                cotizacion.fecha_vencimiento.strftime("%d/%m/%Y")
                if cotizacion and cotizacion.fecha_vencimiento else None
            ),
        )

        # 5 ── Renderizar plantilla
        asunto, html_body = self._templates.renderizar(tipo_plantilla, ctx)
        plain_text = self._templates.renderizar_texto_plano(tipo_plantilla, ctx)

        # 6 ── Generar token de tracking e incrustar pixel (si TRACKING_URL configurado)
        from ...modules.tracking.pixel_tracker import generar_token, incrustar_pixel
        token = generar_token()
        html_con_pixel = incrustar_pixel(html_body, token)

        # 7 ── Enviar vía Gmail API
        mensaje_id = self._gmail.send(
            to=empresa.email_contacto,
            subject=asunto,
            html_body=html_con_pixel,
            plain_text=plain_text,
        )

        # 8 ── Registrar en HistorialInteracciones con token de tracking
        id_interaccion = self._log(
            id_empresa=empresa.id_empresa,
            id_cotizacion=cotizacion.id_cotizacion if cotizacion else None,
            asunto=asunto,
            cuerpo=html_body,
            tipo_plantilla=tipo_plantilla,
            responsable=creado_por,
            delay_s=delay,
            tracking_token=token,
        )

        return mensaje_id

    def _log(
        self,
        id_empresa: int,
        id_cotizacion: Optional[int],
        asunto: str,
        cuerpo: str,
        tipo_plantilla: str,
        responsable: str,
        delay_s: float,
        tracking_token: str = "",
    ) -> int:
        notas = f"Plantilla: {tipo_plantilla} | Delay: {delay_s}s"
        if tracking_token:
            notas += f" | TRACK:{tracking_token}"
        with get_session() as session:
            rec = HistorialInteracciones(
                id_empresa=id_empresa,
                id_cotizacion=id_cotizacion if id_cotizacion else None,
                tipo_interaccion="EMAIL_SALIENTE",
                canal="EMAIL",
                asunto=asunto,
                cuerpo_mensaje=cuerpo[:3000],
                estado_respuesta="ENVIADO",
                fecha_interaccion=datetime.now(),
                responsable=responsable,
                notas_seguimiento=notas,
            )
            session.add(rec)
            session.flush()
            return rec.id_interaccion
