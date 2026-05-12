from src.models import CustomBaseModel


class MaskRequest(CustomBaseModel):
    facts: str
    entities: dict


class MaskResponse(CustomBaseModel):
    anonymized_text: str
