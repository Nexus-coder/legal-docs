import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.graph import legal_agent
from src.auth.dependencies import get_current_user
from src.auth.schemas import UserRead
from src.database import get_db
from src.drafting.schemas import DraftingRequest, DraftingResponse, GeneratedBlock
from src.matters import service as matters_service

router = APIRouter()
logger = logging.getLogger(__name__)

INJUNCTION_DRAFT_DOCUMENTS = [
    {
        "document_type": "injunction_motion",
        "title": "Notice of Motion for Temporary Injunction",
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


@router.post("/generate", response_model=DraftingResponse)
async def generate_draft(
    request: DraftingRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserRead, Depends(get_current_user)],
):
    matter = await matters_service.get_user_matter(
        db, user_id=current_user.id, matter_id=request.matter_id
    )
    instructions = matter.masked_facts or request.instructions
    if not instructions or not instructions.strip():
        matter.drafting_error = "empty_context"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="empty_context",
        )

    request.jurisdiction = request.jurisdiction or matter.jurisdiction or matter.division
    request.subcategory = request.subcategory or matter.subcategory or "Temporary Injunction"

    try:
        documents = []
        response_status = "draft_generated"
        response_error_status = None
        legacy_blocks: list[GeneratedBlock] = []

        for spec in INJUNCTION_DRAFT_DOCUMENTS:
            initial_state = _build_initial_state(
                request,
                matter_instructions=instructions,
                document_instruction=spec["instruction"],
            )
            final_state = legal_agent.invoke(initial_state)
            draft = final_state.get("draft", "")
            document_response_status, error_status = _drafting_status_from_state(final_state)
            if error_status:
                response_status = document_response_status
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
            if draft:
                legacy_blocks.append(
                    GeneratedBlock(
                        id=spec["document_type"],
                        title=spec["title"],
                        content=draft,
                        status=_document_status(final_state, error_status),
                    )
                )

        matter.jurisdiction = request.jurisdiction or matter.jurisdiction
        matter.subcategory = request.subcategory or matter.subcategory
        matter.draft_content = "\n\n".join(
            f"# {document.title}\n\n{document.content}"
            for document in documents
            if document.content
        )
        matter.drafting_error = response_error_status
        has_generated_content = any(document.content for document in documents)
        if has_generated_content:
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
        await db.commit()
        await db.refresh(matter)
        for document in documents:
            await db.refresh(document)
        logger.info("draft_generated matter_id=%s user_id=%s", matter.id, current_user.id)
        return DraftingResponse(
            matter_id=matter.id,
            workflow_state=matter.workflow_state,
            status=response_status,
            error_status=response_error_status,
            documents=documents,
            blocks=legacy_blocks,
        )
    except Exception as e:
        error_status = _classify_drafting_error(e)
        matter.drafting_error = error_status
        await matters_service.add_activity(
            db,
            matter,
            event_type="draft_failed",
            title="Drafting failed",
            detail=error_status,
        )
        await db.commit()
        logger.exception("draft_failed matter_id=%s status=%s", matter.id, error_status)
        return DraftingResponse(
            matter_id=matter.id,
            workflow_state=matter.workflow_state,
            status=error_status,
            error_status=error_status,
            documents=[],
            blocks=[
                GeneratedBlock(
                    id="error_block",
                    title="Drafting unavailable",
                    content="Drafting could not complete. Retry after checking retrieval and model availability.",
                    status="error",
                )
            ]
        )


@router.get("/citations")
def get_citations():
    # Keep standard ground-truth format available to the frontend
    return {
        "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
        "held": '"The conditions for the grant of an interlocutory injunction are now well settled in East Africa; first, an applicant must show a prima facie case with a probability of success. Secondly, an interlocutory injunction will not normally be granted unless the applicant might otherwise suffer irreparable injury..."',
    }
