import asyncio
import json
import logging
import re
from collections.abc import AsyncIterator
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.agent.graph import legal_agent
from src.database import SessionFactory
from src.drafting.editor import (
    editor_json_to_docx,
    editor_json_to_plain_text,
    editor_json_to_preview_html,
    text_to_editor_json,
    validate_editor_json,
)
from src.drafting.models import DraftingEvent, DraftingRun
from src.drafting.packets import (
    INJUNCTION_PACKET,
    canonical_subcategory,
    default_pleading_type,
    drafting_packet_for,
    supported_subcategories,
)
from src.drafting.schemas import DraftingEventRead, DraftingRequest, GeneratedBlock
from src.matters import service as matters_service
from src.matters.models import CitationEvidence, DraftDocument, DraftDocumentRevision, Matter

logger = logging.getLogger(__name__)

TERMINAL_RUN_STATUSES = {"completed", "failed"}

INJUNCTION_DRAFT_DOCUMENTS = [
    {
        "document_type": spec.document_type,
        "title": spec.title,
        "activity_title": spec.activity_title,
        "instruction": spec.instruction,
    }
    for spec in INJUNCTION_PACKET.documents
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
    error_status = final_state.get("error_status")
    if error_status:
        return error_status, error_status
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
    subcategory = canonical_subcategory(
        request.subcategory or matter.subcategory or "Temporary Injunction"
    )
    run = DraftingRun(
        matter_id=matter.id,
        user_id=matter.user_id,
        status="running",
        jurisdiction=request.jurisdiction or matter.jurisdiction or matter.division,
        subcategory=subcategory,
        pleading_type=request.pleading_type or default_pleading_type(subcategory),
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


async def get_user_draft_document(
    db: AsyncSession,
    *,
    user_id: int,
    document_id: int,
) -> DraftDocument:
    result = await db.execute(
        select(DraftDocument)
        .join(Matter, DraftDocument.matter_id == Matter.id)
        .where(DraftDocument.id == document_id, Matter.user_id == user_id)
        .options(selectinload(DraftDocument.matter))
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft document not found")
    return document


async def save_draft_document_editor_json(
    db: AsyncSession,
    *,
    user_id: int,
    document_id: int,
    editor_json: dict,
    expected_revision: int,
    revision_type: str = "manual",
) -> DraftDocument:
    document = await get_user_draft_document(db, user_id=user_id, document_id=document_id)
    current_revision = document.edit_revision or 0
    if expected_revision != current_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="stale_revision",
        )
    allowed_evidence_ids = await _matter_evidence_ids(db, document.matter_id)
    validated_json = validate_editor_json(editor_json, allowed_evidence_ids)
    content = editor_json_to_plain_text(validated_json)
    now = datetime.now(timezone.utc)
    document.editor_json = validated_json
    document.content = content
    document.edit_revision = current_revision + 1
    document.last_edited_at = now
    document.last_edited_by = user_id
    document.updated_at = now
    document.status = "draft" if document.status == "verified" else document.status
    db.add(
        DraftDocumentRevision(
            draft_document_id=document.id,
            user_id=user_id,
            revision_type=revision_type if revision_type in {"manual", "autosave", "restore"} else "manual",
            edit_revision=document.edit_revision,
            editor_json=validated_json,
            content=content,
        )
    )
    await db.commit()
    await db.refresh(document)
    await _refresh_matter_draft_content(db, document.matter_id)
    await db.commit()
    await db.refresh(document)
    return document


async def draft_document_export_preview(
    db: AsyncSession,
    *,
    user_id: int,
    document_id: int,
) -> str:
    document = await get_user_draft_document(db, user_id=user_id, document_id=document_id)
    editor_json = document.editor_json or text_to_editor_json(document.content)
    allowed_evidence_ids = await _matter_evidence_ids(db, document.matter_id)
    validated_json = validate_editor_json(editor_json, allowed_evidence_ids)
    return editor_json_to_preview_html(validated_json)


async def draft_document_export_docx(
    db: AsyncSession,
    *,
    user_id: int,
    document_id: int,
) -> tuple[str, bytes]:
    document = await get_user_draft_document(db, user_id=user_id, document_id=document_id)
    editor_json = document.editor_json or text_to_editor_json(document.content)
    allowed_evidence_ids = await _matter_evidence_ids(db, document.matter_id)
    validated_json = validate_editor_json(editor_json, allowed_evidence_ids)
    filename = f"{document.title.lower().replace(' ', '-')}-{document.id}.docx"
    return filename, editor_json_to_docx(validated_json)


async def _matter_evidence_ids(db: AsyncSession, matter_id: int) -> set[int]:
    result = await db.execute(
        select(CitationEvidence.id).where(CitationEvidence.matter_id == matter_id)
    )
    return set(result.scalars().all())


def _retrieved_contexts_from_state(final_state: dict) -> list[dict[str, Any]]:
    contexts = final_state.get("context") or []
    return [context for context in contexts if isinstance(context, dict)]


def _evidence_items_from_contexts(
    contexts: list[dict[str, Any]],
    *,
    draft_content: str,
    max_items: int = 8,
) -> list[dict[str, Any]]:
    evidence_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for context in sorted(
        contexts,
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    ):
        metadata = dict(context.get("metadata") or {})
        title = _metadata_value(metadata, "title", "canonical_title")
        source_url = _metadata_value(metadata, "source_url", "canonical_url", "url")
        identity = source_url or title
        if not identity or identity in seen:
            continue
        seen.add(identity)

        score = max(0.0, min(1.0, float(context.get("score") or 0.0)))
        cited = _authority_appears_in_draft(draft_content, metadata)
        confidence = round((score * 0.8) + (0.2 if cited else 0.0), 4)
        evidence_items.append(
            {
                "citation_type": "precedent",
                "title": title or "Retrieved Kenya Law authority",
                "source": _metadata_value(metadata, "source") or "Kenya Law",
                "source_url": source_url,
                "neutral_citation": _metadata_value(metadata, "neutral_citation"),
                "court": _metadata_value(metadata, "court"),
                "judgment_date": _metadata_value(metadata, "judgment_date"),
                "snippet": _bounded_context_snippet(str(context.get("text") or "")),
                "confidence": confidence,
                "confidence_breakdown": json.dumps(
                    {
                        "retrieval_score": round(score, 4),
                        "cited_in_draft": cited,
                        "source_url_present": bool(source_url),
                    }
                ),
                "status": "pending" if cited else "needs_review",
            }
        )
        if len(evidence_items) >= max_items:
            break
    return evidence_items


def _metadata_value(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _authority_appears_in_draft(draft_content: str, metadata: dict[str, Any]) -> bool:
    draft_lower = (draft_content or "").lower()
    for key in ("neutral_citation", "title"):
        value = _metadata_value(metadata, key)
        if not value:
            continue
        lowered = value.lower()
        if len(lowered) >= 8 and lowered in draft_lower:
            return True
        title_prefix = re.split(r"\s+\(", lowered, maxsplit=1)[0].strip()
        if len(title_prefix) >= 12 and title_prefix in draft_lower:
            return True
    return False


def _bounded_context_snippet(text: str, limit: int = 700) -> str:
    usable_text = _strip_index_metadata(text)
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", usable_text)
        if paragraph.strip()
    ]
    snippet = next((paragraph for paragraph in paragraphs if len(paragraph) >= 80), "")
    if not snippet and paragraphs:
        snippet = paragraphs[0]
    if not snippet:
        snippet = "Retrieved authority did not include readable text content."
    return snippet[:limit]


def _strip_index_metadata(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n")
    lines = []
    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("# "):
            continue
        if re.match(
            r"^(source|source_url|canonical_url|title|neutral_citation|court|"
            r"judgment_date|topic_tags|source_document_url|source_format|"
            r"extraction_status|text_quality_score|document_hash|corpus_scope):\s*",
            stripped,
            flags=re.IGNORECASE,
        ):
            continue
        lines.append(stripped)
    return "\n\n".join(lines).strip()


def _link_documents_to_evidence(
    documents: list[DraftDocument],
    evidence_items: list[CitationEvidence],
) -> None:
    for document in documents:
        if not document.content:
            continue
        editor_json = text_to_editor_json(document.content)
        linked_json = _link_editor_json_to_evidence(editor_json, evidence_items)
        document.editor_json = linked_json
        document.generated_editor_json = linked_json


def _link_editor_json_to_evidence(
    editor_json: dict[str, Any],
    evidence_items: list[CitationEvidence],
) -> dict[str, Any]:
    labels = _citation_labels(evidence_items)
    if not labels:
        return editor_json

    linked = deepcopy(editor_json)
    _link_editor_node(linked, labels)
    return linked


def _citation_labels(
    evidence_items: list[CitationEvidence],
) -> list[tuple[str, int]]:
    labels: list[tuple[str, int]] = []
    for evidence in evidence_items:
        for value in (evidence.neutral_citation, evidence.title):
            if value and len(value.strip()) >= 8:
                labels.append((value.strip(), evidence.id))
        title_prefix = re.split(r"\s+\(", evidence.title or "", maxsplit=1)[0].strip()
        if len(title_prefix) >= 12:
            labels.append((title_prefix, evidence.id))

    deduped: dict[str, int] = {}
    for label, evidence_id in labels:
        deduped.setdefault(label.lower(), evidence_id)
    return sorted(
        ((label, evidence_id) for label, evidence_id in deduped.items()),
        key=lambda item: len(item[0]),
        reverse=True,
    )


def _link_editor_node(node: dict[str, Any], labels: list[tuple[str, int]]) -> None:
    if node.get("type") == "text":
        replacement = _linked_text_nodes(node, labels)
        if len(replacement) == 1 and replacement[0] is node:
            return
        node.clear()
        node.update(replacement[0])
        node["_split_remainder"] = replacement[1:]
        return

    content = node.get("content") or []
    linked_content = []
    for child in content:
        if not isinstance(child, dict):
            linked_content.append(child)
            continue
        _link_editor_node(child, labels)
        remainder = child.pop("_split_remainder", [])
        linked_content.append(child)
        linked_content.extend(remainder)
    if linked_content:
        node["content"] = linked_content


def _linked_text_nodes(
    node: dict[str, Any],
    labels: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    text = node.get("text", "")
    if not isinstance(text, str) or not text:
        return [node]

    parts: list[dict[str, Any]] = []
    cursor = 0
    lower_text = text.lower()
    while cursor < len(text):
        match = _next_citation_match(lower_text, cursor, labels)
        if match is None:
            parts.append(_copy_text_node(node, text[cursor:]))
            break
        start, end, evidence_id = match
        if start > cursor:
            parts.append(_copy_text_node(node, text[cursor:start]))
        parts.append(
            _copy_text_node(
                node,
                text[start:end],
                citation_evidence_id=evidence_id,
            )
        )
        cursor = end

    return [part for part in parts if part.get("text")] or [node]


def _next_citation_match(
    lower_text: str,
    cursor: int,
    labels: list[tuple[str, int]],
) -> tuple[int, int, int] | None:
    best: tuple[int, int, int] | None = None
    for label, evidence_id in labels:
        start = lower_text.find(label, cursor)
        if start < 0:
            continue
        end = start + len(label)
        candidate = (start, end, evidence_id)
        if best is None or candidate[0] < best[0] or (
            candidate[0] == best[0] and candidate[1] > best[1]
        ):
            best = candidate
    return best


def _copy_text_node(
    source: dict[str, Any],
    text: str,
    *,
    citation_evidence_id: int | None = None,
) -> dict[str, Any]:
    copied = {"type": "text", "text": text}
    marks = deepcopy(source.get("marks") or [])
    if citation_evidence_id is not None:
        marks.append(
            {
                "type": "citationRef",
                "attrs": {"evidenceId": citation_evidence_id},
            }
        )
    if marks:
        copied["marks"] = marks
    return copied


async def _refresh_matter_draft_content(db: AsyncSession, matter_id: int) -> None:
    result = await db.execute(
        select(DraftDocument)
        .where(DraftDocument.matter_id == matter_id)
        .order_by(DraftDocument.id)
    )
    documents = result.scalars().all()
    matter = await db.get(Matter, matter_id)
    if matter is None:
        return
    matter.draft_content = "\n\n".join(
        f"# {document.title}\n\n{document.content}"
        for document in documents
        if document.content
    )


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
        subcategory=canonical_subcategory(
            run.subcategory or matter.subcategory or "Temporary Injunction"
        ),
        pleading_type=run.pleading_type
        or default_pleading_type(run.subcategory or matter.subcategory),
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

    packet = drafting_packet_for(
        subcategory=request.subcategory,
        pleading_type=request.pleading_type,
    )
    if packet is None:
        return await _fail_run(
            db,
            run,
            matter,
            stage="select_packet",
            error_status="unsupported_subcategory",
            message=(
                "Drafting is not configured for this subcategory and pleading type. "
                f"Supported subcategories: {', '.join(sorted(supported_subcategories()))}."
            ),
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
        retrieved_contexts: list[dict[str, Any]] = []
        response_error_status = None
        for spec in packet.documents:
            await record_event(
                db,
                run,
                "drafting_document",
                spec.document_type,
                spec.activity_title,
                document_type=spec.document_type,
            )
            initial_state = _build_initial_state(
                request,
                matter_instructions=instructions,
                document_instruction=spec.instruction,
            )
            final_state = await asyncio.to_thread(legal_agent.invoke, initial_state)
            retrieved_contexts.extend(_retrieved_contexts_from_state(final_state))
            await record_event(
                db,
                run,
                "running_critique",
                "critique",
                f"Running critique for {spec.title}.",
                document_type=spec.document_type,
            )

            draft = final_state.get("draft", "")
            _document_response_status, error_status = _drafting_status_from_state(final_state)
            if error_status == "retrieval_failed":
                return await _fail_run(
                    db,
                    run,
                    matter,
                    stage="authorities",
                    error_status=error_status,
                    message="Drafting did not retrieve any authority context to ground the draft.",
                )
            if error_status:
                response_error_status = error_status
            if error_status == "malformed_output":
                draft = ""

            document = await matters_service.upsert_draft_document(
                db,
                matter,
                document_type=spec.document_type,
                title=spec.title,
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
                spec.document_type,
                (
                    f"{spec.title} is ready for advocate review."
                    if draft
                    else f"{spec.title} could not be drafted from the model output."
                ),
                document_type=spec.document_type,
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
        evidence_items = _evidence_items_from_contexts(
            retrieved_contexts,
            draft_content=matter.draft_content or "",
        )
        if not evidence_items:
            return await _fail_run(
                db,
                run,
                matter,
                stage="authorities",
                error_status="retrieval_failed",
                message="Drafting did not retrieve any authority context to ground the draft.",
            )
        evidence = await matters_service.upsert_citation_evidence(db, matter, evidence_items)
        await db.flush()
        _link_documents_to_evidence(documents, evidence)
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
