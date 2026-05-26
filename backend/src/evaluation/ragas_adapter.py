from __future__ import annotations

import csv
import math
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.evaluation.drafting_dataset import DraftingEvaluationRow


DEFAULT_LEGAL_DB_PATH = (
    Path(__file__).resolve().parents[2] / "legal_docs.db"
)


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    context_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


def context_id_from_metadata(metadata: dict[str, Any]) -> str:
    for key in ("case_document_id", "document_id", "title", "canonical_title"):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value)
    for key in ("canonical_url", "source_url", "url"):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return ""


def normalize_retrieved_contexts(results: list[dict[str, Any]]) -> list[RetrievedContext]:
    contexts: list[RetrievedContext] = []
    for index, result in enumerate(results):
        metadata = dict(result.get("metadata") or {})
        context_id = context_id_from_metadata(metadata) or f"retrieved-{index + 1}"
        contexts.append(
            RetrievedContext(
                text=str(result.get("text") or ""),
                context_id=context_id,
                metadata=metadata,
                score=result.get("score"),
            )
        )
    return contexts


def resolve_reference_context_ids(
    row: DraftingEvaluationRow,
    *,
    db_path: Path | str = DEFAULT_LEGAL_DB_PATH,
) -> list[str]:
    if not row.expected_authority_titles:
        return []

    path = Path(db_path)
    if not path.exists():
        return list(row.expected_authority_titles)

    placeholders = ",".join("?" for _ in row.expected_authority_titles)
    query = (
        "select id, title from case_document "
        "where extraction_status = 'valid' and title in "
        f"({placeholders})"
    )
    with sqlite3.connect(path) as conn:
        matches = {
            title: str(document_id)
            for document_id, title in conn.execute(query, row.expected_authority_titles)
        }
    return [matches.get(title, title) for title in row.expected_authority_titles]


def authority_mrr(
    retrieved_context_ids: list[str],
    reference_context_ids: list[str],
) -> float:
    reference = set(reference_context_ids)
    for index, context_id in enumerate(retrieved_context_ids, start=1):
        if context_id in reference:
            return 1.0 / index
    return 0.0


def authority_map(
    retrieved_context_ids: list[str],
    reference_context_ids: list[str],
) -> float:
    reference = set(reference_context_ids)
    if not reference:
        return 0.0

    hits = 0
    precision_sum = 0.0
    seen: set[str] = set()
    for index, context_id in enumerate(retrieved_context_ids, start=1):
        if context_id in reference and context_id not in seen:
            hits += 1
            seen.add(context_id)
            precision_sum += hits / index
    return precision_sum / len(reference)


def checklist_pass_rate(response: str, checklist: list[str]) -> float:
    if not checklist:
        return 0.0
    response_lower = response.lower()
    passed = 0
    for item in checklist:
        item_terms = [
            token.strip(".,;:()[]").lower()
            for token in item.split()
            if len(token.strip(".,;:()[]")) >= 4
        ]
        if item_terms and any(term in response_lower for term in item_terms):
            passed += 1
    return passed / len(checklist)


def negative_control_pass(row: DraftingEvaluationRow, response: str | None) -> bool:
    if row.should_draft:
        return True
    if response is None:
        return True
    response_lower = response.lower()
    refusal_terms = (
        "insufficient",
        "cannot draft",
        "wrong forum",
        "not enough",
        "unable to draft",
        "outside",
    )
    return any(term in response_lower for term in refusal_terms)


def id_context_precision(
    retrieved_context_ids: list[str],
    reference_context_ids: list[str],
) -> float:
    if not retrieved_context_ids:
        return 0.0
    reference = set(reference_context_ids)
    return sum(1 for context_id in retrieved_context_ids if context_id in reference) / len(
        retrieved_context_ids
    )


def id_context_recall(
    retrieved_context_ids: list[str],
    reference_context_ids: list[str],
) -> float:
    if not reference_context_ids:
        return 0.0
    retrieved = set(retrieved_context_ids)
    return sum(1 for context_id in reference_context_ids if context_id in retrieved) / len(
        reference_context_ids
    )


