import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agent.graph import legal_agent
from src.database import SessionFactory
from src.drafting.models import DraftingEvent, DraftingRun
from src.drafting.schemas import DraftingEventRead, DraftingRequest, GeneratedBlock
from src.matters import service as matters_service
from src.matters.models import Matter

logger = logging.getLogger(__name__)

TERMINAL_RUN_STATUSES = {"completed", "failed"}

INJUNCTION_DRAFT_DOCUMENTS = [
    {
        "document_type": "injunction_motion",
        "title": "Notice of Motion for Temporary Injunction",
        "activity_title": "Drafting Notice of Motion",
        "instruction": (
            "Draft a Notice of Motion for temporary injunction in an Environment and "
            "Land Court matter. Include the court heading, certificate-style urgency "
            "context only if the facts justify it, prayers, grounds, and a concise "
            "legal basis tied to the supplied facts and retrieved Kenyan authorities."
        ),
    },
    {
        "document_type": "supporting_affidavit",
        "title": "Supporting Affidavit",
        "activity_title": "Drafting Supporting Affidavit",
        "instruction": (
            "Draft a Supporting Affidavit for the temporary injunction application. "
            "Use numbered deposition paragraphs, preserve a clear fact chronology, "
            "identify anonymized parties and land references, refer to exhibits only "
            "when supported by the facts, and avoid legal argument that belongs in "
            "submissions or grounds."
        ),
    },
]


def _classify_drafting_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "pinecone" in message or "retrieve" in message or "retrieval" in message:
        return "retrieval_failed"
    if "openai" in message or "api" in message or "model" in message or "rate" in message:
        return "model_failed"
    if "revision" in message:
        return "max_revisions_failed"
    return "malformed_output"


def _drafting_status_from_state(final_state: dict) -> tuple[str, str | None]:
    if not final_state.get("draft", ""):
        return "malformed_output", "malformed_output"
    if (
        not final_state.get("passed_critique", False)
        and final_state.get("revision_count", 0) >= 3
    ):
        return "max_revisions_failed", "max_revisions_failed"
    return "draft_generated", None


def _document_status(final_state: dict, error_status: str | None) -> str:
    if error_status == "max_revisions_failed":
        return "needs_review"
    if error_status:
        return "error"
    if final_state.get("passed_critique", False):
        return "verified"
    return "draft"


def _build_initial_state(
    request: DraftingRequest,
    *,
    matter_instructions: str,
    document_instruction: str,
) -> dict:
    return {
        "request": {
            "jurisdiction": request.jurisdiction,
            "subcategory": request.subcategory,
            "instructions": f"{document_instruction}\n\nMatter facts:\n{matter_instructions}",
        },
        "context": [],
        "draft": "",
        "feedback": "",
        "revision_count": 0,
        "passed_critique": False,
    }


