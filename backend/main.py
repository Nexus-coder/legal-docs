from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import matters, pii, drafting, admin

app = FastAPI(title="LegalDocs API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(matters.router, prefix="/api/matters", tags=["Matters"])
app.include_router(pii.router, prefix="/api/pii", tags=["PII Masking"])
app.include_router(drafting.router, prefix="/api/drafting", tags=["Drafting Workspace"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Console"])

@app.get("/api/stats")
def get_dashboard_stats():
    return {
        "citations_verified": {
            "current": 142,
            "total": 158
        },
        "recent_matches": 24,
        "draft_status": {
            "drafting": 8,
            "verified": 3,
            "exported": 12
        }
    }
