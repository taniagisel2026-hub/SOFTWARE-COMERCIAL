"""
Motor de plantillas HTML para correos outbound.
Cada plantilla usa variables dinámicas de la empresa y la Resolución 0312 para
garantizar que cada mensaje sea único y personalizado (anti-spam semántico).
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from jinja2 import Environment, StrictUndefined


@dataclass
class EmailContext:
    razon_social: str
    nombre_contacto: str
    ciudad: str
    departamento: str
    num_estandares: int
    nivel_riesgo: str
    articulo_resolucion: str
    empresa_remitente: str
    email_remitente: str
    opt_out_url: str
    sector_economico: str = ""
    num_empleados: int = 0
    valor_cotizacion: Optional[Decimal] = None
    fecha_vencimiento_cotizacion: Optional[str] = None


# ── Plantillas Jinja2 ─────────────────────────────────────────────────────────

_ASUNTOS = {
    "PRIMER_CONTACTO":          "SG-SST para {{ razon_social }} – Cumplimiento Res. 0312/2019",
    "SEGUIMIENTO_COTIZACION":   "Re: Propuesta SG-SST {{ razon_social }} – ¿Tiene alguna pregunta?",
    "RECORDATORIO_VENCIMIENTO": "Su propuesta SG-SST vence pronto – {{ razon_social }}",
}

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#F2F5F9;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
  <tr><td align="center" style="padding:24px 12px;">
    <table width="600" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 12px rgba(0,0,0,0.09);max-width:600px;">

      <!-- HEADER -->
      <tr>
        <td style="background:#1B3A6B;padding:22px 32px;">
          <p style="margin:0;color:#ffffff;font-size:19px;font-weight:bold;
                    letter-spacing:-0.3px;">{{ empresa_remitente }}</p>
          <p style="margin:5px 0 0;color:#B8C8DF;font-size:11px;">
            Seguridad y Salud en el Trabajo &nbsp;·&nbsp; SG-SST &nbsp;·&nbsp; Resolución 0312/2019
          </p>
        </td>
      </tr>

      <!-- BODY -->
      <tr><td style="padding:32px 32px 24px;">{{ body }}</td></tr>

      <!-- FOOTER LEY 1581 -->
      <tr>
        <td style="background:#F2F5F9;padding:14px 32px;
                   border-top:1px solid #DDE5EF;">
          <p style="margin:0;font-size:10px;color:#999999;text-align:center;">
            © {{ empresa_remitente }} &nbsp;·&nbsp;
            <a href="{{ opt_out_url }}" style="color:#999999;text-decoration:underline;">
              Cancelar suscripción
            </a>
          </p>
          <p style="margin:4px 0 0;font-size:9px;color:#BBBBBB;text-align:center;">
            Sus datos personales son tratados conforme a la Ley 1581 de 2012
            (Habeas Data). Para ejercer sus derechos escriba a {{ email_remitente }}
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

_BODY_PRIMER_CONTACTO = """\
<p style="margin:0 0 6px;font-size:14px;color:#333;">Apreciado/a <strong>{{ nombre_contacto }}</strong>,</p>

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  Mi nombre es parte del equipo de <strong>{{ empresa_remitente }}</strong> y me comunico
  con usted porque identificamos que <strong>{{ razon_social }}</strong>, con sede en
  <strong>{{ ciudad }}, {{ departamento }}</strong>, puede estar próxima a una inspección
  del Ministerio del Trabajo bajo la <strong>Resolución 0312 de 2019</strong>.
</p>

<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#EEF2F9;border-left:4px solid #1B3A6B;
              border-radius:4px;margin:18px 0;">
  <tr><td style="padding:14px 18px;">
    <p style="margin:0;font-size:12px;color:#555;font-weight:bold;">
      Perfil regulatorio de {{ razon_social }}:
    </p>
    <p style="margin:6px 0 0;font-size:13px;color:#222;">
      ✔ &nbsp;<strong>{{ articulo_resolucion }}</strong> &nbsp;–&nbsp;
      Le aplican <strong>{{ num_estandares }} estándares mínimos</strong>
      (Riesgo ARL {{ nivel_riesgo }})
    </p>
  </td></tr>
