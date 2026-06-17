"""
Generador de PDF para cotizaciones con precios manuales.
No depende de la lógica de Resolución 0312 — recibe servicios y precios directamente.
"""
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ...config import get_config

_AZUL       = colors.HexColor("#1B3A6B")
_NARANJA    = colors.HexColor("#E65C00")
_AZUL_CLARO = colors.HexColor("#EEF2F9")
_BORDE      = colors.HexColor("#C8D4E8")
_GRIS       = colors.HexColor("#5A5A5A")
_NEGRO      = colors.HexColor("#1E1E1E")

_LOGO_PATH         = Path(__file__).parent.parent.parent.parent / "assets" / "logo_medina.png"
_LOGO_COMPECER     = Path(__file__).parent.parent.parent.parent / "assets" / "logo_compecer.jpg"


def _estilos() -> dict:
    base = getSampleStyleSheet()
    n = base["Normal"]
    return {
        "empresa":    ParagraphStyle("empresa",  parent=n, fontSize=14, textColor=_AZUL,
                                     fontName="Helvetica-Bold", spaceAfter=1),
        "subtitulo":  ParagraphStyle("sub",      parent=n, fontSize=8,  textColor=_GRIS,
                                     fontName="Helvetica", spaceAfter=1),
        "cot_ref":    ParagraphStyle("cotref",   parent=n, fontSize=10, textColor=_NEGRO,
                                     fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "enc_col":    ParagraphStyle("enccol",   parent=n, fontSize=9,  textColor=colors.white,
                                     fontName="Helvetica-Bold", leftIndent=6),
        "enc_r":      ParagraphStyle("encr",     parent=n, fontSize=9,  textColor=colors.white,
                                     fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "cuerpo":     ParagraphStyle("cuerpo",   parent=n, fontSize=9,  textColor=_NEGRO,
                                     fontName="Helvetica", leading=13, spaceAfter=2),
        "cuerpo_b":   ParagraphStyle("cuerpob",  parent=n, fontSize=9,  textColor=_NEGRO,
                                     fontName="Helvetica-Bold", leading=13),
        "cuerpo_r":   ParagraphStyle("cuerpor",  parent=n, fontSize=9,  textColor=_NEGRO,
                                     fontName="Helvetica", alignment=TA_RIGHT, leading=13),
        "cuerpo_br":  ParagraphStyle("cuerpobr", parent=n, fontSize=9,  textColor=_NEGRO,
                                     fontName="Helvetica-Bold", alignment=TA_RIGHT, leading=13),
        "pequeno":    ParagraphStyle("pequeno",  parent=n, fontSize=7.5, textColor=_GRIS,
                                     fontName="Helvetica", leading=11),
        "total_lbl":  ParagraphStyle("totlbl",   parent=n, fontSize=10, textColor=_AZUL,
                                     fontName="Helvetica-Bold"),
        "total_val":  ParagraphStyle("totval",   parent=n, fontSize=10, textColor=_AZUL,
                                     fontName="Helvetica-Bold", alignment=TA_RIGHT),
    }


def _cop(valor: float) -> str:
    return f"$ {valor:,.0f}".replace(",", ".")


def _barra(titulo: str, s: dict, ancho: float = 17.0) -> Table:
    tbl = Table([[Paragraph(titulo, s["enc_col"])]], colWidths=[ancho * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, -1), _AZUL),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return tbl


def generar_pdf_manual(
    codigo: str,
    razon_social: str,
    nit: str,
    nombre_contacto: str,
    cargo_contacto: str,
    ciudad: str,
    telefono: str,
    email_contacto: str,
    servicios: list[dict],
    servicios_compecer: Optional[list[dict]] = None,
    descuento: float = 0.0,
    elaborado_por: str = "Asesor",
    condiciones_pago: str = "50% al inicio · 50% contra entrega",
    output_path: Optional[Path] = None,
) -> Path:
    cfg = get_config()

    if output_path is None:
        out_dir = cfg.output_dir / "cotizaciones"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"{codigo}.pdf"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2.5 * cm,
        title=f"Cotización {codigo}",
        author=cfg.empresa_nombre,
    )

    s = _estilos()
    story = []
    hoy = date.today()
    vencimiento = hoy + timedelta(days=30)

    # ── ENCABEZADO CON LOGO ────────────────────────────────────────────────────
    logo_cell = ""
    if _LOGO_PATH.exists():
        from PIL import Image as PILImage
        with PILImage.open(_LOGO_PATH) as im:
            orig_w, orig_h = im.size
        max_dim = 2.5 * cm
        ratio = orig_w / orig_h
        if ratio >= 1:
            logo_w, logo_h = max_dim, max_dim / ratio
        else:
            logo_w, logo_h = max_dim * ratio, max_dim
        logo_cell = Image(str(_LOGO_PATH), width=logo_w, height=logo_h)

    cabecera = Table(
        [[
            logo_cell,
            [
                Paragraph(cfg.empresa_nombre, s["empresa"]),
                Paragraph("Servicios de Seguridad y Salud en el Trabajo · SG-SST", s["subtitulo"]),
                Paragraph(
                    f"Email: {cfg.empresa_email}   ·   Tel: {cfg.empresa_telefono}   ·   NIT: {cfg.empresa_nit}",
                    s["pequeno"],
                ),
            ],
            Paragraph(f"<b>Cotización N.°</b><br/>{codigo}", s["cot_ref"]),
        ]],
        colWidths=[3.0 * cm, 9.5 * cm, 4.5 * cm],
    )
    cabecera.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(cabecera)
    story.append(HRFlowable(width="100%", thickness=2, color=_NARANJA, spaceAfter=6, spaceBefore=4))

    # Meta datos
    meta = Table(
        [[
            Paragraph(f"<b>Fecha emisión:</b>  {hoy.strftime('%d/%m/%Y')}",           s["cuerpo"]),
            Paragraph(f"<b>Válida hasta:</b>  {vencimiento.strftime('%d/%m/%Y')}",    s["cuerpo"]),
            Paragraph(f"<b>Elaboró:</b>  {elaborado_por}",                            s["cuerpo"]),
            Paragraph(f"<b>Código:</b>  {codigo}",                                    s["cuerpo"]),
        ]],
        colWidths=[4.25 * cm] * 4,
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _AZUL_CLARO),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0.4, _BORDE),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.35 * cm))

    # ── DATOS DEL CLIENTE ──────────────────────────────────────────────────────
    story.append(_barra("DATOS DEL CLIENTE", s))
    filas_cliente = [
        ["Razón social:",     razon_social,       "NIT:",           nit or "—"],
        ["Representante:",    nombre_contacto or "—", "Cargo:",     cargo_contacto or "—"],
        ["Ciudad:",           ciudad or "—",      "Teléfono:",      telefono or "—"],
        ["Email:",            email_contacto or "—", "",            ""],
    ]
    tbl_cliente = Table(
        [[Paragraph(f[0], s["cuerpo_b"]), Paragraph(f[1], s["cuerpo"]),
          Paragraph(f[2], s["cuerpo_b"]), Paragraph(f[3], s["cuerpo"])]
         for f in filas_cliente],
        colWidths=[3.5 * cm, 5.0 * cm, 3.2 * cm, 5.3 * cm],
    )
    tbl_cliente.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, _AZUL_CLARO]),
        ("GRID",          (0, 0), (-1, -1), 0.3, _BORDE),
    ]))
    story.append(tbl_cliente)
    story.append(Spacer(1, 0.35 * cm))

    # ── SERVICIOS ──────────────────────────────────────────────────────────────
    story.append(_barra("SERVICIOS OFERTADOS", s))
    story.append(Spacer(1, 0.2 * cm))

    encab = [
        Paragraph("Servicio", s["enc_col"]),
        Paragraph("Valor", s["enc_r"]),
    ]
    filas_svc = [encab]
    subtotal = 0.0
    for i, svc in enumerate(servicios):
        precio = float(svc.get("precio", 0))
        subtotal += precio
        bg = colors.white if i % 2 == 0 else _AZUL_CLARO
        filas_svc.append([
            Paragraph(svc["nombre"], s["cuerpo"]),
            Paragraph(_cop(precio), s["cuerpo_r"]),
        ])

    tbl_svc = Table(filas_svc, colWidths=[13.0 * cm, 4.0 * cm])
    row_bgs = [colors.white if i % 2 == 0 else _AZUL_CLARO for i in range(len(filas_svc) - 1)]
    tbl_svc.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _AZUL),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), row_bgs),
        ("GRID",          (0, 0), (-1, -1), 0.3, _BORDE),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tbl_svc)
    story.append(Spacer(1, 0.35 * cm))

    # ── ALIANZA COMPECER (mención al pie, siempre visible) ────────────────────
    _MORADO      = colors.HexColor("#4B2D8F")
    _MORADO_CLARO= colors.HexColor("#EDE9F6")
    subtotal_comp = 0.0

    comp_logo_cell = ""
    if _LOGO_COMPECER.exists():
        from PIL import Image as PILImage
        with PILImage.open(_LOGO_COMPECER) as im:
            cw, ch = im.size
        ratio = cw / ch
        max_w = 3.8 * cm
        max_h = 1.1 * cm
        logo_w = min(max_w, max_h * ratio)
        logo_h = logo_w / ratio
        comp_logo_cell = Image(str(_LOGO_COMPECER), width=logo_w, height=logo_h)

    alianza_tbl = Table(
        [[
            comp_logo_cell,
            Paragraph(
                "En alianza con <b>COMPECER®</b>, Organismo Internacional de Certificación "
                "(doble acreditación EMA · IAF, presencia en 9 países), ofrecemos acceso a "
                "certificaciones en más de 10 normas ISO reconocidas internacionalmente. "
                "Consulte a su asesor para mayor información.",
                s["pequeno"],
            ),
        ]],
        colWidths=[4.2 * cm, 12.8 * cm],
    )
    alianza_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _MORADO_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#C4B5E8")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(alianza_tbl)
    story.append(Spacer(1, 0.35 * cm))

    # ── RESUMEN ECONÓMICO ──────────────────────────────────────────────────────
    story.append(_barra("RESUMEN ECONÓMICO", s))
    story.append(Spacer(1, 0.2 * cm))

    total = subtotal - descuento
    filas_res = [
        ("Subtotal servicios:", subtotal, False),
    ]
    if descuento > 0:
        filas_res.append(("Descuento:", -descuento, False))
    filas_res.append(("VALOR TOTAL (IVA no incluido):", total, True))

    tbl_res = Table(
        [[Paragraph(label, s["cuerpo_b"] if es_t else s["cuerpo"]),
          Paragraph(_cop(abs(val)), s["total_val"] if es_t else s["cuerpo_r"])]
         for label, val, es_t in filas_res],
        colWidths=[12.0 * cm, 5.0 * cm],
    )
    tbl_res.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [colors.white, _AZUL_CLARO]),
        ("LINEABOVE",     (0, -1), (-1, -1), 1.5, _AZUL),
        ("LINEBELOW",     (0, -1), (-1, -1), 1.5, _AZUL),
        ("BACKGROUND",    (0, -1), (-1, -1), _AZUL_CLARO),
        ("GRID",          (0, 0), (-1, -1), 0.3, _BORDE),
    ]))
    story.append(tbl_res)
    story.append(Spacer(1, 0.35 * cm))

    # ── CONDICIONES COMERCIALES ────────────────────────────────────────────────
    story.append(_barra("CONDICIONES COMERCIALES", s))
    story.append(Spacer(1, 0.2 * cm))
    condiciones = [
        "Vigencia de la propuesta: 30 días calendario a partir de la fecha de emisión.",
        f"Forma de pago: {condiciones_pago}.",
        "Los valores expresados no incluyen IVA (19%). Aplica si el proveedor es responsable del tributo.",
        "No incluye costos de exámenes médicos ocupacionales ni EPP.",
        "El plazo de ejecución se acuerda contractualmente según disponibilidad del cliente.",
    ]
    for c in condiciones:
        story.append(Paragraph(f"•  {c}", s["cuerpo"]))
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
