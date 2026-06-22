"""
Motor de plantillas HTML para correos outbound.

Estructura de cada correo:
  1. Intro personalizada — generada por Gemini (única por empresa/sector)
  2. Bloque de servicios — estático (siempre visible, nunca cambia)
  3. Firma — estática con nombre de la asesora

Si Gemini no está disponible, la intro cae al texto de respaldo (fallback).
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
    nombre_asesora: str = "Tania Peñaloza"


# ── Asuntos (rotan variantes para evitar filtros de spam) ─────────────────────

_ASUNTOS = {
    "PRIMER_CONTACTO":          "SG-SST para {{ razon_social }} – Cumplimiento Res. 0312/2019",
    "SEGUIMIENTO_COTIZACION":   "Re: Propuesta SG-SST {{ razon_social }} – ¿Tiene alguna pregunta?",
    "RECORDATORIO_VENCIMIENTO": "Seguimiento: Servicios SST y certificaciones ISO para {{ razon_social }}",
}

# ── Estructura base del correo ────────────────────────────────────────────────

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
    <table width="700" cellpadding="0" cellspacing="0"
           style="background:#ffffff;border-radius:8px;overflow:hidden;
                  box-shadow:0 2px 12px rgba(0,0,0,0.09);max-width:700px;">

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

# ── Bloque estático de servicios (siempre aparece, igual para todos) ──────────

_BLOQUE_SERVICIOS = """\
<p style="margin:20px 0 8px;font-size:13px;font-weight:bold;color:#1B3A6B;">Nuestros servicios en SST:</p>

<table width="100%" cellpadding="0" cellspacing="4">
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Implementación y administración del SG-SST
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Mediciones Ambientales (Luxometría, Sonometría, Dosimetría, Estrés Térmico, Gases y Material Particulado)
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Batería de Riesgo Psicosocial (Ministerio del Trabajo)
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Rumba Terapia y programas de Bienestar Laboral
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Capacitaciones y Talleres SST
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Planos de Emergencia y señalización
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Formación de Brigadas de Emergencia
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Certificación de Estándares Mínimos ante ARL y Ministerio del Trabajo
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Profesiograma Ocupacional
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Análisis Ergonómico de Puesto de Trabajo
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Diseño e instalación de Red Contra Incendios
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Inspecciones de Puesto de Trabajo
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Investigación de Accidentes de Trabajo
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span>Acompañamiento y asesoría continua en SST
  </td></tr>
</table>

<p style="margin:20px 0 8px;font-size:13px;font-weight:bold;color:#1B3A6B;">A través de nuestra alianza con COMPECER también ofrecemos certificaciones ISO internacionales:</p>

<table width="100%" cellpadding="0" cellspacing="4">
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span><strong>ISO 9001:2015</strong> — Gestión de la Calidad
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span><strong>ISO 45001:2018</strong> — Seguridad y Salud en el Trabajo
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span><strong>ISO 14001:2015</strong> — Gestión Ambiental
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span><strong>ISO 27001:2022</strong> — Seguridad de la Información
  </td></tr>
  <tr><td style="padding:4px 0;font-size:13px;color:#444;">
    <span style="display:inline-block;width:18px;height:18px;background:#1B3A6B;color:#fff;
                 font-size:11px;font-weight:bold;text-align:center;line-height:18px;
                 border-radius:3px;margin-right:8px;vertical-align:middle;">&#10003;</span><strong>ISO 37001:2016</strong> — Gestión Antisoborno
  </td></tr>
</table>

<p style="margin:20px 0 6px;font-size:13px;color:#444;line-height:1.7;">
  Puede comunicarse con nosotros por WhatsApp o llamada al:<br>
  📞 <strong>+57 322 818 7963</strong>
</p>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:14px 0 8px;">
  <tr>
    <td style="padding-right:10px;width:1%;">
      <a href="https://wa.me/573228187963?text=Hola%2C%20estoy%20interesado%20en%20los%20servicios%20de%20Medina%20SST%20Empresarial%20SAS"
         style="display:inline-block;background:#25D366;color:#ffffff;
                font-size:13px;font-weight:bold;padding:11px 24px;
                border-radius:5px;text-decoration:none;white-space:nowrap;">
        💬 Contáctanos por WhatsApp
      </a>
    </td>
    <td style="width:1%;">
      <a href="mailto:{{ email_remitente }}?subject=Información servicios SST – {{ razon_social }}"
         style="display:inline-block;background:#1B3A6B;color:#ffffff;
                font-size:13px;font-weight:bold;padding:11px 24px;
                border-radius:5px;text-decoration:none;white-space:nowrap;">
        ✉️ Escribir por correo
      </a>
    </td>
  </tr>
