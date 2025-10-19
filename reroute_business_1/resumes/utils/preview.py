from __future__ import annotations

import io
import os
from typing import Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string

from PIL import Image, ImageDraw, ImageFont

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover - optional dependency
    fitz = None


THUMB_WIDTH = 240
THUMB_HEIGHT = 320


def _placeholder_png(title: str = "Resume") -> bytes:
    img = Image.new("RGB", (THUMB_WIDTH, THUMB_HEIGHT), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)
    # Border
    draw.rounded_rectangle([(8, 8), (THUMB_WIDTH - 8, THUMB_HEIGHT - 8)], radius=12, outline=(220, 224, 229), width=2)
    # Icon (simple page)
    draw.rectangle([(64, 42), (176, 230)], fill=(245, 245, 245), outline=(220, 224, 229))
    # Fold corner
    draw.polygon([(176, 42), (156, 42), (176, 62)], fill=(235, 235, 235), outline=(220, 224, 229))
    # Lines
    for i, y in enumerate(range(72, 200, 18)):
        x2 = 168 if i % 2 == 0 else 150
        draw.line([(74, y), (x2, y)], fill=(180, 186, 194), width=2)

    # Title text
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    tw, th = draw.textbbox((0, 0), title, font=font)[2:]
    draw.text(((THUMB_WIDTH - tw) / 2, THUMB_HEIGHT - th - 16), title, fill=(55, 65, 81), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _save_png_bytes(prefix: str, data: bytes) -> str:
    name = f"resumes/previews/{prefix}_{get_random_string(8)}.png"
    default_storage.save(name, ContentFile(data))
    return name


def _pdf_first_page_to_png(path: str) -> Optional[bytes]:
    if not fitz:
        return None
    try:
        doc = fitz.open(path)
        if doc.page_count == 0:
            return None
        page = doc.load_page(0)
        # Render at higher zoom for clarity, then downscale
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img.thumbnail((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


def generate_resume_preview(resume) -> Optional[str]:
    """
    Generate and attach a small PNG preview for the given Resume.
    Returns the storage path of the preview, or None on failure.
    """
    # If already has a preview and file didn't change, keep it
    file_field = getattr(resume, "file", None)
    file_path = None
    if file_field and getattr(file_field, "name", None):
        try:
            file_path = file_field.path  # type: ignore[attr-defined]
        except Exception:
            # Storage may not be local; try URL-based placeholder
            file_path = None

    png_bytes: Optional[bytes] = None

    if file_path and file_path.lower().endswith(".pdf"):
        png_bytes = _pdf_first_page_to_png(file_path)

    if not png_bytes:
        # Fallback placeholder
        title = "Imported" if getattr(resume, "is_imported", False) else "Resume"
        png_bytes = _placeholder_png(title)

    # Save to storage and update model
    try:
        storage_path = _save_png_bytes(prefix=f"resume_{resume.pk}", data=png_bytes)
        # Clean old preview if any
        old = getattr(resume, "preview_image", None)
        if old and getattr(old, "name", None) and default_storage.exists(old.name):
            try:
                default_storage.delete(old.name)
            except Exception:
                pass
        resume.preview_image.name = storage_path
        resume.save(update_fields=["preview_image"])
        return storage_path
    except Exception:
        return None

