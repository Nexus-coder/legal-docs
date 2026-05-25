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
    usable_text = _strip_index_metadata(text)
    paragraph = _best_evidence_paragraph(usable_text)
    compact = re.sub(r"\s+", " ", paragraph).strip()
    return compact[:limit] if compact else "Retrieved result did not include text content."


def _strip_index_metadata(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n")
    lines = []
    for line in normalized.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            continue
        if _is_index_metadata_line(stripped):
            continue
        lines.append(stripped)
    stripped = "\n\n".join(lines).strip()
    if stripped:
        return stripped

    compact = re.sub(r"\s+", " ", normalized).strip()
    return re.sub(
        r"^#?\s*.*?\bcorpus_scope:\s*\S+\s*",
        "",
        compact,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def _is_index_metadata_line(line: str) -> bool:
    return bool(
        re.match(
            r"^(source|source_url|canonical_url|title|neutral_citation|court|"
            r"judgment_date|topic_tags|source_document_url|source_format|"
            r"extraction_status|text_quality_score|document_hash|corpus_scope):\s*",
            line,
            flags=re.IGNORECASE,
        )
    )


def _best_evidence_paragraph(text: str) -> str:
    paragraphs = [
        re.sub(r"\s+", " ", paragraph).strip()
        for paragraph in re.split(r"\n\s*\n", text or "")
        if paragraph.strip()
    ]
    if not paragraphs:
        return ""

    legal_terms = (
        "injunction",
        "prima facie",
        "irreparable",
        "balance of convenience",
        "application",
        "applicant",
        "respondent",
        "court",
        "held",
        "order",
    )
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        if len(paragraph) >= 80 and any(term in lowered for term in legal_terms):
            return paragraph
    for paragraph in paragraphs:
        if len(paragraph) >= 80:
            return paragraph
    return paragraphs[0]
