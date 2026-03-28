from fastapi import APIRouter
from app.models.domain import DraftingRequest, DraftingResponse, GeneratedBlock

router = APIRouter()

@router.post("/generate", response_model=DraftingResponse)
def generate_draft(request: DraftingRequest):
    return DraftingResponse(
        blocks=[
            GeneratedBlock(
                id="block_1",
                title="GROUND 1: ADVERSE POSSESSION",
                content="The Plaintiff has been in open, notorious, and continuous possession of [LAND_ID_1] for a period exceeding 12 years without the consent of the Registered Owner, meeting the threshold under Section 7 of the Limitation of Actions Act.",
                status="draft"
            )
        ]
    )

@router.get("/citations")
def get_citations():
    return {
        "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
        "court": "IN THE ENVIRONMENT AND LAND COURT AT NAIROBI",
        "held": "\"The conditions for the grant of an interlocutory injunction are now well settled in East Africa; first, an applicant must show a prima facie case with a probability of success. Secondly, an interlocutory injunction will not normally be granted unless the applicant might otherwise suffer irreparable injury...\""
    }
