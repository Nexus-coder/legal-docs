from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "drafting_rag_v1.jsonl"
)


class DraftingEvaluationRow(BaseModel):
    id: str = Field(pattern=r"^draft-[a-z0-9-]+$")
    jurisdiction: str
    subcategory: str
    pleading_type: str
    masked_facts: str
    retrieval_queries: list[str] = Field(default_factory=list)
    expected_authority_titles: list[str] = Field(default_factory=list)
    expected_statutory_materials: list[str] = Field(default_factory=list)
    expected_context_terms: list[str] = Field(default_factory=list)
    draft_checklist: list[str]
    should_draft: bool = True
    insufficiency_reason: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_drafting_contract(self) -> "DraftingEvaluationRow":
        if self.should_draft and not self.expected_authority_titles:
            raise ValueError("positive drafting rows require expected authorities")
        if not self.should_draft and not self.insufficiency_reason:
            raise ValueError("negative-control rows require an insufficiency reason")
        if "[APPLICANT]" not in self.masked_facts and "[CLIENT]" not in self.masked_facts:
            raise ValueError("masked_facts must preserve anonymized party markers")
        if len(self.draft_checklist) < 5:
            raise ValueError("draft_checklist must contain enough drafting criteria")
        return self

    def to_ragas_user_input(self) -> str:
        checklist = "\n".join(f"- {item}" for item in self.draft_checklist)
        queries = "\n".join(f"- {query}" for query in self.retrieval_queries)
        return (
            f"Pleading type: {self.pleading_type}\n"
            f"Jurisdiction: {self.jurisdiction}\n"
            f"Subcategory: {self.subcategory}\n\n"
            f"Masked facts:\n{self.masked_facts}\n\n"
            f"Retrieval queries:\n{queries}\n\n"
            f"Drafting checklist:\n{checklist}"
        )

    def to_ragas_reference(self) -> str:
        if not self.should_draft:
            return (
                "The system should not produce a normal pleading draft. It should "
                f"report insufficient context or wrong forum: {self.insufficiency_reason}"
            )

        authorities = "\n".join(
            f"- {title}" for title in self.expected_authority_titles
        )
        statutes = "\n".join(
            f"- {material}" for material in self.expected_statutory_materials
        )
        terms = ", ".join(self.expected_context_terms)
        checklist = "\n".join(f"- {item}" for item in self.draft_checklist)
        return (
            "A legally useful draft should be grounded in the expected authorities "
            "and statutory materials, preserve all anonymized placeholders, and "
            "satisfy the drafting checklist.\n\n"
            f"Expected authorities:\n{authorities}\n\n"
            f"Expected statutory materials:\n{statutes or '- None'}\n\n"
            f"Expected legal context terms: {terms}\n\n"
            f"Checklist:\n{checklist}"
        )

    def to_ragas_rubric(self) -> dict[str, object]:
        return {
            "should_draft": self.should_draft,
            "draft_checklist": self.draft_checklist,
            "negative_control_expectation": self.insufficiency_reason,
            "expected_context_terms": self.expected_context_terms,
            "expected_authority_titles": self.expected_authority_titles,
        }

    def to_ragas_input(
        self,
        *,
        retrieved_contexts: list[str] | None = None,
        retrieved_context_ids: list[str] | None = None,
        reference_context_ids: list[str] | None = None,
        response: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "user_input": self.to_ragas_user_input(),
            "reference": self.to_ragas_reference(),
            "retrieved_contexts": retrieved_contexts or [],
            "retrieved_context_ids": retrieved_context_ids or [],
            "reference_context_ids": reference_context_ids
            if reference_context_ids is not None
            else list(self.expected_authority_titles),
            "rubric": self.to_ragas_rubric(),
        }
        if response is not None:
            payload["response"] = response
        return payload

    def to_ragas_sample(self, **kwargs):
        try:
            from ragas import SingleTurnSample
        except ImportError:
            from ragas.dataset_schema import SingleTurnSample

        return SingleTurnSample(**self.to_ragas_input(**kwargs))


def load_drafting_dataset(
    path: Path | str = DEFAULT_DATASET_PATH,
) -> list[DraftingEvaluationRow]:
    dataset_path = Path(path)
    rows: list[DraftingEvaluationRow] = []
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on {dataset_path}:{line_number}: {exc.msg}"
                ) from exc
            rows.append(DraftingEvaluationRow.model_validate(payload))

    ids = [row.id for row in rows]
    duplicate_ids = sorted(row_id for row_id, count in Counter(ids).items() if count > 1)
    if duplicate_ids:
        raise ValueError(f"Duplicate drafting evaluation ids: {', '.join(duplicate_ids)}")
    return rows


def drafting_dataset_summary(
    rows: list[DraftingEvaluationRow],
) -> dict[str, int | dict[str, int]]:
    subcategories = Counter(row.subcategory for row in rows)
    return {
        "rows": len(rows),
        "positive_rows": sum(1 for row in rows if row.should_draft),
        "negative_rows": sum(1 for row in rows if not row.should_draft),
        "subcategories": dict(sorted(subcategories.items())),
    }
