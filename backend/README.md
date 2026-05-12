# Legal Text Cleaner

A Python pipeline for cleaning Kenyan legal PDF sources (eKLR judgments, Laws of Kenya statutes) before ingesting them into a **RAG pipeline**.

---

## Project Structure

```
backend/
├── src/                        ← FastAPI Domain-based application
│   ├── main.py                 ← API Entrypoint
│   ├── config.py               ← pydantic-settings configuration
│   ├── database.py             ← SQLAlchemy session management
│   ├── matters/                ← Matters Domain
│   ├── drafting/               ← Drafting Domain
│   └── ...
├── scripts/                    ← Utility scripts
│   ├── run_cleaner.py          ← Clean raw PDFs into .txt
│   └── run_ingestion.py        ← Ingest .txt into Pinecone (RAG)
├── legal_cleaner/              ← PDF Extraction & Cleaning Package
├── legal_rag/                  ← RAG Ingestion Package
├── sources/                    ← Drop raw PDF files here
├── cleaned/                    ← Cleaned .txt output
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

| Variable              | Default    | Description                                   |
|-----------------------|------------|-----------------------------------------------|
| `SOURCES_DIR`         | `sources`  | Directory containing raw source PDFs          |
| `OUTPUT_DIR`          | `cleaned`  | Directory where cleaned `.txt` files go       |
| `LOG_LEVEL`           | `INFO`     | Logging verbosity                             |
| `OPENAI_API_KEY`      | None       | **Required** for RAG embeddings               |
| `PINECONE_API_KEY`    | None       | **Required** for vector upload                |
| `PINECONE_INDEX_NAME` | None       | **Required** target Pinecone index name       |
| `CHUNK_SIZE`          | `1500`     | RAG text splitter max chunk size              |
| `CHUNK_OVERLAP`       | `150`      | RAG text splitter chunk overlap               |

---

## Usage

### Batch Mode (default)

Process every `.pdf` in `sources/`:

```bash
python scripts/run_cleaner.py
```

### Single File

```bash
python scripts/run_cleaner.py --file sources/my_document.pdf
```

### Custom Directories

```bash
python scripts/run_cleaner.py --sources-dir /data/pdfs --output-dir /data/clean
```

### RAG Ingestion (Pinecone)

Once you have your cleaned `.txt` files in `cleaned/`, run the ingestion pipeline. **Ensure your API keys are set in `.env`**.

```bash
# Dry-run (chunks text without uploading to Pinecone)
python scripts/run_ingestion.py --dry-run

# Ingest all cleaned text
python scripts/run_ingestion.py

# Ingest a single file
python scripts/run_ingestion.py --file cleaned/my_document.txt
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
