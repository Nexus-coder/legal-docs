# LegalDocs Full-Stack Application

A comprehensive full-stack application for managing legal matters, masking Personally Identifiable Information (PII), and drafting pleadings with AI assistance via a Retrieval-Augmented Generation (RAG) pipeline trained on Kenyan legal sources (eKLR).

---

## 🏗 System Architecture

The project is split into two primary environments:

- **`frontend/`**: A modern web application built with [Next.js](https://nextjs.org/) (App Router), React 19, and Tailwind CSS v4.
- **`backend/`**: A high-performance Python server powered by [FastAPI](https://fastapi.tiangolo.com/), featuring dedicated pipelines for automated PDF text cleaning and LangChain/Pinecone vector ingestion.

---

## ✅ What Has Been Implemented So Far

### 1. Robust Python Backend (FastAPI & RAG)
- **Legal Text Cleaning Pipeline**: An extensive batch processor using PyMuPDF and pdfplumber that targets raw Kenyan legal PDFs. It runs 8 sequential cleaning passes, effectively stripping out URLs, page numbers, eKLR boilerplates, unprintable Unicode, and collapses whitespace.
- **RAG Ingestion Pipeline**: Integration with LangChain and Pinecone to semantically chunk cleaned legal texts and vectorize them for intelligent, precedent-based retrieval.
- **Core API Contracts**: Structured REST endpoints modularized using FastAPI routers.
  - `/api/matters` - For fetching and updating legal cases and their statuses.
  - `/api/pii` - For interacting with the PII redaction services.
  - `/api/drafting` - For interacting with AI-assisted drafting logic.
  - `/api/admin` - For system administration workflows.
- **CORS Configured**: Pre-configured Cross-Origin Resource Sharing for seamless communication with the Next.js frontend (`http://localhost:3000`).

### 2. Modern Next.js Frontend
- **Matter Management Dashboard**: A central hub at `/` displaying key analytics ("Citations Verified", "Recent eKLR Matches", "Draft Status") and a data table tracking the verification and status of active legal matters (e.g., *Environment & Land Court* cases).
- **PII Masking Interface**: A dedicated page at `/pii-masking` designed for redacting sensitive information securely before drafting.
- **Drafting Workspace**: Located at `/drafting`, providing an intuitive interface for drafting and resuming active pleadings.
- **Admin Console**: Located at `/admin` to handle organizational and administrative configurations.
- **Styling Pipeline**: Styled systematically utilizing the newly integrated Tailwind CSS v4, supporting dynamic layouts and modern UI aesthetics.

---

## 📁 Project Structure

```text
legal-docs/
├── backend/                  
│   ├── src/                  ← Domain-based application logic
│   │   ├── main.py           ← FastAPI entrypoint
│   │   ├── matters/          ← Matter management domain
│   │   ├── pii/              ← PII redaction domain
│   │   ├── drafting/         ← Drafting workspace domain
│   │   ├── admin/            ← Admin console domain
│   │   └── ...
│   ├── legal_cleaner/        ← 8-pass PDF Extraction & Cleaning Package
│   ├── legal_rag/            ← Pinecone Vector Database & Langchain Ingestion Package
│   ├── scripts/              ← Standalone utility scripts
│   └── requirements.txt      ← Python dependency definitions
└── frontend/                 
    ├── app/                  ← Next.js App Router pages
    │   ├── page.tsx          ← Dashboard & Matter Management UI
    │   ├── pii-masking/      ← PII Masking layout & components
    │   ├── drafting/         ← Drafting workspace interface
    │   └── admin/            ← Admin console views
    ├── package.json          ← Node dependency definitions (Next 16, React 19)
    └── tailwind.css / etc.   ← Asset configuration files
```

---

## 🚀 Getting Started

To get both servers running concurrently, you will need two separate terminal instances.

### 1. Start the Backend

```bash
cd backend

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup Environment Variables (Fill in API Keys for OpenAI/Pinecone)
cp .env.example .env

# Run the FastAPI Server
uvicorn src.main:app --reload --port 8000
```
> **Note**: For data processing jobs like PDF cleaning and Pinecone ingestion, use the standalone scripts: `python run_cleaner.py` and `python run_ingestion.py`. (*See `backend/README.md` for extended documentation on the ingestion pipeline.*)

### 2. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install
# or yarn install / pnpm install

# Run Next.js Development Server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to view the Matter Management dashboard!