</table>"""

# ── Firma (siempre al final de todo correo) ───────────────────────────────────

_BLOQUE_FIRMA = """\
<p style="margin:24px 0 4px;font-size:13px;color:#444;">
  Cordialmente,<br>
  <strong>{{ nombre_asesora }}</strong><br>
  <span style="color:#6B7280;font-size:12px;">{{ empresa_remitente }}</span>
</p>"""

# ── Separador visual entre intro y servicios ─────────────────────────────────

_SEPARADOR = '<hr style="border:none;border-top:2px solid #EEF2F9;margin:24px 0;">'

# ── Párrafo legal fijo (personalizado con variables de plantilla) ─────────────

_PARRAFO_LEGAL = """\
<p style="margin:14px 0;font-size:13px;color:#444;line-height:1.75;">
  Como empresa del sector <strong>{{ sector_economico or "su sector" }}</strong>
  con <strong>{{ num_empleados }} trabajadores</strong> y riesgo ARL Clase
  <strong>{{ nivel_riesgo }}</strong>, a <strong>{{ razon_social }}</strong> le aplican
  exactamente <strong>{{ num_estandares }} estándares mínimos</strong>
  ({{ articulo_resolucion }} — Res. 0312/2019). El Decreto 472 de 2015 establece multas
  de hasta <strong>500 SMMLV</strong> por incumplimiento, y el Ministerio del Trabajo
  no anuncia sus visitas de inspección con anticipación.
</p>"""

_PARRAFO_CTA_PRIMER = """\
<p style="margin:14px 0;font-size:13px;color:#444;line-height:1.75;">
  Soy <strong>{{ nombre_asesora }}</strong> de <strong>{{ empresa_remitente }}</strong>
  y ayudamos a empresas en <strong>{{ ciudad }}</strong> a implementar el SG-SST de forma
  rápida, sin complicaciones y con acompañamiento continuo.
  ¿Le gustaría revisar el estado actual de {{ razon_social }} en una llamada de 15 minutos?
</p>"""

_PARRAFO_CTA_RECORDATORIO = """\
<p style="margin:14px 0;font-size:13px;color:#444;line-height:1.75;">
  En <strong>{{ empresa_remitente }}</strong> ya hemos ayudado a varias empresas en
  {{ ciudad }} a cumplir estos {{ num_estandares }} estándares en tiempo récord.
  ¿Cuándo sería un buen momento para hablar 15 minutos esta semana?
</p>"""

_PARRAFO_SEGUIMIENTO_COTIZACION = """\
<p style="margin:14px 0;font-size:13px;color:#444;line-height:1.75;">
  Hace unos días les enviamos una propuesta para <strong>{{ razon_social }}</strong>
  relacionada con el SG-SST ({{ articulo_resolucion }} — {{ num_estandares }} estándares,
  Riesgo {{ nivel_riesgo }}).
  {% if valor_cotizacion %}
  <br><strong>Inversión del proyecto:</strong>
  $ {{ "{:,.0f}".format(valor_cotizacion).replace(",",".") }} COP
  {% if fecha_vencimiento_cotizacion %}
  &nbsp;·&nbsp; <strong>Válida hasta:</strong> {{ fecha_vencimiento_cotizacion }}
  {% endif %}
  {% endif %}
</p>
<p style="margin:14px 0;font-size:13px;color:#444;line-height:1.75;">
  ¿Tiene alguna duda sobre el alcance o la forma de pago? Podemos ajustar la propuesta.
  Son solo 15 minutos de llamada.