</table>

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  Diseñamos e implementamos el SG-SST completo para su empresa en los plazos
  exigidos por la norma, con documentación lista para auditoría. ¿Le envío una
  propuesta sin costo en las próximas horas?
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0 8px;">
  <tr><td>
    <a href="mailto:{{ email_remitente }}?subject=Solicito propuesta SG-SST – {{ razon_social }}"
       style="display:inline-block;background:#E65C00;color:#ffffff;
              font-size:13px;font-weight:bold;padding:11px 24px;
              border-radius:5px;text-decoration:none;">
      Solicitar propuesta gratuita
    </a>
  </td></tr>
</table>

<p style="margin:16px 0 0;font-size:12px;color:#888;">
  Cordialmente,<br>
  <strong>Equipo {{ empresa_remitente }}</strong><br>
  <a href="mailto:{{ email_remitente }}" style="color:#1B3A6B;">{{ email_remitente }}</a>
</p>"""

_BODY_SEGUIMIENTO_COTIZACION = """\
<p style="margin:0 0 6px;font-size:14px;color:#333;">
  Hola <strong>{{ nombre_contacto }}</strong>,
</p>

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  Quiero hacer un seguimiento a la propuesta que enviamos para <strong>{{ razon_social }}</strong>
  relacionada con el diseño del SG-SST bajo la <strong>Resolución 0312/2019</strong>
  ({{ articulo_resolucion }} – {{ num_estandares }} estándares, Riesgo {{ nivel_riesgo }}).
</p>

{% if valor_cotizacion %}
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#EEF2F9;border-left:4px solid #E65C00;border-radius:4px;margin:18px 0;">
  <tr><td style="padding:14px 18px;">
    <p style="margin:0;font-size:13px;color:#222;">
      <strong>Valor total del proyecto:</strong>
      $ {{ "{:,.0f}".format(valor_cotizacion).replace(",",".") }} COP
      {% if fecha_vencimiento_cotizacion %}
      &nbsp;·&nbsp; <strong>Válida hasta:</strong> {{ fecha_vencimiento_cotizacion }}
      {% endif %}
    </p>
  </td></tr>
</table>
{% endif %}

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  ¿Tiene alguna pregunta sobre el alcance o la forma de pago?
  Podemos ajustar la propuesta a sus posibilidades. No dude en responder este correo
  o llamarme directamente.
</p>

<p style="margin:16px 0 0;font-size:12px;color:#888;">
  Quedamos atentos,<br>
  <strong>Equipo {{ empresa_remitente }}</strong><br>
  <a href="mailto:{{ email_remitente }}" style="color:#1B3A6B;">{{ email_remitente }}</a>
</p>"""

_BODY_RECORDATORIO_VENCIMIENTO = """\
<p style="margin:0 0 6px;font-size:14px;color:#333;">
  Estimado/a <strong>{{ nombre_contacto }}</strong>,
</p>

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  Le recordamos que la propuesta enviada a <strong>{{ razon_social }}</strong> para el
  diseño del SG-SST ({{ num_estandares }} estándares – {{ articulo_resolucion }})
  {% if fecha_vencimiento_cotizacion %}
  <strong>vence el {{ fecha_vencimiento_cotizacion }}</strong>.
  {% else %}
  está próxima a vencer.
  {% endif %}
</p>

<p style="margin:12px 0;font-size:13px;color:#C0392B;font-weight:bold;">
  ⚠ Las multas por incumplimiento de la Res. 0312/2019 pueden alcanzar
  hasta 500 SMMLV según el Decreto 472 de 2015.
</p>

<p style="margin:12px 0;font-size:13px;color:#444;line-height:1.6;">
  Responda este correo o contáctenos para iniciar el proceso antes del vencimiento.
  Podemos comenzar la primera semana con la documentación inicial sin costo adicional.
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0 8px;">
  <tr><td>
    <a href="mailto:{{ email_remitente }}?subject=Acepto propuesta SG-SST – {{ razon_social }}"
       style="display:inline-block;background:#1B3A6B;color:#ffffff;
              font-size:13px;font-weight:bold;padding:11px 24px;
              border-radius:5px;text-decoration:none;">
      Confirmar propuesta
    </a>
  </td></tr>
