# LegalDocs AI Architecture

*This document outlines the state-of-the-art AI stack implemented into the LegalDocs Application. It details how complex ingestion, structured retrieval, and cyclic logic generation are securely integrated into the Python FastAPI layer.*

---

## 1. Architectural Overview

The core requirement of LegalDocs is to parse raw Kenyan court cases, build an intelligent knowledge base mapping legal precedent, and use an LLM to dynamically draft and synthesize legally sound pleading blocks mapped to those precedents.

To achieve superior parsing precision and minimize unverified LLM hallucinations, the backend has been completely revolutionized utilizing modern, industry-standard AI packages:
- **[MarkItDown](https://github.com/microsoft/markitdown)**: Developed by Microsoft; the ultimate processor for transforming dirty PDFs, Excel files, and Word docs flawlessly into Markdown.
- **[LlamaIndex](https://www.llamaindex.ai/)**: The premier framework replacing standard extraction setups; handles extremely complex data chunking semantics and recursive Vector Database indexing natively into **Pinecone**.
- **[LangGraph](https://langchain-ai.github.io/langgraph/)**: A cyclical execution state engine that allows the AI to literally draft its own work, heavily critique it based on rigorous prompt rules, and recursively patch its logic until it meets the standards of a Senior Partner at a law firm.

---

## 2. Document Ingestion Phase: MarkItDown

Instead of writing extremely verbose text-cleaning pipelines with tools like PyMuPDF or pdfplumber—which universally struggle parsing hierarchical formatting and tabular constraints—we migrated the ingestion engine entirely to Microsoft's **MarkItDown**.

### Implementation specifics:
- **Module:** `backend/app/services/ingestion/parser.py`
- **How it works**: A thin wrapper initialized via `MarkItDown()`. It converts incoming `.pdf`, `.docx`, or `.xlsx` files inside the `/sources` directory mapping them 1:1 into strictly formatted Markdown without losing native formatting elements like embedded tables.
- **CLI Interface**: Exposed via the updated `python backend/scripts/run_cleaner.py` batch script. Processed strings are formatted dynamically to the `/cleaned/` directory as beautifully structured `.md` files universally comprehended by LLMs.

---

## 3. High-Fidelity Indexing & Retrieval: LlamaIndex + Pinecone

With high-fidelity Markdown generated natively, splitting raw text via simple space characters directly harms context mapping inside Retrieval-Augmented Generation (RAG). To solve this, conventional text splitters were swapped for LlamaIndex architectures mapping closely with Pinecone.

### Implementation specifics:
- **Module:** `backend/app/services/ingestion/indexer.py`
- **Node Precision (MarkdownNodeParser)**: LlamaIndex scans the newly converted Markdown files intelligently. Instead of arbitrarily chunking 500 characters, it reads Markdown Headers (`#`, `##`) identifying hierarchical segments accurately as interconnected `nodes`. 
- **Embeddings**: `text-embedding-3-small` bindings wrap natively onto the generated document context using `OpenAIEmbedding`.
- **Vector Storage**: Operates on `PineconeVectorStore` passing vectors natively via Pinecone's official libraries, creating queryable recursive indices.
- **CLI Interface**: Exposed dynamically via `python backend/scripts/run_ingestion.py`.
- **Querying**: The `retrieve_context` function retrieves the Top-K closest embeddings matched effectively via string similarity parameters.

---

## 4. Cyclic Generation Loop: The LangGraph Engine

The single most critical integration inside LegalDocs is moving beyond zero-shot linear LLM prompts. Linear LLM generation allows for high rates of hallucination because the AI is not afforded a step to pause and legally review what it actually output.

This is solved natively via the **LangGraph** engine operating within the FastAPI drafting route.

### Implementation specifics:
- **Module:** `backend/src/agent/graph.py`
- **Model selection:** Drafting and critique use `OPENAI_DRAFTING_MODEL`, which defaults to `gpt-5.5`. Embeddings remain separately configured through `OPENAI_EMBEDDING_MODEL`.
- **State Definition (`AgentState`)**: The LangGraph carries `request` instructions, Pinecone retrieved `context`, the current LLM `draft`, critique `feedback`, revision counters, pass/fail state, and typed safe `error_status` values.
- **Node 1: Retrieve**: Runs LlamaIndex querying dynamically mapping the parameters configured from the Next.js `DraftingWorkspace` (e.g. *Adverse Possession* mapped to the *jurisdiction* rules). If no usable Kenya Law authority context is returned, the graph stops before generation with `retrieval_failed`.
- **Node 2: Draft**: Initializes `ChatOpenAI` lazily and processes retrieved precedent with explicit prompt-injection boundaries. Matter facts and retrieved authorities are treated as untrusted source material, not instructions to follow.
- **Node 3: Critique Node**: Acts as the explicit validator for Kenyan Law submissions. It reviews the draft alongside the original request and retrieved authority context, and it only passes on an exact **"PASS"** response.

### Dynamic State Routing:
The graph utilizes conditional edges after retrieval and critique.
1. The AI attempts to draft the response.
2. The AI critiques the drafted response.
3. If Critique LLM says "FAIL: Context lacks test parameters", the system natively cycles back to the Draft logic, piping in the feedback loop iteratively ensuring the LLM patches its logic without human oversight.
4. If retrieval fails, the graph exits without drafting so the backend can record a safe `retrieval_failed` state.
5. Yields back to the UI when standard constraints are validated or the bounded revision limit is reached for advocate review.

## 5. Connecting the Dots (FastAPI to Next.js)

The resulting endpoint at `POST /api/drafting/generate` inside `backend/src/drafting/router.py` was fully converted to point natively into this exact graph pipeline. The background drafting service invokes the graph off the async event loop:

```python
        # LangGraph Pipeline Execution
        final_state = await asyncio.to_thread(legal_agent.invoke, initial_state)
```

The React asynchronous architecture on the frontend hits this `generate_draft` endpoint successfully returning mapping dynamic responses—wherever they are legally verified or strictly drafted—bridging cutting-edge Agentic LLM logic reliably back to standard human user dashboards natively.
## 6. Matter-Centered Workflow Governance

The active drafting endpoint is `POST /api/drafting/generate` in `backend/src/drafting/router.py`. It is matter-scoped: the backend loads the authenticated user's selected matter, reads stored `masked_facts`, and invokes the LangGraph pipeline from server-side workflow data. Raw facts are no longer passed through the drafting URL.

The `Matter` model owns explicit workflow states: `created`, `facts_entered`, `pii_masked`, `draft_generated`, `citations_verified`, and `export_ready`. Backend transition validation rejects invalid jumps and stale clients. Major workflow events write no-PII activity entries, and citation evidence records store source metadata, confidence, status, and a bounded snippet for the frontend evidence drawer.

Drafting failures return named safe statuses (`retrieval_failed`, `model_failed`, `empty_context`, `malformed_output`, `max_revisions_failed`) rather than raw exception text.
