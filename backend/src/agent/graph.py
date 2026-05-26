from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.ingestion.indexer import retrieve_context
from src.kenyalaw.service import PINECONE_NAMESPACE
from src.config import settings


class AgentState(TypedDict):
    request: dict
    context: List[Dict[str, Any]]
    draft: str
    feedback: str
    revision_count: int
    passed_critique: bool


# Initialize the OpenAI model (using standard gpt-4o or similar depending on env)
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.OPENAI_API_KEY)


def retrieve_node(state: AgentState) -> dict:
    req = state["request"]
    query = f"{req.get('subcategory', '')} in {req.get('jurisdiction', '')}. {req.get('instructions', '')}"
    context = retrieve_context(query, namespace=PINECONE_NAMESPACE)
    return {"context": context}


def draft_node(state: AgentState) -> dict:
    req = state["request"]
    context_str = "\n---\n".join([c["text"] for c in state.get("context", [])])
    feedback = state.get("feedback", "")

    prompt = f"""
    Draft a pleading block for the following legal request:
    Jurisdiction: {req.get("jurisdiction", "N/A")}
    Category: {req.get("subcategory", "N/A")}
    Instructions: {req.get("instructions", "N/A")}
    
    ## Ground Truth / Relevant Context:
    {context_str}
    """

    if feedback:
        prompt += f"\n\n## Feedback on Previous Draft\nThe previous draft failed critique for the following reasons:\n{feedback}\n\nPlease revise the draft to address these issues."

    messages = [
        SystemMessage(
            content="You are an expert litigation lawyer assisting in drafting Kenyan legal pleadings. Output only the requested pleading block without conversational padding."
        ),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    revision_count = state.get("revision_count", 0) + 1
    return {"draft": response.content, "revision_count": revision_count}


def critique_node(state: AgentState) -> dict:
    draft = state["draft"]

    prompt = f"""
    Critique the following legal pleading draft:
    
    {draft}
    
    Strictly evaluate based on:
    1. Formatting rules for Kenyan Court submissions.
    2. Logic and reasoning tied to the extracted context.
    3. Proper inclusion of provided instructions.
    
    If it is rigorous, legally sound, and directly addresses the prompt, return exactly: "PASS".
    If it needs improvement, return a detailed explanation prefixed with "FAIL: " outlining what must be fixed.
    """

    messages = [
        SystemMessage(
            content="You are a strict Senior Partner reviewing a draft. Your standard is absolute perfection."
        ),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    result = response.content.strip()

    if result.startswith("PASS"):
        return {"passed_critique": True, "feedback": ""}
    else:
        return {"passed_critique": False, "feedback": result}


def route_critique(state: AgentState) -> str:
    """Routes to END if passed or max revisions hit, else loops back to draft."""
    if state.get("passed_critique", False):
        return END
    if state.get("revision_count", 0) >= 3:
        return END
    return "draft"


workflow = StateGraph(AgentState)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("draft", draft_node)
workflow.add_node("critique", critique_node)

workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "draft")
workflow.add_edge("draft", "critique")
workflow.add_conditional_edges("critique", route_critique, {END: END, "draft": "draft"})

legal_agent = workflow.compile()
