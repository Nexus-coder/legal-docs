# Legal Text Cleaner

A Python pipeline for cleaning Kenyan legal PDF sources (eKLR judgments, Laws of Kenya statutes) before ingesting them into a **RAG pipeline**.

---

## Project Structure

```
backend/
├── run_cleaner.py              ← CLI entry-point (thin wrapper)
├── legal_cleaner/              ← Core package
│   ├── __init__.py             ← Public API re-exports
│   ├── config.py               ← Settings & logging (reads .env)
│   ├── extractor.py            ← PDF → raw text (PyMuPDF + pdfplumber)
│   ├── cleaner.py              ← Regex cleaning passes
│   └── pipeline.py             ← Orchestration: extract → clean → write
├── sources/                    ← Drop raw PDF files here
├── cleaned/                    ← Cleaned .txt output (auto-created)
├── requirements.txt
├── .env / .env.example
└── .gitignore
```

---

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and customise environment variables
cp .env.example .env
```

### Environment Variables

| Variable       | Default    | Description                                   |
|----------------|------------|-----------------------------------------------|
| `SOURCES_DIR`  | `sources`  | Directory containing raw source PDFs          |
| `OUTPUT_DIR`   | `cleaned`  | Directory where cleaned `.txt` files go       |
| `LOG_LEVEL`    | `INFO`     | Logging verbosity (`DEBUG`, `INFO`, `WARNING`) |

---

## Usage

### Batch Mode (default)

Process every `.pdf` in `sources/`:

```bash
python run_cleaner.py
```

### Single File

```bash
python run_cleaner.py --file sources/my_document.pdf
```

### Custom Directories

```bash
python run_cleaner.py --sources-dir /data/pdfs --output-dir /data/clean
```

### Programmatic Usage

```python
from legal_cleaner import process_pdf
from pathlib import Path

process_pdf(Path("sources/my_doc.pdf"), Path("cleaned"))
```

Or use individual components:

```python
from legal_cleaner import extract_text, clean_legal_text

raw = extract_text("sources/my_doc.pdf")
clean = clean_legal_text(raw)
```

---

## Cleaning Pipeline

The cleaner applies **8 sequential passes** in `legal_cleaner/cleaner.py`:

| # | Pass                          | Example noise removed                              |
|---|-------------------------------|-----------------------------------------------------|
| 1 | Strip URLs                    | `http://www.kenyalaw.org`                           |
| 2 | Strip page numbers            | `Page 3 of 14`, `– 3 –`, lone `42`                 |
| 3 | Strip eKLR boilerplate        | `Kenya Law Reports`, `National Council for Law Reporting` |
| 4 | Strip case-number stamps      | `ELC Case No. 123 of 2022`                         |
| 5 | Strip legislation headers     | `Rev. Edition 2009`, `Cap. 21`, `Laws of Kenya`    |
| 6 | Remove invisible Unicode      | Zero-width spaces, BOMs, soft hyphens               |
| 7 | NFC Unicode normalisation     | Compose diacritics, canonical ordering              |
| 8 | Collapse whitespace           | Multiple spaces → 1, 3+ newlines → paragraph break |

---

## Extraction Strategy

`legal_cleaner/extractor.py` uses a two-backend approach:

1. **PyMuPDF** (`fitz`) — fast, C-based, handles most standard PDFs.
2. **pdfplumber** — automatic fallback when PyMuPDF yields very little text (scanned pages, unusual font encodings).

The quality gate checks average characters per page; if below threshold, pdfplumber is used instead.
