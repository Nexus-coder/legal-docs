import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from collections.abc import AsyncIterator, Callable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import SessionFactory
from src.ingestion.indexer import (
    PineconeDimensionMismatch,
    PineconePreflightError,
    index_markdown,
    validate_pinecone_index_dimension,
)
from src.kenyalaw.fetcher import KenyaLawFetchError, KenyaLawFetcher
from src.kenyalaw.filtering import is_elc_relevant
from src.kenyalaw.models import (
    CaseChunk,
    CaseDocument,
    IngestionError,
    IngestionEvent,
    IngestionRun,
    LegalSource,
)
from src.kenyalaw.parser import ParsedCase, parse_case_html, parse_listing_links
from src.kenyalaw.schemas import IngestionEventRead, IngestionRunCreate

logger = logging.getLogger(__name__)

KENYA_LAW_SOURCE = {
    "name": "Kenya Law",
    "base_url": "https://new.kenyalaw.org",
    "license": "Primary legal text public domain; metadata/publication formats CC BY-SA 4.0",
    "terms_url": "https://www.kenyalaw.org/kl/index.php?id=2161",
}

PINECONE_NAMESPACE = "kenya-law-elc"
TERMINAL_RUN_STATUSES = {"completed", "failed"}
PreflightValidator = Callable[[], object]


class FatalIngestionError(RuntimeError):
    def __init__(self, *, url: str, stage: str, error_type: str, message: str):
        super().__init__(message)
        self.url = url
        self.stage = stage
        self.error_type = error_type
        self.message = message


