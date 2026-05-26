from datetime import datetime
from typing import Any, List

from pydantic import ConfigDict

from src.models import CustomBaseModel
from src.matters.schemas import DraftDocumentRead


class DraftingRequest(CustomBaseModel):
    matter_id: int
    jurisdiction: str | None = None
    subcategory: str | None = None
    pleading_type: str | None = None
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
    documents: List[DraftDocumentRead] = []
    blocks: List[GeneratedBlock]


class DraftingRunRead(CustomBaseModel):
    id: int
    matter_id: int
    user_id: int
    status: str
    jurisdiction: str | None = None
    subcategory: str | None = None
    pleading_type: str | None = None
    error_status: str | None = None
    started_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DraftingEventRead(CustomBaseModel):
    id: int
    drafting_run_id: int
    event_type: str
    stage: str
    message: str
    document_type: str | None = None
    error_type: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitationResponse(CustomBaseModel):
    title: str
    held: str
    court: str | None = None
    source: str | None = None


class DraftDocumentSaveRequest(CustomBaseModel):
    editor_json: dict[str, Any]
    expected_revision: int
    revision_type: str = "manual"


class DraftDocumentSaveResponse(CustomBaseModel):
    document: DraftDocumentRead