async def create_drafting_run(
    db: AsyncSession,
    *,
    matter: Matter,
    request: DraftingRequest,
) -> DraftingRun:
    run = DraftingRun(
        matter_id=matter.id,
        user_id=matter.user_id,
        status="running",
        jurisdiction=request.jurisdiction or matter.jurisdiction or matter.division,
        subcategory=request.subcategory or matter.subcategory or "Temporary Injunction",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    await record_event(
        db,
        run,
        "started",
        "start",
        "Opened the drafting desk and started a live drafting run.",
    )
    return run


async def get_user_drafting_run(
    db: AsyncSession,
    *,
    user_id: int,
    run_id: int,
) -> DraftingRun:
    result = await db.execute(
        select(DraftingRun).where(DraftingRun.id == run_id, DraftingRun.user_id == user_id)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drafting run not found")
    return run


async def get_drafting_run(db: AsyncSession, run_id: int) -> DraftingRun | None:
    result = await db.execute(
        select(DraftingRun).options(selectinload(DraftingRun.matter)).where(DraftingRun.id == run_id)
    )
    return result.scalar_one_or_none()


async def get_drafting_events(
    db: AsyncSession, run_id: int, *, after_id: int = 0
) -> list[DraftingEvent]:
    result = await db.execute(
        select(DraftingEvent)
        .where(
            DraftingEvent.drafting_run_id == run_id,
            DraftingEvent.id > after_id,
        )
        .order_by(DraftingEvent.id)
    )
    return list(result.scalars().all())


async def record_event(
    db: AsyncSession,
    run: DraftingRun,
    event_type: str,
    stage: str,
    message: str,
    *,
    document_type: str | None = None,
    error_type: str | None = None,
) -> DraftingEvent:
    event = DraftingEvent(
        drafting_run_id=run.id,
        event_type=event_type,
        stage=stage,
        message=message,
        document_type=document_type,
        error_type=error_type,
    )
    db.add(run)
    db.add(event)
    await db.commit()
    await db.refresh(run)
    await db.refresh(event)
    return event


async def run_drafting_background(run_id: int) -> None:
    async with SessionFactory() as db:
        await execute_drafting_run(db, run_id)


async def execute_drafting_run(db: AsyncSession, run_id: int) -> DraftingRun | None:
    run = await get_drafting_run(db, run_id)
    if run is None:
        return None
    matter = run.matter
    request = DraftingRequest(
        matter_id=matter.id,
        jurisdiction=run.jurisdiction or matter.jurisdiction or matter.division,
        subcategory=run.subcategory or matter.subcategory or "Temporary Injunction",
    )
    instructions = matter.masked_facts

    if not instructions or not instructions.strip():
        return await _fail_run(
            db,
            run,
            matter,
            stage="read_facts",
            error_status="empty_context",
            message="No masked matter facts were available for drafting.",
        )

    try:
        await record_event(
            db,
            run,
            "reading_facts",
            "read_facts",
            "Reading masked facts.",
        )
        await record_event(
            db,
            run,
            "searching_authorities",
            "authorities",
            "Searching Kenyan authorities.",
        )

        documents = []
        response_error_status = None
        for spec in INJUNCTION_DRAFT_DOCUMENTS:
            await record_event(
                db,
                run,
                "drafting_document",
                spec["document_type"],
                spec["activity_title"],
                document_type=spec["document_type"],
            )
            initial_state = _build_initial_state(
                request,
                matter_instructions=instructions,
                document_instruction=spec["instruction"],
            )
            final_state = legal_agent.invoke(initial_state)
            await record_event(
                db,
                run,
                "running_critique",
                "critique",
                f"Running critique for {spec['title']}.",
                document_type=spec["document_type"],
            )

            draft = final_state.get("draft", "")
            _document_response_status, error_status = _drafting_status_from_state(final_state)
            if error_status:
                response_error_status = error_status
            if error_status == "malformed_output":
                draft = ""

            document = await matters_service.upsert_draft_document(
                db,
                matter,
                document_type=spec["document_type"],
                title=spec["title"],
                content=draft,
                status=_document_status(final_state, error_status),
                error_status=error_status,
                revision_count=final_state.get("revision_count", 0),
            )
            documents.append(document)
            matter.draft_content = "\n\n".join(
                f"# {document.title}\n\n{document.content}"
                for document in documents
                if document.content
            )
            matter.drafting_error = response_error_status
            await db.commit()
            await db.refresh(document)
            await record_event(
                db,
                run,
                "document_ready" if draft else "document_failed",
                spec["document_type"],
                (
                    f"{spec['title']} is ready for advocate review."
                    if draft
                    else f"{spec['title']} could not be drafted from the model output."
                ),
                document_type=spec["document_type"],
                error_type=error_status,
            )

        has_generated_content = any(document.content for document in documents)
        if not has_generated_content:
            return await _fail_run(
                db,
                run,
                matter,
                stage="draft",
                error_status=response_error_status or "malformed_output",
                message="Drafting finished without reviewable document content.",
            )

        matter.jurisdiction = request.jurisdiction or matter.jurisdiction
        matter.subcategory = request.subcategory or matter.subcategory
        await matters_service.upsert_citation_evidence(
            db,
            matter,
            [
                {
                    "citation_type": "precedent",
                    "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
                    "source": "eKLR reference corpus",
                    "snippet": "The conditions for grant of an interlocutory injunction include a prima facie case, irreparable injury, and balance of convenience.",
                    "confidence": 0.94,
                    "status": "pending",
                }
            ],
        )
        if matter.workflow_state == "pii_masked":
            await matters_service.transition_matter(
                db,
                matter,
                "draft_generated",
                activity_title="Draft generated",
                activity_detail=(
                    "AI draft reached the revision limit and needs lawyer review."
                    if response_error_status == "max_revisions_failed"
                    else "AI draft documents were generated from masked facts."
                ),
            )
        run.status = "completed"
        run.error_status = response_error_status
        run.finished_at = datetime.now(timezone.utc)
        await record_event(
            db,
            run,
            "completed",
            "completed",
            "Ready for advocate review.",
            error_type=response_error_status,
        )
        logger.info("drafting_run_completed run_id=%s matter_id=%s", run.id, matter.id)
    except Exception as exc:
        error_status = _classify_drafting_error(exc)
        logger.exception("drafting_run_failed run_id=%s status=%s", run.id, error_status)
        await db.rollback()
        failed_run = await get_drafting_run(db, run_id)
        if failed_run is None:
            return None
        return await _fail_run(
            db,
            failed_run,
            failed_run.matter,
            stage="failed",
            error_status=error_status,
            message="Drafting could not complete. Retry after checking retrieval and model availability.",
        )

    await db.refresh(run)
    return run


async def _fail_run(
    db: AsyncSession,
    run: DraftingRun,
    matter: Matter,
    *,
    stage: str,
    error_status: str,
    message: str,
) -> DraftingRun:
    run.status = "failed"
    run.error_status = error_status
    run.finished_at = datetime.now(timezone.utc)
    matter.drafting_error = error_status
    await matters_service.add_activity(
        db,
        matter,
        event_type="draft_failed",
        title="Drafting failed",
        detail=error_status,
    )
    await record_event(
        db,
        run,
        "failed",
        stage,
        message,
        error_type=error_status,
    )
    await db.refresh(run)
    return run


async def stream_drafting_events(
    run_id: int,
    *,
    session_factory=SessionFactory,
    poll_interval: float = 1.0,
) -> AsyncIterator[str]:
    last_id = 0
    while True:
        async with session_factory() as db:
            events = await get_drafting_events(db, run_id, after_id=last_id)
            for event in events:
                last_id = event.id
                yield _sse_payload(event)

            run = await get_drafting_run(db, run_id)
            terminal = run is None or run.status in TERMINAL_RUN_STATUSES

        if terminal:
            break
        await asyncio.sleep(poll_interval)


def response_blocks_from_documents(documents) -> list[GeneratedBlock]:
    return [
        GeneratedBlock(
            id=document.document_type,
            title=document.title,
            content=document.content,
            status=document.status,
        )
        for document in documents
        if document.content
    ]


def _sse_payload(event: DraftingEvent) -> str:
    data = DraftingEventRead.model_validate(event).model_dump_json()
    return f"id: {event.id}\ndata: {data}\n\n"
