from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.database import get_db
from src.drafting import service as drafting_service
from src.drafting.schemas import DraftingRequest, DraftingResponse, DraftingRunRead, GeneratedBlock
from src.matters import service as matters_service

router = APIRouter()

_classify_drafting_error = drafting_service._classify_drafting_error
_drafting_status_from_state = drafting_service._drafting_status_from_state


@router.post(
    "/runs",
    response_model=DraftingRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_drafting_run(
    request: DraftingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
):
    matter = await matters_service.get_user_matter(
        db, user_id=current_user.id, matter_id=request.matter_id
    )
    request.jurisdiction = request.jurisdiction or matter.jurisdiction or matter.division
    request.subcategory = request.subcategory or matter.subcategory or "Temporary Injunction"
    run = await drafting_service.create_drafting_run(db, matter=matter, request=request)
    background_tasks.add_task(drafting_service.run_drafting_background, run.id)
    return run


@router.get("/runs/{run_id}/events")
async def stream_drafting_run_events(
    run_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    await drafting_service.get_user_drafting_run(
        db, user_id=current_user.id, run_id=run_id
    )
    return StreamingResponse(
        drafting_service.stream_drafting_events(run_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate", response_model=DraftingResponse)
async def generate_draft(
    request: DraftingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    matter = await matters_service.get_user_matter(
        db, user_id=current_user.id, matter_id=request.matter_id
    )
    request.jurisdiction = request.jurisdiction or matter.jurisdiction or matter.division
    request.subcategory = request.subcategory or matter.subcategory or "Temporary Injunction"

    if not (matter.masked_facts or request.instructions or "").strip():
        matter.drafting_error = "empty_context"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="empty_context",
        )

    run = await drafting_service.create_drafting_run(db, matter=matter, request=request)
    completed = await drafting_service.execute_drafting_run(db, run.id)
    refreshed = await matters_service.get_user_matter(
        db, user_id=current_user.id, matter_id=matter.id, include_related=True
    )
    documents = refreshed.draft_documents or []
    error_status = completed.error_status if completed else "malformed_output"
    status_name = (
        error_status
        if completed and completed.status == "failed"
        else error_status or "draft_generated"
    )
    blocks = drafting_service.response_blocks_from_documents(documents)
    if completed and completed.status == "failed" and not blocks:
        blocks = [
            GeneratedBlock(
                id="error_block",
                title="Drafting unavailable",
                content=(
                    "Drafting could not complete. Retry after checking retrieval and "
                    "model availability."
                ),
                status="error",
            )
        ]
    return DraftingResponse(
        matter_id=refreshed.id,
        workflow_state=refreshed.workflow_state,
        status=status_name,
        error_status=error_status,
        documents=documents,
        blocks=blocks,
    )


@router.get("/citations")
def get_citations():
    return {
        "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
        "held": '"The conditions for the grant of an interlocutory injunction are now well settled in East Africa; first, an applicant must show a prima facie case with a probability of success. Secondly, an interlocutory injunction will not normally be granted unless the applicant might otherwise suffer irreparable injury..."',
    }
