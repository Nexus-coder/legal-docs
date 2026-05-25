import unittest
import zipfile
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.models import User
from src.models import Base
from src.matters.schemas import MatterCreate, MatterRead
from src.matters import service
from src.matters.models import CitationEvidence, DraftDocumentRevision
from src.drafting.editor import validate_editor_json
from src.drafting.router import _classify_drafting_error, _drafting_status_from_state
from src.drafting.schemas import DraftingRequest
from src.drafting import service as drafting_service
from src.ingestion.indexer import (
    PineconeDimensionMismatch,
    embedding_safe_nodes,
    validate_pinecone_index_dimension,
)
from src.kenyalaw.extraction import (
    REJECTED_SHELL_TEXT,
    VALID_EXTRACTION,
    assess_judgment_text_quality,
    extract_judgment_source,
    extract_source_text,
    resolve_source_candidates,
)
from src.kenyalaw.fetcher import FetchBinaryResult, FetchResult, KenyaLawFetchError
from src.kenyalaw.filtering import is_elc_relevant
from src.kenyalaw.models import (
    CaseChunk,
    CaseDocument,
    IngestionError,
    IngestionEvent,
    LegalSource,
)
from src.kenyalaw.parser import parse_case_html
from src.kenyalaw.schemas import IngestionRunCreate
from src.kenyalaw import service as kenyalaw_service
from src.kenyalaw import verifier as kenyalaw_verifier


class FakeKenyaLawFetcher:
    def __init__(self, pages):
        self.pages = pages

    def fetch_text(self, url):
        for key, content in sorted(self.pages.items(), key=lambda item: len(item[0]), reverse=True):
            if key in url:
                body, content_type = self._payload(content)
                if isinstance(body, bytes):
                    body = body.decode("utf-8", errors="replace")
                return FetchResult(url=url, content=body, content_type=content_type)
        raise AssertionError(f"Unexpected fetch URL: {url}")

    def fetch_bytes(self, url):
        for key, content in sorted(self.pages.items(), key=lambda item: len(item[0]), reverse=True):
            if key in url:
                body, content_type = self._payload(content)
                if isinstance(body, str):
                    body = body.encode("utf-8")
                return FetchBinaryResult(url=url, content=body, content_type=content_type)
        raise KenyaLawFetchError(url, "http_404", "Not found")

    @staticmethod
    def _payload(content):
        if isinstance(content, tuple):
            return content
        return content, "text/html"


def realistic_judgment_text() -> str:
    return """
    REPUBLIC OF KENYA
    IN THE ENVIRONMENT AND LAND COURT AT NAIROBI
    Mwangi v Kamau [2024] KEELC 10 (KLR)

    JUDGMENT

    1. The plaintiff filed this suit seeking a permanent injunction over land parcel LR 1.
    The defendant opposed the application and contended that the title was acquired lawfully.

    2. The court has considered the pleadings, the evidence on occupation, and the rival
    submissions on whether the applicant has established a prima facie case.

    3. The dispute concerns ownership, use, and possession of land. The Environment and
    Land Court therefore has jurisdiction to determine the claim and the application.

    4. I find that the plaintiff has shown a registrable interest in the parcel and that
    damages would not be an adequate remedy if the land is alienated before trial.

    5. The application is allowed. The defendant is restrained from transferring,
    charging, or interfering with LR 1 pending hearing of the suit. Costs shall abide
    the outcome of the main suit.

    DATED, SIGNED AND DELIVERED AT NAIROBI THIS 5TH DAY OF FEBRUARY 2024.
    """


def minimal_docx(text: str) -> bytes:
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in text.strip().splitlines()
        if line.strip()
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>'
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


class MatterWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _create_user(self, db, email="advocate@example.test"):
        user = User(
            email=email,
            full_name="Advocate Test",
            firm_name="Test Firm",
            hashed_password="not-used",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def test_valid_invalid_duplicate_and_stale_transitions(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-1", division="ELC"),
            )

            await service.transition_matter(db, matter, "facts_entered")
            self.assertEqual(matter.workflow_state, "facts_entered")

            duplicate = await service.transition_matter(db, matter, "facts_entered")
            self.assertIs(duplicate, matter)

            with self.assertRaises(HTTPException) as invalid:
                await service.transition_matter(db, matter, "draft_generated")
            self.assertEqual(invalid.exception.status_code, 409)

            with self.assertRaises(HTTPException) as stale:
                await service.transition_matter(
                    db,
                    matter,
                    "pii_masked",
                    expected_state="created",
                )
            self.assertEqual(stale.exception.status_code, 409)

    async def test_ownership_scope_and_zero_dashboard_stats(self):
        async with self.Session() as db:
            owner = await self._create_user(db, "owner@example.test")
            other = await self._create_user(db, "other@example.test")
            matter = await service.create_matter(
                db,
                owner.id,
                MatterCreate(case_number="ELC-2", division="ELC"),
            )

            found = await service.get_user_matter(db, owner.id, matter.id)
            self.assertEqual(found.id, matter.id)

            with self.assertRaises(HTTPException) as not_found:
                await service.get_user_matter(db, other.id, matter.id)
            self.assertEqual(not_found.exception.status_code, 404)

            stats = await service.get_user_dashboard_stats(db, owner.id)
            self.assertEqual(stats["citations_verified"], {"current": 0, "total": 0})

    async def test_matter_response_serializes_without_system_tzdata(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-serialization", division="ELC"),
            )

            payload = MatterRead.model_validate(matter).model_dump_json()
            self.assertIn('"created_at"', payload)
            self.assertIn("+0000", payload)

    async def test_pii_and_citation_results_are_persisted(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-3", division="ELC"),
            )
            matter.raw_facts = "Jane Doe occupied LR 1."
            matter.masked_facts = "[PERSON] occupied [LOCATION]."
            matter.pii_entity_count = 2
            await service.transition_matter(db, matter, "facts_entered")
            await service.transition_matter(db, matter, "pii_masked")
            await service.upsert_citation_evidence(
                db,
                matter,
                [
                    {
                        "citation_type": "statute",
                        "title": "Limitation of Actions Act",
                        "snippet": "Twelve years from accrual.",
                        "confidence": 1.0,
                        "status": "verified",
                    }
                ],
            )
            await db.commit()

            refreshed = await service.get_user_matter(
                db, user.id, matter.id, include_related=True
            )
            self.assertEqual(refreshed.masked_facts, "[PERSON] occupied [LOCATION].")
            self.assertEqual(refreshed.verification_done, 1)
            self.assertEqual(refreshed.verification_total, 1)
            self.assertEqual(len(refreshed.citation_evidence), 1)

    async def test_draft_documents_are_matter_owned_and_upserted(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-4", division="ELC"),
            )

            first = await service.upsert_draft_document(
                db,
                matter,
                document_type="injunction_motion",
                title="Notice of Motion",
                content="Initial motion draft.",
                status="draft",
                error_status=None,
                revision_count=1,
            )
            await db.commit()
            await db.refresh(first)

            updated = await service.upsert_draft_document(
                db,
                matter,
                document_type="injunction_motion",
                title="Notice of Motion",
                content="Updated motion draft.",
                status="verified",
                error_status=None,
                revision_count=2,
            )
            affidavit = await service.upsert_draft_document(
                db,
                matter,
                document_type="supporting_affidavit",
                title="Supporting Affidavit",
                content="Affidavit draft.",
                status="needs_review",
                error_status="max_revisions_failed",
                revision_count=3,
            )
            await db.commit()

            self.assertEqual(updated.id, first.id)
            self.assertNotEqual(affidavit.id, first.id)

            refreshed = await service.get_user_matter(
                db, user.id, matter.id, include_related=True
            )
            self.assertEqual(len(refreshed.draft_documents), 2)
            by_type = {document.document_type: document for document in refreshed.draft_documents}
            self.assertEqual(by_type["injunction_motion"].content, "Updated motion draft.")
            self.assertEqual(by_type["injunction_motion"].status, "verified")
            self.assertEqual(by_type["supporting_affidavit"].error_status, "max_revisions_failed")

    def test_tiptap_json_validation_rejects_unknown_and_script_payloads(self):
        valid = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "Giella",
                            "marks": [{"type": "citationRef", "attrs": {"evidenceId": 10}}],
                        }
                    ],
                }
            ],
        }
        self.assertEqual(validate_editor_json(valid, {10})["type"], "doc")

        with self.assertRaises(HTTPException) as unknown:
            validate_editor_json({"type": "doc", "content": [{"type": "html"}]}, set())
        self.assertEqual(unknown.exception.status_code, 422)

        with self.assertRaises(HTTPException) as script:
            validate_editor_json(
                {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "<script>alert(1)</script>"}],
                        }
                    ],
                },
                set(),
            )
        self.assertEqual(script.exception.status_code, 422)

    async def test_save_editor_json_updates_revision_and_plain_text(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-editor-save", division="ELC"),
            )
            evidence = await service.upsert_citation_evidence(
                db,
                matter,
                [
                    {
                        "citation_type": "precedent",
                        "title": "Giella v Cassman Brown",
                        "snippet": "Injunction test.",
                        "confidence": 1.0,
                        "status": "verified",
                    }
                ],
            )
            document = await service.upsert_draft_document(
                db,
                matter,
                document_type="injunction_motion",
                title="Notice of Motion",
                content="Initial draft.",
                status="draft",
                error_status=None,
                revision_count=1,
            )
            await db.commit()
            await db.refresh(document)
            await db.refresh(evidence[0])

            saved = await drafting_service.save_draft_document_editor_json(
                db,
                user_id=user.id,
                document_id=document.id,
                expected_revision=0,
                editor_json={
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Edited draft with "},
                                {
                                    "type": "text",
                                    "text": "Giella",
                                    "marks": [
                                        {
                                            "type": "citationRef",
                                            "attrs": {"evidenceId": evidence[0].id},
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                },
            )

            self.assertEqual(saved.content, "Edited draft with Giella")
            self.assertEqual(saved.edit_revision, 1)
            self.assertEqual(saved.last_edited_by, user.id)
            revisions = (
                await db.execute(
                    select(DraftDocumentRevision).where(
                        DraftDocumentRevision.draft_document_id == document.id
                    )
                )
            ).scalars().all()
            self.assertEqual([revision.revision_type for revision in revisions], ["generated", "manual"])

    async def test_save_editor_json_rejects_stale_and_cross_matter_citation_refs(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-editor-owned", division="ELC"),
            )
            other_matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-editor-other", division="ELC"),
            )
            foreign_evidence = CitationEvidence(
                matter_id=other_matter.id,
                citation_type="precedent",
                title="Other case",
                snippet="Other matter.",
                confidence=1.0,
            )
            db.add(foreign_evidence)
            document = await service.upsert_draft_document(
                db,
                matter,
                document_type="injunction_motion",
                title="Notice of Motion",
                content="Initial draft.",
                status="draft",
                error_status=None,
                revision_count=1,
            )
            await db.commit()
            await db.refresh(document)
            await db.refresh(foreign_evidence)

            with self.assertRaises(HTTPException) as stale:
                await drafting_service.save_draft_document_editor_json(
                    db,
                    user_id=user.id,
                    document_id=document.id,
                    expected_revision=99,
                    editor_json={"type": "doc", "content": [{"type": "paragraph"}]},
                )
            self.assertEqual(stale.exception.status_code, 409)
            self.assertEqual(stale.exception.detail, "stale_revision")

            with self.assertRaises(HTTPException) as invalid_citation:
                await drafting_service.save_draft_document_editor_json(
                    db,
                    user_id=user.id,
                    document_id=document.id,
                    expected_revision=0,
                    editor_json={
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Other case",
                                        "marks": [
                                            {
                                                "type": "citationRef",
                                                "attrs": {"evidenceId": foreign_evidence.id},
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    },
                )
            self.assertEqual(invalid_citation.exception.status_code, 422)

    async def test_export_preview_and_docx_use_edited_content(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-export", division="ELC"),
            )
            document = await service.upsert_draft_document(
                db,
                matter,
                document_type="injunction_motion",
                title="Notice of Motion",
                content="Initial draft.",
                status="draft",
                error_status=None,
                revision_count=1,
            )
            await db.commit()
            await db.refresh(document)

            await drafting_service.save_draft_document_editor_json(
                db,
                user_id=user.id,
                document_id=document.id,
                expected_revision=0,
                editor_json={
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Edited export text."}],
                        }
                    ],
                },
            )
            preview = await drafting_service.draft_document_export_preview(
                db,
                user_id=user.id,
                document_id=document.id,
            )
            _, docx_payload = await drafting_service.draft_document_export_docx(
                db,
                user_id=user.id,
                document_id=document.id,
            )

            self.assertIn("Edited export text.", preview)
            with zipfile.ZipFile(BytesIO(docx_payload)) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Edited export text.", document_xml)

    def test_drafting_error_statuses_are_safe_and_named(self):
        self.assertEqual(
            _classify_drafting_error(RuntimeError("Pinecone retrieval timeout")),
            "retrieval_failed",
        )
        self.assertEqual(
            _classify_drafting_error(RuntimeError("OpenAI API rate limit")),
            "model_failed",
        )
        self.assertEqual(
            _classify_drafting_error(RuntimeError("revision loop exceeded")),
            "max_revisions_failed",
        )
        self.assertEqual(
            _classify_drafting_error(RuntimeError("unexpected parser shape")),
            "malformed_output",
        )

    def test_max_revision_state_preserves_draft_as_reviewable(self):
        status, error = _drafting_status_from_state(
            {
                "draft": "A usable but imperfect pleading draft.",
                "passed_critique": False,
                "revision_count": 3,
            }
        )

        self.assertEqual(status, "max_revisions_failed")
        self.assertEqual(error, "max_revisions_failed")

    async def test_drafting_run_creation_records_started_event(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-run-start", division="ELC"),
            )
            request = DraftingRequest(
                matter_id=matter.id,
                jurisdiction="ELC",
                subcategory="Temporary Injunction",
            )

            run = await drafting_service.create_drafting_run(
                db,
                matter=matter,
                request=request,
            )
            events = await drafting_service.get_drafting_events(db, run.id)

            self.assertEqual(run.status, "running")
            self.assertEqual(events[0].event_type, "started")
            self.assertEqual(events[0].stage, "start")

    async def test_completed_drafting_run_streams_historical_events_in_order(self):
        class FakeLegalAgent:
            def invoke(self, state):
                title = (
                    "Supporting Affidavit"
                    if "Supporting Affidavit" in state["request"]["instructions"]
                    else "Notice of Motion"
                )
                return {
                    "draft": f"{title} draft from masked facts.",
                    "feedback": "PASS",
                    "revision_count": 1,
                    "passed_critique": True,
                }

        original_agent = drafting_service.legal_agent
        drafting_service.legal_agent = FakeLegalAgent()
        try:
            async with self.Session() as db:
                user = await self._create_user(db)
                matter = await service.create_matter(
                    db,
                    user.id,
                    MatterCreate(case_number="ELC-run-complete", division="ELC"),
                )
                matter.masked_facts = "[PERSON] seeks to preserve [LOCATION]."
                await service.transition_matter(db, matter, "facts_entered")
                await service.transition_matter(db, matter, "pii_masked")
                request = DraftingRequest(
                    matter_id=matter.id,
                    jurisdiction="ELC",
                    subcategory="Temporary Injunction",
                )
                run = await drafting_service.create_drafting_run(
                    db,
                    matter=matter,
                    request=request,
                )
                completed = await drafting_service.execute_drafting_run(db, run.id)

                self.assertEqual(completed.status, "completed")
                self.assertEqual(matter.workflow_state, "draft_generated")

            chunks = []
            async for chunk in drafting_service.stream_drafting_events(
                run.id,
                session_factory=self.Session,
                poll_interval=0,
            ):
                chunks.append(chunk)
            stream_payload = "".join(chunks)
            self.assertIn('"event_type":"started"', stream_payload)
            self.assertIn('"event_type":"completed"', stream_payload)
            self.assertLess(
                stream_payload.index('"event_type":"started"'),
                stream_payload.index('"event_type":"completed"'),
            )
        finally:
            drafting_service.legal_agent = original_agent

    async def test_failed_drafting_run_records_safe_error_event(self):
        async with self.Session() as db:
            user = await self._create_user(db)
            matter = await service.create_matter(
                db,
                user.id,
                MatterCreate(case_number="ELC-run-failed", division="ELC"),
            )
            request = DraftingRequest(
                matter_id=matter.id,
                jurisdiction="ELC",
                subcategory="Temporary Injunction",
            )
            run = await drafting_service.create_drafting_run(
                db,
                matter=matter,
                request=request,
            )

            failed = await drafting_service.execute_drafting_run(db, run.id)
            events = await drafting_service.get_drafting_events(db, run.id)

            self.assertEqual(failed.status, "failed")
            self.assertEqual(failed.error_status, "empty_context")
            self.assertEqual(events[-1].event_type, "failed")
            self.assertEqual(events[-1].error_type, "empty_context")
            self.assertEqual(matter.drafting_error, "empty_context")

    async def test_drafting_run_ownership_prevents_cross_user_streaming(self):
        async with self.Session() as db:
            owner = await self._create_user(db, "draft-owner@example.test")
            other = await self._create_user(db, "draft-other@example.test")
            matter = await service.create_matter(
                db,
                owner.id,
                MatterCreate(case_number="ELC-run-owned", division="ELC"),
            )
            run = await drafting_service.create_drafting_run(
                db,
                matter=matter,
                request=DraftingRequest(
                    matter_id=matter.id,
                    jurisdiction="ELC",
                    subcategory="Temporary Injunction",
                ),
            )

            found = await drafting_service.get_user_drafting_run(
                db,
                user_id=owner.id,
                run_id=run.id,
            )
            self.assertEqual(found.id, run.id)
            with self.assertRaises(HTTPException) as not_found:
                await drafting_service.get_user_drafting_run(
                    db,
                    user_id=other.id,
                    run_id=run.id,
                )
            self.assertEqual(not_found.exception.status_code, 404)

    def test_elc_filter_accepts_land_matters_and_rejects_criminal_noise(self):
        self.assertTrue(
            is_elc_relevant(
                title="Mwangi v Kamau (Environment and Land Case E001 of 2024)",
                court="Environment and Land Court at Nairobi",
                text="temporary injunction over land parcel",
            )
        )
        self.assertFalse(
            is_elc_relevant(
                title="Republic v Otieno",
                court="High Court",
                text="criminal murder charge",
            )
        )

    def test_kenyalaw_parser_extracts_core_case_metadata(self):
        html = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <p>5 February 2024</p>
          <p>The application seeks a temporary injunction over land parcel LR 1.</p>
        </body></html>
        """
        parsed = parse_case_html(html, "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10")
        self.assertEqual(parsed.title, "Mwangi v Kamau [2024] KEELC 10 (KLR)")
        self.assertEqual(parsed.neutral_citation, "[2024] KEELC 10")
        self.assertEqual(parsed.court, "Environment and Land Court at Nairobi")
        self.assertIn("temporary injunction", parsed.topic_tags)

    def test_source_candidates_include_canonical_and_download_links(self):
        html = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <a href="/akn/ke/judgment/keelc/2024/10/download.docx">Download DOCX</a>
          <a href="/akn/ke/judgment/keelc/2024/10/source.pdf">Download PDF</a>
          <button data-url="/media/judgment/ruling.doc">Load document</button>
          <button>Load document</button>
        </body></html>
        """
        parsed = parse_case_html(
            html,
            "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/",
        )
        candidates = resolve_source_candidates(parsed.canonical_url, parsed.source_links)
        self.assertEqual(
            candidates[0].url,
            "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/source",
        )
        self.assertEqual(candidates[1].source_format, "pdf")
        self.assertIn("download.docx", [candidate.url for candidate in candidates][2])
        self.assertTrue(any(candidate.url.endswith("/media/judgment/ruling.doc") for candidate in candidates))

    def test_quality_gate_rejects_shell_text_and_accepts_judgment_body(self):
        shell = """
        Kenya Law Judgments Advanced Search Download DOCX Download PDF Load document
        Home About Kenya Law Privacy Policy Footer National Council for Law Reporting
        """
        rejected = assess_judgment_text_quality(shell)
        self.assertEqual(rejected.status, REJECTED_SHELL_TEXT)

        accepted = assess_judgment_text_quality(
            realistic_judgment_text(),
            title="Mwangi v Kamau [2024] KEELC 10 (KLR)",
            court="Environment and Land Court at Nairobi",
        )
        self.assertEqual(accepted.status, VALID_EXTRACTION)
        self.assertGreaterEqual(accepted.score, 55)

    def test_docx_source_extraction_produces_body_text(self):
        page = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body><a href="/akn/ke/judgment/keelc/2024/10/source">Download DOCX</a></body></html>
        """
        parsed = parse_case_html(
            page,
            "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/",
        )
        fetcher = FakeKenyaLawFetcher(
            {
                "2024/10/source": (
                    minimal_docx(realistic_judgment_text()),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            }
        )
        extracted = extract_judgment_source(fetcher, parsed)
        self.assertEqual(extracted.source_format, "docx")
        self.assertIn("permanent injunction over land parcel LR 1", extracted.text)

    def test_legacy_doc_and_non_docx_zip_sources_do_not_raise_docx_key_error(self):
        rtf_doc = (
            r"{\rtf1\ansi REPUBLIC OF KENYA \par IN THE ENVIRONMENT AND LAND COURT "
            r"AT NAIROBI \par JUDGMENT \par "
            r"1. The plaintiff seeks an injunction over land parcel LR 1. \par "
            r"2. The court considers the evidence and grants orders with costs.}"
        )
        text = extract_source_text(
            rtf_doc.encode("utf-8"),
            source_format="doc",
            source_url="https://example.test/ruling.doc",
        )
        self.assertIn("REPUBLIC OF KENYA", text)
        self.assertIn("injunction over land parcel LR 1", text)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("judgment.txt", realistic_judgment_text())
        zipped_text = extract_source_text(
            buffer.getvalue(),
            source_format="doc",
            source_url="https://example.test/source",
        )
        self.assertIn("permanent injunction over land parcel LR 1", zipped_text)

    def test_html_body_can_be_used_when_source_documents_are_missing(self):
        html = f"""
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <article>{realistic_judgment_text()}</article>
        </body></html>
        """
        parsed = parse_case_html(
            html,
            "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/",
        )
        extracted = extract_judgment_source(FakeKenyaLawFetcher({}), parsed)
        self.assertEqual(extracted.source_format, "html")
        self.assertEqual(extracted.url, parsed.canonical_url)
        self.assertIn("permanent injunction over land parcel LR 1", extracted.text)

    def test_pinecone_preflight_detects_dimension_mismatch(self):
        result = validate_pinecone_index_dimension(
            index_dimension_provider=lambda: 1536,
        )
        self.assertEqual(result.embedding_dimension, 1536)
        self.assertEqual(result.index_dimension, 1536)

        with self.assertRaises(PineconeDimensionMismatch) as mismatch:
            validate_pinecone_index_dimension(
                index_dimension_provider=lambda: 3072,
            )
        self.assertEqual(
            str(mismatch.exception),
            "Pinecone index dimension 3072 does not match embedding dimension 1536",
        )

    def test_indexer_splits_long_judgments_before_embedding(self):
        long_text = "\n\n".join(
            [
                "# Long Kenya Law judgment",
                "source: Kenya Law",
                "canonical_url: https://new.kenyalaw.org/akn/ke/judgment/keelc/2026/2845",
                ("The plaintiff seeks orders over land parcel LR 1. " * 1200),
                ("The court considered evidence, submissions, costs, and final orders. " * 1200),
            ]
        )
        nodes = embedding_safe_nodes(
            long_text,
            {
                "source": "Kenya Law",
                "canonical_url": "https://new.kenyalaw.org/akn/ke/judgment/keelc/2026/2845",
            },
        )
        self.assertGreater(len(nodes), 1)
        self.assertTrue(
            all(len(node.get_content().split()) < 2500 for node in nodes),
            "Indexer produced a node that is too large for embedding.",
        )

    async def test_dry_run_elc_ingestion_discovers_filters_and_counts(self):
        listing = """
        <html><body>
          <a href="/akn/ke/judgment/keelc/2024/10/">ELC case</a>
        </body></html>
        """
        case = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <p>The plaintiff seeks an injunction over land parcel LR 1.</p>
        </body></html>
        """
        fetcher = FakeKenyaLawFetcher(
            {"KEELC": listing, "2024/10/source": realistic_judgment_text(), "2024/10": case}
        )
        async with self.Session() as db:
            run = await kenyalaw_service.start_ingestion_run(
                db,
                IngestionRunCreate(dry_run=True, max_pages=1, max_documents=5),
                fetcher=fetcher,
            )
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.discovered_count, 1)
            self.assertEqual(run.indexed_count, 1)

            documents = await db.execute(select(CaseDocument))
            document_list = documents.scalars().all()
            self.assertEqual(len(document_list), 1)
            document = document_list[0]
            self.assertEqual(document.fetch_status, "stored")
            self.assertEqual(document.extraction_status, "valid")
            self.assertEqual(document.source_document_url, "https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/source")
            self.assertEqual(document.last_ingestion_run_id, run.id)
            self.assertIn("injunction over land parcel", document.normalized_text)
            self.assertNotIn("Load document", document.normalized_text)

            listed = await kenyalaw_service.list_case_documents(db, query="Mwangi")
            self.assertEqual(listed["total"], 1)
            self.assertEqual(listed["documents"][0]["chunk_count"], 1)
            self.assertIn("injunction", listed["documents"][0]["topic_tags"])

            detail = await kenyalaw_service.get_case_document_detail(db, document.id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["id"], document.id)
            self.assertIn("Mwangi v Kamau", detail["title"])
            self.assertEqual(len(detail["chunks"]), 1)
            self.assertEqual(detail["extraction_status"], "valid")

    async def test_navigation_only_source_is_not_stored_as_valid_text(self):
        listing = """
        <html><body>
          <a href="/akn/ke/judgment/keelc/2024/10/">ELC case</a>
        </body></html>
        """
        case = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <a href="/akn/ke/judgment/keelc/2024/10/source">Download DOCX</a>
        </body></html>
        """
        shell_source = """
        <html><body>
          <nav>Kenya Law Judgments Advanced Search</nav>
          <button>Load document</button>
          <a>Download DOCX</a><a>Download PDF</a>
          <footer>National Council for Law Reporting Privacy Policy</footer>
        </body></html>
        """
        fetcher = FakeKenyaLawFetcher(
            {"KEELC": listing, "2024/10/source": shell_source, "2024/10": case}
        )
        async with self.Session() as db:
            run = await kenyalaw_service.start_ingestion_run(
                db,
                IngestionRunCreate(dry_run=True, max_pages=1, max_documents=5),
                fetcher=fetcher,
            )
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.failed_count, 1)
            self.assertEqual(run.indexed_count, 0)

            document = (await db.execute(select(CaseDocument))).scalar_one()
            self.assertEqual(document.fetch_status, "failed")
            self.assertEqual(document.extraction_status, "rejected_shell_text")
            self.assertIsNone(document.normalized_text)

    async def test_repair_replaces_existing_chunks_and_vectors(self):
        source_text = realistic_judgment_text()
        original_index = kenyalaw_service.index_markdown
        original_delete = kenyalaw_service.delete_document_vectors
        indexed_payloads = []
        deleted_urls = []

        def fake_index(markdown, metadata, namespace=None):
            indexed_payloads.append((markdown, metadata, namespace))
            return 2

        def fake_delete(canonical_url, namespace=None):
            deleted_urls.append((canonical_url, namespace))

        kenyalaw_service.index_markdown = fake_index
        kenyalaw_service.delete_document_vectors = fake_delete
        try:
            async with self.Session() as db:
                source = LegalSource(
                    name="Kenya Law",
                    base_url="https://new.kenyalaw.org",
                )
                db.add(source)
                await db.flush()
                document = CaseDocument(
                    source_id=source.id,
                    canonical_url="https://new.kenyalaw.org/akn/ke/judgment/keelc/2024/10/",
                    title="Mwangi v Kamau [2024] KEELC 10 (KLR)",
                    court="Environment and Land Court at Nairobi",
                    source_format="html",
                    extraction_status="valid",
                    normalized_text="Load document Download PDF Kenya Law",
                    normalized_hash="bad-hash",
                    text_length=34,
                    fetch_status="indexed",
                    indexed_at=datetime.now(timezone.utc),
                )
                db.add(document)
                await db.flush()
                db.add(
                    CaseChunk(
                        case_document_id=document.id,
                        chunk_index=0,
                        text="Load document Download PDF Kenya Law",
                        text_hash="bad",
                        pinecone_vector_id="kenyalaw:1:0",
                    )
                )
                await db.commit()

                page = """
                <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
                <body><p>Court: Environment and Land Court at Nairobi</p></body></html>
                """
                fetcher = FakeKenyaLawFetcher(
                    {"2024/10/source": source_text, "2024/10": page}
                )
                run = await kenyalaw_service.create_document_repair_run(db)
                completed = await kenyalaw_service.execute_document_repair_run(
                    db,
                    run.id,
                    fetcher=fetcher,
                    preflight_validator=lambda: None,
                )
                self.assertEqual(completed.status, "completed")
                self.assertEqual(completed.indexed_count, 1)
                self.assertEqual(deleted_urls[0][0], document.canonical_url)
                self.assertEqual(deleted_urls[0][1], kenyalaw_service.PINECONE_NAMESPACE)
                self.assertEqual(indexed_payloads[0][2], kenyalaw_service.PINECONE_NAMESPACE)

                repaired = await db.get(CaseDocument, document.id)
                self.assertEqual(repaired.extraction_status, "valid")
                self.assertIn("permanent injunction over land parcel LR 1", repaired.normalized_text)
                chunks = (
                    await db.execute(
                        select(CaseChunk).where(CaseChunk.case_document_id == document.id)
                    )
                ).scalars().all()
                self.assertEqual(len(chunks), 1)
                self.assertNotIn("Load document", chunks[0].text)
        finally:
            kenyalaw_service.index_markdown = original_index
            kenyalaw_service.delete_document_vectors = original_delete

    async def test_preflight_failure_records_readable_event(self):
        def failing_preflight():
            raise PineconeDimensionMismatch(
                index_name="legal-docs",
                embedding_model="text-embedding-3-small",
                embedding_dimension=1536,
                index_dimension=3072,
            )

        fetcher = FakeKenyaLawFetcher({})
        async with self.Session() as db:
            run = await kenyalaw_service.start_ingestion_run(
                db,
                IngestionRunCreate(dry_run=False, max_pages=1, max_documents=5),
                fetcher=fetcher,
                preflight_validator=failing_preflight,
            )
            self.assertEqual(run.status, "failed")
            self.assertEqual(run.failed_count, 1)
            self.assertEqual(run.discovered_count, 0)

            events = await db.execute(
                select(IngestionEvent)
                .where(IngestionEvent.ingestion_run_id == run.id)
                .order_by(IngestionEvent.id)
            )
            event_list = events.scalars().all()
            failed_event = event_list[-1]
            self.assertEqual(failed_event.event_type, "failed")
            self.assertEqual(failed_event.stage, "preflight")
            self.assertEqual(failed_event.error_type, "pinecone_dimension_mismatch")
            self.assertEqual(
                failed_event.message,
                "Pinecone index dimension 3072 does not match embedding dimension 1536",
            )

    async def test_ingestion_run_can_be_created_then_executed_with_sse_history(self):
        listing = """
        <html><body>
          <a href="/akn/ke/judgment/keelc/2024/10/">ELC case</a>
        </body></html>
        """
        case = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <p>The plaintiff seeks an injunction over land parcel LR 1.</p>
        </body></html>
        """
        fetcher = FakeKenyaLawFetcher(
            {"KEELC": listing, "2024/10/source": realistic_judgment_text(), "2024/10": case}
        )
        request = IngestionRunCreate(dry_run=True, max_pages=1, max_documents=5)
        async with self.Session() as db:
            run = await kenyalaw_service.create_ingestion_run(db, request)
            self.assertEqual(run.status, "running")

            started_events = await kenyalaw_service.get_ingestion_events(db, run.id)
            self.assertEqual(started_events[0].event_type, "started")

            completed = await kenyalaw_service.execute_ingestion_run(
                db,
                run.id,
                request,
                fetcher=fetcher,
            )
            self.assertIsNotNone(completed)
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.indexed_count, 1)

        chunks = []
        async for chunk in kenyalaw_service.stream_ingestion_events(
            run.id,
            session_factory=self.Session,
            poll_interval=0,
        ):
            chunks.append(chunk)
        stream_payload = "".join(chunks)
        self.assertIn('"event_type":"started"', stream_payload)
        self.assertIn('"event_type":"completed"', stream_payload)

    async def test_indexing_failure_records_judgment_url_event_and_continues(self):
        listing = """
        <html><body>
          <a href="/akn/ke/judgment/keelc/2024/10/">ELC case</a>
          <a href="/akn/ke/judgment/keelc/2024/11/">Second ELC case</a>
        </body></html>
        """
        failing_case = """
        <html><head><title>Mwangi v Kamau [2024] KEELC 10 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <p>The plaintiff seeks an injunction over land parcel LR 1.</p>
        </body></html>
        """
        succeeding_case = """
        <html><head><title>Otieno v Achieng [2024] KEELC 11 (KLR)</title></head>
        <body>
          <p>Court: Environment and Land Court at Nairobi</p>
          <p>The plaintiff seeks an injunction over land parcel LR 2.</p>
        </body></html>
        """

        index_calls = []

        def flaky_index(markdown, metadata, namespace=None):
            index_calls.append((markdown, metadata, namespace))
            if len(index_calls) == 1:
                raise RuntimeError("vector write rejected")
            return 2

        original = kenyalaw_service.index_markdown
        kenyalaw_service.index_markdown = flaky_index
        try:
            fetcher = FakeKenyaLawFetcher(
                {
                    "KEELC": listing,
                    "2024/10/source": realistic_judgment_text(),
                    "2024/10": failing_case,
                    "2024/11/source": realistic_judgment_text(),
                    "2024/11": succeeding_case,
                }
            )
            async with self.Session() as db:
                run = await kenyalaw_service.start_ingestion_run(
                    db,
                    IngestionRunCreate(dry_run=False, max_pages=1, max_documents=5),
                    fetcher=fetcher,
                    preflight_validator=lambda: None,
                )
                self.assertEqual(run.status, "completed")
                self.assertEqual(run.failed_count, 1)
                self.assertEqual(run.indexed_count, 1)

                events = await db.execute(
                    select(IngestionEvent)
                    .where(IngestionEvent.ingestion_run_id == run.id)
                    .order_by(IngestionEvent.id)
                )
                event_list = events.scalars().all()
                failed_event = next(
                    event
                    for event in event_list
                    if event.event_type == "failed" and event.stage == "index"
                )
                indexed_event = next(
                    event
                    for event in event_list
                    if event.event_type == "indexed" and event.stage == "index"
                )
                self.assertEqual(failed_event.stage, "index")
                self.assertEqual(failed_event.error_type, "RuntimeError")
                self.assertIn("/akn/ke/judgment/keelc/2024/10/", failed_event.url)
                self.assertEqual(failed_event.message, "vector write rejected")
                self.assertIn("/akn/ke/judgment/keelc/2024/11/", indexed_event.url)

                errors = await db.execute(
                    select(IngestionError).where(IngestionError.ingestion_run_id == run.id)
                )
                self.assertEqual(len(errors.scalars().all()), 1)

                documents = await db.execute(
                    select(CaseDocument).order_by(CaseDocument.canonical_url)
                )
                document_list = documents.scalars().all()
                self.assertEqual(document_list[0].fetch_status, "failed")
                self.assertEqual(document_list[1].fetch_status, "indexed")
        finally:
            kenyalaw_service.index_markdown = original

    def test_verifier_uses_source_url_before_marking_verified(self):
        original = kenyalaw_verifier.retrieve_context
        try:
            kenyalaw_verifier.retrieve_context = lambda *args, **kwargs: [
                {
                    "text": "The court grants temporary injunctions where the Giella principles are met.",
                    "score": 0.9,
                    "metadata": {
                        "title": "Giella v Cassman Brown [1973] EA 358",
                        "source_url": "https://new.kenyalaw.org/akn/ke/judgment/example",
                        "neutral_citation": "[1973] EA 358",
                        "court": "Court of Appeal",
                    },
                }
            ]
            matter = type(
                "MatterStub",
                (),
                {
                    "id": 1,
                    "draft_content": "",
                    "masked_facts": "",
                    "citation_evidence": [
                        type(
                            "EvidenceStub",
                            (),
                            {
                                "status": "pending",
                                "citation_type": "precedent",
                                "title": "Giella v Cassman Brown [1973] EA 358",
                                "snippet": "temporary injunction principles",
                            },
                        )()
                    ],
                },
            )()
            evidence = kenyalaw_verifier.verify_matter_citations(matter)
            self.assertEqual(evidence[0]["status"], "verified")
            self.assertEqual(evidence[0]["source"], "Kenya Law")
            self.assertIn("source_url", evidence[0])
        finally:
            kenyalaw_verifier.retrieve_context = original

    def test_verifier_snippet_strips_index_metadata(self):
        original = kenyalaw_verifier.retrieve_context
        indexed_text = """
        # Kinyanjui & another v Nyambura & 2 others [2026] KEELC 2818 (KLR)

        source: Kenya Law
        source_url: https://new.kenyalaw.org/akn/ke/judgment/keelc/2026/2818
        canonical_url: https://new.kenyalaw.org/akn/ke/judgment/keelc/2026/2818
        title: Kinyanjui & another v Nyambura & 2 others [2026] KEELC 2818 (KLR)
        neutral_citation: [2026] KEELC 2818
        court:
        judgment_date: 13 May 2026
        topic_tags: environment and land
        document_hash: 4bf4cf945b438887af18dab8c151a7912d8e798bc0dd4641f4
        corpus_scope: elc

        The court must consider whether the applicant has established a prima facie
        case and whether damages would be an adequate remedy before granting a
        temporary injunction over the suit property.
        """
        try:
            kenyalaw_verifier.retrieve_context = lambda *args, **kwargs: [
                {
                    "text": indexed_text,
                    "score": 0.9,
                    "metadata": {
                        "title": "Kinyanjui & another v Nyambura & 2 others [2026] KEELC 2818",
                        "source_url": "https://new.kenyalaw.org/akn/ke/judgment/keelc/2026/2818",
                    },
                }
            ]
            matter = type(
                "MatterStub",
                (),
                {
                    "id": 1,
                    "draft_content": "",
                    "masked_facts": "",
                    "citation_evidence": [
                        type(
                            "EvidenceStub",
                            (),
                            {
                                "status": "pending",
                                "citation_type": "precedent",
                                "title": "Kinyanjui & another v Nyambura & 2 others [2026] KEELC 2818",
                                "snippet": "temporary injunction",
                            },
                        )()
                    ],
                },
            )()
            evidence = kenyalaw_verifier.verify_matter_citations(matter)
            self.assertIn("prima facie", evidence[0]["snippet"])
            self.assertNotIn("source_url", evidence[0]["snippet"])
            self.assertNotIn("document_hash", evidence[0]["snippet"])
            self.assertNotIn("corpus_scope", evidence[0]["snippet"])
        finally:
            kenyalaw_verifier.retrieve_context = original


if __name__ == "__main__":
    unittest.main()
