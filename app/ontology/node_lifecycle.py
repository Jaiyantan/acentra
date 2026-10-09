"""
SMCH Node Lifecycle Manager
============================
State-based TTL expiration for operational graph nodes.

Design
------
- Each operational node type has a TTL in hours, but the countdown only STARTS
  when the node reaches its terminal / inactive state. While a node is still
  operationally active (patient is admitted, alert is unacknowledged, claim is
  pending) it carries ``_expires_at = None`` and is never pruned.
- On every prune run, ``stamp_ttl`` is re-evaluated for all nodes so that
  nodes which recently reached their terminal state get their expiry set.
- Governance nodes (SOPs, Policies, KAs, RoutingRules, Beds) are permanent.

Why state-based TTL beats fixed-from-creation TTL
--------------------------------------------------
A patient admitted for a 20-day ICU stay would be wrongly pruned on day 90 if
the clock started at admission.  With state-based TTL the clock only starts
after the discharge is confirmed — so active clinical records are protected
regardless of how long treatment takes.

Why TTL solves two problems
---------------------------
Context Decay:
    Without TTL a discharged patient's stale embedding stays in the vector
    index forever, polluting semantic search for current-patient queries.
    With TTL the node is removed from both the builder dict and the vector
    index once it expires, so it can never surface as a false positive.

Storage Cost:
    A busy hospital generates ~300 new operational nodes/day.  Without pruning
    the builder holds 100K+ nodes after a year.  With TTL the steady-state
    stays bounded at ~5K–10K live nodes.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL policy — hours the countdown runs AFTER terminal state is reached
# ---------------------------------------------------------------------------
NODE_TTL_HOURS: Dict[str, Optional[int]] = {
    # Short-lived operational
    "LabPanicAlertNode":    72,     # 3 days after Acknowledged
    "EmergencyCaseNode":    168,    # 7 days after closed
    "PrescriptionNode":     168,    # 7 days after dispensed/completed
    "TicketNode":           720,    # 30 days after resolved

    # Medium-lived clinical records
    "AdmissionNode":        2160,   # 90 days after discharge_date set
    "DischargeNode":        2160,   # 90 days after gate_pass_issued
    "LabResultNode":        2160,   # 90 days — always static once reported
    "BillNode":             8760,   # 1 year after final_settled
    "ClaimNode":            8760,   # 1 year after approved/rejected

    # Identity — long but not permanent
    "PatientNode":          4320,   # 180 days after status == discharged

    # Infrastructure — permanent, never pruned
    "BedNode":              None,
    "SOPNode":              None,
    "PolicyNode":           None,
    "KnowledgeArticleNode": None,
    "RoutingRuleNode":      None,
    "FieldDefinitionNode":  None,
}

PERMANENT_TYPES = {"BedNode", "SOPNode", "PolicyNode", "KnowledgeArticleNode",
                   "RoutingRuleNode", "FieldDefinitionNode"}

# Terminal-state predicates — return True when the node is done / inactive
_TERMINAL_CHECKS = {
    "PatientNode":       lambda n: getattr(n, "status", "") == "discharged",
    "AdmissionNode":     lambda n: bool(getattr(n, "discharge_date", None)),
    "DischargeNode":     lambda n: (not getattr(n, "is_blocked", True)
                                    and getattr(n, "gate_pass_issued", False)),
    "LabPanicAlertNode": lambda n: getattr(n, "readback_status", "") == "Acknowledged",
    "LabResultNode":     lambda n: True,        # static once reported
    "BillNode":          lambda n: getattr(n, "status", "") == "final_settled",
    "ClaimNode":         lambda n: getattr(n, "status", "").lower() in ("approved", "rejected"),
    "PrescriptionNode":  lambda n: getattr(n, "status", "").lower() in ("dispensed", "completed"),
    "EmergencyCaseNode": lambda n: getattr(n, "status", "") == "closed",
    "TicketNode":        lambda n: getattr(n, "status", "") == "resolved",
}

PRUNE_INTERVAL_SECONDS = 300  # suggested background cadence


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def stamp_ttl(node: Any, node_type: str) -> None:
    """Attach ``_expires_at`` ISO string to a node object in-place.

    Sets ``_expires_at = None`` while the node is still active.
    Sets an ISO timestamp once the node has reached its terminal state.
    Safe to call repeatedly — nodes whose expiry is already set keep it.
    Uses ``object.__setattr__`` so frozen Pydantic models work without
    schema changes.
    """
    # Permanent types — never expire
    if node_type in PERMANENT_TYPES:
        _set_attr(node, "_expires_at", None)
        return

    ttl = NODE_TTL_HOURS.get(node_type)
    if ttl is None:
        _set_attr(node, "_expires_at", None)
        return

    # If already stamped with a concrete expiry, leave it alone — the clock
    # should not reset on subsequent re-stamps (e.g. background sync runs).
    existing = getattr(node, "_expires_at", "__missing__")
    if existing != "__missing__" and existing is not None:
        return  # already counting down

    check = _TERMINAL_CHECKS.get(node_type)
    if check and check(node):
        exp = datetime.now(timezone.utc) + timedelta(hours=ttl)
        _set_attr(node, "_expires_at", exp.isoformat())
    else:
        _set_attr(node, "_expires_at", None)   # still active


def is_expired(expires_at_iso: Optional[str]) -> bool:
    """Return True if the ISO timestamp is non-null and in the past."""
    if not expires_at_iso:
        return False
    try:
        exp = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > exp
    except Exception:
        return False


def prune_builder(builder) -> Dict[str, Any]:
    """Remove expired nodes from the in-memory OntologyBuilder.

    Steps:
    1. Re-stamp all nodes so newly-terminal nodes get their expiry set.
    2. Scan for nodes whose ``_expires_at`` is now in the past.
    3. Remove them from the builder dict.
    4. Evict their embeddings from the LanceDB operational vector store.

    Returns a summary dict with counts by type.
    """
    collections = [
        ("lab_critical_alerts", "LabPanicAlertNode"),
        ("emergency_cases",     "EmergencyCaseNode"),
        ("prescriptions",       "PrescriptionNode"),
        ("admissions",          "AdmissionNode"),
        ("discharges",          "DischargeNode"),
        ("lab_results",         "LabResultNode"),
        ("bills",               "BillNode"),
        ("claims",              "ClaimNode"),
        ("patients",            "PatientNode"),
    ]

    # Step 1 — re-stamp so newly-terminal nodes get their countdown started
    for attr, node_type in collections:
        for node in getattr(builder, attr, {}).values():
            stamp_ttl(node, node_type)

    # Step 2 & 3 — find and remove expired nodes
    pruned: Dict[str, List[str]] = {}
    ids_to_evict: List[str] = []

    for attr, node_type in collections:
        store: dict = getattr(builder, attr, {})
        expired = [
            key for key, node in store.items()
            if is_expired(getattr(node, "_expires_at", None))
        ]
        for key in expired:
            del store[key]
            ids_to_evict.append(key)
        if expired:
            pruned[node_type] = expired

    # Step 4 — evict embeddings from LanceDB
    if ids_to_evict:
        try:
            from app.ontology.vector_store import remove_nodes
            remove_nodes(ids_to_evict)
        except Exception as e:
            _log.warning("Vector store prune failed: %s", e)

    result: Dict[str, Any] = {
        "pruned_total": len(ids_to_evict),
        "by_type": {k: len(v) for k, v in pruned.items()},
        "pruned_ids_sample": ids_to_evict[:10],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if ids_to_evict:
        _log.info("Node pruner removed %d expired nodes: %s",
                  len(ids_to_evict), result["by_type"])
    return result


def get_lifecycle_stats(builder) -> Dict[str, Any]:
    """Return counts of live vs terminal vs expired nodes per type for the dashboard."""
    collections = [
        ("lab_critical_alerts", "LabPanicAlertNode"),
        ("emergency_cases",     "EmergencyCaseNode"),
        ("prescriptions",       "PrescriptionNode"),
        ("admissions",          "AdmissionNode"),
        ("discharges",          "DischargeNode"),
        ("lab_results",         "LabResultNode"),
        ("bills",               "BillNode"),
        ("claims",              "ClaimNode"),
        ("patients",            "PatientNode"),
        ("beds",                "BedNode"),
        ("sops",                "SOPNode"),
        ("policies",            "PolicyNode"),
        ("articles",            "KnowledgeArticleNode"),
        ("routing_rules",       "RoutingRuleNode"),
    ]
    stats = {}
    total_live = total_terminal = total_expired = 0
    for attr, node_type in collections:
        store: dict = getattr(builder, attr, {})
        live = terminal = expired = 0
        for node in store.values():
            exp = getattr(node, "_expires_at", None)
            if exp is None:
                live += 1
            elif is_expired(exp):
                expired += 1
            else:
                terminal += 1
        stats[node_type] = {"live": live, "terminal": terminal, "expired": expired,
                            "total": live + terminal + expired}
        total_live += live
        total_terminal += terminal
        total_expired += expired

    return {
        "by_type": stats,
        "totals": {"live": total_live, "terminal": total_terminal, "expired": total_expired},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _set_attr(node: Any, name: str, value: Any) -> None:
    try:
        object.__setattr__(node, name, value)
    except Exception:
        try:
            node.__dict__[name] = value
        except Exception:
            pass
