import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.models import User
from src.models import Base
from src.matters.schemas import MatterCreate, MatterRead
from src.matters import service
from src.drafting.router import _classify_drafting_error, _drafting_status_from_state


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


if __name__ == "__main__":
    unittest.main()
