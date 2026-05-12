from typing import List
from src.models import CustomBaseModel


class DraftingRequest(CustomBaseModel):
    jurisdiction: str
    subcategory: str
    instructions: str


class GeneratedBlock(CustomBaseModel):
    id: str
    title: str
    content: str
    status: str


class DraftingResponse(CustomBaseModel):
    blocks: List[GeneratedBlock]
