from datetime import datetime
from pydantic import ConfigDict
from src.models import CustomBaseModel


class MatterBase(CustomBaseModel):
    case_number: str
    division: str
    status: str = "Drafting"
    verification_done: int = 0
    verification_total: int = 0
    last_activity: str | None = None


class MatterCreate(MatterBase):
    pass


class MatterRead(MatterBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# For backward compatibility if needed, but we should use MatterRead
Matter = MatterRead
