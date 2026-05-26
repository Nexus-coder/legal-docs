import sqlite3
import unittest
from unittest.mock import patch

from src.evaluation.drafting_dataset import (
    DEFAULT_DATASET_PATH,
    drafting_dataset_summary,
    load_drafting_dataset,
)
from src.evaluation.ragas_adapter import (
    authority_map,
    authority_mrr,
    deterministic_id_metric_scores,
    resolve_reference_context_ids,
)
from src.evaluation.run_drafting_ragas import run_evaluation


class DraftingEvaluationDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = load_drafting_dataset()

    def test_dataset_loads_expected_v1_shape(self):
        summary = drafting_dataset_summary(self.rows)

        self.assertEqual(summary["rows"], 27)
        self.assertEqual(summary["positive_rows"], 25)
        self.assertEqual(summary["negative_rows"], 2)
        self.assertEqual(
            summary["subcategories"],
            {
                "Adverse Possession": 6,
                "Boundary/Title Dispute": 4,
                "Negative Control": 2,
                "Procedural Application": 3,
                "Temporary Injunction": 8,
                "Trespass/Eviction": 4,
            },
        )

    def test_rows_have_evaluation_fields(self):
        for row in self.rows:
            self.assertTrue(row.retrieval_queries)
            self.assertTrue(row.expected_context_terms)
            self.assertTrue(row.draft_checklist)
            self.assertIn(row.jurisdiction, {"Environment and Land Court"})

            if row.should_draft:
                self.assertTrue(row.expected_authority_titles)
                self.assertIsNone(row.insufficiency_reason)
            else:
                self.assertEqual(row.expected_authority_titles, [])
                self.assertTrue(row.insufficiency_reason)

    def test_expected_authority_titles_exist_in_local_corpus(self):
        db_path = DEFAULT_DATASET_PATH.parents[2] / "legal_docs.db"
        if not db_path.exists():
            self.skipTest("legal_docs.db is not available")

        with sqlite3.connect(db_path) as conn:
            titles = {
                row[0]
                for row in conn.execute(
                    "select title from case_document where extraction_status = 'valid'"
                )
            }

        missing = sorted(
            {
                title
                for row in self.rows
                for title in row.expected_authority_titles
                if title not in titles
            }
        )

        self.assertEqual(missing, [])

    def test_dataset_file_is_jsonl(self):
        lines = DEFAULT_DATASET_PATH.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 27)
        self.assertTrue(all(line.startswith("{") and line.endswith("}") for line in lines))

    def test_rows_convert_to_ragas_sample_dictionaries(self):
        row = self.rows[0]
        payload = row.to_ragas_input(
            retrieved_contexts=["context text"],
            retrieved_context_ids=["doc-1"],
            reference_context_ids=["doc-1"],
            response="draft text",
        )

        self.assertIn(row.pleading_type, payload["user_input"])
        self.assertIn(row.masked_facts, payload["user_input"])
        self.assertIn(row.expected_authority_titles[0], payload["reference"])
        self.assertEqual(payload["retrieved_contexts"], ["context text"])
        self.assertEqual(payload["retrieved_context_ids"], ["doc-1"])
        self.assertEqual(payload["reference_context_ids"], ["doc-1"])
        self.assertEqual(payload["response"], "draft text")
        self.assertEqual(payload["rubric"]["draft_checklist"], row.draft_checklist)

    def test_positive_expected_authorities_resolve_to_local_document_ids(self):
        db_path = DEFAULT_DATASET_PATH.parents[2] / "legal_docs.db"
        if not db_path.exists():
            self.skipTest("legal_docs.db is not available")

        unresolved = []
        for row in self.rows:
            if not row.should_draft:
                continue
            reference_ids = resolve_reference_context_ids(row, db_path=db_path)
            unresolved.extend(
                reference_id
                for reference_id in reference_ids
                if not str(reference_id).isdigit()
            )

        self.assertEqual(unresolved, [])

    def test_deterministic_retriever_metric_plumbing(self):
        sample = {
            "retrieved_context_ids": ["a", "x", "b"],
            "reference_context_ids": ["a", "b"],
        }

        scores = deterministic_id_metric_scores([sample])[0]

        self.assertAlmostEqual(scores["id_based_context_precision"], 2 / 3)
        self.assertEqual(scores["id_based_context_recall"], 1.0)
        self.assertEqual(authority_mrr(["x", "b", "a"], ["a", "b"]), 0.5)
        self.assertAlmostEqual(authority_map(["a", "x", "b"], ["a", "b"]), 5 / 6)

    def test_negative_controls_are_not_generated_by_default(self):
        negative_rows = [row for row in self.rows if not row.should_draft]

        with patch(
            "src.evaluation.run_drafting_ragas.generate_row_draft",
            side_effect=AssertionError("generator should not be called"),
        ):
            results = run_evaluation(
                negative_rows,
                mode="all",
                db_path=DEFAULT_DATASET_PATH.parents[2] / "legal_docs.db",
                mock_retrieval=True,
                llm_metrics="off",
            )

        self.assertEqual(len(results), 2)
        self.assertTrue(all(result["negative_control_pass"] for result in results))
        self.assertTrue(all(result["error_status"] is None for result in results))

    def test_runner_smoke_retriever_only_with_mock_retrieval(self):
        results = run_evaluation(
            self.rows[:2],
            mode="retriever-only",
            db_path=DEFAULT_DATASET_PATH.parents[2] / "legal_docs.db",
            mock_retrieval=True,
            llm_metrics="off",
        )

        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn("id_based_context_precision", result)
            self.assertIn("id_based_context_recall", result)
            self.assertIsNone(result["error_status"])


if __name__ == "__main__":
    unittest.main()
