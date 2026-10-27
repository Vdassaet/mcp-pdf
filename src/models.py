"""
Data models for NJ Fence and Railing Desktop Catalog Generator.
Enforces strict pricing rules: NEVER invent or auto-generate prices.
Only exact numbers entered by the user are stored and printed in PDF catalogs.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class PricingMode(str, Enum):
    """Allowed pricing modalities for NJ Fence and Railing products."""
    PER_LINEAR_FOOT = "per_linear_foot"  # Precio por pie lineal ($ / LF)
    PER_KIT = "per_kit"                  # Precio por kit completo ($ / Kit)
    BOTH = "both"                        # Ambos (Pie lineal + Kit)
    QUOTE_ONLY = "quote_only"            # Sin cifra / Cotización bajo pedido


def parse_user_price(raw_input: Optional[str]) -> Optional[float]:
    """
    Strictly parse a price entered manually by the user.
    Returns None if empty. Raises ValueError if invalid or negative.
    NEVER invents or guesses a number.
    """
    if raw_input is None:
        return None
    cleaned = str(raw_input).strip()
    if not cleaned:
        return None
    # Remove currency symbol and thousand separators if user typed "$1,250.50"
    cleaned = cleaned.replace("$", "").replace(",", "").strip()
    if not re.match(r"^\d+(\.\d{1,2})?$", cleaned):
        raise ValueError(
            f"Valor de precio inválido '{raw_input}'. Introduce únicamente cifras reales (ej. 45.00 o 320.50)."
        )
    value = float(cleaned)
    if value <= 0:
        raise ValueError("El precio debe ser mayor que 0.")
    return round(value, 2)


@dataclass
class ProductItem:
    """Represents a single railing, fence, or gate item in the catalog."""
    id: str = field(default_factory=lambda: f"NJF-{uuid.uuid4().hex[:6].upper()}")
    sku: str = ""
    name: str = ""
    category: str = "Aluminum Railing"
    material: str = ""
    finish_color: str = ""
    description_es: str = ""
    description_en: str = ""
    features: List[str] = field(default_factory=list)

    # Strict User-Entered Pricing (Never invented by AI)
    pricing_mode: str = PricingMode.PER_LINEAR_FOOT.value
    price_per_linear_ft: Optional[float] = None
    price_per_kit: Optional[float] = None
    kit_includes_note: str = ""

    # Image Paths
    original_image_path: str = ""
    white_bg_image_path: str = ""
    bg_processing_mode: str = "auto_isolate_white"

    # Metadata
    ai_source: str = "manual"
    flow_prompt_suggestion: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    def __post_init__(self) -> None:
        if not self.sku:
            self.sku = self.id

    def format_pricing_lines(self, lang: str = "es") -> List[str]:
        """
        Format the exact user-provided prices for display and PDF rendering.
        Never invents numbers; if a price was not entered by the user, shows 'Consultar / Upon Request'.
        """
        lines: List[str] = []
        mode = self.pricing_mode

        has_lf = self.price_per_linear_ft is not None and self.price_per_linear_ft > 0
        has_kit = self.price_per_kit is not None and self.price_per_kit > 0

        if mode in (PricingMode.PER_LINEAR_FOOT.value, PricingMode.BOTH.value) and has_lf:
            if lang == "en":
                lines.append(f"${self.price_per_linear_ft:,.2f} USD / Linear Foot (LF)")
            else:
                lines.append(f"${self.price_per_linear_ft:,.2f} USD / Pie Lineal (LF)")

        if mode in (PricingMode.PER_KIT.value, PricingMode.BOTH.value) and has_kit:
            if lang == "en":
                lines.append(f"${self.price_per_kit:,.2f} USD / Complete Kit")
            else:
                lines.append(f"${self.price_per_kit:,.2f} USD / Por Kit")

        if not lines:
            if lang == "en":
                lines.append("Price Upon Request (No price specified)")
            else:
                lines.append("Precio bajo cotización (Sin cifra asignada)")

        if self.kit_includes_note.strip():
            lines.append(f"Nota: {self.kit_includes_note.strip()}")

        return lines

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductItem":
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class CompanyHeader:
    """Header & contact details for NJ Fence and Railing PDF catalogs (independent of website)."""
    company_name: str = "NJ Fence and Railing"
    catalog_title: str = "Catálogo Oficial de Barandillas y Cercas / Product & Pricing Catalog"
    subtitle: str = "Fabricación e Instalación Profesional — New Jersey & New York"
    phone: str = "(973) 555-0199"
    email: str = "sales@njfenceandrailing.com"
    location: str = "New Jersey & New York Metro Area"
    footer_disclaimer: str = (
        "Precios exactos en USD por Pie Lineal (LF) o por Kit según modelo. "
        "Impuestos e instalación se cotizan según medidas del proyecto."
    )
    language_mode: str = "bilingual"  # "es", "en", or "bilingual"
