"""
extractor.py – PDF → raw-text extraction.

Extraction Strategy
-------------------
1. **PyMuPDF** (``fitz``) is tried first.  It is native-C and fast,
   producing good results for the vast majority of text-layer PDFs.
2. If PyMuPDF returns suspiciously few characters per page (below
   ``_MIN_CHARS_PER_PAGE``), we fall back to **pdfplumber** which
   can handle trickier font encodings and CID-mapped glyphs.

Public API
----------
- ``extract_text(pdf_path)`` → ``str``
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz            # PyMuPDF
import pdfplumber

logger = logging.getLogger(__name__)

# If the average character count per page is below this value we assume
# PyMuPDF failed silently and retry with pdfplumber.
_MIN_CHARS_PER_PAGE: int = 50


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def extract_text(pdf_path: Path | str) -> str:
    """
    Extract all text from *pdf_path* and return it as a single string.

    Parameters
    ----------
    pdf_path : Path | str
        Filesystem path to the source PDF.

    Returns
    -------
    str
        The concatenated page texts separated by double newlines.

    Raises
    ------
    FileNotFoundError
        If *pdf_path* does not exist on disk.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    text = _extract_with_pymupdf(pdf_path)

    # Quick quality gate
    num_pages = _count_pages(pdf_path)
    if num_pages and len(text) / num_pages < _MIN_CHARS_PER_PAGE:
        logger.warning(
            "PyMuPDF returned very little text for '%s' "
            "(%d chars / %d pages) – falling back to pdfplumber",
            pdf_path.name, len(text), num_pages,
        )
        text = _extract_with_pdfplumber(pdf_path)

    return text


# ──────────────────────── Private Helpers ─────────────────────────────

def _extract_with_pymupdf(pdf_path: Path) -> str:
    """Use PyMuPDF's native text extraction (fast, C-based)."""
    pages: list[str] = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return "\n\n".join(pages)


def _extract_with_pdfplumber(pdf_path: Path) -> str:
    """Use pdfplumber for trickier PDFs with non-standard encodings."""
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
    return "\n\n".join(pages)


def _count_pages(pdf_path: Path) -> int:
    """Return the total number of pages in *pdf_path*."""
    with fitz.open(pdf_path) as doc:
        return len(doc)
