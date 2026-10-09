"""
Shared in-memory state for approval queue and audit log.
Single module import ensures both modules reference the same lists.
"""
from typing import Any, Dict, List
import uuid
from datetime import datetime, timezone

APPROVAL_QUEUE: List[Dict[str, Any]] = []    # pending human approvals
APPROVAL_HISTORY: List[Dict[str, Any]] = []  # approved / denied records
AUDIT_LOG: List[Dict[str, Any]] = []         # every significant action


def add_approval(query: str, guardrail: str, escalation: str, reason: str, context: str = "") -> str:
    """Add an item to the approval queue. Returns the approval ID."""
    aid = "APR-" + uuid.uuid4().hex[:8].upper()
    APPROVAL_QUEUE.append({
        "id": aid,
        "query": query,
        "guardrail": guardrail,
        "escalation": escalation,
        "reason": reason,
        "context": context,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return aid


def resolve_approval(approval_id: str, action: str, resolved_by: str = "admin") -> bool:
    """Move an item from queue to history with the given action (approved/denied)."""
    for i, item in enumerate(APPROVAL_QUEUE):
        if item["id"] == approval_id:
            resolved = {**item, "status": action, "resolved_by": resolved_by,
                        "resolved_at": datetime.now(timezone.utc).isoformat()}
            APPROVAL_HISTORY.insert(0, resolved)
            APPROVAL_QUEUE.pop(i)
            audit("APPROVAL", approval_id, action, f"{action} by {resolved_by}")
            return True
    return False


def audit(event_type: str, entity_id: str, action: str, detail: str = "", role: str = "system"):
    """Append an audit entry."""
    AUDIT_LOG.insert(0, {
        "id": "AUD-" + uuid.uuid4().hex[:6].upper(),
        "event_type": event_type,      # QUERY, GUARDRAIL, ACTION, APPROVAL, RBAC_DENY
        "entity_id": entity_id,
        "action": action,
        "detail": detail,
        "role": role,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    # Keep only last 500 entries
    if len(AUDIT_LOG) > 500:
        AUDIT_LOG.pop()
