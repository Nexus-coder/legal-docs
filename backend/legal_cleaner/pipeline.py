"""
pipeline.py – High-level orchestration for the extract → clean → write workflow.

This module wires together the ``extractor`` and ``cleaner`` modules and
adds file-system I/O (reading source PDFs, writing cleaned ``.txt`` files).

Public API
----------
- ``process_pdf(pdf_path, output_dir)``  → ``Path`` of the written file
- ``process_batch(sources_dir, output_dir)`` → ``list[Path]``
"""

from __future__ import annotations

import logging
from pathlib import Path

from legal_cleaner.extractor import extract_text
from legal_cleaner.cleaner import clean_legal_text

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def process_pdf(pdf_path: Path | str, output_dir: Path | str) -> Path:
    """
    Run the full cleaning pipeline on a single PDF.

    Steps
    -----
    1. **Extract** raw text from *pdf_path* (PyMuPDF → pdfplumber fallback).
    2. **Clean** the raw text through the regex pipeline.
    3. **Write** the cleaned result to ``<output_dir>/<stem>_cleaned.txt``.

    Parameters
    ----------
    pdf_path : Path | str
        Path to the source PDF.
    output_dir : Path | str
        Directory where the cleaned ``.txt`` will be saved.

    Returns
    -------
    Path
        Absolute path to the written cleaned file.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    logger.info("📄  Processing: %s", pdf_path.name)

    # 1 – Extract
    raw_text = extract_text(pdf_path)
    logger.debug("   raw characters: %d", len(raw_text))

    # 2 – Clean
    cleaned_text = clean_legal_text(raw_text)
    logger.debug("   cleaned characters: %d", len(cleaned_text))

    # 3 – Write
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{pdf_path.stem}_cleaned.txt"
    out_file.write_text(cleaned_text, encoding="utf-8")

    reduction = (1 - len(cleaned_text) / max(len(raw_text), 1)) * 100
    logger.info(
        "✅  Saved: %s  (%d → %d chars, %.0f%% reduction)",
        out_file.name, len(raw_text), len(cleaned_text), reduction,
    )
    return out_file


def process_batch(
    sources_dir: Path | str,
    output_dir: Path | str,
) -> list[Path]:
    """
    Process every ``.pdf`` file found in *sources_dir*.

    Parameters
    ----------
    sources_dir : Path | str
        Directory to scan for PDF files.
    output_dir : Path | str
        Directory where cleaned outputs are written.

    Returns
    -------
    list[Path]
        Paths to all successfully written output files.
    """
    sources_dir = Path(sources_dir)
    output_dir = Path(output_dir)

    pdfs = sorted(sources_dir.glob("*.pdf"))
    if not pdfs:
        logger.warning("No PDFs found in %s", sources_dir)
        return []

    logger.info("Found %d PDF(s) in %s", len(pdfs), sources_dir)

    results: list[Path] = []
    for pdf in pdfs:
        try:
            out = process_pdf(pdf, output_dir)
            results.append(out)
        except Exception:
            logger.exception("❌  Failed to process %s", pdf.name)

    logger.info("🏁  Done – %d/%d cleaned → %s/", len(results), len(pdfs), output_dir)
    return results
