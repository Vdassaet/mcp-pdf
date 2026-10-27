"""
Local filesystem & JSON storage manager for NJ Fence and Railing Catalog Studio.
Operates 100% locally on the user's PC, completely independent of the website.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List

from src.models import CompanyHeader, ProductItem


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_PHOTOS_DIR = DATA_DIR / "photos_raw"
WHITE_PHOTOS_DIR = DATA_DIR / "photos_white"
OUTPUT_PDF_DIR = BASE_DIR / "output" / "catalogs"

CATALOG_JSON_PATH = DATA_DIR / "catalog_items.json"
COMPANY_JSON_PATH = DATA_DIR / "company_header.json"


def ensure_directories() -> None:
    """Ensure all local application directories exist."""
    for d in (DATA_DIR, RAW_PHOTOS_DIR, WHITE_PHOTOS_DIR, OUTPUT_PDF_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_catalog_items() -> List[ProductItem]:
    """Load saved catalog items from local JSON storage."""
    ensure_directories()
    if not CATALOG_JSON_PATH.exists():
        return []
    try:
        raw = json.loads(CATALOG_JSON_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [ProductItem.from_dict(item) for item in raw]
    except Exception:
        pass
    return []


def get_next_sku(items: List[ProductItem], prefix: str = "RS-") -> str:
    """
    Compute the next sequential SKU starting with prefix.
    If 'RS-1' exists, returns 'RS-2', etc.
    """
    import re
    max_num = 0
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    for it in items:
        sku = (it.sku or "").strip()
        m = pattern.match(sku)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return f"{prefix}{max_num + 1}"


def save_catalog_items(items: List[ProductItem]) -> None:
    """Persist catalog items to local JSON storage."""
    ensure_directories()
    payload = [item.to_dict() for item in items]
    CATALOG_JSON_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_company_header() -> CompanyHeader:
    """Load saved company header configuration or return default NJ Fence and Railing header."""
    ensure_directories()
    if COMPANY_JSON_PATH.exists():
        try:
            data = json.loads(COMPANY_JSON_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                valid_keys = {f.name for f in CompanyHeader.__dataclass_fields__.values()}  # type: ignore
                filtered = {k: v for k, v in data.items() if k in valid_keys}
                return CompanyHeader(**filtered)
        except Exception:
            pass
    return CompanyHeader()


def save_company_header(header: CompanyHeader) -> None:
    """Save company header configuration locally."""
    ensure_directories()
    COMPANY_JSON_PATH.write_text(
        json.dumps(header.__dict__, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def copy_raw_photo_to_workspace(source_path: str | Path, item_id: str) -> Path:
    """Copy a user-selected photograph into `data/photos_raw/`."""
    ensure_directories()
    src = Path(source_path).resolve()
    ext = src.suffix.lower() or ".jpg"
    dest = RAW_PHOTOS_DIR / f"{item_id}_raw{ext}"
    if src != dest.resolve():
        shutil.copy2(src, dest)
    return dest
