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
    "PRIMER_CONTACTO":          "Seguridad y Salud en el Trabajo – {{ razon_social }}",
    "SEGUIMIENTO_COTIZACION":   "Re: propuesta para {{ razon_social }}",
    "RECORDATORIO_VENCIMIENTO": "{{ razon_social }} – seguimiento SST",
    "ULTIMO_CONTACTO":          "Para {{ razon_social }}",
}

# ── Estructura base del correo — estilo personal/texto para evitar Promociones ─

_BASE_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:20px;background-color:#ffffff;
             font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222222;">
  <div style="max-width:620px;margin:0 auto;">
    {{ body }}
    <p style="margin:32px 0 0;font-size:11px;color:#cccccc;border-top:1px solid #f5f5f5;padding-top:10px;">
      Ley 1581 de 2012 — si no desea recibir más mensajes responda este correo con la palabra REMOVER.
    </p>
  </div>
</body>
</html>"""

# ── Bloque estático de servicios (siempre aparece, igual para todos) ──────────

_BLOQUE_SERVICIOS = """\
<p style="margin:18px 0 6px;font-size:14px;color:#222;">Entre los servicios que ofrecemos:</p>
<ul style="margin:0 0 16px 20px;padding:0;font-size:14px;color:#333;line-height:1.9;">
  <li>Implementación y administración del SG-SST</li>
  <li>Mediciones Ambientales (Luxometría, Sonometría, Dosimetría, Estrés Térmico, Gases y Material Particulado)</li>
  <li>Batería de Riesgo Psicosocial (Ministerio del Trabajo)</li>
  <li>Rumba Terapia y programas de Bienestar Laboral</li>
  <li>Capacitaciones y Talleres SST</li>
  <li>Formación de Brigadas de Emergencia</li>
  <li>Planos de Emergencia y señalización</li>
  <li>Certificación de Estándares Mínimos ante ARL y Ministerio del Trabajo</li>
  <li>Profesiograma Ocupacional</li>
  <li>Análisis Ergonómico de Puesto de Trabajo</li>
  <li>Diseño e instalación de Red Contra Incendios</li>
  <li>Inspecciones de Puesto de Trabajo</li>
  <li>Investigación de Accidentes de Trabajo</li>
  <li>Acompañamiento y asesoría continua en SST</li>
  <li>Certificaciones ISO a través de nuestra alianza con COMPECER:
    <ul style="margin:4px 0 0 18px;line-height:1.9;">
      <li>ISO 9001:2015 — Gestión de la Calidad</li>
      <li>ISO 45001:2018 — Seguridad y Salud en el Trabajo</li>
      <li>ISO 14001:2015 — Gestión Ambiental</li>
      <li>ISO 27001:2022 — Seguridad de la Información</li>
      <li>ISO 37001:2016 — Gestión Antisoborno</li>
    </ul>
  </li>
</ul>
<p style="margin:0 0 6px;font-size:14px;color:#333;">
  Puede escribirme a este correo o contactarme al <strong>322 818 7963</strong>.
</p>"""

# ── Firma (siempre al final de todo correo) ───────────────────────────────────

_BLOQUE_FIRMA = """\
<p style="margin:24px 0 0;font-size:14px;color:#222;line-height:1.8;">
  Cordialmente,<br>
  <strong>Tania Peñaloza</strong><br>
  Coordinadora Comercial — Medina SST Empresarial S.A.S.<br>
  Tel: 601 903 8072 &nbsp;|&nbsp; Cel: 322 818 7963<br>
  medinasstempresarial30@gmail.com<br>
  www.medinaempresarialsst.com
</p>"""

# ── Separador visual entre intro y servicios ─────────────────────────────────

_SEPARADOR = '<br>'

# ── Párrafo legal fijo (personalizado con variables de plantilla) ─────────────

_PARRAFO_LEGAL = """\
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
  Como empresa del sector <strong>{{ sector_economico or "su sector" }}</strong>,
  a <strong>{{ razon_social }}</strong> le aplican estándares mínimos del SG-SST
  ({{ articulo_resolucion }} — Res. 0312/2019). El Decreto 472 de 2015 establece multas
  de hasta <strong>500 SMMLV</strong> por incumplimiento, y el Ministerio del Trabajo
  no anuncia sus visitas de inspección con anticipación.
</p>"""

_PARRAFO_CTA_PRIMER = """\
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
  Soy <strong>{{ nombre_asesora }}</strong> de <strong>{{ empresa_remitente }}</strong>
  y ayudamos a empresas en <strong>{{ ciudad }}</strong> a implementar el SG-SST de forma
  rápida, sin complicaciones y con acompañamiento continuo.
  Contáctenos — con gusto le explicamos cómo podemos ayudar a
  <strong>{{ razon_social }}</strong> a cumplir estos requisitos sin complicaciones.
</p>"""

_PARRAFO_CTA_RECORDATORIO = """\
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
  En <strong>{{ empresa_remitente }}</strong> ya hemos ayudado a varias empresas en
  {{ ciudad }} a cumplir estos {{ num_estandares }} estándares en tiempo récord.
  Comuníquese con nosotros cuando guste — estamos disponibles para resolver sus dudas.
</p>"""

_PARRAFO_SEGUIMIENTO_COTIZACION = """\
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
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
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
  ¿Tiene alguna duda sobre el alcance o la forma de pago? Podemos ajustar la propuesta.
  Contáctenos cuando lo considere y con gusto la revisamos juntos.
</p>"""

# ── Ganchos de respaldo por tipo (texto plano, Gemini los reemplaza) ──────────

_PARRAFO_ULTIMO_CONTACTO = """\
<p style="margin:14px 0;font-size:14px;color:#222;line-height:1.75;">
  Este es nuestro último mensaje para no saturar su bandeja de entrada.
  Si en algún momento <strong>{{ razon_social }}</strong> necesita apoyo con el SG-SST,
  mediciones ambientales o certificaciones ISO, con gusto los atendemos.
  Quedamos a su disposición.
</p>"""

_GANCHO_FALLBACK = {
    "PRIMER_CONTACTO":          "¿Sabe cuánto puede costarle a {razon_social} no tener el SG-SST al día?",
    "RECORDATORIO_VENCIMIENTO": "{razon_social}: el Ministerio del Trabajo no avisa antes de inspeccionar.",
    "SEGUIMIENTO_COTIZACION":   "Quiero asegurarme de que {razon_social} esté protegida antes de la próxima inspección.",
    "ULTIMO_CONTACTO":          "Este es nuestro último contacto — quedamos atentos si {razon_social} necesita apoyo en SST.",
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

        gancho_html = (
            f'<p style="margin:0 0 12px;font-size:14px;color:#222;line-height:1.7;">'
            f'{gancho_texto}</p>'
        )

        if ctx.nombre_contacto and ctx.nombre_contacto not in ("Gerente", ""):
            saludo_html = (
                f'<p style="margin:0 0 12px;font-size:14px;color:#222;">'
                f'Hola <strong>{ctx.nombre_contacto}</strong>,</p>'
            )
        else:
            saludo_html = (
                f'<p style="margin:0 0 12px;font-size:14px;color:#222;">'
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

        elif tipo == "ULTIMO_CONTACTO":
            body_rendered = (
                saludo_html
                + gancho_html
                + _jinja.from_string(_PARRAFO_ULTIMO_CONTACTO).render(**data)
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
