from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.matters import router as matters_router
from src.pii import router as pii_router
from src.drafting import router as drafting_router
from src.admin import router as admin_router

app_kwargs = {"title": "LegalDocs API", "version": "1.0.0"}

# Hide docs outside selected envs as per AGENTS.md
SHOW_DOCS_IN = {"local", "staging"}
if settings.ENVIRONMENT not in SHOW_DOCS_IN:
    app_kwargs["openapi_url"] = None

app = FastAPI(**app_kwargs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain routers
app.include_router(matters_router.router, prefix="/api/matters", tags=["Matters"])
app.include_router(pii_router.router, prefix="/api/pii", tags=["PII Masking"])
app.include_router(
    drafting_router.router, prefix="/api/drafting", tags=["Drafting Workspace"]
)
app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin Console"])


@app.get("/api/stats")
def get_dashboard_stats():
    return {
        "citations_verified": {"current": 142, "total": 158},
        "recent_matches": 24,
        "draft_status": {"drafting": 8, "verified": 3, "exported": 12},
    }
