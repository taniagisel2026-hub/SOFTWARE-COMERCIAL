from decimal import Decimal
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ...config import get_config
from ...domain.entities import Cotizacion, EmpresaProspecto
from ...domain.resolution_0312 import ESPECIFICACIONES

# ── Paleta de colores corporativa ─────────────────────────────────────────────
_AZUL = colors.HexColor("#1B3A6B")
_NARANJA = colors.HexColor("#E65C00")
_AZUL_CLARO = colors.HexColor("#EEF2F9")
_BORDE = colors.HexColor("#C8D4E8")
_GRIS = colors.HexColor("#5A5A5A")
_NEGRO = colors.HexColor("#1E1E1E")


def _estilos() -> dict:
    base = getSampleStyleSheet()
    normal = base["Normal"]
    return {
        "titulo": ParagraphStyle("titulo", parent=normal, fontSize=19, textColor=_AZUL,
                                 fontName="Helvetica-Bold", spaceAfter=2),
        "subtitulo": ParagraphStyle("subtitulo", parent=normal, fontSize=9, textColor=_GRIS,
                                    fontName="Helvetica", spaceAfter=1),
        "encabezado_col": ParagraphStyle("enc_col", parent=normal, fontSize=9, textColor=colors.white,
                                         fontName="Helvetica-Bold", leftIndent=6),
        "cuerpo": ParagraphStyle("cuerpo", parent=normal, fontSize=9, textColor=_NEGRO,
                                 fontName="Helvetica", leading=13, spaceAfter=3),
        "cuerpo_b": ParagraphStyle("cuerpo_b", parent=normal, fontSize=9, textColor=_NEGRO,
                                   fontName="Helvetica-Bold", leading=13, spaceAfter=3),
        "cuerpo_r": ParagraphStyle("cuerpo_r", parent=normal, fontSize=9, textColor=_NEGRO,
                                   fontName="Helvetica", alignment=TA_RIGHT, leading=13),
        "cuerpo_br": ParagraphStyle("cuerpo_br", parent=normal, fontSize=9, textColor=_NEGRO,
                                    fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=13),
        "cuerpo_c": ParagraphStyle("cuerpo_c", parent=normal, fontSize=9, textColor=_NEGRO,
                                   fontName="Helvetica", alignment=TA_CENTER, leading=13),
        "pequeno": ParagraphStyle("pequeno", parent=normal, fontSize=7.5, textColor=_GRIS,
                                  fontName="Helvetica", leading=11, spaceAfter=2),
        "cot_ref": ParagraphStyle("cot_ref", parent=normal, fontSize=10, textColor=_NEGRO,
                                  fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=14),
    }


def _cop(valor: Decimal) -> str:
    formatted = f"{float(valor):,.0f}".replace(",", ".")
    return f"$ {formatted}"