async def create_ingestion_run(
    db: AsyncSession,
    request: IngestionRunCreate,
) -> IngestionRun:
    run = IngestionRun(
        source=KENYA_LAW_SOURCE["name"],
        scope="elc",
        status="running",
        dry_run=1 if request.dry_run else 0,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    mode = "dry-run" if request.dry_run else "full sync"
    await _record_event(
        db,
        run,
        "started",
        "start",
        f"Created Kenya Law ELC {mode} run for up to {request.max_documents} documents.",
    )
    return run


async def run_ingestion_background(run_id: int, request: IngestionRunCreate) -> None:
    async with SessionFactory() as db:
        await execute_ingestion_run(db, run_id, request)


async def start_ingestion_run(
    db: AsyncSession,
    request: IngestionRunCreate,
    *,
    fetcher: KenyaLawFetcher | None = None,
    preflight_validator: PreflightValidator | None = None,
) -> IngestionRun:
    run = await create_ingestion_run(db, request)
    executed = await execute_ingestion_run(
        db,
        run.id,
        request,
        fetcher=fetcher,
        preflight_validator=preflight_validator,
    )
    return executed or run


async def execute_ingestion_run(
    db: AsyncSession,
    run_id: int,
    request: IngestionRunCreate,
    *,
    fetcher: KenyaLawFetcher | None = None,
    preflight_validator: PreflightValidator | None = None,
) -> IngestionRun | None:
    run = await get_ingestion_run(db, run_id)
    if run is None:
        return None
    fetcher = fetcher or KenyaLawFetcher()
    try:
        if not request.dry_run:
            await _record_event(
                db,
                run,
                "indexing",
                "preflight",
                "Checking Pinecone index dimension before writing vectors.",
            )
            if preflight_validator is None:
                validate_pinecone_index_dimension()
            else:
                preflight_validator()
            await _record_event(
                db,
                run,
                "indexing",
                "preflight",
                "Pinecone index dimension matches the configured embedding model.",
            )
        source = await _get_or_create_source(db)
        urls = await _discover_case_urls(db, run, request, fetcher)
        for url in urls[: request.max_documents]:
            await _process_case_url(
                db,
                run,
                source,
                url,
                fetcher,
                dry_run=request.dry_run,
            )
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        await _record_event(
            db,
            run,
            "completed",
            "verify",
            "Kenya Law ELC ingestion completed.",
        )
    except PineconeDimensionMismatch as exc:
        await _fail_run(
            db,
            run,
            request.start_url,
            "preflight",
            "pinecone_dimension_mismatch",
            str(exc),
        )
        logger.warning("kenyalaw_preflight_failed run_id=%s error=%s", run.id, exc)
    except PineconePreflightError as exc:
        await _fail_run(
            db,
            run,
            request.start_url,
            "preflight",
            "pinecone_preflight_failed",
            str(exc),
        )
        logger.warning("kenyalaw_preflight_failed run_id=%s error=%s", run.id, exc)
    except FatalIngestionError as exc:
        await _fail_run(
            db,
            run,
            exc.url,
            exc.stage,
            exc.error_type,
            exc.message,
        )
        logger.warning(
            "kenyalaw_ingestion_failed run_id=%s url=%s error=%s",
            run.id,
            exc.url,
            exc.message,
        )
    except Exception as exc:
        await _fail_run(
            db,
            run,
            request.start_url,
            "run",
            exc.__class__.__name__,
            str(exc),
        )
        logger.exception("kenyalaw_ingestion_failed run_id=%s", run.id)
    await db.refresh(run)
    return run


async def get_ingestion_run(db: AsyncSession, run_id: int) -> IngestionRun | None:
    result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    return result.scalar_one_or_none()


async def get_ingestion_events(
    db: AsyncSession, run_id: int, *, after_id: int = 0
) -> list[IngestionEvent]:
    result = await db.execute(
        select(IngestionEvent)
        .where(
            IngestionEvent.ingestion_run_id == run_id,
            IngestionEvent.id > after_id,
        )
        .order_by(IngestionEvent.id)
    )
    return list(result.scalars().all())


async def stream_ingestion_events(
    run_id: int,
    *,
    session_factory=SessionFactory,
    poll_interval: float = 1.0,
) -> AsyncIterator[str]:
    last_id = 0
    while True:
        async with session_factory() as db:
            events = await get_ingestion_events(db, run_id, after_id=last_id)
            for event in events:
                last_id = event.id
                yield _sse_payload(event)

            run = await get_ingestion_run(db, run_id)
            terminal = run is None or run.status in TERMINAL_RUN_STATUSES

        if terminal:
            break
        await asyncio.sleep(poll_interval)


async def retry_failed_urls(
    db: AsyncSession,
    run_id: int,
    *,
    fetcher: KenyaLawFetcher | None = None,
) -> IngestionRun | None:
    original = await get_ingestion_run(db, run_id)
    if original is None:
        return None
    result = await db.execute(
        select(IngestionError.url).where(IngestionError.ingestion_run_id == run_id)
    )
    urls = sorted(set(result.scalars().all()))
    retry_run = IngestionRun(
        source=KENYA_LAW_SOURCE["name"],
        scope="elc",
        status="running",
        dry_run=original.dry_run,
        discovered_count=len(urls),
    )
    db.add(retry_run)
    await db.commit()
    await db.refresh(retry_run)
    await _record_event(
        db,
        retry_run,
        "started",
        "start",
        f"Retrying {len(urls)} failed Kenya Law URLs.",
    )

    fetcher = fetcher or KenyaLawFetcher()
    source = await _get_or_create_source(db)
    for url in urls:
        await _process_case_url(
            db,
            retry_run,
            source,
            url,
            fetcher,
            dry_run=bool(original.dry_run),
        )
    retry_run.status = "completed"
    retry_run.finished_at = datetime.now(timezone.utc)
    await _record_event(
        db,
        retry_run,
        "completed",
        "verify",
        "Kenya Law retry run completed.",
    )
    return retry_run


async def get_corpus_stats(db: AsyncSession) -> dict:
    documents = await db.scalar(select(func.count()).select_from(CaseDocument))
    indexed_documents = await db.scalar(
        select(func.count()).select_from(CaseDocument).where(CaseDocument.indexed_at.is_not(None))
    )
    chunks = await db.scalar(select(func.count()).select_from(CaseChunk))
    failed_runs = await db.scalar(
        select(func.count()).select_from(IngestionRun).where(IngestionRun.status == "failed")
    )
    latest_result = await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(1)
    )
    return {
        "documents": documents or 0,
        "indexed_documents": indexed_documents or 0,
        "chunks": chunks or 0,
        "failed_runs": failed_runs or 0,
        "latest_run": latest_result.scalar_one_or_none(),
        "preflight": get_pinecone_preflight_status(),
    }


def get_pinecone_preflight_status() -> dict:
    try:
        result = validate_pinecone_index_dimension()
        return {
            "status": "passed",
            "message": "Pinecone index dimension matches the configured embedding model.",
            "index_name": result.index_name,
            "embedding_model": result.embedding_model,
            "embedding_dimension": result.embedding_dimension,
            "index_dimension": result.index_dimension,
            "error_type": None,
        }
    except PineconeDimensionMismatch as exc:
        return {
            "status": "failed",
            "message": str(exc),
            "index_name": exc.index_name,
            "embedding_model": exc.embedding_model,
            "embedding_dimension": exc.embedding_dimension,
            "index_dimension": exc.index_dimension,
            "error_type": "pinecone_dimension_mismatch",
        }
    except PineconePreflightError as exc:
        return {
            "status": "failed",
            "message": str(exc),
            "error_type": "pinecone_preflight_failed",
        }
    except Exception as exc:
        logger.warning("kenyalaw_preflight_status_unavailable error=%s", exc)
        return {
            "status": "failed",
            "message": str(exc),
            "error_type": exc.__class__.__name__,
        }


