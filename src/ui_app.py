"""
Desktop GUI Application for NJ Fence and Railing — Catalog Studio.
Built with CustomTkinter. Runs 100% standalone on Windows PC, independent of the website.
"""

from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import List, Optional

import customtkinter as ctk
from PIL import Image

from src.google_integrations import (
    analyze_railing_image,
    check_all_google_integrations,
    generate_flow_prompt_for_product,
    generate_image_via_official_genai_api,
    open_ai_studio_key_page,
    open_google_flow_in_browser,
    save_gemini_api_key_to_env,
)
from src.image_processor import (
    create_sample_railing_photo,
    process_photo_to_white_background,
)
from src.models import CompanyHeader, PricingMode, ProductItem, parse_user_price
from src.pdf_generator import generate_catalog_pdf
from src.storage import (
    OUTPUT_PDF_DIR,
    RAW_PHOTOS_DIR,
    WHITE_PHOTOS_DIR,
    copy_raw_photo_to_workspace,
    ensure_directories,
    get_next_sku,
    load_catalog_items,
    load_company_header,
    save_catalog_items,
    save_company_header,
)


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CATEGORIES = [
    "Aluminum Railing",
    "Wrought Iron / Steel Railing",
    "Vinyl Railing",
    "Cable / Glass Railing",
    "Vinyl Fence",
    "Wood / Chain Link Fence",
    "Custom Gate",
]

BG_MODE_MAP = {
    "🌟 Catálogo Estudio Pro (Fondo Blanco Puro #FFFFFF - Recomendado)": "studio_catalog_render",
    "🛠️ Aislamiento de Barandilla Metal (Sin Escalones/Revestimiento)": "railing_metal_isolate_white",
    "🤖 Recorte Automático IA (rembg)": "rembg_ai_white",
    "🖼️ Encuadre Estudio sobre Blanco": "studio_frame_white",
}

PRICING_MODE_MAP = {
    "Por Pie Lineal ($ / Linear Ft)": PricingMode.PER_LINEAR_FOOT.value,
    "Por Kit Completo ($ / Kit)": PricingMode.PER_KIT.value,
    "Ambos (Pie Lineal + Kit)": PricingMode.BOTH.value,
    "Sin Cifra / Cotización Bajo Pedido": PricingMode.QUOTE_ONLY.value,
}

ENGINE_MAP = {
    "Automático (Cuenta Antigravity OAuth / API Key si existe)": "auto",
    "Mi Cuenta Personal en Antigravity (`agy` OAuth — $0 Sin API Key)": "antigravity_account",
    "Gemini API Key Directa (`google-genai` — Google AI Studio)": "gemini_api_key",
}

DEFAULT_SPEC_FIELDS = [
    (
        "Post Type",
        ["", "Square Post", "Round Post", "Flanged Surface Mount Post", "Core-Drilled Post", "Heavy-Duty Base Post"],
    ),
    (
        "Top Cap / Top Molding Type",
        ["", "Flat Top", "Decorative Top", "Molded Handrail Cap", "Pyramid Cap", "Continuous Top Rail"],
    ),
    (
        "Bottom Channel Type",
        ["", "Standard Bottom Channel", "Wide Bottom Channel", "Slotted Bottom Channel", "Flush Bottom Rail"],
    ),
    (
        "Spindle Type",
        ["", "Square Spindles", "Round Spindles", "Twisted Spindles", "Basket Spindles", "Rectangular Pickets"],
    ),
    (
        "Railing Style",
        ["", "Traditional Vertical Picket", "Vertical Picket Railing", "Horizontal Railing", "Modern Architectural", "Stair and Porch Railing"],
    ),
    (
        "Railing Height",
        ["", "36 inches", "42 inches", '36"', '42"', "48 inches"],
    ),
    (
        "Material",
        ["", "Aluminum", "Metal or Aluminum", "Wrought Iron / Steel", "Stainless Steel", "Powder-Coated Aluminum"],
    ),
    (
        "Finish / Color",
        ["", "Black Powder Coated", "Any Color Powder coating", "Matte Black", "Gloss Black", "Bronze", "White"],
    ),
]


