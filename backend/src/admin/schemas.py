from src.models import CustomBaseModel


class FlaggedItem(CustomBaseModel):
    reference: str
    claim: str
    status: str
    action: str
