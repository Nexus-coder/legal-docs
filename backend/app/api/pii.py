from fastapi import APIRouter
from app.models.domain import MaskRequest, MaskResponse

router = APIRouter()

@router.post("/mask", response_model=MaskResponse)
def mask_data(request: MaskRequest):
    # Mock masking logic
    text = request.facts
    for entity, variable in request.entities.items():
        text = text.replace(entity, variable)
    return MaskResponse(anonymized_text=text)
