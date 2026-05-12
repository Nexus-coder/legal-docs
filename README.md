# LegalDocs

A full-stack platform for managing Kenyan legal matters — from raw PDF ingestion to AI-powered PII redaction and precedent-aware drafting.

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 16 (App Router) · React 19 · Tailwind CSS v4 |
| **Backend** | FastAPI · SQLAlchemy 2.0 (async) · SQLite (dev) |
| **AI / ML** | OpenAI Privacy Filter (PII) · LangChain · LangGraph · Pinecone |
| **Infra** | PyJWT auth · pydantic-settings · Ruff |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│  Next.js Frontend  (localhost:3000)                             │
│  Dashboard · PII Masking · Drafting Workspace · Admin Console   │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST / JSON
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend  (localhost:8000)                              │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │   Auth   │ │ Matters  │ │   PII    │ │ Drafting │  ...      │
│  │ JWT+bcrypt│ │  CRUD    │ │ Privacy  │ │   RAG    │          │
│  └──────────┘ └──────────┘ │  Filter  │ └──────────┘          │
│                             └──────────┘                        │
│  SQLite (dev)  ·  Pinecone (vectors)  ·  OpenAI (embeddings)   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```text
legal-docs/
├── backend/
│   ├── src/                      ← Domain-driven FastAPI application
│   │   ├── main.py               ← Entrypoint & lifespan
│   │   ├── config.py             ← Global pydantic-settings
│   │   ├── database.py           ← Async SQLAlchemy engine
│   │   ├── models.py             ← Shared ORM Base & Pydantic base
│   │   ├── auth/                 ← JWT authentication domain
│   │   ├── matters/              ← Matter management domain
│   │   ├── pii/                  ← PII detection & masking (Privacy Filter)
│   │   ├── drafting/             ← AI-assisted drafting domain
│   │   ├── admin/                ← Admin console domain
│   │   ├── agent/                ← LangGraph agent orchestration
│   │   ├── ingestion/            ← Document parsing & indexing
│   │   ├── legal_cleaner/        ← 8-pass PDF text cleaning
│   │   └── legal_rag/            ← Pinecone vector ingestion
│   ├── scripts/                  ← CLI utilities (cleaner, ingestion)
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── app/                      ← Next.js App Router
    │   ├── page.tsx              ← Dashboard
    │   ├── pii-masking/          ← PII Masking UI
    │   ├── drafting/             ← Drafting workspace UI
    │   └── admin/                ← Admin console UI
    ├── package.json
    └── tailwind.css
```

---

## Getting Started

You need **two terminals** — one for the backend and one for the frontend.

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
.\venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env             # Then fill in your API keys

# Start the server
uvicorn src.main:app --reload --port 8000
```

> The SQLite database and tables are created automatically on first startup.
> The PII model (~600 MB) downloads from Hugging Face on the first `/api/pii/*` request and is cached locally after that.

### 2. Frontend

```bash
cd frontend

npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

---

## API Reference

Interactive docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) in `local` and `staging` environments.

| Prefix | Domain | Key Endpoints |
|--------|--------|---------------|
| `/api/auth` | Authentication | `POST /signup` · `POST /login` · `GET /me` |
| `/api/matters` | Matter Management | CRUD for legal cases and statuses |
| `/api/pii` | PII Masking | `POST /detect` · `POST /mask` |
| `/api/drafting` | Drafting Workspace | AI-assisted pleading drafting |
| `/api/admin` | Admin Console | System administration |
| `/api/stats` | Dashboard | Aggregated stats for the frontend |

---

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for RAG embeddings |
| `PINECONE_API_KEY` | Pinecone API key for vector storage |

### Optional (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `local` | `local` / `staging` / `production` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./legal_docs.db` | Async database URL |
| `PINECONE_INDEX_NAME` | `legal-docs` | Target Pinecone index |
| `AUTH_JWT_SECRET` | `super-secret-dev-key` | JWT signing secret (**change in production**) |
| `AUTH_JWT_ALG` | `HS256` | JWT algorithm |
| `AUTH_JWT_EXP_MINUTES` | `1440` | Token expiry (24 hours) |
| `PII_MODEL_NAME` | `openai/privacy-filter` | Hugging Face model for PII detection |
| `PII_DEVICE` | `cpu` | Inference device (`cpu` or `cuda`) |
| `PII_CONFIDENCE_THRESHOLD` | `0.5` | Minimum score to report a PII entity |

---

## License

Private — All rights reserved.
