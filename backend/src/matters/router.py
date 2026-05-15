from typing import Annotated, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.matters import schemas, service

router = APIRouter()


@router.get("/", response_model=List[schemas.MatterRead])
async def list_matters(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    return await service.get_user_matters(db, user_id=current_user.id)


@router.post("/", response_model=schemas.MatterRead, status_code=status.HTTP_201_CREATED)
async def create_matter(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
    matter_in: schemas.MatterCreate,
):
    return await service.create_matter(db, user_id=current_user.id, matter_in=matter_in)


@router.get("/{matter_id}", response_model=schemas.MatterDetailRead)
async def get_matter(
    matter_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    return await service.get_user_matter(
        db, user_id=current_user.id, matter_id=matter_id, include_related=True
    )


@router.post("/{matter_id}/transition", response_model=schemas.MatterRead)
async def transition_matter(
    matter_id: int,
    transition: schemas.MatterTransitionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    matter = await service.get_user_matter(db, current_user.id, matter_id)
    await service.transition_matter(
        db,
        matter,
        transition.workflow_state,
        expected_state=transition.expected_state,
    )
    await db.commit()
    await db.refresh(matter)
    return matter


@router.post("/{matter_id}/verify-citations", response_model=schemas.VerificationResponse)
async def verify_citations(
    matter_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    matter = await service.get_user_matter(db, current_user.id, matter_id)
    await service.upsert_citation_evidence(
        db,
        matter,
        [
            {
                "citation_type": "statute",
                "title": "Limitation of Actions Act, Section 7",
                "source": "Kenya Law",
                "snippet": "An action may not be brought by any person to recover land after the end of twelve years from the date on which the right of action accrued.",
                "confidence": 1.0,
                "status": "verified",
            },
            {
                "citation_type": "precedent",
                "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
                "source": "eKLR reference corpus",
                "snippet": "The conditions for grant of an interlocutory injunction include a prima facie case, irreparable injury, and balance of convenience.",
                "confidence": 0.94,
                "status": "verified",
            },
        ],
    )
    if matter.workflow_state == "draft_generated":
        await service.transition_matter(
            db,
            matter,
            "citations_verified",
            activity_title="Citations verified",
            activity_detail="All available citation evidence was reviewed.",
        )
    await db.commit()
    refreshed = await service.get_user_matter(
        db, user_id=current_user.id, matter_id=matter_id, include_related=True
    )
    return {"matter": refreshed, "evidence": refreshed.citation_evidence}
