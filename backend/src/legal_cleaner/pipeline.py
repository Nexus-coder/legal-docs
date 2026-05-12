"""
pipeline.py – High-level orchestration for the extract → clean → write workflow.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.legal_cleaner.extractor import extract_text
from src.legal_cleaner.cleaner import clean_legal_text

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════


def process_pdf(pdf_path: Path | str, output_dir: Path | str) -> Path:
    """
    Run the full cleaning pipeline on a single PDF.
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
        out_file.name,
        len(raw_text),
        len(cleaned_text),
        reduction,
    )
    return out_file


def process_batch(
    sources_dir: Path | str,
    output_dir: Path | str,
) -> list[Path]:
    """
    Process every ``.pdf`` file found in *sources_dir*.
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
