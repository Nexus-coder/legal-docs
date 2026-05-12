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
    text: str


class MaskResponse(CustomBaseModel):
    masked_text: str
    entities: list[PiiEntity]
    entity_count: int
