"""
Main entry point for NJ Fence and Railing — Desktop PDF Catalog Generator.

Usage:
  python main.py            -> Launch Desktop GUI Application
  python main.py --verify   -> Run full integration check & end-to-end PDF catalog pipeline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.google_integrations import (
    analyze_railing_image,
    check_all_google_integrations,
    generate_flow_prompt_for_product,
)
from src.image_processor import (
    create_sample_railing_photo,
    process_photo_to_white_background,
)
from src.models import CompanyHeader, PricingMode, ProductItem
from src.pdf_generator import generate_catalog_pdf
from src.storage import (
    OUTPUT_PDF_DIR,
    RAW_PHOTOS_DIR,
    WHITE_PHOTOS_DIR,
    ensure_directories,
    load_catalog_items,
    load_company_header,
    save_catalog_items,
)


def run_verification_pipeline(skip_live_ai: bool = False) -> int:
    """
    Execute a full end-to-end verification of:
    1. Google Integrations status (Antigravity OAuth, Gemini API, Google Flow)
    2. White-background (#FFFFFF) photo isolation
    3. Gemini visual analysis & product description proposal
    4. Strict user-specified pricing (Per Linear Foot & Per Kit)
    5. Professional PDF Catalog generation
    """
    print("=" * 78)
    print("NJ FENCE AND RAILING — VERIFICACIÓN DE INTEGRACIONES Y FLUJO COMPLETO")
    print("=" * 78)

    ensure_directories()

    # 1. Verify Google Integrations
    print("\n[1/4] Comprobando integraciones con servicios de Google...")
    statuses = check_all_google_integrations()
    for st in statuses:
        icon = "[OK]" if st.is_working else "[INFO]"
        print(f"  {icon} {st.service_name}")
        print(f"       Estado       : {st.status_label}")
        print(f"       Autenticación: {st.auth_status}")
        print(f"       Costes       : {st.cost_explanation}\n")

    # 2. Create & Process Railing Photo onto Pure White Background (#FFFFFF)
    print("[2/4] Procesando fotografía de barandilla sobre fondo blanco puro (#FFFFFF)...")
    sample_raw = RAW_PHOTOS_DIR / "NJF-201_raw.jpg"
    sample_white = WHITE_PHOTOS_DIR / "NJF-201_white.png"
    create_sample_railing_photo(sample_raw)
    process_photo_to_white_background(
        sample_raw,
        sample_white,
        mode="auto_isolate_white",
        tolerance=42.0,
    )
    print(f"  -> Foto original  : {sample_raw}")
    print(f"  -> Fondo blanco   : {sample_white}")

    # 3. Analyze Photo with Gemini (using authenticated account if available)
    print("\n[3/4] Analizando fotografía con Gemini para proponer descripción...")
    ai_data = {}
    if not skip_live_ai:
        try:
            ai_data = analyze_railing_image(sample_raw, engine="auto")
            print(f"  -> Fuente IA      : {ai_data.get('ai_source')}")
            print(f"  -> Nombre propuesto: {ai_data.get('name')}")
        except Exception as exc:
            print(f"  -> Aviso IA en vivo: {exc}")

    item = ProductItem(
        id="NJF-201",
        sku="NJF-201",
        name=str(
            ai_data.get(
                "name",
                "Architectural Matte Black Ornamental Picket Railing / Barandilla Ornamental Negra",
            )
        ),
        category=str(ai_data.get("category", "Aluminum Railing")),
        material=str(
            ai_data.get(
                "material",
                "Powder-Coated Architectural Aluminum / Aluminio Termolacado",
            )
        ),
        finish_color=str(ai_data.get("finish_color", "Matte Black with Gold Knuckle Accents")),
        description_es=str(
            ai_data.get(
                "description_es",
                "Barandilla arquitectónica de barrotes verticales con canal superior decorativo de anillos "
                "y postes cuadrados reforzados con remate piramidal. Diseñada para balcones, porches y "
                "escaleras exteriores de alta durabilidad en climas de New Jersey y New York.",
            )
        ),
        description_en=str(
            ai_data.get(
                "description_en",
                "Architectural vertical-picket railing featuring an ornamental top ring channel and "
                "heavy-duty square newel posts with pyramid caps. Engineered for residential and commercial "
                "decks, balconies, and stairs across New Jersey and New York.",
            )
        ),
        features=list(
            ai_data.get(
                "features",
                [
                    "Postes estructurales cuadrados con tapa piramidal y base de anclaje reforzada",
                    "Canal superior decorativo con anillos ornamentales y detalles centrales",
                    "Acabado negro mate resistente a la corrosión e intemperie (NJ/NY)",
                    "Fotografía procesada sobre fondo blanco puro (#FFFFFF) para catálogo",
                ],
            )
        ),
        pricing_mode=PricingMode.BOTH.value,
        # Exact user-defined test prices (never invented by AI)
        price_per_linear_ft=54.00,
        price_per_kit=345.00,
        kit_includes_note='Kit de sección de 6 pies (36" de altura) incluye riel superior/inferior, barrotes y soportes.',
        original_image_path=str(sample_raw),
        white_bg_image_path=str(sample_white),
        ai_source=str(ai_data.get("ai_source", "Cuenta Personal Google en Antigravity")),
        flow_prompt_suggestion=str(
            ai_data.get("flow_prompt_suggestion")
            or generate_flow_prompt_for_product(
                "Architectural Matte Black Ornamental Picket Railing",
                "Aluminum Railing",
                "Powder-Coated Aluminum",
                "Matte Black",
            )
        ),
    )

    items = load_catalog_items()
    existing_idx = next((i for i, x in enumerate(items) if x.sku == item.sku), None)
    if existing_idx is not None:
        items[existing_idx] = item
    else:
        items.append(item)
    save_catalog_items(items)

    # 4. Generate Professional PDF Catalog
    print("\n[4/4] Generando Catálogo PDF profesional...")
    header = load_company_header()
    pdf_out = OUTPUT_PDF_DIR / "NJ_Fence_and_Railing_Catalog_Verified.pdf"
    generated_pdf = generate_catalog_pdf(items, header, pdf_out)
    print(f"  -> Catálogo PDF generado con éxito en: {generated_pdf}")
    print("=" * 78)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="NJ Fence and Railing — Desktop PDF Catalog Generator"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run end-to-end verification of Google integrations, white-bg processing, and PDF export.",
    )
    parser.add_argument(
        "--skip-live-ai",
        action="store_true",
        help="Skip live CLI call during quick verification.",
    )
    args = parser.parse_args()

    if args.verify:
        return run_verification_pipeline(skip_live_ai=args.skip_live_ai)

    from src.ui_app import launch_desktop_app

    launch_desktop_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