def _barra_seccion(titulo: str, s: dict) -> Table:
    tbl = Table([[Paragraph(titulo, s["encabezado_col"])]], colWidths=[17 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tbl


def exportar_pdf(
    cotizacion: Cotizacion,
    empresa: EmpresaProspecto,
    output_path: Optional[Path] = None,
) -> Path:
    cfg = get_config()

    if output_path is None:
        out_dir = cfg.output_dir / "cotizaciones"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{cotizacion.codigo_cotizacion}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2.5 * cm,
        title=f"Cotización {cotizacion.codigo_cotizacion}",
        author=cfg.empresa_nombre,
    )

    s = _estilos()
    spec = ESPECIFICACIONES[cotizacion.nivel_estandares]
    story = []

    # ── ENCABEZADO ─────────────────────────────────────────────────────────────
    cabecera = Table(
        [[
            Paragraph(cfg.empresa_nombre, s["titulo"]),
            Paragraph(
                f"<b>Cotización N.°</b><br/>{cotizacion.codigo_cotizacion}",
                s["cot_ref"],
            ),
        ]],
        colWidths=[11 * cm, 6 * cm],
    )
    cabecera.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(cabecera)
    story.append(Paragraph("Servicios de Seguridad y Salud en el Trabajo · SG-SST", s["subtitulo"]))
    story.append(Paragraph(
        f"Email: {cfg.empresa_email}   ·   Tel: {cfg.empresa_telefono}   ·   NIT: {cfg.empresa_nit}",
        s["pequeno"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=_NARANJA, spaceAfter=6, spaceBefore=4))

    # Fila de meta datos
    meta = Table(
        [[
            Paragraph(f"<b>Fecha emisión:</b>  {cotizacion.fecha_emision.strftime('%d/%m/%Y')}", s["cuerpo"]),
            Paragraph(
                f"<b>Válida hasta:</b>  "
                f"{cotizacion.fecha_vencimiento.strftime('%d/%m/%Y') if cotizacion.fecha_vencimiento else '—'}",
                s["cuerpo"],
            ),
            Paragraph(f"<b>Elaboró:</b>  {cotizacion.creado_por}", s["cuerpo"]),
            Paragraph(f"<b>Versión:</b>  {cotizacion.version}", s["cuerpo"]),
        ]],
        colWidths=[4.25 * cm] * 4,
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _AZUL_CLARO),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.4, _BORDE),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.35 * cm))

    # ── DATOS DEL CLIENTE ──────────────────────────────────────────────────────
    story.append(_barra_seccion("DATOS DEL CLIENTE", s))
    filas_cliente = [
        [s["cuerpo_b"], "Razón social:", s["cuerpo"], empresa.razon_social,
         s["cuerpo_b"], "NIT:", s["cuerpo"], empresa.nit],
        [s["cuerpo_b"], "Representante:", s["cuerpo"], empresa.nombre_contacto or "—",
         s["cuerpo_b"], "Cargo:", s["cuerpo"], empresa.cargo_contacto or "—"],
        [s["cuerpo_b"], "Dirección:", s["cuerpo"], empresa.direccion or "—",
         s["cuerpo_b"], "Teléfono:", s["cuerpo"], empresa.telefono or "—"],
        [s["cuerpo_b"], "Ciudad:", s["cuerpo"], f"{empresa.ciudad} – {empresa.departamento}",
         s["cuerpo_b"], "Email:", s["cuerpo"], empresa.email_contacto or "—"],
        [s["cuerpo_b"], "Sector:", s["cuerpo"], empresa.sector_economico or "—",
         s["cuerpo_b"], "N.° trabajadores:", s["cuerpo"], str(empresa.num_empleados)],
        [s["cuerpo_b"], "Nivel de riesgo ARL:", s["cuerpo"],
         f"Clase {empresa.nivel_riesgo_arl.value}",
         s["cuerpo_b"], "Fuente prospección:", s["cuerpo"], empresa.fuente_origen or "—"],
    ]
    datos_cliente = Table(
        [[Paragraph(fila[1], fila[0]), Paragraph(fila[3], fila[2]),
          Paragraph(fila[5], fila[4]), Paragraph(fila[7], fila[6])]
         for fila in filas_cliente],
        colWidths=[3.5 * cm, 4.8 * cm, 3.2 * cm, 5.5 * cm],
    )
    datos_cliente.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _AZUL_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.3, _BORDE),
    ]))
    story.append(datos_cliente)
    story.append(Spacer(1, 0.35 * cm))

    # ── FUNDAMENTO LEGAL ───────────────────────────────────────────────────────
    story.append(_barra_seccion(
        f"FUNDAMENTO LEGAL — RESOLUCIÓN 0312 DE 2019 · {spec.articulo_resolucion.upper()}", s
    ))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(spec.descripcion_legal, s["cuerpo"]))
    story.append(Paragraph(
        f"Nivel aplicable: <b>{cotizacion.nivel_estandares.value.replace('_', ' ')} "
        f"({spec.num_estandares} estándares mínimos)</b>",
        s["cuerpo"],
    ))
    story.append(Spacer(1, 0.35 * cm))

    # ── ALCANCE DEL SERVICIO ───────────────────────────────────────────────────
    story.append(_barra_seccion("ALCANCE DEL SERVICIO OFERTADO", s))
    story.append(Spacer(1, 0.2 * cm))
    for i, desc in enumerate(spec.descripcion_servicios, 1):
        story.append(Paragraph(f"  {i}.  {desc}", s["cuerpo"]))
    story.append(Spacer(1, 0.35 * cm))

    # ── DESGLOSE DE HONORARIOS ─────────────────────────────────────────────────
    story.append(_barra_seccion("DESGLOSE DE HONORARIOS PROFESIONALES", s))
    story.append(Spacer(1, 0.2 * cm))

    encab_svc = [
        Paragraph("Actividad / Entregable", s["encabezado_col"]),
        Paragraph("Horas", ParagraphStyle("_ec", parent=s["encabezado_col"], alignment=TA_CENTER)),
        Paragraph("Valor/hora", ParagraphStyle("_er", parent=s["encabezado_col"], alignment=TA_RIGHT)),
        Paragraph("Subtotal", ParagraphStyle("_er2", parent=s["encabezado_col"], alignment=TA_RIGHT)),
    ]
    filas_svc = [encab_svc]
    for svc in cotizacion.servicios_incluidos:
        filas_svc.append([
            Paragraph(svc.descripcion, s["cuerpo"]),
            Paragraph(str(svc.cantidad_horas), s["cuerpo_c"]),
            Paragraph(_cop(svc.valor_unitario), s["cuerpo_r"]),
            Paragraph(_cop(svc.valor_total), s["cuerpo_r"]),
        ])

    tabla_svc = Table(filas_svc, colWidths=[8.5 * cm, 2 * cm, 3 * cm, 3.5 * cm])
    tabla_svc.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _AZUL_CLARO]),
        ("GRID", (0, 0), (-1, -1), 0.3, _BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tabla_svc)
    story.append(Spacer(1, 0.35 * cm))

    # ── VIÁTICOS (sólo si aplica) ──────────────────────────────────────────────
    if cotizacion.valor_viaticos > 0:
        story.append(_barra_seccion("VIÁTICOS Y DESPLAZAMIENTO", s))
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(
            f"Ciudad de prestación del servicio: <b>{empresa.ciudad}, {empresa.departamento}</b>",
            s["cuerpo"],
        ))
        story.append(Paragraph(
            f"Estimado de viáticos (incluye transporte, alojamiento y manutención): "
            f"<b>{_cop(cotizacion.valor_viaticos)}</b>",
            s["cuerpo"],
        ))
        story.append(Spacer(1, 0.35 * cm))

    # ── RESUMEN ECONÓMICO ──────────────────────────────────────────────────────
    story.append(_barra_seccion("RESUMEN ECONÓMICO", s))
    story.append(Spacer(1, 0.2 * cm))

    filas_res = [
        ("Subtotal honorarios profesionales:", _cop(cotizacion.valor_servicios), False),
        ("Viáticos y desplazamiento:", _cop(cotizacion.valor_viaticos), False),
        ("VALOR TOTAL DEL PROYECTO (IVA no incluido):", _cop(cotizacion.valor_total_proyecto), True),
        ("Cuota mensual equivalente (÷ 12):", _cop(cotizacion.valor_total_mensual), False),
    ]
    tabla_res = Table(
        [[Paragraph(label, s["cuerpo_b"] if es_total else s["cuerpo"]),
          Paragraph(valor, s["cuerpo_br"] if es_total else s["cuerpo_r"])]
         for label, valor, es_total in filas_res],
        colWidths=[12 * cm, 5 * cm],
    )
    tabla_res.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _AZUL_CLARO]),
        ("LINEABOVE", (0, 2), (-1, 2), 1.5, _AZUL),
        ("LINEBELOW", (0, 2), (-1, 2), 1.5, _AZUL),
        ("BACKGROUND", (0, 2), (-1, 2), _AZUL_CLARO),
        ("GRID", (0, 0), (-1, -1), 0.3, _BORDE),
    ]))
    story.append(tabla_res)
    story.append(Spacer(1, 0.35 * cm))

    # ── CONDICIONES COMERCIALES ────────────────────────────────────────────────
    story.append(_barra_seccion("CONDICIONES COMERCIALES", s))
    story.append(Spacer(1, 0.2 * cm))
    condiciones = [
        "Vigencia de la propuesta: 30 días calendario a partir de la fecha de emisión.",
        "Forma de pago: 50 % al inicio del proyecto · 50 % contra entrega de documentación.",
        "Los valores expresados no incluyen IVA (19 %). Aplica si el proveedor es responsable del tributo.",
        "No incluye costos de exámenes médicos ocupacionales, EPP, ni capacitación externa certificada.",
        "El plazo de ejecución se acuerda contractualmente según disponibilidad del cliente.",
    ]
    for cond in condiciones:
        story.append(Paragraph(f"•  {cond}", s["cuerpo"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── FIRMA ──────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="38%", thickness=0.5, color=_GRIS, spaceAfter=5))
    story.append(Paragraph(f"<b>{cfg.empresa_nombre}</b>", s["cuerpo"]))
    story.append(Paragraph("Especialistas en Seguridad y Salud en el Trabajo — SG-SST", s["pequeno"]))
    story.append(Paragraph(
        f"NIT: {cfg.empresa_nit}   ·   {cfg.empresa_email}   ·   {cfg.empresa_telefono}",
        s["pequeno"],
    ))

    doc.build(story)
    return output_path