class NJFenceCatalogApp(ctk.CTk):
    """Main Desktop Window for NJ Fence and Railing PDF Catalog Generator."""

    def __init__(self) -> None:
        super().__init__()
        ensure_directories()

        self.title("NJ Fence and Railing — Estudio de Catálogos PDF (Independiente de la Web)")
        self.geometry("1380x880")
        self.minsize(1180, 760)

        self.catalog_items: List[ProductItem] = load_catalog_items()
        self.company_header: CompanyHeader = load_company_header()

        self.current_item_id: str = get_next_sku(self.catalog_items, "RS-")
        self.current_raw_path: Optional[Path] = None
        self.current_white_path: Optional[Path] = None
        self.current_ai_source: str = "manual"
        self.last_generated_pdf: Optional[Path] = None

        self.default_spec_combos: Dict[str, ctk.CTkComboBox] = {}
        self.extra_spec_rows: List[Dict[str, Any]] = []

        self._build_top_bar()
        self._build_tabs()
        self._refresh_catalog_list_ui()
        self._refresh_integrations_report_ui()

        self.bind_all("<Control-v>", self._handle_ctrl_v)
        self.bind_all("<Control-V>", self._handle_ctrl_v)

    def _handle_ctrl_v(self, event=None) -> None:
        focus_w = self.focus_get()
        if focus_w and any(k in str(focus_w).lower() for k in ("entry", "text")):
            return
        self.on_paste_photo()

    # ------------------------------------------------------------------
    # Top Header Bar
    # ------------------------------------------------------------------
    def _build_top_bar(self) -> None:
        top = ctk.CTkFrame(self, fg_color="#141C2B", corner_radius=0, height=68)
        top.pack(fill="x", side="top")

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left", padx=18, pady=10)

        ctk.CTkLabel(
            title_box,
            text="NJ FENCE AND RAILING — CATALOG STUDIO",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Fotos sobre Fondo Blanco (#FFFFFF)  •  Análisis con Gemini IA  •  Precios por Pie Lineal / Kit (Sin Inventar Cifras)",
            font=ctk.CTkFont(size=12),
            text_color="#CBD5E0",
        ).pack(anchor="w")

        btn_box = ctk.CTkFrame(top, fg_color="transparent")
        btn_box.pack(side="right", padx=18, pady=10)

        ctk.CTkButton(
            btn_box,
            text="🧪 Cargar Barandilla de Prueba",
            fg_color="#2B6CB0",
            hover_color="#2C5282",
            width=210,
            command=self.on_load_sample_railing,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_box,
            text="📄 Exportar Catálogo PDF",
            fg_color="#B7791F",
            hover_color="#975A16",
            width=190,
            font=ctk.CTkFont(weight="bold"),
            command=self.on_export_pdf,
        ).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    # Tabs Layout
    # ------------------------------------------------------------------
    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=(6, 12))

        self.tab_editor = self.tabview.add("1. Subir Foto, Procesar Fondo Blanco y Precios")
        self.tab_catalog = self.tabview.add("2. Catálogo de Productos y Exportar PDF")
        self.tab_google = self.tabview.add("3. Google Flow & Diagnóstico de Integraciones")

        self._build_tab_editor()
        self._build_tab_catalog()
        self._build_tab_google()

    # ------------------------------------------------------------------
    # Tab 1: Photo Upload + White BG + Gemini Analysis + Exact Pricing
    # ------------------------------------------------------------------
    def _build_tab_editor(self) -> None:
        container = ctk.CTkFrame(self.tab_editor, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=5)
        container.grid_columnconfigure(1, weight=6)
        container.grid_rowconfigure(0, weight=1)

        # LEFT PANEL: Photo & Gemini Trigger
        left = ctk.CTkScrollableFrame(container, label_text="PASO 1 Y 2: FOTOGRAFÍA DE BARANDILLA (GOOGLE FLOW / FONDO BLANCO)")
        left.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=4)

        btn_row = ctk.CTkFrame(left, fg_color="transparent")
        btn_row.pack(fill="x", pady=4)

        ctk.CTkButton(
            btn_row,
            text="📂 Seleccionar Imagen",
            command=self.on_select_photo,
            fg_color="#2B6CB0",
            height=36,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        ctk.CTkButton(
            btn_row,
            text="📋 Pegar Imagen (Ctrl+V)",
            command=self.on_paste_photo,
            fg_color="#319795",
            hover_color="#2C7A7B",
            height=36,
        ).pack(side="left", fill="x", expand=True, padx=(2, 4))

        ctk.CTkButton(
            btn_row,
            text="🧪 Foto Demo",
            command=self.on_load_sample_railing,
            fg_color="#4A5568",
            width=105,
            height=36,
        ).pack(side="left", padx=(2, 0))

        # Single Preview: Studio Photo on Pure White Background
        preview_frame = ctk.CTkFrame(left, fg_color="#FFFFFF", corner_radius=8, border_width=1, border_color="#CBD5E0")
        preview_frame.pack(fill="x", pady=8, padx=2)

        ctk.CTkLabel(
            preview_frame,
            text="Fotografía de Catálogo (Fondo Blanco Puro #FFFFFF)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1A202C",
        ).pack(pady=(8, 2))

        self.white_preview_lbl = ctk.CTkLabel(
            preview_frame,
            text="[Selecciona una imagen o presiona Pegar Imagen (Ctrl+V)]\n(Generada en Google Flow — sin recortes automáticos)",
            width=440,
            height=210,
            fg_color="#F7FAFC",
            text_color="#4A5568",
            corner_radius=6,
        )
        self.white_preview_lbl.pack(padx=8, pady=(2, 8), fill="both", expand=True)

        # Gemini Analysis Card
        ai_frame = ctk.CTkFrame(left, border_width=1, border_color="#D69E2E")
        ai_frame.pack(fill="x", pady=8, padx=2)

        ctk.CTkLabel(
            ai_frame,
            text="PASO 3: ANÁLISIS VISUAL CON GOOGLE GEMINI",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            ai_frame,
            text="Motor de Gemini (aprovecha primero tu cuenta personal sin coste):",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=10)

        self.engine_var = ctk.StringVar(value=list(ENGINE_MAP.keys())[0])
        ctk.CTkOptionMenu(
            ai_frame,
            variable=self.engine_var,
            values=list(ENGINE_MAP.keys()),
        ).pack(fill="x", padx=10, pady=4)

        self.btn_gemini_analyze = ctk.CTkButton(
            ai_frame,
            text="✨ Analizar Foto con Gemini y Proponer Descripción",
            command=self.on_analyze_with_gemini,
            fg_color="#D69E2E",
            hover_color="#B7791F",
            text_color="#1A202C",
            font=ctk.CTkFont(weight="bold"),
            height=38,
        )
        self.btn_gemini_analyze.pack(fill="x", padx=10, pady=(4, 6))

        self.ai_status_lbl = ctk.CTkLabel(
            ai_frame,
            text="Estado IA: Listo. Tu cuenta personal en Antigravity está autenticada.",
            font=ctk.CTkFont(size=11),
            text_color="#A0AEC0",
            wraplength=460,
            justify="left",
        )
        self.ai_status_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # RIGHT PANEL: Product Description & Strict User Pricing
        right = ctk.CTkScrollableFrame(
            container,
            label_text="PASO 4: DESCRIPCIÓN DEL PRODUCTO Y PRECIOS EXACTOS (SIN INVENTAR CIFRAS)",
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 4), pady=4)

        row1 = ctk.CTkFrame(right, fg_color="transparent")
        row1.pack(fill="x", pady=3)
        row1.grid_columnconfigure(0, weight=3)
        row1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row1, text="Model / Railing Name:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=4
        )
        ctk.CTkLabel(row1, text="SKU / Ref Code:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, sticky="w", padx=4
        )

        self.entry_name = ctk.CTkEntry(
            row1, placeholder_text="Modern Black  Stair and Porch RG Railing Style"
        )
        self.entry_name.insert(0, "Modern Black  Stair and Porch RG Railing Style")
        self.entry_name.grid(row=1, column=0, sticky="ew", padx=4, pady=2)

        self.entry_sku = ctk.CTkEntry(row1, placeholder_text="RS-1")
        self.entry_sku.insert(0, self.current_item_id)
        self.entry_sku.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        row2 = ctk.CTkFrame(right, fg_color="transparent")
        row2.pack(fill="x", pady=3)
        row2.grid_columnconfigure(0, weight=1)
        row2.grid_columnconfigure(1, weight=1)
        row2.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(row2, text="Category:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=4
        )
        ctk.CTkLabel(row2, text="Material:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=1, sticky="w", padx=4
        )
        ctk.CTkLabel(row2, text="Color / Finish:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=2, sticky="w", padx=4
        )

        self.cat_var = ctk.StringVar(value=CATEGORIES[0])
        ctk.CTkOptionMenu(row2, variable=self.cat_var, values=CATEGORIES).grid(
            row=1, column=0, sticky="ew", padx=4, pady=2
        )

        self.entry_material = ctk.CTkEntry(row2, placeholder_text="Metal or Aluminum")
        self.entry_material.insert(0, "Metal or Aluminum")
        self.entry_material.grid(row=1, column=1, sticky="ew", padx=4, pady=2)

        self.entry_finish = ctk.CTkEntry(row2, placeholder_text="Any Color Powder coating")
        self.entry_finish.insert(0, "Any Color Powder coating")
        self.entry_finish.grid(row=1, column=2, sticky="ew", padx=4, pady=2)

        # Descriptions (ES & EN)
        ctk.CTkLabel(
            right,
            text="Descripción Comercial y Técnica (Español) — Propuesta por Gemini / Editable:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=4, pady=(6, 2))
        self.txt_desc_es = ctk.CTkTextbox(right, height=72)
        self.txt_desc_es.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(
            right,
            text="Commercial & Technical Description (English) — Proposed by Gemini / Editable:",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=4, pady=(6, 2))
        self.txt_desc_en = ctk.CTkTextbox(right, height=72)
        self.txt_desc_en.pack(fill="x", padx=4, pady=2)

        # --------------------------------------------------------------
        # RAILING SPECIFICATIONS SECTION (Style & Construction Details)
        # --------------------------------------------------------------
        specs_box = ctk.CTkFrame(right, border_width=1, border_color="#4A5568")
        specs_box.pack(fill="x", padx=4, pady=(8, 4))

        ctk.CTkLabel(
            specs_box,
            text="📋 PRODUCT SPECIFICATIONS (STYLE & CONSTRUCTION DETAILS)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            specs_box,
            text="Exact railing style and construction specifications for the PDF catalog. Empty fields are hidden automatically.",
            font=ctk.CTkFont(size=11),
            text_color="#CBD5E0",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # 8 Default Specification Fields (2 columns x 4 rows)
        default_specs_grid = ctk.CTkFrame(specs_box, fg_color="transparent")
        default_specs_grid.pack(fill="x", padx=10, pady=2)
        default_specs_grid.grid_columnconfigure(0, weight=1)
        default_specs_grid.grid_columnconfigure(1, weight=1)

        field_pairs = [
            (DEFAULT_SPEC_FIELDS[0], DEFAULT_SPEC_FIELDS[4]),  # Post Type | Railing Style
            (DEFAULT_SPEC_FIELDS[1], DEFAULT_SPEC_FIELDS[5]),  # Top Cap / Top Molding Type | Railing Height
            (DEFAULT_SPEC_FIELDS[2], DEFAULT_SPEC_FIELDS[6]),  # Bottom Channel Type | Material
            (DEFAULT_SPEC_FIELDS[3], DEFAULT_SPEC_FIELDS[7]),  # Spindle Type | Finish / Color
        ]

        for r_idx, (left_spec, right_spec) in enumerate(field_pairs):
            f_name_l, f_vals_l = left_spec
            cell_l = ctk.CTkFrame(default_specs_grid, fg_color="transparent")
            cell_l.grid(row=r_idx, column=0, sticky="ew", padx=(0, 6), pady=3)
            ctk.CTkLabel(
                cell_l,
                text=f"{f_name_l}:",
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(anchor="w", pady=(0, 1))
            combo_l = ctk.CTkComboBox(cell_l, values=f_vals_l, height=28)
            combo_l.set("")
            combo_l.pack(fill="x")
            self.default_spec_combos[f_name_l] = combo_l

            f_name_r, f_vals_r = right_spec
            cell_r = ctk.CTkFrame(default_specs_grid, fg_color="transparent")
            cell_r.grid(row=r_idx, column=1, sticky="ew", padx=(6, 0), pady=3)
            ctk.CTkLabel(
                cell_r,
                text=f"{f_name_r}:",
                font=ctk.CTkFont(size=11, weight="bold"),
            ).pack(anchor="w", pady=(0, 1))
            combo_r = ctk.CTkComboBox(cell_r, values=f_vals_r, height=28)
            combo_r.set("")
            combo_r.pack(fill="x")
            self.default_spec_combos[f_name_r] = combo_r

        # Extra Specifications Container
        self.extra_specs_container = ctk.CTkFrame(specs_box, fg_color="transparent")
        self.extra_specs_container.pack(fill="x", padx=10, pady=(4, 2))

        # + Add Extra Specification Button
        ctk.CTkButton(
            specs_box,
            text="➕ Add Extra Specification",
            command=self.on_add_extra_spec,
            fg_color="#2B6CB0",
            hover_color="#2C5282",
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(6, 10))

        # Observable Specifications / Notes
        ctk.CTkLabel(
            right,
            text="Observable Specifications (1 per line):",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=4, pady=(6, 2))
        self.txt_features = ctk.CTkTextbox(right, height=54)
        self.txt_features.pack(fill="x", padx=4, pady=2)

        # STRICT PRICING SECTION (Never invent numbers)
        price_box = ctk.CTkFrame(right, border_width=2, border_color="#ECC94B")
        price_box.pack(fill="x", padx=4, pady=10)

        ctk.CTkLabel(
            price_box,
            text="💲 PRECIOS OFICIALES DEL PRODUCTO (REGLA ESTRICTA: CERO CIFRAS INVENTADAS)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            price_box,
            text="Introduce únicamente los precios reales de NJ Fence and Railing. El sistema jamás inventa ni redondea cifras no autorizadas.",
            font=ctk.CTkFont(size=11),
            text_color="#CBD5E0",
        ).pack(anchor="w", padx=12, pady=(0, 6))

        p_mode_row = ctk.CTkFrame(price_box, fg_color="transparent")
        p_mode_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(p_mode_row, text="Modalidad de Precio:", font=ctk.CTkFont(weight="bold")).pack(
            side="left", padx=(0, 8)
        )
        self.pricing_mode_var = ctk.StringVar(value=list(PRICING_MODE_MAP.keys())[0])
        ctk.CTkOptionMenu(
            p_mode_row,
            variable=self.pricing_mode_var,
            values=list(PRICING_MODE_MAP.keys()),
            width=280,
        ).pack(side="left")

        p_inputs = ctk.CTkFrame(price_box, fg_color="transparent")
        p_inputs.pack(fill="x", padx=12, pady=6)
        p_inputs.grid_columnconfigure(0, weight=1)
        p_inputs.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            p_inputs,
            text="Precio por Pie Lineal ($ USD / Linear Ft):",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(
            p_inputs,
            text="Precio por Kit Completo ($ USD / Kit):",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=4)

        self.entry_price_lf = ctk.CTkEntry(
            p_inputs, placeholder_text="Ej. 48.00 (Dejar vacío si no aplica)"
        )
        self.entry_price_lf.grid(row=1, column=0, sticky="ew", padx=4, pady=3)

        self.entry_price_kit = ctk.CTkEntry(
            p_inputs, placeholder_text="Ej. 325.00 (Dejar vacío si no aplica)"
        )
        self.entry_price_kit.grid(row=1, column=1, sticky="ew", padx=4, pady=3)

        ctk.CTkLabel(
            price_box,
            text="Nota de Precio / Qué incluye el Kit (Opcional):",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=16, pady=(2, 0))
        self.entry_kit_note = ctk.CTkEntry(
            price_box,
            placeholder_text='Ej. Sección de 6 pies x 36" altura, incluye soportes y tornillería de acero inoxidable',
        )
        self.entry_kit_note.pack(fill="x", padx=16, pady=(2, 10))

        # Action Buttons
        action_row = ctk.CTkFrame(right, fg_color="transparent")
        action_row.pack(fill="x", padx=4, pady=8)

        ctk.CTkButton(
            action_row,
            text="➕ Guardar Producto en el Catálogo",
            command=self.on_save_product_to_catalog,
            fg_color="#38A169",
            hover_color="#2F855A",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            action_row,
            text="🧹 Limpiar Formulario",
            command=self.on_clear_form,
            fg_color="#4A5568",
            width=150,
            height=42,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Tab 2: Catalog List, Company Header Config & PDF Export
    # ------------------------------------------------------------------
    def _build_tab_catalog(self) -> None:
        container = ctk.CTkFrame(self.tab_catalog, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=4)
        container.grid_columnconfigure(1, weight=6)
        container.grid_rowconfigure(0, weight=1)

        # Left: Company Header Settings
        hdr_frame = ctk.CTkScrollableFrame(
            container,
            label_text="DATOS DE ENCABEZADO DEL CATÁLOGO PDF (NJ FENCE AND RAILING)",
        )
        hdr_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=4)

        self.hdr_company_entry = self._add_labeled_entry(
            hdr_frame, "Nombre de la Empresa:", self.company_header.company_name
        )
        self.hdr_title_entry = self._add_labeled_entry(
            hdr_frame, "Título del Catálogo:", self.company_header.catalog_title
        )
        self.hdr_sub_entry = self._add_labeled_entry(
            hdr_frame, "Subtítulo / Especialidad:", self.company_header.subtitle
        )
        self.hdr_phone_entry = self._add_labeled_entry(
            hdr_frame, "Teléfono de Contacto:", self.company_header.phone
        )
        self.hdr_email_entry = self._add_labeled_entry(
            hdr_frame, "Correo Electrónico:", self.company_header.email
        )
        self.hdr_loc_entry = self._add_labeled_entry(
            hdr_frame, "Área de Servicio:", self.company_header.location
        )

        ctk.CTkLabel(
            hdr_frame, text="Idioma de Descripciones en el PDF:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=6, pady=(8, 2))
        self.hdr_lang_var = ctk.StringVar(value=self.company_header.language_mode)
        ctk.CTkOptionMenu(
            hdr_frame,
            variable=self.hdr_lang_var,
            values=["bilingual", "es", "en"],
        ).pack(fill="x", padx=6, pady=4)

        ctk.CTkButton(
            hdr_frame,
            text="💾 Guardar Datos de Encabezado",
            command=self.on_save_header_settings,
            fg_color="#2B6CB0",
            height=36,
        ).pack(fill="x", padx=6, pady=12)

        # Right: Saved Catalog Products & PDF Generation
        right = ctk.CTkFrame(container)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 4), pady=4)

        top_bar = ctk.CTkFrame(right, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=8)

        self.catalog_count_lbl = ctk.CTkLabel(
            top_bar,
            text="Productos en el Catálogo (0)",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.catalog_count_lbl.pack(side="left")

        ctk.CTkButton(
            top_bar,
            text="📄 Generar Catálogo PDF Profesional",
            command=self.on_export_pdf,
            fg_color="#B7791F",
            hover_color="#975A16",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="right", padx=4)

        ctk.CTkButton(
            top_bar,
            text="📂 Abrir Último PDF",
            command=self.on_open_last_pdf,
            fg_color="#2D3748",
            width=145,
        ).pack(side="right", padx=4)

        self.items_scroll = ctk.CTkScrollableFrame(right, label_text="Listado de Barandillas y Cercas")
        self.items_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _add_labeled_entry(self, parent, label: str, initial: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=6, pady=(6, 1)
        )
        entry = ctk.CTkEntry(parent)
        entry.insert(0, initial)
        entry.pack(fill="x", padx=6, pady=2)
        return entry

    # ------------------------------------------------------------------
    # Tab 3: Google Flow Manual Assistant & Live Google Integrations Check
    # ------------------------------------------------------------------
    def _build_tab_google(self) -> None:
        container = ctk.CTkFrame(self.tab_google, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=5)
        container.grid_columnconfigure(1, weight=6)
        container.grid_rowconfigure(0, weight=1)

        # Left: Honest Google Flow Assistant
        flow_frame = ctk.CTkScrollableFrame(
            container,
            label_text="GOOGLE FLOW (labs.google/fx/tools/flow) — ASISTENTE Y ESTADO OFICIAL",
        )
        flow_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 8), pady=4)

        info_text = (
            "INFORMACIÓN OFICIAL VERIFICADA SOBRE GOOGLE FLOW:\n\n"
            "1. ¿Existe API pública de Google Flow?: NO. Google Labs diseñó Flow como una aplicación web "
            "interactiva (labs.google/fx/tools/flow) y no publica una API REST para automatizar la web de Flow.\n"
            "2. Cero Simulaciones: Cumpliendo tus instrucciones, NO simulamos ninguna conexión inexistente.\n"
            "3. Cómo aprovechar Google Flow GRATIS con tu cuenta personal:\n"
            "   • Esta aplicación genera automáticamente el Prompt ('Ingredients') en inglés a partir de tu barandilla.\n"
            "   • Haz clic en 'Copiar Prompt y Abrir Google Flow' para crear renders o videos promocionales con Veo/Imagen.\n"
            "   • Descarga la imagen generada en Flow y súbela aquí con el botón 'Importar Imagen desde Google Flow'."
        )
        ctk.CTkLabel(
            flow_frame,
            text=info_text,
            justify="left",
            wraplength=500,
            text_color="#E2E8F0",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=10, pady=8)

        ctk.CTkLabel(
            flow_frame,
            text="Prompt optimizado para Google Flow (Ingredients / Veo / Imagen):",
            font=ctk.CTkFont(weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.txt_flow_prompt = ctk.CTkTextbox(flow_frame, height=110)
        self.txt_flow_prompt.pack(fill="x", padx=10, pady=4)
        default_flow_prompt = generate_flow_prompt_for_product(
            "Architectural Black Picket Railing",
            "Aluminum Railing",
            "Powder-Coated Aluminum",
            "Matte Black",
        )
        self.txt_flow_prompt.insert("1.0", default_flow_prompt)

        flow_btns = ctk.CTkFrame(flow_frame, fg_color="transparent")
        flow_btns.pack(fill="x", padx=10, pady=6)

        ctk.CTkButton(
            flow_btns,
            text="📋 Copiar Prompt",
            command=self.on_copy_flow_prompt,
            fg_color="#2B6CB0",
            width=145,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            flow_btns,
            text="🌐 Abrir Google Flow en Navegador",
            command=open_google_flow_in_browser,
            fg_color="#319795",
        ).pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            flow_frame,
            text="📥 Importar Imagen Descargada de Google Flow al Editor",
            command=self.on_select_photo,
            fg_color="#38A169",
            height=36,
        ).pack(fill="x", padx=10, pady=6)

        # Optional Imagen 3 API section
        api_gen_box = ctk.CTkFrame(flow_frame, border_width=1, border_color="#4A5568")
        api_gen_box.pack(fill="x", padx=10, pady=12)

        ctk.CTkLabel(
            api_gen_box,
            text="Conexión Programática Opcional: Motor Subyacente Imagen 3 (`google-genai`)",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 2))

        ctk.CTkLabel(
            api_gen_box,
            text="Si configuras una GEMINI_API_KEY con facturación habilitada en Google Cloud, puedes generar imágenes directamente vía `imagen-3.0-generate-002` (Coste aprox. $0.03–$0.04 USD/imagen).",
            wraplength=480,
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color="#A0AEC0",
        ).pack(anchor="w", padx=10, pady=4)

        ctk.CTkButton(
            api_gen_box,
            text="⚡ Generar Imagen por API Oficial (Requiere GEMINI_API_KEY con Billing)",
            command=self.on_generate_imagen_api,
            fg_color="#4A5568",
        ).pack(fill="x", padx=10, pady=(4, 10))

        # Right: Live Diagnostic Report of Google Integrations, Auth & Costs
        diag_frame = ctk.CTkScrollableFrame(
            container,
            label_text="ESTADO EN VIVO DE INTEGRACIONES GOOGLE, AUTORIZACIÓN Y COSTES",
        )
        diag_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 4), pady=4)

        top_diag = ctk.CTkFrame(diag_frame, fg_color="transparent")
        top_diag.pack(fill="x", padx=6, pady=4)

        ctk.CTkButton(
            top_diag,
            text="🔄 Comprobar Integraciones Ahora",
            command=self._refresh_integrations_report_ui,
            fg_color="#2B6CB0",
            width=220,
        ).pack(side="left")

        ctk.CTkButton(
            top_diag,
            text="🔑 1. Abrir Google AI Studio (Crear Key)",
            command=open_ai_studio_key_page,
            fg_color="#D69E2E",
            hover_color="#B7791F",
            text_color="#1A202C",
            font=ctk.CTkFont(weight="bold"),
            width=245,
        ).pack(side="right")

        key_box = ctk.CTkFrame(diag_frame, border_width=1, border_color="#ECC94B")
        key_box.pack(fill="x", padx=6, pady=6)

        ctk.CTkLabel(
            key_box,
            text="Configurar tu GEMINI_API_KEY (Se guarda de forma segura en E:\\mcp\\.env, fuera de GitHub):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#F6E05E",
        ).pack(anchor="w", padx=10, pady=(8, 2))

        key_row = ctk.CTkFrame(key_box, fg_color="transparent")
        key_row.pack(fill="x", padx=10, pady=(2, 8))

        self.entry_api_key = ctk.CTkEntry(
            key_row,
            placeholder_text="Pega aquí tu clave AIzaSy... de Google AI Studio",
            show="*",
        )
        self.entry_api_key.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            key_row,
            text="💾 Guardar API Key",
            command=self.on_save_api_key,
            fg_color="#38A169",
            hover_color="#2F855A",
            width=150,
        ).pack(side="left")

        self.integrations_container = ctk.CTkFrame(diag_frame, fg_color="transparent")
        self.integrations_container.pack(fill="both", expand=True, padx=4, pady=6)

    # ------------------------------------------------------------------
    # Event Handlers & Workflows
    # ------------------------------------------------------------------
    def _update_image_previews(self) -> None:
        target_path = self.current_white_path or self.current_raw_path
        if target_path and target_path.exists():
            white_pil = Image.open(target_path)
            # Scale preview preserving aspect ratio
            white_ctk = ctk.CTkImage(light_image=white_pil, dark_image=white_pil, size=(380, 210))
            self.white_preview_lbl.configure(image=white_ctk, text="")
            self.white_preview_lbl.image = white_ctk  # type: ignore

    def on_select_photo(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleccionar fotografía de barandilla (Fondo Blanco)",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not file_path:
            return
        self._load_direct_photo(Path(file_path))

    def on_paste_photo(self) -> None:
        from PIL import ImageGrab
        try:
            data = ImageGrab.grabclipboard()
            if isinstance(data, Image.Image):
                sku_val = self.entry_sku.get().strip() or self.current_item_id
                out_white = WHITE_PHOTOS_DIR / f"{sku_val}_white.png"
                if data.mode not in ("RGB", "RGBA"):
                    data = data.convert("RGB")
                data.save(out_white, format="PNG")
                self.current_white_path = out_white
                self.current_raw_path = out_white
                self._update_image_previews()
                self.ai_status_lbl.configure(
                    text="✅ Imagen pegada correctamente desde el portapapeles. Lista para el catálogo o para analizar con Gemini.",
                    text_color="#68D391",
                )
            elif isinstance(data, list):
                for p in data:
                    path = Path(p)
                    if path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
                        self._load_direct_photo(path)
                        return
                messagebox.showinfo("Portapapeles", "No se encontró ningún archivo de imagen en el portapapeles.")
            else:
                messagebox.showinfo(
                    "Portapapeles",
                    "No hay ninguna imagen en el portapapeles.\nCopia una imagen primero (en Google Flow o explorador de archivos) y presiona 'Pegar Imagen' (o Ctrl+V)."
                )
        except Exception as exc:
            messagebox.showerror("Error al pegar imagen", str(exc))

    def _load_direct_photo(self, source_path: Path) -> None:
        try:
            sku_val = self.entry_sku.get().strip() or self.current_item_id
            out_white = WHITE_PHOTOS_DIR / f"{sku_val}_white.png"
            img = Image.open(source_path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            img.save(out_white, format="PNG")
            self.current_white_path = out_white
            self.current_raw_path = out_white
            self._update_image_previews()
            self.ai_status_lbl.configure(
                text="✅ Imagen cargada correctamente. Lista para el catálogo o para analizar con Gemini.",
                text_color="#68D391",
            )
        except Exception as exc:
            messagebox.showerror("Error al cargar imagen", str(exc))

    def on_load_sample_railing(self) -> None:
        sample_white = WHITE_PHOTOS_DIR / "sample_nj_architectural_railing_white.png"
        create_sample_railing_photo(sample_white)
        self._load_direct_photo(sample_white)
        self.tabview.set("1. Subir Foto, Procesar Fondo Blanco y Precios")
        self.ai_status_lbl.configure(
            text="Foto de prueba cargada sobre fondo blanco (#FFFFFF). Haz clic en '✨ Analizar Foto con Gemini' o introduce tus precios.",
            text_color="#68D391",
        )

    def on_process_white_bg(self) -> None:
        if self.current_white_path:
            self._update_image_previews()

    def on_analyze_with_gemini(self) -> None:
        target_img = self.current_raw_path or self.current_white_path
        if not target_img or not target_img.exists():
            messagebox.showwarning(
                "Sube una fotografía primero",
                "Sube una foto de una barandilla o haz clic en '🧪 Usar Foto Demo' antes de analizar con Gemini.",
            )
            return

        selected_engine = ENGINE_MAP.get(self.engine_var.get(), "auto")
        self.btn_gemini_analyze.configure(state="disabled", text="⏳ Analizando imagen con Gemini...")
        self.ai_status_lbl.configure(
            text="Conectando con tu cuenta de Google en Antigravity / Gemini para analizar la barandilla (puede tardar ~20-35s vía CLI OAuth)...",
            text_color="#F6E05E",
        )

        def _worker() -> None:
            try:
                result = analyze_railing_image(target_img, engine=selected_engine)
                self.after(0, lambda: self._apply_gemini_result(result))
            except Exception as exc:
                err_msg = str(exc)
                self.after(0, lambda: self._on_gemini_error(err_msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_gemini_result(self, data: dict) -> None:
        self.btn_gemini_analyze.configure(
            state="normal", text="✨ Analizar Foto con Gemini y Proponer Descripción"
        )
        self.current_ai_source = str(data.get("ai_source", "Gemini"))

        # Preserve user-pinned default specifications
        cur_name = self.entry_name.get().strip()
        if not cur_name:
            self.entry_name.insert(0, str(data.get("name") or "Modern Black  Stair and Porch RG Railing Style"))

        cat = str(data.get("category", ""))
        if cat in CATEGORIES:
            self.cat_var.set(cat)

        cur_mat = self.entry_material.get().strip()
        if not cur_mat:
            self.entry_material.insert(0, str(data.get("material") or "Metal or Aluminum"))

        cur_finish = self.entry_finish.get().strip()
        if not cur_finish:
            self.entry_finish.insert(0, str(data.get("finish_color") or "Any Color Powder coating"))

        if data.get("description_es"):
            self.txt_desc_es.delete("1.0", "end")
            self.txt_desc_es.insert("1.0", str(data["description_es"]))

        if data.get("description_en"):
            self.txt_desc_en.delete("1.0", "end")
            self.txt_desc_en.insert(0, str(data["description_en"])) if False else self.txt_desc_en.insert("1.0", str(data["description_en"]))

        feats = data.get("features") or []
        if isinstance(feats, list) and feats:
            self.txt_features.delete("1.0", "end")
            self.txt_features.insert("1.0", "\n".join(str(x) for x in feats))

        flow_prompt = data.get("flow_prompt_suggestion") or generate_flow_prompt_for_product(
            self.entry_name.get(),
            self.cat_var.get(),
            self.entry_material.get(),
            self.entry_finish.get(),
        )
        self.txt_flow_prompt.delete("1.0", "end")
        self.txt_flow_prompt.insert("1.0", str(flow_prompt))

        self.ai_status_lbl.configure(
            text=f"✅ Análisis completado con éxito vía: {self.current_ai_source}. (Precios intactos: introduce tus cifras reales abajo).",
            text_color="#68D391",
        )

    def _on_gemini_error(self, err_msg: str) -> None:
        self.btn_gemini_analyze.configure(
            state="normal", text="✨ Analizar Foto con Gemini y Proponer Descripción"
        )
        self.ai_status_lbl.configure(text=f"⚠️ {err_msg}", text_color="#FC8181")
        messagebox.showerror("Error en Análisis Gemini", err_msg)

    # ------------------------------------------------------------------
    # Railing Specifications Handlers
    # ------------------------------------------------------------------
    def on_add_extra_spec(self, name: str = "", value: str = "") -> None:
        row = ctk.CTkFrame(self.extra_specs_container, fg_color="transparent")
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=3)

        name_entry = ctk.CTkEntry(row, placeholder_text="Spec Name (e.g. Spindle Spacing)", height=28)
        if name:
            name_entry.insert(0, str(name))
        name_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        val_entry = ctk.CTkEntry(row, placeholder_text="Specification Value (e.g. 4 inches)", height=28)
        if value:
            val_entry.insert(0, str(value))
        val_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        btn_del = ctk.CTkButton(
            row,
            text="✕ Remove",
            fg_color="#C53030",
            hover_color="#9B2C2C",
            width=72,
            height=28,
            command=lambda r=row: self._remove_extra_spec_row(r),
        )
        btn_del.grid(row=0, column=2, padx=(0, 0))

        self.extra_spec_rows.append({"frame": row, "name_entry": name_entry, "val_entry": val_entry})

    def _remove_extra_spec_row(self, target_row: ctk.CTkFrame) -> None:
        for idx, row_dict in enumerate(list(self.extra_spec_rows)):
            if row_dict["frame"] == target_row:
                try:
                    target_row.destroy()
                except Exception:
                    pass
                self.extra_spec_rows.pop(idx)
                break

    def get_current_specifications(self) -> Dict[str, str]:
        specs: Dict[str, str] = {}
        for f_name, _ in DEFAULT_SPEC_FIELDS:
            combo = self.default_spec_combos.get(f_name)
            if combo:
                val = combo.get().strip()
                if val:
                    specs[f_name] = val

        for row_dict in self.extra_spec_rows:
            s_name = row_dict["name_entry"].get().strip()
            s_val = row_dict["val_entry"].get().strip()
            if s_name and s_val:
                specs[s_name] = s_val

        return specs

    def set_specifications(self, specs: Dict[str, str]) -> None:
        for f_name, _ in DEFAULT_SPEC_FIELDS:
            combo = self.default_spec_combos.get(f_name)
            if combo:
                combo.set("")

        for row_dict in list(self.extra_spec_rows):
            try:
                row_dict["frame"].destroy()
            except Exception:
                pass
        self.extra_spec_rows.clear()

        if not specs or not isinstance(specs, dict):
            return

        for f_name, _ in DEFAULT_SPEC_FIELDS:
            combo = self.default_spec_combos.get(f_name)
            if combo and f_name in specs:
                combo.set(str(specs[f_name]))

        default_names = {f[0] for f in DEFAULT_SPEC_FIELDS}
        for k, v in specs.items():
            if k not in default_names:
                self.on_add_extra_spec(name=k, value=str(v))

    def load_product_into_editor(self, item: ProductItem) -> None:
        self.current_item_id = item.id
        self.current_raw_path = Path(item.original_image_path) if item.original_image_path else None
        self.current_white_path = Path(item.white_bg_image_path) if item.white_bg_image_path else None
        self.current_ai_source = item.ai_source or "manual"

        self.entry_sku.delete(0, "end")
        self.entry_sku.insert(0, item.sku or item.id)

        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, item.name)

        if item.category in CATEGORIES:
            self.cat_var.set(item.category)

        self.entry_material.delete(0, "end")
        self.entry_material.insert(0, item.material)

        self.entry_finish.delete(0, "end")
        self.entry_finish.insert(0, item.finish_color)

        self.txt_desc_es.delete("1.0", "end")
        self.txt_desc_es.insert("1.0", item.description_es)

        self.txt_desc_en.delete("1.0", "end")
        self.txt_desc_en.insert("1.0", item.description_en)

        self.txt_features.delete("1.0", "end")
        self.txt_features.insert("1.0", "\n".join(item.features))

        # Restore product-specific specifications
        self.set_specifications(getattr(item, "specifications", {}))

        # Restore pricing
        for mode_label, mode_val in PRICING_MODE_MAP.items():
            if mode_val == item.pricing_mode:
                self.pricing_mode_var.set(mode_label)
                break

        self.entry_price_lf.delete(0, "end")
        if item.price_per_linear_ft is not None:
            self.entry_price_lf.insert(0, f"{item.price_per_linear_ft:.2f}")

        self.entry_price_kit.delete(0, "end")
        if item.price_per_kit is not None:
            self.entry_price_kit.insert(0, f"{item.price_per_kit:.2f}")

        self.entry_kit_note.delete(0, "end")
        self.entry_kit_note.insert(0, item.kit_includes_note)

        self._update_image_previews()
        self.tabview.set("1. Subir Foto, Procesar Fondo Blanco y Precios")
        self.ai_status_lbl.configure(
            text=f"✅ Producto '{item.name}' [{item.sku}] cargado en el editor con sus especificaciones independientes.",
            text_color="#68D391",
        )

    def on_save_product_to_catalog(self) -> None:
        name = self.entry_name.get().strip()
        if not name:
            messagebox.showwarning("Falta el nombre", "Introduce o genera con Gemini el nombre del modelo.")
            return

        if not self.current_white_path or not self.current_white_path.exists():
            if self.current_raw_path and self.current_raw_path.exists():
                self.on_process_white_bg()
            else:
                messagebox.showwarning(
                    "Falta la fotografía",
                    "Sube una fotografía de la barandilla para procesarla sobre fondo blanco antes de guardar.",
                )
                return

        pricing_mode = PRICING_MODE_MAP.get(
            self.pricing_mode_var.get(), PricingMode.PER_LINEAR_FOOT.value
        )

        try:
            price_lf = parse_user_price(self.entry_price_lf.get())
            price_kit = parse_user_price(self.entry_price_kit.get())
        except ValueError as err:
            messagebox.showerror("Precio inválido", str(err))
            return

        if pricing_mode == PricingMode.PER_LINEAR_FOOT.value and price_lf is None:
            messagebox.showwarning(
                "Precio por Pie Lineal requerido",
                "Seleccionaste 'Por Pie Lineal ($ / Linear Ft)'. Introduce el precio exacto por pie lineal (no inventamos cifras) o cambia la modalidad.",
            )
            return

        if pricing_mode == PricingMode.PER_KIT.value and price_kit is None:
            messagebox.showwarning(
                "Precio por Kit requerido",
                "Seleccionaste 'Por Kit Completo ($ / Kit)'. Introduce el precio exacto por kit (no inventamos cifras) o cambia la modalidad.",
            )
            return

        if pricing_mode == PricingMode.BOTH.value and (price_lf is None or price_kit is None):
            messagebox.showwarning(
                "Ambos precios requeridos",
                "Seleccionaste 'Ambos (Pie Lineal + Kit)'. Introduce ambas cifras exactas o elige una sola modalidad.",
            )
            return

        features_raw = self.txt_features.get("1.0", "end").splitlines()
        features_list = [f.strip().lstrip("•- ") for f in features_raw if f.strip()]

        item_specs = self.get_current_specifications()
        if "Material" in item_specs and not self.entry_material.get().strip():
            self.entry_material.insert(0, item_specs["Material"])
        elif self.entry_material.get().strip() and "Material" not in item_specs:
            item_specs["Material"] = self.entry_material.get().strip()

        if "Finish / Color" in item_specs and not self.entry_finish.get().strip():
            self.entry_finish.insert(0, item_specs["Finish / Color"])
        elif self.entry_finish.get().strip() and "Finish / Color" not in item_specs:
            item_specs["Finish / Color"] = self.entry_finish.get().strip()

        sku_val = self.entry_sku.get().strip() or self.current_item_id
        item = ProductItem(
            id=self.current_item_id,
            sku=sku_val,
            name=name,
            category=self.cat_var.get(),
            material=self.entry_material.get().strip(),
            finish_color=self.entry_finish.get().strip(),
            description_es=self.txt_desc_es.get("1.0", "end").strip(),
            description_en=self.txt_desc_en.get("1.0", "end").strip(),
            features=features_list,
            specifications=item_specs,
            pricing_mode=pricing_mode,
            price_per_linear_ft=price_lf,
            price_per_kit=price_kit,
            kit_includes_note=self.entry_kit_note.get().strip(),
            original_image_path=str(self.current_raw_path) if self.current_raw_path else "",
            white_bg_image_path=str(self.current_white_path) if self.current_white_path else "",
            bg_processing_mode="direct_white_studio",
            ai_source=self.current_ai_source,
            flow_prompt_suggestion=self.txt_flow_prompt.get("1.0", "end").strip(),
        )

        # Replace if SKU/ID exists, else append
        existing_idx = next(
            (i for i, x in enumerate(self.catalog_items) if x.sku == item.sku or x.id == item.id),
            None,
        )
        if existing_idx is not None:
            self.catalog_items[existing_idx] = item
        else:
            self.catalog_items.append(item)

        save_catalog_items(self.catalog_items)
        self._refresh_catalog_list_ui()
        messagebox.showinfo(
            "Producto guardado",
            f"El modelo '{item.name}' ({item.sku}) fue guardado en el catálogo con sus especificaciones y precios exactos.",
        )
        self.on_clear_form()

    def on_clear_form(self) -> None:
        self.current_item_id = get_next_sku(self.catalog_items, "RS-")
        self.current_raw_path = None
        self.current_white_path = None
        self.current_ai_source = "manual"

        self.entry_name.delete(0, "end")
        self.entry_name.insert(0, "Modern Black  Stair and Porch RG Railing Style")

        self.entry_sku.delete(0, "end")
        self.entry_sku.insert(0, self.current_item_id)

        self.entry_material.delete(0, "end")
        self.entry_material.insert(0, "Metal or Aluminum")

        self.entry_finish.delete(0, "end")
        self.entry_finish.insert(0, "Any Color Powder coating")

        self.txt_desc_es.delete("1.0", "end")
        self.txt_desc_en.delete("1.0", "end")
        self.txt_features.delete("1.0", "end")

        # Clear specifications
        self.set_specifications({})

        self.entry_price_lf.delete(0, "end")
        self.entry_price_kit.delete(0, "end")
        self.entry_kit_note.delete(0, "end")

        if hasattr(self, "raw_preview_lbl"):
            self.raw_preview_lbl.configure(image=None, text="[Sube una foto]")
        self.white_preview_lbl.configure(
            image=None,
            text="[Selecciona una imagen o presiona Pegar Imagen (Ctrl+V)]\n(Generada en Google Flow — sin recortes automáticos)",
        )

    def _refresh_catalog_list_ui(self) -> None:
        for child in self.items_scroll.winfo_children():
            child.destroy()

        self.catalog_count_lbl.configure(text=f"Productos en el Catálogo ({len(self.catalog_items)})")

        if not self.catalog_items:
            ctk.CTkLabel(
                self.items_scroll,
                text="Aún no hay productos guardados. Ve a la Pestaña 1 para subir una foto, procesarla y añadir su precio.",
                text_color="#A0AEC0",
            ).pack(pady=24)
            return

        for idx, item in enumerate(self.catalog_items, start=1):
            card = ctk.CTkFrame(self.items_scroll, border_width=1, border_color="#2D3748")
            card.pack(fill="x", padx=4, pady=5)

            info_col = ctk.CTkFrame(card, fg_color="transparent")
            info_col.pack(side="left", fill="both", expand=True, padx=10, pady=8)

            ctk.CTkLabel(
                info_col,
                text=f"{idx}. {item.name}  [{item.sku}]  —  {item.category}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#F6E05E",
            ).pack(anchor="w")

            price_str = "  |  ".join(item.format_pricing_lines("es"))
            ctk.CTkLabel(
                info_col,
                text=f"💲 {price_str}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#68D391",
            ).pack(anchor="w", pady=(2, 2))

            if getattr(item, "specifications", None):
                specs_summary = "  •  ".join(f"{k}: {v}" for k, v in list(item.specifications.items())[:3])
                ctk.CTkLabel(
                    info_col,
                    text=f"📋 Specs ({len(item.specifications)}): {specs_summary}...",
                    font=ctk.CTkFont(size=10.5),
                    text_color="#A0AEC0",
                ).pack(anchor="w", pady=(1, 2))

            desc_preview = (item.description_es or item.description_en)[:140]
            if desc_preview:
                ctk.CTkLabel(
                    info_col,
                    text=desc_preview + ("..." if len(desc_preview) == 140 else ""),
                    font=ctk.CTkFont(size=11),
                    text_color="#CBD5E0",
                ).pack(anchor="w")

            action_box = ctk.CTkFrame(card, fg_color="transparent")
            action_box.pack(side="right", padx=10, pady=10)

            ctk.CTkButton(
                action_box,
                text="✏️ Editar",
                fg_color="#2B6CB0",
                hover_color="#2C5282",
                width=85,
                command=lambda it=item: self.load_product_into_editor(it),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                action_box,
                text="🗑️ Eliminar",
                fg_color="#C53030",
                hover_color="#9B2C2C",
                width=85,
                command=lambda sku=item.sku: self.on_delete_item(sku),
            ).pack(side="left")

    def on_delete_item(self, sku: str) -> None:
        self.catalog_items = [x for x in self.catalog_items if x.sku != sku]
        save_catalog_items(self.catalog_items)
        self._refresh_catalog_list_ui()

    def on_save_header_settings(self) -> None:
        self.company_header.company_name = self.hdr_company_entry.get().strip() or "NJ Fence and Railing"
        self.company_header.catalog_title = self.hdr_title_entry.get().strip()
        self.company_header.subtitle = self.hdr_sub_entry.get().strip()
        self.company_header.phone = self.hdr_phone_entry.get().strip()
        self.company_header.email = self.hdr_email_entry.get().strip()
        self.company_header.location = self.hdr_loc_entry.get().strip()
        self.company_header.language_mode = self.hdr_lang_var.get()
        save_company_header(self.company_header)
        messagebox.showinfo("Encabezado guardado", "Los datos de NJ Fence and Railing se han actualizado.")

    def on_export_pdf(self) -> None:
        if not self.catalog_items:
            messagebox.showwarning(
                "Catálogo vacío",
                "Añade al menos un producto al catálogo antes de generar el PDF.",
            )
            return

        self.on_save_header_settings()
        default_filename = f"NJ_Fence_and_Railing_Catalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        out_file = filedialog.asksaveasfilename(
            title="Guardar Catálogo PDF de NJ Fence and Railing",
            initialdir=str(OUTPUT_PDF_DIR),
            initialfile=default_filename,
            defaultextension=".pdf",
            filetypes=[("Archivo PDF", "*.pdf")],
        )
        if not out_file:
            return

        try:
            self.last_generated_pdf = generate_catalog_pdf(
                self.catalog_items,
                self.company_header,
                Path(out_file),
            )
            if messagebox.askyesno(
                "Catálogo PDF Generado",
                f"Catálogo PDF generado correctamente en:\n{self.last_generated_pdf}\n\n¿Deseas abrir el PDF ahora?",
            ):
                self.on_open_last_pdf()
        except Exception as exc:
            messagebox.showerror("Error al generar PDF", str(exc))

    def on_open_last_pdf(self) -> None:
        target = self.last_generated_pdf
        if not target or not target.exists():
            pdfs = sorted(OUTPUT_PDF_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
            if pdfs:
                target = pdfs[0]
        if target and target.exists():
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            messagebox.showinfo("Sin PDF reciente", "Aún no se ha generado ningún catálogo PDF.")

    def on_copy_flow_prompt(self) -> None:
        prompt_txt = self.txt_flow_prompt.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(prompt_txt)
        messagebox.showinfo(
            "Prompt copiado",
            "El prompt para Google Flow fue copiado al portapapeles. Pega este texto en Google Flow.",
        )

    def on_generate_imagen_api(self) -> None:
        prompt_txt = self.txt_flow_prompt.get("1.0", "end").strip()
        out_path = RAW_PHOTOS_DIR / f"imagen3_{datetime.now().strftime('%H%M%S')}.png"
        try:
            generated = generate_image_via_official_genai_api(prompt_txt, out_path)
            self._load_direct_photo(generated)
            self.tabview.set("1. Subir Foto, Procesar Fondo Blanco y Precios")
            messagebox.showinfo("Imagen generada", f"Imagen generada con Imagen 3 y procesada:\n{generated}")
        except Exception as exc:
            messagebox.showwarning("Integración Imagen 3 API", str(exc))

    def on_save_api_key(self) -> None:
        raw_key = self.entry_api_key.get().strip()
        if not raw_key:
            messagebox.showwarning("Clave vacía", "Pega tu GEMINI_API_KEY (empieza por AIzaSy...) antes de guardar.")
            return
        try:
            env_file = save_gemini_api_key_to_env(raw_key)
            self.entry_api_key.delete(0, "end")
            self._refresh_integrations_report_ui()
            self.ai_status_lbl.configure(
                text="✅ GEMINI_API_KEY guardada en .env. Análisis instantáneo (1-2s) activado.",
                text_color="#68D391",
            )
            messagebox.showinfo(
                "API Key Guardada",
                f"Tu GEMINI_API_KEY se guardó de forma segura en:\n{env_file}\n\n(Este archivo está en .gitignore y nunca se sube a GitHub).",
            )
        except Exception as exc:
            messagebox.showerror("Error al guardar API Key", str(exc))

    def _refresh_integrations_report_ui(self) -> None:
        for child in self.integrations_container.winfo_children():
            child.destroy()

        statuses = check_all_google_integrations()
        for st in statuses:
            border_col = "#38A169" if st.is_working else "#D69E2E"
            card = ctk.CTkFrame(self.integrations_container, border_width=1, border_color=border_col)
            card.pack(fill="x", padx=4, pady=6)

            ctk.CTkLabel(
                card,
                text=st.service_name,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#F6E05E",
            ).pack(anchor="w", padx=10, pady=(8, 2))

            ctk.CTkLabel(
                card,
                text=f"Estado: {st.status_label}  |  Autenticación: {st.auth_status}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#68D391" if st.is_working else "#FBD38D",
                wraplength=560,
                justify="left",
            ).pack(anchor="w", padx=10, pady=1)

            ctk.CTkLabel(
                card,
                text=f"Autorización: {st.how_to_authorize}",
                font=ctk.CTkFont(size=11),
                text_color="#E2E8F0",
                wraplength=560,
                justify="left",
            ).pack(anchor="w", padx=10, pady=2)

            ctk.CTkLabel(
                card,
                text=f"Costes: {st.cost_explanation}",
                font=ctk.CTkFont(size=11),
                text_color="#CBD5E0",
                wraplength=560,
                justify="left",
            ).pack(anchor="w", padx=10, pady=(2, 8))


def launch_desktop_app() -> None:
    app = NJFenceCatalogApp()
    app.mainloop()
