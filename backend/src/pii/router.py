from fastapi import APIRouter, status
from src.pii import schemas, service

router = APIRouter()


@router.post(
    "/detect",
    response_model=schemas.DetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect PII entities in text",
    description="Runs the OpenAI Privacy Filter model to identify PII spans. "
    "Returns entity type, text, offsets, and confidence score for each detection.",
)
def detect_pii(request: schemas.DetectRequest):
    entities = service.detect_pii(request.text)
    return schemas.DetectResponse(
        entities=[schemas.PiiEntity(**e) for e in entities],
        entity_count=len(entities),
    )


@router.post(
    "/mask",
    response_model=schemas.MaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect and mask PII in text",
    description="Detects PII spans using the Privacy Filter model, then replaces "
    "each span with a bracketed placeholder (e.g. [PRIVATE_PERSON]).",
)
def mask_pii(request: schemas.MaskRequest):
    entities = service.detect_pii(request.text)
    masked_text = service.mask_text(request.text, entities)
    return schemas.MaskResponse(
        masked_text=masked_text,
        entities=[schemas.PiiEntity(**e) for e in entities],
        entity_count=len(entities),
    )
