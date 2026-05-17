import json
import logging
import re
from difflib import SequenceMatcher
from typing import Any

from src.ingestion.indexer import retrieve_context
from src.kenyalaw.service import PINECONE_NAMESPACE
from src.matters.models import Matter

logger = logging.getLogger(__name__)


def extract_citation_queries(matter: Matter) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for evidence in matter.citation_evidence:
        if evidence.status in {"verified", "not_found"}:
            continue
        queries.append(
            {
                "citation_type": evidence.citation_type,
                "title": evidence.title,
                "query": f"{evidence.title}. {evidence.snippet}",
            }
        )

    if queries:
        return queries

    content = matter.draft_content or matter.masked_facts or ""
    for citation in _extract_neutral_citations(content):
        queries.append(
            {
                "citation_type": "precedent",
                "title": citation,
                "query": citation,
            }
        )
    if not queries and content.strip():
        queries.append(
            {
                "citation_type": "precedent",
                "title": "ELC authority search",
                "query": content[:1200],
            }
        )
    return queries


def verify_matter_citations(matter: Matter) -> list[dict[str, Any]]:
    evidence_items = []
    for query in extract_citation_queries(matter):
        try:
            results = retrieve_context(
                query["query"], similarity_top_k=5, namespace=PINECONE_NAMESPACE
            )
        except Exception as exc:
            logger.exception("kenyalaw_retrieval_failed matter_id=%s", matter.id)
            evidence_items.append(_error_evidence(query, "retrieval_failed", str(exc)))
            continue
        evidence_items.append(_evidence_from_results(query, results))
    if not evidence_items:
        evidence_items.append(
            {
                "citation_type": "precedent",
                "title": "No citations found in draft",
                "source": "Kenya Law",
                "snippet": "No draft citation or searchable matter content was available for verification.",
                "confidence": 0.0,
                "confidence_breakdown": json.dumps(
                    {"citation_match_score": 0.0, "semantic_score": 0.0, "support_score": 0.0}
                ),
                "status": "needs_review",
            }
        )
    return evidence_items


def _evidence_from_results(query: dict[str, str], results: list[dict[str, Any]]) -> dict:
    if not results:
        return {
            "citation_type": query["citation_type"],
            "title": query["title"],
            "source": "Kenya Law",
            "snippet": "No matching ELC authority was found in the indexed Kenya Law corpus.",
            "confidence": 0.0,
            "confidence_breakdown": json.dumps(
                {"citation_match_score": 0.0, "semantic_score": 0.0, "support_score": 0.0}
            ),
            "status": "not_found",
        }

    best = max(results, key=lambda item: item.get("score") or 0.0)
    metadata = best.get("metadata") or {}
    source_title = metadata.get("title") or query["title"]
    citation_score = _similarity(query["title"], source_title)
    semantic_score = float(best.get("score") or 0.0)
    support_score = min(1.0, max(semantic_score, citation_score * 0.8))
    confidence = round((citation_score * 0.45) + (semantic_score * 0.35) + (support_score * 0.20), 4)
    status = "verified" if confidence >= 0.72 and metadata.get("source_url") else "needs_review"
    breakdown = {
        "citation_match_score": round(citation_score, 4),
        "semantic_score": round(semantic_score, 4),
        "support_score": round(support_score, 4),
    }
    return {
        "citation_type": query["citation_type"],
        "title": source_title,
        "source": "Kenya Law",
        "source_url": metadata.get("source_url") or metadata.get("canonical_url"),
        "neutral_citation": metadata.get("neutral_citation"),
        "court": metadata.get("court"),
        "judgment_date": metadata.get("judgment_date"),
        "snippet": _bounded_snippet(best.get("text") or ""),
        "confidence": confidence,
        "confidence_breakdown": json.dumps(breakdown),
        "status": status,
    }


def _error_evidence(query: dict[str, str], status: str, message: str) -> dict:
    return {
        "citation_type": query["citation_type"],
        "title": query["title"],
        "source": "Kenya Law",
        "snippet": f"Citation verification failed: {message[:240]}",
        "confidence": 0.0,
        "confidence_breakdown": json.dumps(
            {"citation_match_score": 0.0, "semantic_score": 0.0, "support_score": 0.0}
        ),
        "status": status,
    }


def _extract_neutral_citations(content: str) -> list[str]:
    return sorted(set(re.findall(r"\[\d{4}\]\s*[A-Z]{2,}[A-Z0-9\s]*\d*", content)))


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, (left or "").lower(), (right or "").lower()).ratio()


def _bounded_snippet(text: str, limit: int = 700) -> str:
    compact = re.sub(r"\s+", " ", text or "").strip()
    return compact[:limit] if compact else "Retrieved result did not include text content."
