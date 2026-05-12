from src.models import CustomBaseModel


class Matter(CustomBaseModel):
    id: str
    division: str
    status: str
    verification_done: int
    verification_total: int
    last_activity: str