def build_sample_dict(
    row: DraftingEvaluationRow,
    contexts: list[RetrievedContext],
    *,
    response: str | None = None,
    db_path: Path | str = DEFAULT_LEGAL_DB_PATH,
) -> dict[str, object]:
    return row.to_ragas_input(
        retrieved_contexts=[context.text for context in contexts],
        retrieved_context_ids=[context.context_id for context in contexts],
        reference_context_ids=resolve_reference_context_ids(row, db_path=db_path),
        response=response,
    )


def build_ragas_dataset(sample_dicts: list[dict[str, object]]):
    try:
        from ragas import EvaluationDataset, SingleTurnSample
    except ImportError:
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    return EvaluationDataset(
        samples=[SingleTurnSample(**sample_dict) for sample_dict in sample_dicts]
    )


def build_ragas_metrics(*, include_llm_metrics: bool, include_generation_metrics: bool):
    from ragas.metrics import IDBasedContextPrecision, IDBasedContextRecall

    metrics = [IDBasedContextPrecision(), IDBasedContextRecall()]
    if include_llm_metrics:
        from ragas.metrics import LLMContextPrecisionWithReference, LLMContextRecall

        metrics.extend([LLMContextPrecisionWithReference(), LLMContextRecall()])
        if include_generation_metrics:
            from ragas.metrics import Faithfulness, ResponseRelevancy

            metrics.extend([Faithfulness(), ResponseRelevancy()])
    return metrics


def evaluate_with_ragas(
    sample_dicts: list[dict[str, object]],
    *,
    include_llm_metrics: bool = False,
    include_generation_metrics: bool = False,
) -> list[dict[str, float | None]]:
    from ragas import evaluate

    dataset = build_ragas_dataset(sample_dicts)
    metrics = build_ragas_metrics(
        include_llm_metrics=include_llm_metrics,
        include_generation_metrics=include_generation_metrics,
    )
    result = evaluate(
        dataset,
        metrics=metrics,
        raise_exceptions=False,
        show_progress=False,
    )
    if hasattr(result, "to_pandas"):
        frame = result.to_pandas()
        return [
            {
                key: _clean_metric_value(value)
                for key, value in record.items()
                if isinstance(value, int | float) or value is None
            }
            for record in frame.to_dict(orient="records")
        ]
    raise TypeError("Unsupported Ragas evaluation result; expected to_pandas().")


def _clean_metric_value(value: Any) -> float | None:
    if isinstance(value, int | float):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    return None


def deterministic_id_metric_scores(
    sample_dicts: list[dict[str, object]],
) -> list[dict[str, float]]:
    scores: list[dict[str, float]] = []
    for sample in sample_dicts:
        retrieved = [str(value) for value in sample.get("retrieved_context_ids", [])]
        reference = [str(value) for value in sample.get("reference_context_ids", [])]
        scores.append(
            {
                "id_based_context_precision": id_context_precision(retrieved, reference),
                "id_based_context_recall": id_context_recall(retrieved, reference),
            }
        )
    return scores


def custom_legal_scores(
    row: DraftingEvaluationRow,
    sample_dict: dict[str, object],
    *,
    response: str | None = None,
) -> dict[str, object]:
    retrieved = [str(value) for value in sample_dict.get("retrieved_context_ids", [])]
    reference = [str(value) for value in sample_dict.get("reference_context_ids", [])]
    return {
        "authority_mrr": authority_mrr(retrieved, reference),
        "authority_map": authority_map(retrieved, reference),
        "checklist_pass_rate": checklist_pass_rate(response or "", row.draft_checklist)
        if row.should_draft and response
        else None,
        "negative_control_pass": negative_control_pass(row, response),
    }


def write_results_csv(
    path: Path | str,
    rows: list[dict[str, object]],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


Retriever = Callable[[str], list[dict[str, Any]]]
