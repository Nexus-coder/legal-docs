from __future__ import annotations

import logging
import threading
from transformers import pipeline as hf_pipeline

from src.pii.config import pii_settings

logger = logging.getLogger(__name__)

# ── Lazy singleton for the HF pipeline ───────────────────────────
_classifier = None
_lock = threading.Lock()


def _get_classifier():
    """Load the model lazily on first call. Thread-safe via lock."""
    global _classifier
    if _classifier is None:
        with _lock:
            if _classifier is None:
                logger.info(
                    "Loading PII model '%s' on device '%s' …",
                    pii_settings.MODEL_NAME,
                    pii_settings.DEVICE,
                )
                _classifier = hf_pipeline(
                    task="token-classification",
                    model=pii_settings.MODEL_NAME,
                    device=pii_settings.DEVICE,
                    aggregation_strategy="simple",
                )
                logger.info("PII model loaded successfully.")
    return _classifier


# ── Public API ───────────────────────────────────────────────────

def detect_pii(text: str) -> list[dict]:
    """
    Run the Privacy Filter model over *text* and return a list of
    detected PII entities that meet the confidence threshold.

    Each entity dict has: entity_type, text, start, end, score.
    """
    classifier = _get_classifier()
    raw_entities = classifier(text)

    entities = []
    for ent in raw_entities:
        score = float(ent["score"])
        if score < pii_settings.CONFIDENCE_THRESHOLD:
            continue
        entities.append(
            {
                "entity_type": ent["entity_group"],
                "text": ent["word"].strip(),
                "start": int(ent["start"]),
                "end": int(ent["end"]),
                "score": round(score, 4),
            }
        )
    return entities


def mask_text(text: str, entities: list[dict]) -> str:
    """
    Replace each detected entity span with a placeholder like
    ``[PRIVATE_PERSON]``.  Processes spans right-to-left so that
    earlier offsets stay valid.
    """
    # Sort by start offset descending so replacements don't shift indices
    sorted_entities = sorted(entities, key=lambda e: e["start"], reverse=True)
    masked = text
    for ent in sorted_entities:
        label = ent["entity_type"].upper()
        placeholder = f"[{label}]"
        masked = masked[: ent["start"]] + placeholder + masked[ent["end"] :]
    return masked