</table>

<p style="margin:16px 0 0;font-size:12px;color:#888;">
  <strong>{{ empresa_remitente }}</strong><br>
  <a href="mailto:{{ email_remitente }}" style="color:#1B3A6B;">{{ email_remitente }}</a>
</p>"""

_PLANTILLAS = {
    "PRIMER_CONTACTO":          (_ASUNTOS["PRIMER_CONTACTO"],          _BODY_PRIMER_CONTACTO),
    "SEGUIMIENTO_COTIZACION":   (_ASUNTOS["SEGUIMIENTO_COTIZACION"],   _BODY_SEGUIMIENTO_COTIZACION),
    "RECORDATORIO_VENCIMIENTO": (_ASUNTOS["RECORDATORIO_VENCIMIENTO"], _BODY_RECORDATORIO_VENCIMIENTO),
}

_jinja = Environment(undefined=StrictUndefined, autoescape=False)


class EmailTemplateEngine:

    TIPOS_DISPONIBLES = list(_PLANTILLAS.keys())

    def renderizar(self, tipo: str, ctx: EmailContext) -> tuple[str, str]:
        """
        Retorna (asunto, html_body).
        Intenta generar el body con IA (Claude); si falla o no hay API key,
        usa la plantilla estática Jinja2 como fallback transparente.
        """
        if tipo not in _PLANTILLAS:
            raise ValueError(
                f"Plantilla '{tipo}' no existe. Disponibles: {self.TIPOS_DISPONIBLES}"
            )

        # ── Intentar generación con IA ────────────────────────────────────────
        from .ai_generator import generar_cuerpo_ia
        body_ia = generar_cuerpo_ia(
            tipo=tipo,
            razon_social=ctx.razon_social,
            nombre_contacto=ctx.nombre_contacto,
            ciudad=ctx.ciudad,
            departamento=ctx.departamento,
            sector=ctx.sector_economico,
            num_empleados=ctx.num_empleados,
            nivel_riesgo=ctx.nivel_riesgo,
            articulo_resolucion=ctx.articulo_resolucion,
            num_estandares=ctx.num_estandares,
            empresa_remitente=ctx.empresa_remitente,
        )

        # ── Asunto siempre desde plantilla (consistencia) ─────────────────────
        asunto_tpl, body_tpl = _PLANTILLAS[tipo]
        data = ctx.__dict__
        asunto = _jinja.from_string(asunto_tpl).render(**data)

        # ── Body: IA si disponible, estático si no ────────────────────────────
        body_rendered = body_ia if body_ia else _jinja.from_string(body_tpl).render(**data)

        html = _jinja.from_string(_BASE_HTML).render(
            body=body_rendered,
            empresa_remitente=ctx.empresa_remitente,
            email_remitente=ctx.email_remitente,
            opt_out_url=ctx.opt_out_url,
        )
        return asunto, html

    def renderizar_texto_plano(self, tipo: str, ctx: EmailContext) -> str:
        """Versión sin HTML para adjuntar como alternativa y mejorar entregabilidad."""
        asunto, _ = self.renderizar(tipo, ctx)
        return (
            f"De: {ctx.empresa_remitente} <{ctx.email_remitente}>\n"
            f"Para: {ctx.nombre_contacto} – {ctx.razon_social}\n"
            f"Asunto: {asunto}\n\n"
            f"Estimado/a {ctx.nombre_contacto},\n\n"
            f"Nos comunicamos respecto al cumplimiento de la Resolución 0312/2019 "
            f"para {ctx.razon_social} en {ctx.ciudad}. "
            f"Le aplican {ctx.num_estandares} estándares mínimos ({ctx.articulo_resolucion}).\n\n"
            f"Escriba a {ctx.email_remitente} para solicitar su propuesta.\n\n"
            f"Para cancelar la suscripción: {ctx.opt_out_url}\n"
            f"Ley 1581 de 2012 – Habeas Data."
        )
