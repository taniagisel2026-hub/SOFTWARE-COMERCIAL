"""
Orquestador del canal de correo electrónico.
Pipeline: Ley 1581 → Rate limit → Delay → Render → Brevo (o Gmail) → Log

Prioridad de envío:
  1. Brevo  — si BREVO_API_KEY está en .env (recomendado, mejor entregabilidad)
  2. Gmail  — fallback si no hay clave Brevo
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
from .brevo_client import BrevoClient
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
        self._gmail = gmail_client  # se inicializa lazy si se necesita
        self._rate = rate_limiter or RateLimiter()
        self._templates = template_engine or EmailTemplateEngine()
        self._habeas = habeas_data or HabeasDataService()

    def _get_sender(self):
        """Retorna cliente Brevo si está configurado, si no usa Gmail."""
        if os.getenv("BREVO_API_KEY", "").strip():
            return "brevo", BrevoClient.from_env()
        if self._gmail is None:
            self._gmail = GmailClient.from_config()
        return "gmail", self._gmail

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

        # 3 ── Delay aleatorio (simula cadencia humana) — se omite en envíos manuales
        delay = 0.0 if tipo_plantilla in ("ENVIO_PORTAFOLIO",) else self._rate.aplicar_delay("EMAIL")

        # 4 ── Construir contexto dinámico con variables de la empresa y la Res. 0312
        nivel = clasificar_nivel_estandares(empresa.num_empleados, empresa.nivel_riesgo_arl)
        spec = ESPECIFICACIONES[nivel]
        from ...config import get_config
        cfg = get_config()
        ctx = EmailContext(
            razon_social=empresa.razon_social,
            nombre_contacto=empresa.nombre_contacto or "Gerente",
            ciudad=empresa.ciudad,
            departamento=empresa.departamento,
            num_estandares=spec.num_estandares,
            nivel_riesgo=empresa.nivel_riesgo_arl.value,
            articulo_resolucion=spec.articulo_resolucion,
            empresa_remitente=cfg.empresa_nombre,
            email_remitente=cfg.empresa_email,
            opt_out_url=(
                f"mailto:{cfg.empresa_email}?"
                f"subject=Exclusión Base de Datos - {empresa.razon_social}"
            ),
            sector_economico=empresa.sector_economico or "",
            num_empleados=empresa.num_empleados,
            valor_cotizacion=cotizacion.valor_total_proyecto if cotizacion else None,
            fecha_vencimiento_cotizacion=(
                cotizacion.fecha_vencimiento.strftime("%d/%m/%Y")
                if cotizacion and cotizacion.fecha_vencimiento else None
            ),
            nombre_asesora=cfg.asesora_nombre,
        )

        # 5 ── Renderizar plantilla
        asunto, html_body = self._templates.renderizar(tipo_plantilla, ctx)
        plain_text = self._templates.renderizar_texto_plano(tipo_plantilla, ctx)

        # 6 ── Generar token de tracking e incrustar pixel (si TRACKING_URL configurado)
        from ...modules.tracking.pixel_tracker import generar_token, incrustar_pixel
        token = generar_token()
        html_con_pixel = incrustar_pixel(html_body, token)

        # 7 ── Enviar vía Brevo o Gmail según configuración
        canal_usado, sender = self._get_sender()
        reply_to = os.getenv("EMPRESA_EMAIL", "")
        if canal_usado == "brevo":
            mensaje_id = sender.send(
                to=empresa.email_contacto,
                subject=asunto,
                html_body=html_con_pixel,
                plain_text=plain_text,
                reply_to=reply_to,
                to_name=empresa.nombre_contacto or empresa.razon_social,
            )
        else:
            mensaje_id = sender.send(
                to=empresa.email_contacto,
                subject=asunto,
                html_body=html_con_pixel,
                plain_text=plain_text,
                reply_to=reply_to,
            )
        print(f"[EMAIL] Enviado vía {canal_usado.upper()} a {empresa.email_contacto}")

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
