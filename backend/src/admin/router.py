from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.schemas import FlaggedItem
from src.database import get_db
from src.kenyalaw import schemas as kenyalaw_schemas
from src.kenyalaw import service as kenyalaw_service

router = APIRouter()


@router.get("/hallucinations", response_model=List[FlaggedItem])
def get_hallucinations():
    return [
        FlaggedItem(
            reference="#ELC-45-G3",
            claim="Cited 'Sec 22 of Land Act' for Adverse Possession",
            status="No Match Found",
            action="Retrain Model",
        )
    ]


@router.post("/ingest")
def ingest_eklr():
    return {
        "status": "deprecated",
        "message": "Use /api/admin/kenyalaw/ingestion-runs for ELC-scoped Kenya Law ingestion.",
    }


@router.post(
    "/kenyalaw/ingestion-runs",
    response_model=kenyalaw_schemas.IngestionRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_kenyalaw_ingestion(
    payload: kenyalaw_schemas.IngestionRunCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    run = await kenyalaw_service.create_ingestion_run(db, payload)
    background_tasks.add_task(
        kenyalaw_service.run_ingestion_background,
        run.id,
        payload,
    )
    return run


@router.get(
    "/kenyalaw/ingestion-runs/{run_id}",
    response_model=kenyalaw_schemas.IngestionRunRead,
)
async def get_kenyalaw_ingestion_run(
    run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await kenyalaw_service.get_ingestion_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/kenyalaw/ingestion-runs/{run_id}/events")
async def stream_kenyalaw_ingestion_events(
    run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await kenyalaw_service.get_ingestion_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return StreamingResponse(
        kenyalaw_service.stream_ingestion_events(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/kenyalaw/ingestion-runs/{run_id}/retry-failures",
    response_model=kenyalaw_schemas.IngestionRunRead,
)
async def retry_kenyalaw_failures(
    run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await kenyalaw_service.retry_failed_urls(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/kenyalaw/corpus-stats", response_model=kenyalaw_schemas.CorpusStats)
async def get_kenyalaw_corpus_stats(db: Annotated[AsyncSession, Depends(get_db)]):
    return await kenyalaw_service.get_corpus_stats(db)
