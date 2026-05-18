from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin import router as admin_router
from src.auth import router as auth_router
from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.config import settings
from src.database import engine, get_db
from src.drafting import router as drafting_router
from src.matters import router as matters_router
from src.matters import service as matters_service
from src.models import Base
from src.pii import router as pii_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (local dev only)
    if settings.ENVIRONMENT == "local":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            if "sqlite" in settings.DATABASE_URL:
                await conn.run_sync(_backfill_matter_workflow_columns)
                await conn.run_sync(_backfill_citation_evidence_columns)
                await conn.run_sync(_backfill_case_document_columns)
    yield


def _backfill_matter_workflow_columns(sync_conn):
    columns = {
        row[1] for row in sync_conn.exec_driver_sql("PRAGMA table_info(matter)").fetchall()
    }
    additions = {
        "workflow_state": "VARCHAR(50) DEFAULT 'created'",
        "jurisdiction": "VARCHAR(150)",
        "subcategory": "VARCHAR(150)",
        "raw_facts": "TEXT",
        "masked_facts": "TEXT",
        "pii_entity_count": "INTEGER DEFAULT 0",
        "draft_content": "TEXT",
        "drafting_error": "VARCHAR(80)",
        "masked_at": "DATETIME",
        "drafted_at": "DATETIME",
        "citations_verified_at": "DATETIME",
        "export_ready_at": "DATETIME",
    }
    for name, ddl in additions.items():
        if name not in columns:
            sync_conn.exec_driver_sql(f"ALTER TABLE matter ADD COLUMN {name} {ddl}")
    sync_conn.exec_driver_sql(
        """
        UPDATE matter
        SET workflow_state = CASE
            WHEN status = 'Verified' THEN 'citations_verified'
            WHEN status = 'Exported' THEN 'export_ready'
            ELSE COALESCE(workflow_state, 'created')
        END
        WHERE workflow_state IS NULL OR workflow_state = ''
        """
    )


def _backfill_citation_evidence_columns(sync_conn):
    tables = {
        row[0]
        for row in sync_conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "citation_evidence" not in tables:
        return
    columns = {
        row[1]
        for row in sync_conn.exec_driver_sql(
            "PRAGMA table_info(citation_evidence)"
        ).fetchall()
    }
    additions = {
        "source_url": "VARCHAR(500)",
        "neutral_citation": "VARCHAR(255)",
        "court": "VARCHAR(180)",
        "judgment_date": "VARCHAR(40)",
        "confidence_breakdown": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in columns:
            sync_conn.exec_driver_sql(
                f"ALTER TABLE citation_evidence ADD COLUMN {name} {ddl}"
            )


def _backfill_case_document_columns(sync_conn):
    tables = {
        row[0]
        for row in sync_conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "case_document" not in tables:
        return
    columns = {
        row[1]
        for row in sync_conn.exec_driver_sql(
            "PRAGMA table_info(case_document)"
        ).fetchall()
    }
    additions = {
        "normalized_text": "TEXT",
        "text_length": "INTEGER DEFAULT 0",
        "stored_at": "DATETIME",
        "last_ingestion_run_id": "INTEGER",
        "source_document_url": "VARCHAR(500)",
        "extraction_status": "VARCHAR(40) DEFAULT 'valid'",
        "extraction_error": "TEXT",
        "extracted_at": "DATETIME",
        "text_quality_score": "INTEGER DEFAULT 0",
    }
    for name, ddl in additions.items():
        if name not in columns:
            sync_conn.exec_driver_sql(
                f"ALTER TABLE case_document ADD COLUMN {name} {ddl}"
            )


app_kwargs = {
    "title": "LegalDocs API",
    "version": "1.0.0",
    "lifespan": lifespan,
}

# Hide docs outside selected envs as per AGENTS.md
SHOW_DOCS_IN = {"local", "staging"}
if settings.ENVIRONMENT not in SHOW_DOCS_IN:
    app_kwargs["openapi_url"] = None

app = FastAPI(**app_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain routers
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(matters_router.router, prefix="/api/matters", tags=["Matters"])
app.include_router(pii_router.router, prefix="/api/pii", tags=["PII Masking"])
app.include_router(
    drafting_router.router, prefix="/api/drafting", tags=["Drafting Workspace"]
)
app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin Console"])

@app.get("/api/stats")
async def get_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    return await matters_service.get_user_dashboard_stats(db, user_id=current_user.id)
