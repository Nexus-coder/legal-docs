# LegalDocs Backend

FastAPI server for the LegalDocs platform — domain-driven, async-first, and built around Kenyan legal data workflows.

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.136 · Pydantic v2 · pydantic-settings |
| Database | SQLAlchemy 2.0 (async) · SQLite via aiosqlite (dev) |
| Auth | PyJWT · passlib (bcrypt) |
| PII | OpenAI Privacy Filter (Hugging Face transformers) |
| RAG | LangChain · LangGraph · Pinecone · OpenAI embeddings |
| PDF Processing | PyMuPDF · pdfplumber |
| Linting | Ruff (replaces black + isort + flake8) |

---

## Project Structure

```text
backend/
├── src/                            ← Domain-driven application
│   ├── main.py                     ← FastAPI app + lifespan
│   ├── config.py                   ← Global BaseSettings
│   ├── database.py                 ← Async engine + session factory
│   ├── models.py                   ← Shared ORM Base + Pydantic base
│   ├── exceptions.py               ← Global exception classes
│   │
│   ├── auth/                       ← Authentication domain
│   │   ├── config.py               ← AuthConfig (JWT_SECRET, etc.)
│   │   ├── models.py               ← User ORM model
│   │   ├── schemas.py              ← UserCreate, UserRead, Token
│   │   ├── service.py              ← Password hashing, token creation
│   │   ├── dependencies.py         ← get_current_user (JWT validation)
│   │   └── router.py               ← /signup, /login, /me
│   │
│   ├── pii/                        ← PII detection & masking domain
│   │   ├── config.py               ← PiiConfig (model name, device, threshold)
│   │   ├── schemas.py              ← PiiEntity, DetectRequest, MaskResponse
│   │   ├── service.py              ← Privacy Filter pipeline (lazy-loaded)
│   │   └── router.py               ← /detect, /mask
│   │
│   ├── matters/                    ← Matter management domain
│   ├── drafting/                   ← AI-assisted drafting domain
│   ├── admin/                      ← Admin console domain
│   ├── agent/                      ← LangGraph agent orchestration
│   ├── ingestion/                  ← Document parsing & indexing
│   ├── legal_cleaner/              ← 8-pass PDF text cleaning
│   └── legal_rag/                  ← Pinecone vector ingestion
│
├── scripts/
│   ├── run_cleaner.py              ← Batch PDF → .txt cleaning
│   └── run_ingestion.py            ← .txt → Pinecone vector upload
│
├── requirements.txt
├── .env.example
├── .gitignore
└── AGENTS.md                       ← AI agent coding guidelines
```

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate            # Linux / macOS
.\venv\Scripts\activate              # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env                 # Then fill in your API keys

# 4. Start the server
uvicorn src.main:app --reload --port 8000
```

> **Auto-init**: When `ENVIRONMENT=local`, the server creates all SQLite tables and the `legal_docs.db` file on startup automatically.
> Local SQLite startup also backfills the matter workflow columns added for `workflow_state`, masked facts, draft content, verification timestamps, activity timeline, and citation evidence support.

---

## API Endpoints

Interactive Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Authentication (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/signup` | Register a new user |
| `POST` | `/login` | Get a JWT access token (OAuth2 form) |
| `GET` | `/me` | Get current authenticated user |

### PII Masking (`/api/pii`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/detect` | Detect PII entities for an authenticated user (returns spans + scores) |
| `POST` | `/mask` | Matter-scoped PII masking; persists raw facts, masked facts, metadata, and workflow state |

**Example — detect:**
```bash
curl -X POST http://localhost:8000/api/pii/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "My name is Alice Smith and my email is alice@lawfirm.co.ke"}'
```

**Response:**
```json
{
  "entities": [
    {"entity_type": "private_person", "text": "Alice Smith", "start": 11, "end": 22, "score": 0.9999},
    {"entity_type": "private_email", "text": "alice@lawfirm.co.ke", "start": 42, "end": 61, "score": 0.9999}
  ],
  "entity_count": 2
}
```