</p>"""

# ── Ganchos de respaldo por tipo (texto plano, Gemini los reemplaza) ──────────

_GANCHO_FALLBACK = {
    "PRIMER_CONTACTO":          "¿Sabe cuánto puede costarle a {razon_social} no tener el SG-SST al día?",
    "RECORDATORIO_VENCIMIENTO": "{razon_social}: el Ministerio del Trabajo no avisa antes de inspeccionar.",
    "SEGUIMIENTO_COTIZACION":   "Quiero asegurarme de que {razon_social} esté protegida antes de la próxima inspección.",
}

_jinja = Environment(undefined=StrictUndefined, autoescape=False)


class EmailTemplateEngine:

    TIPOS_DISPONIBLES = list(_ASUNTOS.keys())

    def renderizar(self, tipo: str, ctx: EmailContext) -> tuple[str, str]:
        """
        Retorna (asunto, html_body).
        Estructura siempre: Saludo + Gancho + Párrafo legal + CTA + [Servicios] + Firma
        Gemini solo genera el gancho (1 oración). El resto es fijo y personalizado.
        """
        if tipo not in _ASUNTOS:
            raise ValueError(
                f"Plantilla '{tipo}' no existe. Disponibles: {self.TIPOS_DISPONIBLES}"
            )

        data = ctx.__dict__
        asunto = _jinja.from_string(_ASUNTOS[tipo]).render(**data)

        # Gemini genera SOLO el gancho (1 oración, texto plano)
        from .ai_generator import generar_cuerpo_ia
        gancho_texto = generar_cuerpo_ia(
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
            nombre_asesora=ctx.nombre_asesora,
        )

        # Fallback si Gemini no responde
        if not gancho_texto:
            gancho_texto = _GANCHO_FALLBACK.get(tipo, "").format(
                razon_social=ctx.razon_social
            )

        # Envolver gancho en <p> con estilo destacado (nosotros controlamos el HTML)
        gancho_html = (
            f'<p style="margin:0 0 4px;font-size:14px;color:#1B3A6B;'
            f'font-weight:bold;line-height:1.6;">{gancho_texto}</p>'
        )

        # Saludo personalizado
        if ctx.nombre_contacto and ctx.nombre_contacto not in ("Gerente", ""):
            saludo_html = (
                f'<p style="margin:0 0 16px;font-size:13px;color:#444;">'
                f'Hola <strong>{ctx.nombre_contacto}</strong>,</p>'
            )
        else:
            saludo_html = (
                f'<p style="margin:0 0 16px;font-size:13px;color:#444;">'
                f'Buen día, equipo de <strong>{ctx.razon_social}</strong>,</p>'
            )

        firma = _jinja.from_string(_BLOQUE_FIRMA).render(**data)

        if tipo == "PRIMER_CONTACTO":
            body_rendered = (
                saludo_html
                + gancho_html
                + _jinja.from_string(_PARRAFO_LEGAL).render(**data)
                + _jinja.from_string(_PARRAFO_CTA_PRIMER).render(**data)
                + _SEPARADOR
                + _jinja.from_string(_BLOQUE_SERVICIOS).render(**data)
                + firma
            )

        elif tipo == "RECORDATORIO_VENCIMIENTO":
            body_rendered = (
                saludo_html
                + gancho_html
                + _jinja.from_string(_PARRAFO_LEGAL).render(**data)
                + _jinja.from_string(_PARRAFO_CTA_RECORDATORIO).render(**data)
                + _SEPARADOR
                + _jinja.from_string(_BLOQUE_SERVICIOS).render(**data)
                + firma
            )

        else:  # SEGUIMIENTO_COTIZACION
            body_rendered = (
                saludo_html
                + gancho_html
                + _jinja.from_string(_PARRAFO_SEGUIMIENTO_COTIZACION).render(**data)
                + firma
            )

        html = _jinja.from_string(_BASE_HTML).render(
            body=body_rendered,
            empresa_remitente=ctx.empresa_remitente,
            email_remitente=ctx.email_remitente,
            opt_out_url=ctx.opt_out_url,
        )
        return asunto, html

    def renderizar_texto_plano(self, tipo: str, ctx: EmailContext) -> str:
        asunto, _ = self.renderizar(tipo, ctx)
        return (
            f"De: {ctx.empresa_remitente} <{ctx.email_remitente}>\n"
            f"Para: {ctx.nombre_contacto} – {ctx.razon_social}\n"
            f"Asunto: {asunto}\n\n"
            f"Estimado/a {ctx.nombre_contacto},\n\n"
            f"Nos comunicamos respecto al cumplimiento de la Resolución 0312/2019 "
            f"para {ctx.razon_social} en {ctx.ciudad}. "
            f"Le aplican {ctx.num_estandares} estándares mínimos ({ctx.articulo_resolucion}).\n\n"
            f"Escriba a {ctx.email_remitente} o llame al +57 322 818 7963.\n\n"
            f"Atentamente,\n{ctx.nombre_asesora}\n{ctx.empresa_remitente}\n\n"
            f"Para cancelar la suscripción: {ctx.opt_out_url}\n"
            f"Ley 1581 de 2012 – Habeas Data."
        )
