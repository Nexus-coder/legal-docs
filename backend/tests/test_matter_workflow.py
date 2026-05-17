import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.models import User
from src.models import Base
from src.matters.schemas import MatterCreate, MatterRead
from src.matters import service
from src.drafting.router import _classify_drafting_error, _drafting_status_from_state
from src.ingestion.indexer import PineconeDimensionMismatch, validate_pinecone_index_dimension
from src.kenyalaw.fetcher import FetchResult
from src.kenyalaw.filtering import is_elc_relevant
from src.kenyalaw.models import CaseDocument, IngestionEvent
from src.kenyalaw.parser import parse_case_html
from src.kenyalaw.schemas import IngestionRunCreate
from src.kenyalaw import service as kenyalaw_service
from src.kenyalaw import verifier as kenyalaw_verifier


class FakeKenyaLawFetcher:
    def __init__(self, pages):
        self.pages = pages

    def fetch_text(self, url):
        for key, content in self.pages.items():
            if key in url:
                return FetchResult(url=url, content=content, content_type="text/html")
        raise AssertionError(f"Unexpected fetch URL: {url}")


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
        fetcher = FakeKenyaLawFetcher({"KEELC": listing, "2024/10": case})
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
            self.assertEqual(len(documents.scalars().all()), 0)

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
        fetcher = FakeKenyaLawFetcher({"KEELC": listing, "2024/10": case})
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

    async def test_indexing_failure_records_judgment_url_event(self):
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

        def failing_index(*args, **kwargs):
            raise RuntimeError("vector write rejected")

        original = kenyalaw_service.index_markdown
        kenyalaw_service.index_markdown = failing_index
        try:
            fetcher = FakeKenyaLawFetcher({"KEELC": listing, "2024/10": case})
            async with self.Session() as db:
                run = await kenyalaw_service.start_ingestion_run(
                    db,
                    IngestionRunCreate(dry_run=False, max_pages=1, max_documents=5),
                    fetcher=fetcher,
                    preflight_validator=lambda: None,
                )
                self.assertEqual(run.status, "failed")

                events = await db.execute(
                    select(IngestionEvent)
                    .where(IngestionEvent.ingestion_run_id == run.id)
                    .order_by(IngestionEvent.id)
                )
                failed_event = events.scalars().all()[-1]
                self.assertEqual(failed_event.stage, "index")
                self.assertEqual(failed_event.error_type, "RuntimeError")
                self.assertIn("/akn/ke/judgment/keelc/2024/10/", failed_event.url)
                self.assertEqual(failed_event.message, "vector write rejected")
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


if __name__ == "__main__":
    unittest.main()