async def _record_event(
    db: AsyncSession,
    run: IngestionRun,
    event_type: str,
    stage: str,
    message: str,
    *,
    url: str | None = None,
    error_type: str | None = None,
    counts: dict | None = None,
) -> IngestionEvent:
    event = IngestionEvent(
        ingestion_run_id=run.id,
        event_type=event_type,
        stage=stage,
        message=message,
        url=url,
        error_type=error_type,
        counts=counts or _run_counts(run),
    )
    db.add(run)
    db.add(event)
    await db.commit()
    await db.refresh(run)
    await db.refresh(event)
    return event


async def _fail_run(
    db: AsyncSession,
    run: IngestionRun,
    url: str,
    stage: str,
    error_type: str,
    message: str,
) -> None:
    run.status = "failed"
    run.failed_count += 1
    run.finished_at = datetime.now(timezone.utc)
    db.add(
        IngestionError(
            ingestion_run_id=run.id,
            url=url,
            error_type=error_type,
            message=message,
        )
    )
    await _record_event(
        db,
        run,
        "failed",
        stage,
        message,
        url=url,
        error_type=error_type,
    )


def _run_counts(run: IngestionRun) -> dict[str, int]:
    return {
        "discovered": run.discovered_count,
        "fetched": run.fetched_count,
        "indexed": run.indexed_count,
        "skipped": run.skipped_count,
        "failed": run.failed_count,
    }


def _sse_payload(event: IngestionEvent) -> str:
    data = IngestionEventRead.model_validate(event).model_dump_json()
    return f"id: {event.id}\ndata: {data}\n\n"


async def _get_or_create_source(db: AsyncSession) -> LegalSource:
    result = await db.execute(
        select(LegalSource).where(LegalSource.name == KENYA_LAW_SOURCE["name"])
    )
    source = result.scalar_one_or_none()
    if source:
        return source
    source = LegalSource(**KENYA_LAW_SOURCE)
    db.add(source)
    await db.flush()
    return source


async def _discover_case_urls(
    db: AsyncSession,
    run: IngestionRun,
    request: IngestionRunCreate,
    fetcher: KenyaLawFetcher,
) -> list[str]:
    discovered: list[str] = []
    for page in range(1, request.max_pages + 1):
        url = _page_url(request.start_url, page)
        await _record_event(
            db,
            run,
            "discovering",
            "discover",
            f"Discovering Kenya Law listing page {page}.",
            url=url,
        )
        try:
            result = fetcher.fetch_text(url)
        except KenyaLawFetchError as exc:
            run.failed_count += 1
            db.add(
                IngestionError(
                    ingestion_run_id=run.id,
                    url=exc.url,
                    error_type=exc.error_type,
                    message=str(exc),
                )
            )
            await _record_event(
                db,
                run,
                "failed",
                "discover",
                str(exc),
                url=exc.url,
                error_type=exc.error_type,
            )
            continue
        links = parse_listing_links(result.content, result.url)
        discovered.extend(links)
    unique = sorted(set(discovered))
    run.discovered_count = len(unique)
    await _record_event(
        db,
        run,
        "discovered",
        "discover",
        f"Discovered {len(unique)} unique candidate case URLs.",
    )
    return unique


async def _process_case_url(
    db: AsyncSession,
    run: IngestionRun,
    source: LegalSource,
    url: str,
    fetcher: KenyaLawFetcher,
    *,
    dry_run: bool,
) -> None:
    await _record_event(
        db,
        run,
        "fetching",
        "fetch",
        "Fetching Kenya Law judgment page.",
        url=url,
    )
    try:
        fetched = fetcher.fetch_text(url)
        parsed = parse_case_html(fetched.content, fetched.url)
    except KenyaLawFetchError as exc:
        run.failed_count += 1
        db.add(
            IngestionError(
                ingestion_run_id=run.id,
                url=exc.url,
                error_type=exc.error_type,
                message=str(exc),
            )
        )
        await _record_event(
            db,
            run,
            "failed",
            "fetch",
            str(exc),
            url=exc.url,
            error_type=exc.error_type,
        )
        return
    except Exception as exc:
        run.failed_count += 1
        db.add(
            IngestionError(
                ingestion_run_id=run.id,
                url=url,
                error_type="parse_error",
                message=str(exc),
            )
        )
        await _record_event(
            db,
            run,
            "failed",
            "filter",
            str(exc),
            url=url,
            error_type="parse_error",
        )
        return

    if not is_elc_relevant(title=parsed.title, court=parsed.court, text=parsed.text[:5000]):
        run.skipped_count += 1
        await _record_event(
            db,
            run,
            "skipped",
            "filter",
            "Skipped non-ELC judgment after relevance filtering.",
            url=parsed.canonical_url,
        )
        return
    run.fetched_count += 1
    await _record_event(
        db,
        run,
        "filtered",
        "filter",
        "Accepted ELC-relevant judgment.",
        url=parsed.canonical_url,
    )
    if dry_run:
        run.indexed_count += 1
        await _record_event(
            db,
            run,
            "indexed",
            "verify",
            "Dry-run accepted this judgment; vector upload was skipped.",
            url=parsed.canonical_url,
        )
        return

    document = await _upsert_case_document(db, source, parsed)
    if document.indexed_at and document.normalized_hash == parsed.normalized_hash:
        run.skipped_count += 1
        await _record_event(
            db,
            run,
            "skipped",
            "index",
            "Skipped unchanged judgment already indexed in Pinecone.",
            url=parsed.canonical_url,
        )
        return
    await _replace_chunks(db, document, parsed)
    await _record_event(
        db,
        run,
        "indexing",
        "index",
        "Uploading judgment chunks to Pinecone.",
        url=parsed.canonical_url,
    )
    try:
        node_count = index_markdown(
            _markdown_for(parsed), _metadata_for(parsed), namespace=PINECONE_NAMESPACE
        )
    except Exception as exc:
        raise FatalIngestionError(
            url=parsed.canonical_url,
            stage="index",
            error_type=exc.__class__.__name__,
            message=str(exc),
        ) from exc
    document.indexed_at = datetime.now(timezone.utc)
    document.fetch_status = "indexed"
    run.indexed_count += 1
    await _record_event(
        db,
        run,
        "indexed",
        "index",
        f"Indexed {node_count} vector nodes for this judgment.",
        url=parsed.canonical_url,
        counts={**_run_counts(run), "vector_nodes": node_count},
    )
    logger.info("kenyalaw_case_indexed document_id=%s url=%s", document.id, parsed.canonical_url)


