"""
legal_cleaner – A pipeline for cleaning Kenyan legal PDF text before RAG ingestion.

Modules
-------
config      : Centralised settings loaded from environment / .env file.
extractor   : PDF → raw-text extraction (PyMuPDF + pdfplumber fallback).
cleaner     : Regex-based cleaning passes that strip noise from raw legal text.
pipeline    : Orchestrates extract → clean → write for individual PDFs.

Quick Start
-----------
    from legal_cleaner.pipeline import process_pdf
    from pathlib import Path

    process_pdf(Path("sources/my_doc.pdf"), Path("cleaned"))
"""

from legal_cleaner.cleaner import clean_legal_text
from legal_cleaner.extractor import extract_text
from legal_cleaner.pipeline import process_pdf

__all__ = ["clean_legal_text", "extract_text", "process_pdf"]
