"""
config.py – Centralised configuration for the legal-cleaner pipeline.

All runtime settings are loaded from environment variables (with sensible
defaults) so that the rest of the codebase never touches ``os.getenv``
directly.  A ``.env`` file in the project root is loaded automatically
via ``python-dotenv``.

Environment Variables
---------------------
SOURCES_DIR : str
    Directory that contains the raw source PDFs.  Default: ``sources``.
OUTPUT_DIR  : str
    Directory where cleaned ``.txt`` files are written.  Default: ``cleaned``.
LOG_LEVEL   : str
    Python log level name (DEBUG, INFO, WARNING, ERROR).  Default: ``INFO``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from the project root (backend/) ──────────────────────
load_dotenv()

# ── Settings ─────────────────────────────────────────────────────────

SOURCES_DIR: Path = Path(os.getenv("SOURCES_DIR", "data/sources"))
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "data/cleaned"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

# ── Logging bootstrap ────────────────────────────────────────────────

def setup_logging() -> None:
    """
    Configure the root logger once.

    Call this at application startup (e.g. in ``run_cleaner.py``).
    Subsequent calls are idempotent because ``basicConfig`` only
    applies when handlers have not been set.
    """
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
