import logging
from fastapi import APIRouter
from src.drafting.schemas import DraftingRequest, DraftingResponse, GeneratedBlock
from src.agent.graph import legal_agent

router = APIRouter()


@router.post("/generate", response_model=DraftingResponse)
def generate_draft(request: DraftingRequest):
    initial_state = {
        "request": request.model_dump(),
        "context": [],
        "draft": "",
        "feedback": "",
        "revision_count": 0,
        "passed_critique": False,
    }

    try:
        # LangGraph Pipeline Execution
        final_state = legal_agent.invoke(initial_state)

        return DraftingResponse(
            blocks=[
                GeneratedBlock(
                    id="block_1",
                    title=f"PROPOSED DRAFT: {request.subcategory.upper()}",
                    content=final_state.get("draft", "No draft output"),
                    status="verified"
                    if final_state.get("passed_critique", False)
                    else "draft",
                )
            ]
        )
    except Exception as e:
        logging.error(f"LangGraph execution failed: {e}")
        return DraftingResponse(
            blocks=[
                GeneratedBlock(
                    id="error_block",
                    title="ERROR: RAG COMPILATION",
                    content=f"Drafting process failed. Ensure API keys are active. Diagnostic: {str(e)}",
                    status="error",
                )
            ]
        )


@router.get("/citations")
def get_citations():
    # Keep standard ground-truth format available to the frontend
    return {
        "title": "Giella v. Cassman Brown & Co. Ltd [1973] EA 358",
        "held": '"The conditions for the grant of an interlocutory injunction are now well settled in East Africa; first, an applicant must show a prima facie case with a probability of success. Secondly, an interlocutory injunction will not normally be granted unless the applicant might otherwise suffer irreparable injury..."',
    }
