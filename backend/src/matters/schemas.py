from datetime import datetime
from pydantic import ConfigDict, Field
from src.models import CustomBaseModel

WORKFLOW_STATES = {
    "created",
    "facts_entered",
    "pii_masked",
    "draft_generated",
    "citations_verified",
    "export_ready",
}


class MatterBase(CustomBaseModel):
    case_number: str
    division: str
    status: str = "Drafting"
    workflow_state: str = "created"
    jurisdiction: str | None = None
    subcategory: str | None = None
    verification_done: int = 0
    verification_total: int = 0
    last_activity: str | None = None


class MatterCreate(MatterBase):
    workflow_state: str = Field(default="created", exclude=True)
    status: str = "Drafting"


class MatterTransitionRequest(CustomBaseModel):
    workflow_state: str
    expected_state: str | None = None


class MatterActivityRead(CustomBaseModel):
    id: int
    matter_id: int
    event_type: str
    title: str
    detail: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CitationEvidenceRead(CustomBaseModel):
    id: int
    matter_id: int
    citation_type: str
    title: str
    source: str | None = None
    snippet: str
    confidence: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DraftDocumentRead(CustomBaseModel):
    id: int
    matter_id: int
    document_type: str
    title: str
    content: str
    status: str
    error_status: str | None = None
    revision_count: int = 0
    generated_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatterDetailRead(MatterBase):
    id: int
    user_id: int
    raw_facts: str | None = None
    masked_facts: str | None = None
    pii_entity_count: int = 0
    draft_content: str | None = None
    drafting_error: str | None = None
    masked_at: datetime | None = None
    drafted_at: datetime | None = None
    citations_verified_at: datetime | None = None
    export_ready_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    activities: list[MatterActivityRead] = []
    citation_evidence: list[CitationEvidenceRead] = []
    draft_documents: list[DraftDocumentRead] = []

    model_config = ConfigDict(from_attributes=True)


class VerificationResponse(CustomBaseModel):
    matter: MatterDetailRead
    evidence: list[CitationEvidenceRead]


class MatterRead(MatterBase):
    id: int
    user_id: int
    pii_entity_count: int = 0
    masked_at: datetime | None = None
    drafted_at: datetime | None = None
    citations_verified_at: datetime | None = None
    export_ready_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# For backward compatibility if needed, but we should use MatterRead
Matter = MatterRead