### Other Domains

| Prefix | Domain | Description |
|--------|--------|-------------|
| `/api/matters` | Matters | Legal case CRUD, ownership checks, state transitions, activity timeline, citation verification |
| `/api/drafting` | Drafting | Matter-scoped AI drafting from stored masked facts with safe error statuses |
| `/api/admin` | Admin | System administration |
| `/api/stats` | Dashboard | Aggregated statistics |

### Matter Workflow States

Matter transitions are restricted to `created` -> `facts_entered` -> `pii_masked` -> `draft_generated` -> `citations_verified` -> `export_ready`. The service rejects invalid jumps, duplicate transitions are idempotent, and callers may pass an expected state to detect stale clients. Drafting and PII routes require JWT auth and verify that the selected matter belongs to the current user.

---

## Environment Variables

### Global (`src/config.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `local` | `local` · `staging` · `production` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./legal_docs.db` | Async database connection string |
| `OPENAI_API_KEY` | — | **Required** for RAG embeddings |
| `PINECONE_API_KEY` | — | **Required** for vector storage |
| `PINECONE_INDEX_NAME` | `legal-docs` | Pinecone index name |
| `CHUNK_SIZE` | `1500` | RAG text splitter chunk size |
| `CHUNK_OVERLAP` | `150` | RAG text splitter overlap |
| `SOURCES_DIR` | `sources` | Raw PDF input directory |
| `OUTPUT_DIR` | `cleaned` | Cleaned .txt output directory |

### Auth (`src/auth/config.py` — prefix `AUTH_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_JWT_SECRET` | `super-secret-dev-key` | JWT signing secret (**change in production**) |
| `AUTH_JWT_ALG` | `HS256` | JWT signing algorithm |
| `AUTH_JWT_EXP_MINUTES` | `1440` | Token expiration (24 hours) |

### PII (`src/pii/config.py` — prefix `PII_`)

| Variable | Default | Description |
|----------|---------|-------------|
| `PII_MODEL_NAME` | `openai/privacy-filter` | Hugging Face model identifier |
| `PII_DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `PII_CONFIDENCE_THRESHOLD` | `0.5` | Minimum confidence to report an entity |

---

## Data Processing Scripts

### PDF Cleaning

```bash
# Batch — process all PDFs in sources/
python scripts/run_cleaner.py

# Single file
python scripts/run_cleaner.py --file sources/my_document.pdf

# Custom directories
python scripts/run_cleaner.py --sources-dir /data/pdfs --output-dir /data/clean
```

The cleaner applies **8 sequential passes**:

| # | Pass | Example noise removed |
|---|------|-----------------------|
| 1 | Strip URLs | `http://www.kenyalaw.org` |
| 2 | Strip page numbers | `Page 3 of 14`, `– 3 –` |
| 3 | Strip eKLR boilerplate | `Kenya Law Reports`, `National Council for Law Reporting` |
| 4 | Strip case-number stamps | `ELC Case No. 123 of 2022` |
| 5 | Strip legislation headers | `Rev. Edition 2009`, `Cap. 21` |
| 6 | Remove invisible Unicode | Zero-width spaces, BOMs, soft hyphens |
| 7 | NFC Unicode normalisation | Compose diacritics, canonical ordering |
| 8 | Collapse whitespace | Multiple spaces → 1, 3+ newlines → paragraph break |

### RAG Ingestion (Pinecone)

```bash
# Dry-run (chunks text without uploading)
python scripts/run_ingestion.py --dry-run

# Ingest all cleaned text
python scripts/run_ingestion.py

# Ingest a single file
python scripts/run_ingestion.py --file cleaned/my_document.txt
```

---

## Linting & Formatting

```bash
ruff check --fix src
ruff format src
```

See [AGENTS.md](./AGENTS.md) for the full coding guidelines used in this project.
