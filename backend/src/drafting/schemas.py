from typing import List
from src.models import CustomBaseModel


class DraftingRequest(CustomBaseModel):
    matter_id: int
    jurisdiction: str
    subcategory: str
    instructions: str | None = None


class GeneratedBlock(CustomBaseModel):
    id: str
    title: str
    content: str
    status: str


class DraftingResponse(CustomBaseModel):
    matter_id: int
    workflow_state: str
    status: str
    error_status: str | None = None
    blocks: List[GeneratedBlock]


class CitationResponse(CustomBaseModel):
    title: str
    held: str
    court: str | None = None
    source: str | None = None