async def _upsert_case_document(
    db: AsyncSession, source: LegalSource, parsed: ParsedCase
) -> CaseDocument:
    result = await db.execute(
        select(CaseDocument).where(CaseDocument.canonical_url == parsed.canonical_url)
    )
    document = result.scalar_one_or_none()
    if document is None:
        document = CaseDocument(source_id=source.id, canonical_url=parsed.canonical_url)
        db.add(document)

    document.title = parsed.title
    document.neutral_citation = parsed.neutral_citation
    document.court = parsed.court
    document.judgment_date = parsed.judgment_date
    document.topic_tags = json.dumps(parsed.topic_tags)
    document.source_format = parsed.source_format
    document.raw_hash = parsed.raw_hash
    document.normalized_hash = parsed.normalized_hash
    document.fetch_status = "fetched"
    document.last_seen_at = datetime.now(timezone.utc)
    await db.flush()
    return document


async def _replace_chunks(db: AsyncSession, document: CaseDocument, parsed: ParsedCase) -> None:
    await db.execute(delete(CaseChunk).where(CaseChunk.case_document_id == document.id))
    chunks = _chunk_text(parsed.text)
    db.add_all(
        [
            CaseChunk(
                case_document_id=document.id,
                chunk_index=index,
                text=chunk,
                text_hash=hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                section_label=_section_label(chunk),
                pinecone_vector_id=f"kenyalaw:{document.id}:{index}",
            )
            for index, chunk in enumerate(chunks)
        ]
    )
    await db.flush()


def _metadata_for(parsed: ParsedCase) -> dict:
    return {
        "source": "Kenya Law",
        "source_url": parsed.canonical_url,
        "canonical_url": parsed.canonical_url,
        "title": parsed.title,
        "neutral_citation": parsed.neutral_citation or "",
        "court": parsed.court or "",
        "judgment_date": parsed.judgment_date or "",
        "topic_tags": ",".join(parsed.topic_tags),
        "document_hash": parsed.normalized_hash,
        "corpus_scope": "elc",
    }


def _markdown_for(parsed: ParsedCase) -> str:
    metadata = _metadata_for(parsed)
    frontmatter = "\n".join(f"{key}: {value}" for key, value in metadata.items())
    return f"# {parsed.title}\n\n{frontmatter}\n\n{parsed.text}"


def _section_label(text: str) -> str:
    lowered = text[:500].lower()
    for label in ("facts", "issues", "analysis", "holding", "orders", "ruling", "judgment"):
        if label in lowered:
            return label
    return "unknown"


def _chunk_text(text: str, *, chunk_size: int = 1500, overlap: int = 150) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= chunk_size:
            current = paragraph
            continue
        for start in range(0, len(paragraph), max(1, chunk_size - overlap)):
            chunks.append(paragraph[start : start + chunk_size])
        current = ""
    if current:
        chunks.append(current)
    return chunks or [text[:chunk_size]]


def _page_url(start_url: str, page: int) -> str:
    if page == 1:
        return start_url
    parsed = urlparse(start_url)
    query = dict(parse_qsl(parsed.query))
    query["page"] = str(page)
    return urlunparse(parsed._replace(query=urlencode(query)))
