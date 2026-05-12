"""
cleaner.py – Regex-based cleaning passes for Kenyan legal text.

This module contains a curated set of compiled regular expressions that
target the specific noise patterns found in **eKLR court judgments** and
**Laws-of-Kenya legislation PDFs**.  Each category of noise is isolated
in its own section so that individual passes can be toggled or extended
without touching unrelated logic.

Noise Categories
----------------
1. **URLs & hyperlinks** – e.g. ``http://www.kenyalaw.org``
2. **Page numbers & running headers/footers** – ``Page 3 of 14``, ``– 3 –``
3. **eKLR boilerplate** – ``Kenya Law Reports``, ``National Council for Law Reporting``
4. **Case-number stamps** – ``ELC Case No. 123 of 2022`` (repeated per page)
5. **Legislation headers** – ``Rev. Edition 2009``, ``Cap. 21``, ``Laws of Kenya``
6. **Invisible Unicode artefacts** – zero-width spaces, BOMs, soft hyphens

Public API
----------
- ``clean_legal_text(raw_text)`` → ``str``
"""

from __future__ import annotations

import re
import unicodedata


# ──────────────────────────────────────────────────────────────────────
# 1.  URLs & hyperlinks
# ──────────────────────────────────────────────────────────────────────

_URL_RE = re.compile(r"https?://(?:[a-zA-Z0-9]|[$\-_@.&+!*(),]|%[0-9a-fA-F]{2})+")

# ──────────────────────────────────────────────────────────────────────
# 2.  Page numbers & running headers / footers
# ──────────────────────────────────────────────────────────────────────

_PAGE_NUMBER_RES: list[re.Pattern[str]] = [
    re.compile(r"Page\s+\d+\s+of\s+\d+", re.IGNORECASE),
    re.compile(r"Page\s+\d+/\d+", re.IGNORECASE),
    re.compile(r"[-–—]\s*\d+\s*[-–—]"),  # centred: – 3 –
    re.compile(r"^\s*\d{1,4}\s*$", re.MULTILINE),  # lone page numbers on their own line
]

# ──────────────────────────────────────────────────────────────────────
# 3.  eKLR boilerplate
# ──────────────────────────────────────────────────────────────────────

_EKLR_HEADER_RE = re.compile(
    r"(?i)(?:Kenya\s+Law\s+Reports?|eKLR|"
    r"National\s+Council\s+for\s+Law\s+Reporting|"
    r"www\.kenyalaw\.org)",
)

# ──────────────────────────────────────────────────────────────────────
# 4.  Case-number stamps (repeated on every page of a judgment)
# ──────────────────────────────────────────────────────────────────────

_CASE_NUMBER_RE = re.compile(
    r"(?i)"
    r"(?:Civil\s+Appeal|Criminal\s+Appeal|ELC\s+Case|"
    r"Misc(?:ellaneous)?\.?\s*(?:Civil\s+)?App(?:lication)?|"
    r"Petition|Constitutional\s+Petition|"
    r"Judicial\s+Review|Succession\s+Cause|"
    r"Environment\s+&?\s*Land\s+Case|"
    r"ELCR?\s+Case|High\s+Court\s+Case|"
    r"Anti[\s-]?Corruption\s+Case)\s*"
    r"No\.?\s*\d+\s+of\s+\d{4}"
)

# ──────────────────────────────────────────────────────────────────────
# 5.  Legislation headers (Laws of Kenya publications)
# ──────────────────────────────────────────────────────────────────────

_LEGISLATION_HEADER_RE = re.compile(
    r"(?i)"
    r"(?:Rev(?:ised)?\s+Edition\s+\d{4}|"
    r"\[Issue\s+\d+\]|"
    r"Subsidiary\s+Legislation|"
    r"Laws\s+of\s+Kenya|"
    r"Cap\.?\s*\d+)",
)

# ──────────────────────────────────────────────────────────────────────
# 6.  Invisible Unicode artefacts from PDF extraction
# ──────────────────────────────────────────────────────────────────────

_INVISIBLE_CHARS: set[str] = {
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\u00ad",  # soft hyphen
    "\ufeff",  # BOM / zero-width no-break space
    "\u2060",  # word joiner
    "\u00a0",  # non-breaking space  → replaced with normal space below
}


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════


def clean_legal_text(raw_text: str) -> str:
    """
    Apply all cleaning passes to *raw_text* and return the result.

    The pipeline runs in a fixed order so that earlier passes (e.g. URL
    removal) do not interfere with later ones (e.g. whitespace collapse).

    Parameters
    ----------
    raw_text : str
        The unprocessed text extracted from a legal PDF.

    Returns
    -------
    str
        Cleaned text with noise removed and whitespace normalised.

    Pipeline Steps
    --------------
    1. Strip URLs
    2. Strip page numbers & running headers / footers
    3. Strip eKLR boilerplate
    4. Strip repeated case-number stamps
    5. Strip legislation-publication headers
    6. Remove invisible / artefact Unicode characters
    7. NFC Unicode normalisation
    8. Collapse excessive whitespace & blank lines
    """
    text = raw_text

    # 1 – URLs
    text = _URL_RE.sub("", text)

    # 2 – Page numbers & headers
    for pat in _PAGE_NUMBER_RES:
        text = pat.sub("", text)

    # 3 – eKLR boilerplate
    text = _EKLR_HEADER_RE.sub("", text)

    # 4 – Repeated case numbers
    text = _CASE_NUMBER_RE.sub("", text)

    # 5 – Legislation headers
    text = _LEGISLATION_HEADER_RE.sub("", text)

    # 6 – Invisible / artefact characters
    for ch in _INVISIBLE_CHARS:
        if ch == "\u00a0":
            text = text.replace(ch, " ")  # NBSP → normal space
        else:
            text = text.replace(ch, "")

    # 7 – Unicode normalisation (compose diacritics, etc.)
    text = unicodedata.normalize("NFC", text)

    # 8 – Whitespace normalisation
    text = re.sub(r"[ \t]+", " ", text)  # horizontal runs → single space
    text = re.sub(r"\n{3,}", "\n\n", text)  # 3+ newlines → paragraph break
    text = "\n".join(line.strip() for line in text.splitlines())

    return text.strip()
