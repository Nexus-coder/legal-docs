from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
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


@router.get(
    "/kenyalaw/documents",
    response_model=kenyalaw_schemas.CaseDocumentList,
)
async def list_kenyalaw_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", max_length=40),
    court: str | None = Query(default=None, max_length=180),
    topic: str | None = Query(default=None, max_length=80),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    return await kenyalaw_service.list_case_documents(
        db,
        query=q,
        status=status_filter,
        court=court,
        topic=topic,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/kenyalaw/documents/repair",
    response_model=kenyalaw_schemas.IngestionRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def repair_kenyalaw_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    background_tasks: BackgroundTasks,
):
    run = await kenyalaw_service.create_document_repair_run(db)
    background_tasks.add_task(kenyalaw_service.run_document_repair_background, run.id)
    return run


@router.get(
    "/kenyalaw/documents/{document_id}",
    response_model=kenyalaw_schemas.CaseDocumentDetail,
)
async def get_kenyalaw_document(
    document_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    document = await kenyalaw_service.get_case_document_detail(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document
