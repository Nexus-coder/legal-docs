from pydantic import BaseModel
from typing import List, Optional

class Matter(BaseModel):
    id: str
    division: str
    status: str
    verification_done: int
    verification_total: int
    last_activity: str

class MaskRequest(BaseModel):
    facts: str
    entities: dict

class MaskResponse(BaseModel):
    anonymized_text: str

class DraftingRequest(BaseModel):
    jurisdiction: str
    subcategory: str
    instructions: str

class GeneratedBlock(BaseModel):
    id: str
    title: str
    content: str
    status: str

class DraftingResponse(BaseModel):
    blocks: List[GeneratedBlock]

class FlaggedItem(BaseModel):
    reference: str
    claim: str
    status: str
    action: str
