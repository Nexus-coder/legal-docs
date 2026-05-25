from datetime import datetime, timezone
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.drafting.editor import text_to_editor_json
from src.matters.models import (
    CitationEvidence,
    DraftDocument,
    DraftDocumentRevision,
    Matter,
    MatterActivity,
)
from src.matters.schemas import MatterCreate, WORKFLOW_STATES

logger = logging.getLogger(__name__)

TRANSITIONS = {
    "created": {"facts_entered"},
    "facts_entered": {"pii_masked"},
    "pii_masked": {"draft_generated"},
    "draft_generated": {"citations_verified"},
    "citations_verified": {"export_ready"},
    "export_ready": set(),
}

STATE_STATUS = {
    "created": "Drafting",
    "facts_entered": "Drafting",
    "pii_masked": "Drafting",
    "draft_generated": "Verification",
    "citations_verified": "Verified",
    "export_ready": "Export Ready",
}


async def get_user_matters(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Matter).where(Matter.user_id == user_id).order_by(Matter.updated_at.desc())
    )
    return result.scalars().all()


async def get_user_matter(
    db: AsyncSession, user_id: int, matter_id: int, include_related: bool = False
):
    stmt = select(Matter).where(Matter.id == matter_id, Matter.user_id == user_id)
    if include_related:
        stmt = stmt.options(
            selectinload(Matter.activities),
            selectinload(Matter.citation_evidence),
            selectinload(Matter.draft_documents),
        )
    result = await db.execute(stmt)
    matter = result.scalar_one_or_none()
    if matter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found")
    return matter


async def create_matter(db: AsyncSession, user_id: int, matter_in: MatterCreate):
    db_matter = Matter(
        user_id=user_id,
        **matter_in.model_dump()
    )
    db.add(db_matter)
    db.add(
        MatterActivity(
            matter=db_matter,
            event_type="matter_created",
            title="Matter created",
            detail="Workflow started.",
        )
    )
    await db.commit()
    await db.refresh(db_matter)
    logger.info("matter_created user_id=%s matter_id=%s", user_id, db_matter.id)
    return db_matter


async def add_activity(
    db: AsyncSession,
    matter: Matter,
    event_type: str,
    title: str,
    detail: str | None = None,
) -> MatterActivity:
    activity = MatterActivity(
        matter_id=matter.id, event_type=event_type, title=title, detail=detail
    )
    matter.last_activity = title
    db.add(activity)
    return activity


async def transition_matter(
    db: AsyncSession,
    matter: Matter,
    new_state: str,
    expected_state: str | None = None,
    activity_title: str | None = None,
    activity_detail: str | None = None,
) -> Matter:
    if new_state not in WORKFLOW_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid workflow state",
        )
    current = matter.workflow_state or "created"
    if expected_state is not None and current != expected_state:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Matter state changed. Refresh and retry.",
        )
    if current == new_state:
        return matter
    if new_state not in TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition matter from {current} to {new_state}",
        )

    matter.workflow_state = new_state
    matter.status = STATE_STATUS.get(new_state, matter.status)
    now = datetime.now(timezone.utc)
    if new_state == "pii_masked":
        matter.masked_at = matter.masked_at or now
    elif new_state == "draft_generated":
        matter.drafted_at = matter.drafted_at or now
    elif new_state == "citations_verified":
        matter.citations_verified_at = matter.citations_verified_at or now
    elif new_state == "export_ready":
        matter.export_ready_at = matter.export_ready_at or now

    await add_activity(
        db,
        matter,
        event_type=f"state_{new_state}",
        title=activity_title or f"Workflow moved to {new_state.replace('_', ' ')}",
        detail=activity_detail,
    )
    logger.info(
        "matter_transition matter_id=%s user_id=%s from_state=%s to_state=%s",
        matter.id,
        matter.user_id,
        current,
        new_state,
    )
    return matter


async def upsert_citation_evidence(
    db: AsyncSession,
    matter: Matter,
    evidence_items: list[dict],
) -> list[CitationEvidence]:
    result = await db.execute(
        select(CitationEvidence).where(CitationEvidence.matter_id == matter.id)
    )
    existing = result.scalars().all()
    for item in existing:
        await db.delete(item)

    evidence = [
        CitationEvidence(
            matter_id=matter.id,
            citation_type=item["citation_type"],
            title=item["title"],
            source=item.get("source"),
            source_url=item.get("source_url"),
            neutral_citation=item.get("neutral_citation"),
            court=item.get("court"),
            judgment_date=item.get("judgment_date"),
            snippet=item["snippet"],
            confidence=item.get("confidence", 0.0),
            confidence_breakdown=item.get("confidence_breakdown"),
            status=item.get("status", "pending"),
        )
        for item in evidence_items
    ]
    db.add_all(evidence)
    matter.verification_done = len([e for e in evidence if e.status == "verified"])
    matter.verification_total = len(evidence)
    return evidence


async def upsert_draft_document(
    db: AsyncSession,
    matter: Matter,
    *,
    document_type: str,
    title: str,
    content: str,
    status: str,
    error_status: str | None,
    revision_count: int,
) -> DraftDocument:
    result = await db.execute(
        select(DraftDocument).where(
            DraftDocument.matter_id == matter.id,
            DraftDocument.document_type == document_type,
        )
    )
    document = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    editor_json = text_to_editor_json(content)
    if document is None:
        document = DraftDocument(
            matter_id=matter.id,
            document_type=document_type,
            title=title,
            content=content,
            editor_json=editor_json,
            generated_editor_json=editor_json,
            status=status,
            error_status=error_status,
            revision_count=revision_count,
            edit_revision=0,
            generated_at=now,
            updated_at=now,
        )
        db.add(document)
        db.add(
            DraftDocumentRevision(
                document=document,
                user_id=matter.user_id,
                revision_type="generated",
                edit_revision=0,
                editor_json=editor_json,
                content=content,
            )
        )
        return document

    document.title = title
    document.content = content
    document.editor_json = editor_json
    document.generated_editor_json = editor_json
    document.status = status
    document.error_status = error_status
    document.revision_count = revision_count
    document.edit_revision = (document.edit_revision or 0) + 1
    document.updated_at = now
    db.add(
        DraftDocumentRevision(
            draft_document_id=document.id,
            user_id=matter.user_id,
            revision_type="generated",
            edit_revision=document.edit_revision,
            editor_json=editor_json,
            content=content,
        )
    )
    return document


async def get_user_dashboard_stats(db: AsyncSession, user_id: int):
    # This is a simplified version of stats
    # In a real app, citations_verified might come from another table
    
    matters = await get_user_matters(db, user_id)
    
    citations_current = sum(m.verification_done for m in matters)
    citations_total = sum(m.verification_total for m in matters)
    
    draft_status = {
        "drafting": len([m for m in matters if m.workflow_state in {"created", "facts_entered", "pii_masked"}]),
        "verified": len([m for m in matters if m.workflow_state == "citations_verified"]),
        "exported": len([m for m in matters if m.workflow_state == "export_ready"]),
    }
    
    return {
        "citations_verified": {"current": citations_current, "total": citations_total},
        "recent_matches": 0, # Placeholder for now
        "draft_status": draft_status,
    }
