from fastapi import APIRouter
from typing import List
from app.models.domain import FlaggedItem

router = APIRouter()

@router.get("/hallucinations", response_model=List[FlaggedItem])
def get_hallucinations():
    return [
        FlaggedItem(
            reference="#ELC-45-G3",
            claim="Cited 'Sec 22 of Land Act' for Adverse Possession",
            status="No Match Found",
            action="Retrain Model"
        )
    ]

@router.post("/ingest")
def ingest_eklr():
    return {"status": "success", "message": "eKLR documents ingested into vector database."}
