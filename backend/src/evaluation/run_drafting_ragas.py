from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.evaluation.drafting_dataset import (
    DEFAULT_DATASET_PATH,
    DraftingEvaluationRow,
    load_drafting_dataset,
)
from src.evaluation.ragas_adapter import (
    DEFAULT_LEGAL_DB_PATH,
    build_sample_dict,
    custom_legal_scores,
    deterministic_id_metric_scores,
    evaluate_with_ragas,
    normalize_retrieved_contexts,
    write_results_csv,
)

DEFAULT_RESULTS_DIR = DEFAULT_DATASET_PATH.parent / "results"


def main() -> None:
    args = parse_args()
    output = args.output or default_output_path()
    rows = load_drafting_dataset(args.dataset)
    if args.limit is not None:
        rows = rows[: args.limit]

    results = run_evaluation(
        rows,
        mode=args.mode,
        db_path=args.db,
        mock_retrieval=args.mock_retrieval,
        llm_metrics=args.llm_metrics,
        draft_negative_controls=args.draft_negative_controls,
    )
    write_results_csv(output, results)
    print(f"Wrote {len(results)} drafting Ragas evaluation rows to {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Ragas evaluation for the curated legal drafting RAG dataset."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to drafting_rag_v1.jsonl.",
    )
    parser.add_argument(
        "--mode",
        choices=("retriever-only", "generator", "all"),
        default="retriever-only",
        help="Evaluation surface to execute.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit rows evaluated.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to backend/data/evaluation/results/<timestamp>.csv.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_LEGAL_DB_PATH,
        help="SQLite legal corpus path used to resolve expected authority IDs.",
    )
    parser.add_argument(
        "--mock-retrieval",
        action="store_true",
        help="Use expected authorities as fake retrieved contexts for offline smoke tests.",
    )
    parser.add_argument(
        "--llm-metrics",
        choices=("auto", "on", "off"),
        default="auto",
        help="Whether to run LLM-backed Ragas metrics in addition to ID metrics.",
    )
    parser.add_argument(
        "--draft-negative-controls",
        action="store_true",
        help="Call the drafting generator for negative-control rows.",
    )
    return parser.parse_args()


def default_output_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RESULTS_DIR / f"drafting_ragas_{timestamp}.csv"


def run_evaluation(
    rows: list[DraftingEvaluationRow],
    *,
    mode: str,
    db_path: Path,
    mock_retrieval: bool = False,
    llm_metrics: str = "auto",
    draft_negative_controls: bool = False,
) -> list[dict[str, object]]:
    sample_dicts: list[dict[str, object]] = []
    output_rows: list[dict[str, object]] = []

    for row in rows:
        error_status: str | None = None
        response: str | None = None
        raw_contexts: list[dict[str, Any]] = []

        try:
            if mock_retrieval:
                raw_contexts = mock_retrieve(row)
            elif mode in {"retriever-only", "all"}:
                raw_contexts = retrieve_row_context(row)

            if mode in {"generator", "all"}:
                if row.should_draft or draft_negative_controls:
                    generation = generate_row_draft(row)
                    response = generation["response"]
                    if generation["contexts"]:
                        raw_contexts = generation["contexts"]
                else:
                    response = (
                        "Insufficient context for normal drafting: "
                        f"{row.insufficiency_reason}"
                    )
        except Exception as exc:
            error_status = type(exc).__name__

        contexts = normalize_retrieved_contexts(raw_contexts)
        sample_dict = build_sample_dict(
            row,
            contexts,
            response=response,
            db_path=db_path,
        )
        sample_dicts.append(sample_dict)
        output_rows.append(
            {
                "row_id": row.id,
                "subcategory": row.subcategory,
                "pleading_type": row.pleading_type,
                "should_draft": row.should_draft,
                "expected_authorities": " | ".join(row.expected_authority_titles),
                "retrieved_authority_ids": " | ".join(
                    str(value) for value in sample_dict["retrieved_context_ids"]
                ),
                "error_status": error_status,
                **custom_legal_scores(row, sample_dict, response=response),
            }
        )

    ragas_scores = score_samples(
        sample_dicts,
        mode=mode,
        llm_metrics=llm_metrics,
    )
    for output_row, scores in zip(output_rows, ragas_scores, strict=True):
        output_row.update(scores)
    return output_rows


def retrieve_row_context(row: DraftingEvaluationRow) -> list[dict[str, Any]]:
    from src.ingestion.indexer import retrieve_context

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    queries = row.retrieval_queries or [row.to_ragas_user_input()]
    for query in queries:
        for item in retrieve_context(query, similarity_top_k=5):
            identity = (
                str((item.get("metadata") or {}).get("title") or ""),
                str(item.get("text") or ""),
            )
            if identity in seen:
                continue
            seen.add(identity)
            results.append(item)
    return results


def generate_row_draft(row: DraftingEvaluationRow) -> dict[str, Any]:
    from src.agent.graph import legal_agent
    from src.drafting.packets import drafting_packet_for
    from src.drafting.service import _build_initial_state
    from src.drafting.schemas import DraftingRequest

    request = DraftingRequest(
        matter_id=0,
        jurisdiction=row.jurisdiction,
        subcategory=row.subcategory,
        pleading_type=row.pleading_type,
    )
    packet = drafting_packet_for(
        subcategory=row.subcategory,
        pleading_type=row.pleading_type,
    )
    if packet is None:
        return {
            "response": (
                "Insufficient context for normal drafting: unsupported drafting packet."
            ),
            "contexts": [],
        }

    documents: list[str] = []
    contexts: list[dict[str, Any]] = []
    for spec in packet.documents:
        initial_state = _build_initial_state(
            request,
            matter_instructions=row.masked_facts,
            document_instruction=spec.instruction,
        )
        final_state = legal_agent.invoke(initial_state)
        draft = str(final_state.get("draft") or "")
        if draft:
            documents.append(f"# {spec.title}\n\n{draft}")
        if final_state.get("context"):
            contexts.extend(final_state["context"])
    return {"response": "\n\n".join(documents), "contexts": contexts}


def mock_retrieve(row: DraftingEvaluationRow) -> list[dict[str, Any]]:
    return [
        {
            "text": (
                f"Mock context for {title}. "
                f"Expected terms: {', '.join(row.expected_context_terms)}."
            ),
            "metadata": {"title": title},
            "score": 1.0,
        }
        for title in row.expected_authority_titles
    ]


def score_samples(
    sample_dicts: list[dict[str, object]],
    *,
    mode: str,
    llm_metrics: str,
) -> list[dict[str, object]]:
    include_llm = should_run_llm_metrics(llm_metrics)
    include_generation = mode in {"generator", "all"}
    try:
        return evaluate_with_ragas(
            sample_dicts,
            include_llm_metrics=include_llm,
            include_generation_metrics=include_generation,
        )
    except ImportError:
        if llm_metrics == "on":
            raise
    except Exception:
        if llm_metrics == "on":
            raise
    return deterministic_id_metric_scores(sample_dicts)


def should_run_llm_metrics(llm_metrics: str) -> bool:
    if llm_metrics == "on":
        return True
    if llm_metrics == "off":
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


if __name__ == "__main__":
    main()
