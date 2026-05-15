from src.models import CustomBaseModel


class PiiEntity(CustomBaseModel):
    entity_type: str
    text: str
    start: int
    end: int
    score: float


# ── Detection ────────────────────────────────────────────────────

class DetectRequest(CustomBaseModel):
    text: str


class DetectResponse(CustomBaseModel):
    entities: list[PiiEntity]
    entity_count: int


# ── Masking ──────────────────────────────────────────────────────

class MaskRequest(CustomBaseModel):
    matter_id: int
    text: str
    jurisdiction: str | None = None
    subcategory: str | None = None


class MaskResponse(CustomBaseModel):
    matter_id: int
    workflow_state: str
    masked_text: str
    entities: list[PiiEntity]
    entity_count: int
    status: str = "pii_masked"
