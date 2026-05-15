import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.database import get_db
from src.matters import service as matters_service
from src.pii import schemas, service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/detect",
    response_model=schemas.DetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect PII entities in text",
    description="Runs the OpenAI Privacy Filter model to identify PII spans. "
    "Returns entity type, text, offsets, and confidence score for each detection.",
)
def detect_pii(
    request: schemas.DetectRequest,
    _current_user: Annotated[UserRead, Depends(get_current_user)],
):
    entities = service.detect_pii(request.text)
    return schemas.DetectResponse(
        entities=[schemas.PiiEntity(**e) for e in entities],
        entity_count=len(entities),
    )


@router.post(
    "/mask",
    response_model=schemas.MaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect and mask PII in text",
    description="Detects PII spans using the Privacy Filter model, then replaces "
    "each span with a bracketed placeholder (e.g. [PRIVATE_PERSON]).",
)
async def mask_pii(
    request: schemas.MaskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="empty_text",
        )
    matter = await matters_service.get_user_matter(
        db, user_id=current_user.id, matter_id=request.matter_id
    )
    if matter.workflow_state == "created":
        await matters_service.transition_matter(
            db,
            matter,
            "facts_entered",
            activity_title="Facts entered",
            activity_detail="Raw facts were saved for this matter.",
        )
    entities = service.detect_pii(request.text)
    masked_text = service.mask_text(request.text, entities)
    matter.raw_facts = request.text
    matter.masked_facts = masked_text
    matter.pii_entity_count = len(entities)
    matter.jurisdiction = request.jurisdiction or matter.jurisdiction
    matter.subcategory = request.subcategory or matter.subcategory
    await matters_service.transition_matter(
        db,
        matter,
        "pii_masked",
        activity_title="PII masked",
        activity_detail=f"{len(entities)} entities masked.",
    )
    await db.commit()
    await db.refresh(matter)
    logger.info(
        "pii_masked matter_id=%s user_id=%s entity_count=%s",
        matter.id,
        current_user.id,
        len(entities),
    )
    return schemas.MaskResponse(
        matter_id=matter.id,
        workflow_state=matter.workflow_state,
        masked_text=masked_text,
        entities=[schemas.PiiEntity(**e) for e in entities],
        entity_count=len(entities),
    )
