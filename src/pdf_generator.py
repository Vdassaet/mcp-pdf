"""
Professional PDF Catalog Generator for NJ Fence and Railing.
Renders high-resolution product cards with white-background processed photos,
Gemini-generated technical descriptions, and strict user-entered pricing
(Per Linear Foot / Per Kit — never inventing numbers).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models import CompanyHeader, PricingMode, ProductItem


BRAND_NAVY = colors.HexColor("#141C2B")
BRAND_SLATE = colors.HexColor("#24324A")
BRAND_GOLD = colors.HexColor("#C89D45")
BRAND_LIGHT_BG = colors.HexColor("#F7F9FC")
BRAND_BORDER = colors.HexColor("#DCE2EC")
BRAND_PRICE_BG = colors.HexColor("#FFFDF7")
BRAND_PRICE_BORDER = colors.HexColor("#D4AF37")
TEXT_DARK = colors.HexColor("#1A202C")
TEXT_MUTED = colors.HexColor("#4A5568")


def _fit_image_dimensions(img_path: Path, max_w: float, max_h: float) -> tuple[float, float]:
    """Calculate aspect-preserving dimensions for ReportLab Image flowable."""
    from PIL import Image as PILImage

    with PILImage.open(img_path) as im:
        w, h = im.size
    if w <= 0 or h <= 0:
        return max_w, max_h
    ratio = min(max_w / float(w), max_h / float(h))
    return w * ratio, h * ratio


def _draw_page_chrome(canvas, doc, header: CompanyHeader) -> None:
    """Draw running header bar and footer on every catalog page."""
    canvas.saveState()
    page_w, page_h = letter

    # Top accent bar
    canvas.setFillColor(BRAND_NAVY)
    canvas.rect(0, page_h - 22, page_w, 22, stroke=0, fill=1)
    canvas.setFillColor(BRAND_GOLD)
    canvas.rect(0, page_h - 25, page_w, 3, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawString(0.55 * inch, page_h - 15, header.company_name.upper())
    canvas.setFont("Helvetica", 8)
    right_info = f"{header.phone}  |  {header.email}  |  {header.location}"
    canvas.drawRightString(page_w - 0.55 * inch, page_h - 15, right_info)

    # Bottom footer
    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.75)
    canvas.line(0.55 * inch, 0.58 * inch, page_w - 0.55 * inch, 0.58 * inch)

    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 7.5)
    disclaimer = header.footer_disclaimer[:135]
    canvas.drawString(0.55 * inch, 0.40 * inch, disclaimer)

    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawRightString(
        page_w - 0.55 * inch,
        0.40 * inch,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def generate_catalog_pdf(
    items: List[ProductItem],
    header: CompanyHeader,
    output_pdf_path: str | Path,
) -> Path:
    """
    Generate a professional PDF catalog for NJ Fence and Railing.
    Only renders exact prices entered by the user (Per Linear Foot or Per Kit).
    """
    if not items:
        raise ValueError("El catálogo no tiene productos. Añade al menos una barandilla o cerca antes de exportar.")

    out_path = Path(output_pdf_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.75 * inch,
        title=f"{header.company_name} - {header.catalog_title}",
        author=header.company_name,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BannerTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.white,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "BannerSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#E2E8F0"),
    )
    item_title_style = ParagraphStyle(
        "ItemTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13.5,
        leading=17,
        textColor=BRAND_NAVY,
        spaceAfter=3,
    )
    meta_style = ParagraphStyle(
        "ItemMeta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=12,
        textColor=BRAND_SLATE,
        spaceAfter=5,
    )
    desc_style = ParagraphStyle(
        "ItemDesc",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.2,
        leading=13,
        textColor=TEXT_DARK,
        spaceAfter=4,
    )
    feature_style = ParagraphStyle(
        "ItemFeature",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_MUTED,
    )
    spec_header_style = ParagraphStyle(
        "SpecHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=BRAND_NAVY,
        spaceBefore=2,
        spaceAfter=2,
    )
    spec_item_style = ParagraphStyle(
        "SpecItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.0,
        leading=10.5,
        textColor=TEXT_DARK,
    )
    price_header_style = ParagraphStyle(
        "PriceHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=BRAND_SLATE,
    )
    price_val_style = ParagraphStyle(
        "PriceValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=BRAND_NAVY,
    )
    price_note_style = ParagraphStyle(
        "PriceNote",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=10.5,
        textColor=TEXT_MUTED,
    )

    story = []

    # 1. Executive Cover Banner Table
    date_str = datetime.now().strftime("%Y-%m-%d")
    banner_html = (
        f"<b>{escape(header.company_name)}</b><br/>"
        f"<font size='12' color='#C89D45'><b>{escape(header.catalog_title)}</b></font><br/>"
        f"<font size='9.5' color='#E2E8F0'>{escape(header.subtitle)}</font>"
    )
    contact_html = (
        f"<font size='8.5' color='#FFFFFF'><b>Phone:</b> {escape(header.phone)}<br/>"
        f"<b>Email:</b> {escape(header.email)}<br/>"
        f"<b>Area:</b> {escape(header.location)}<br/>"
        f"<b>Date:</b> {date_str}  |  <b>Products:</b> {len(items)}</font>"
    )

    banner_table = Table(
        [[Paragraph(banner_html, title_style), Paragraph(contact_html, subtitle_style)]],
        colWidths=[4.7 * inch, 2.7 * inch],
    )
    banner_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEBELOW", (0, 0), (-1, -1), 3, BRAND_GOLD),
            ]
        )
    )
    story.append(banner_table)
    story.append(Spacer(1, 0.18 * inch))

    # 2. Render each Product Card
    for idx, item in enumerate(items, start=1):
        img_to_use = Path(item.white_bg_image_path) if item.white_bg_image_path else Path(item.original_image_path)
        if img_to_use.exists() and img_to_use.is_file():
            iw, ih = _fit_image_dimensions(img_to_use, 2.55 * inch, 1.95 * inch)
            rl_img = RLImage(str(img_to_use), width=iw, height=ih)
        else:
            rl_img = Paragraph("<i>[Sin Imagen]</i>", desc_style)

        sku_badge = Paragraph(
            f"<font size='7.5' color='#4A5568'><b>SKU / REF:</b> {escape(item.sku or item.id)} "
            f"&nbsp;|&nbsp; <b>FONDO BLANCO (#FFFFFF)</b></font>",
            feature_style,
        )
        left_cell = [rl_img, Spacer(1, 4), sku_badge]

        # Right column: Title, Metadata, Descriptions, Features, Exact Pricing Box
        right_elements = []
        title_text = escape(item.name or f"Modelo #{idx}")
        right_elements.append(Paragraph(f"{idx}. {title_text}", item_title_style))

        meta_parts = [f"Category: {escape(item.category)}"]
        if item.material.strip():
            meta_parts.append(f"Material: {escape(item.material.strip())}")
        if item.finish_color.strip():
            meta_parts.append(f"Finish: {escape(item.finish_color.strip())}")
        right_elements.append(Paragraph(" &nbsp;&bull;&nbsp; ".join(meta_parts), meta_style))

        if item.description_en.strip():
            right_elements.append(
                Paragraph(f"<b>Description:</b> {escape(item.description_en.strip())}", desc_style)
            )
        elif item.description_es.strip():
            right_elements.append(
                Paragraph(f"<b>Description:</b> {escape(item.description_es.strip())}", desc_style)
            )

        # Product Specifications Section
        specs_to_render: List[tuple[str, str]] = []
        if getattr(item, "specifications", None) and isinstance(item.specifications, dict):
            for k, v in item.specifications.items():
                k_clean = str(k).strip()
                v_clean = str(v).strip()
                if k_clean and v_clean:
                    specs_to_render.append((k_clean, v_clean))

        # Fallback to item.features if specifications dict is empty
        if not specs_to_render and item.features:
            for f in item.features:
                f_clean = str(f).strip().lstrip("•- ")
                if f_clean:
                    if ":" in f_clean:
                        parts = f_clean.split(":", 1)
                        if parts[0].strip() and parts[1].strip():
                            specs_to_render.append((parts[0].strip(), parts[1].strip()))
                        else:
                            specs_to_render.append(("", f_clean))
                    else:
                        specs_to_render.append(("", f_clean))

        if specs_to_render:
            right_elements.append(
                Paragraph("<b>Product Specifications</b>", spec_header_style)
            )
            if len(specs_to_render) > 3:
                half = (len(specs_to_render) + 1) // 2
                spec_rows = []
                for i in range(half):
                    c1_k, c1_v = specs_to_render[i]
                    c1_txt = f"&bull; <b>{escape(c1_k)}:</b> {escape(c1_v)}" if c1_k else f"&bull; {escape(c1_v)}"
                    if i + half < len(specs_to_render):
                        c2_k, c2_v = specs_to_render[i + half]
                        c2_txt = f"&bull; <b>{escape(c2_k)}:</b> {escape(c2_v)}" if c2_k else f"&bull; {escape(c2_v)}"
                    else:
                        c2_txt = ""
                    spec_rows.append([
                        Paragraph(c1_txt, spec_item_style),
                        Paragraph(c2_txt, spec_item_style),
                    ])
                st = Table(spec_rows, colWidths=[2.25 * inch, 2.25 * inch])
                st.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 1),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                        ]
                    )
                )
                right_elements.append(st)
            else:
                for k, v in specs_to_render:
                    txt = f"&bull; <b>{escape(k)}:</b> {escape(v)}" if k else f"&bull; {escape(v)}"
                    right_elements.append(Paragraph(txt, spec_item_style))
            right_elements.append(Spacer(1, 4))

        # Strict Pricing Box — NEVER invents numbers
        price_rows = []
        has_lf = item.price_per_linear_ft is not None and item.price_per_linear_ft > 0
        has_kit = item.price_per_kit is not None and item.price_per_kit > 0

        if item.pricing_mode in (PricingMode.PER_LINEAR_FOOT.value, PricingMode.BOTH.value) and has_lf:
            price_rows.append(
                [
                    Paragraph("PRICE PER LINEAR FOOT:", price_header_style),
                    Paragraph(f"${item.price_per_linear_ft:,.2f} USD / LF", price_val_style),
                ]
            )
        if item.pricing_mode in (PricingMode.PER_KIT.value, PricingMode.BOTH.value) and has_kit:
            price_rows.append(
                [
                    Paragraph("PRICE PER COMPLETE KIT:", price_header_style),
                    Paragraph(f"${item.price_per_kit:,.2f} USD / Kit", price_val_style),
                ]
            )

        if not price_rows:
            price_rows.append(
                [
                    Paragraph("PRICING SPECIFICATION:", price_header_style),
                    Paragraph("Price Upon Request", price_val_style),
                ]
            )

        if item.kit_includes_note.strip():
            price_rows.append(
                [
                    Paragraph(
                        f"<b>Includes / Notes:</b> {escape(item.kit_includes_note.strip())}",
                        price_note_style,
                    ),
                    "",
                ]
            )

        price_table = Table(price_rows, colWidths=[2.45 * inch, 1.85 * inch])
        price_style_cmds = [
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_PRICE_BG),
            ("BOX", (0, 0), (-1, -1), 1.0, BRAND_PRICE_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        if item.kit_includes_note.strip():
            last_row = len(price_rows) - 1
            price_style_cmds.append(("SPAN", (0, last_row), (1, last_row)))
        price_table.setStyle(TableStyle(price_style_cmds))
        right_elements.append(price_table)

        card_table = Table(
            [[left_cell, right_elements]],
            colWidths=[2.8 * inch, 4.6 * inch],
        )
        card_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.white),  # Pure white photo cell (#FFFFFF)
                    ("BACKGROUND", (1, 0), (1, 0), BRAND_LIGHT_BG),
                    ("BOX", (0, 0), (-1, -1), 1.0, BRAND_BORDER),
                    ("LINEAFTER", (0, 0), (0, -1), 0.75, BRAND_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        story.append(KeepTogether([card_table, Spacer(1, 0.14 * inch)]))

    # End of Catalog: Official Quote Request Notice
    quote_notice_style = ParagraphStyle(
        "QuoteNotice",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=13,
        textColor=TEXT_DARK,
    )
    quote_box_html = (
        "<b>To Request a Quote:</b> Please contact us with your desired railing style, total linear footage, "
        "height, and finish color. For orders under 30 linear feet, please request a custom quote, as pricing "
        "may vary. We will be happy to provide you with a personalized estimate."
    )
    quote_table = Table(
        [[Paragraph(quote_box_html, quote_notice_style)]],
        colWidths=[7.4 * inch],
    )
    quote_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_PRICE_BG),
                ("BOX", (0, 0), (-1, -1), 1.2, BRAND_GOLD),
                ("LINEBEFORE", (0, 0), (0, -1), 4.0, BRAND_GOLD),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(KeepTogether([Spacer(1, 0.08 * inch), quote_table]))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_page_chrome(c, d, header),
        onLaterPages=lambda c, d: _draw_page_chrome(c, d, header),
    )
    return out_path
