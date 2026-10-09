"""
SMCH Governed Agent API — Surface 2 Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/agent", tags=["Governed Agent"])


class ConversationMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class AgentQuery(BaseModel):
    query: str
    context: Optional[str] = None
    conversation_history: Optional[List[ConversationMessage]] = []
    role: Optional[str] = "ADMIN"


@router.post("/query")
async def query_agent(body: AgentQuery) -> Dict[str, Any]:
    """
    Send a natural language operational question to the governed agent.
    The agent reads the live ontology graph, applies guardrails, and returns
    a structured answer with policy citations and escalation paths.
    """
    if not body.query or not body.query.strip():
        return {
            "query": body.query,
            "guardrail_triggered": None,
            "answer": "Query cannot be empty.",
            "graph_context_used": False,
            "requires_human_approval": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    try:
        from app.ontology.governed_agent import answer_query
        from app.ontology.graph_service import get_ontology_graph_service
        service = get_ontology_graph_service()
        if service is None or service.builder is None:
            return {
                "query": body.query,
                "guardrail_triggered": None,
                "answer": (
                    "The operational graph is not yet initialised. "
                    "Please run Sync Ontology first via /api/v1/ontology/sync, "
                    "then retry your question."
                ),
                "graph_context_used": False,
                "requires_human_approval": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        history = [{"role": m.role, "content": m.content} for m in (body.conversation_history or [])]
        result = await answer_query(body.query.strip(), service.builder, conversation_history=history, role=body.role or "ADMIN")
        return result
    except Exception as e:
        return {
            "query": body.query,
            "guardrail_triggered": None,
            "answer": f"[Agent pipeline error: {str(e)}]",
            "graph_context_used": False,
            "requires_human_approval": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/health")
async def agent_health() -> Dict[str, Any]:
    """Check if the governed agent is operational."""
    import os
    return {
        "status": "ok",
        "llm_model": os.getenv("LLM_MODEL", "ollama/llama3.2"),
        "llm_endpoint": os.getenv("LLM_ENDPOINT", "http://localhost:11434"),
        "guardrails": "active",
        "surfaces": ["interpretation_dashboard", "governed_agent"],
    }


@router.get("/guardrail-rules")
async def list_guardrail_rules() -> Dict[str, Any]:
    """Return the active guardrail rules (for transparency/audit)."""
    from app.ontology.governed_agent import MEDICAL_ADVICE_KEYWORDS, IRREVERSIBLE_KEYWORDS
    return {
        "medical_advice_triggers": MEDICAL_ADVICE_KEYWORDS,
        "irreversible_action_triggers": IRREVERSIBLE_KEYWORDS,
        "routes": {
            "medical_advice": "Clinical Review — Ext. 1012 | Rule R-001",
            "irreversible_action": "Operations Manager — Ext. 1001 | Rule R-007",
        }
    }
