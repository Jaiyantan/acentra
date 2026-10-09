"""
app/routers/baseline_router.py
FastAPI Router for Baseline Hospital Operations RBAC Endpoints.
Exposes the 14 baseline SQLite tables through the 12 specified RBAC endpoints.
Provides backwards-compatibility with the static simulation specification.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter(tags=["Baseline Operations (12 RBAC Endpoints)"])

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

_HOSP_CANDIDATES = [
    ROOT_DIR / "data" / "hospital.db",
    ROOT_DIR / "db" / "hospital.db",
    ROOT_DIR / "hospital.db",
]
BASELINE_DB_PATH = next((p for p in _HOSP_CANDIDATES if p.exists()), _HOSP_CANDIDATES[0])


def get_baseline_db_connection() -> sqlite3.Connection:
    if not BASELINE_DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Baseline database not found at {BASELINE_DB_PATH}. Please run python data/seed.py."
        )
    conn = sqlite3.connect(BASELINE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def dict_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return {}
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, str) and (v.startswith("{") or v.startswith("[")):
            try:
                d[k] = json.loads(v)
            except Exception:
                pass
    return d


def verify_staff_permission(required_permission: str, staff_id: Optional[str]) -> Dict[str, Any]:
    """
    RBAC Check:
    Checks if X-Staff-ID maps to an active staff record and that its permissions
    array contains the required permission (or wildcard '*').
    Returns HTTP 403 Forbidden on failure.
    """
    if not staff_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Missing X-Staff-ID header."
        )

    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT staff_id, name, role, permissions, is_active FROM staff WHERE staff_id = ?", (staff_id,))
    staff = cursor.fetchone()
    conn.close()

    if not staff or not staff["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Staff ID '{staff_id}' not found or inactive."
        )

    try:
        perms = json.loads(staff["permissions"])
    except Exception:
        perms = []

    if "*" not in perms and required_permission not in perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Staff '{staff_id}' lacks required permission '{required_permission}'."
        )

    return dict(staff)


# =========================================================================
# Endpoint 1: GET /patient/search?name=&dob= (Must precede /patient/{uhid})
# =========================================================================
@router.get("/patient/search", summary="Search matching patients")
def search_patients(
    name: Optional[str] = Query(None, description="Patient name substring"),
    dob: Optional[str] = Query(None, description="Date of birth / Registration date filter"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("patient:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM patients WHERE 1=1"
    params = []

    if name:
        query += " AND name LIKE ?"
        params.append(f"%{name}%")
    if dob:
        query += " AND (registration_date LIKE ? OR address LIKE ?)"
        params.append(f"%{dob}%")
        params.append(f"%{dob}%")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 2: GET /patient/{uhid}
# =========================================================================
@router.get("/patient/{uhid}", summary="Get patient row")
def get_patient(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("patient:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE uhid = ?", (uhid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Patient with UHID '{uhid}' not found.")
    return dict_from_row(row)


# =========================================================================
# Endpoint 3: GET /admission/{admission_id}
# =========================================================================
@router.get("/admission/{admission_id}", summary="Get admission row")
def get_admission(admission_id: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("admission:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admissions WHERE admission_id = ?", (admission_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Admission '{admission_id}' not found.")
    return dict_from_row(row)


# =========================================================================
# Endpoint 4: GET /admissions?status=active
# =========================================================================
@router.get("/admissions", summary="List admissions filtered by status")
def list_admissions(
    status: Optional[str] = Query("active", description="Admission status (e.g. active, discharged, transferred)"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("admission:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute("SELECT * FROM admissions WHERE status = ? ORDER BY admission_date DESC", (status,))
    else:
        cursor.execute("SELECT * FROM admissions ORDER BY admission_date DESC")

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 5: GET /beds/available?ward=
# =========================================================================
@router.get("/beds/available", summary="List available beds in ward")
def get_available_beds(
    ward: Optional[str] = Query(None, description="Ward name: 'General Ward', 'ICU', 'Emergency'"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("beds:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    if ward:
        cursor.execute("SELECT * FROM beds WHERE status = 'available' AND ward = ? ORDER BY bed_id ASC", (ward,))
    else:
        cursor.execute("SELECT * FROM beds WHERE status = 'available' ORDER BY ward ASC, bed_id ASC")

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 6: GET /bill/{uhid}
# =========================================================================
@router.get("/bill/{uhid}", summary="Get latest bill for patient")
def get_latest_bill(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("billing:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bills WHERE uhid = ? ORDER BY bill_date DESC LIMIT 1", (uhid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"No bill found for UHID '{uhid}'.")
    return dict_from_row(row)


# =========================================================================
# Endpoint 7: GET /insurance/{uhid}
# =========================================================================
@router.get("/insurance/{uhid}", summary="Get insurance claim for patient")
def get_insurance_claim(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("insurance:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM insurance_claims WHERE uhid = ? ORDER BY preauth_requested_at DESC LIMIT 1", (uhid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"No insurance claim found for UHID '{uhid}'.")
    return dict_from_row(row)


# =========================================================================
# Endpoint 8: GET /tickets?team=&status=open
# =========================================================================
@router.get("/tickets", summary="List tickets filtered by team and status")
def list_tickets(
    team: Optional[str] = Query(None, description="Assigned team"),
    status: Optional[str] = Query("open", description="Ticket status (open, in_progress, escalated, resolved, closed)"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("tickets:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if team:
        query += " AND assigned_to_team = ?"
        params.append(team)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 9: GET /audit?limit=20
# =========================================================================
@router.get("/audit", summary="Get last N audit log entries")
def get_audit_logs(
    limit: int = Query(20, ge=1, le=100, description="Max number of entries to return"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("audit:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 10: GET /pending_approvals?status=pending
# =========================================================================
@router.get("/pending_approvals", summary="List pending approval records")
def get_pending_approvals(
    status: Optional[str] = Query("pending", description="Status: pending, approved, rejected"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("approvals:read", x_staff_id)
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    if status:
        cursor.execute("SELECT * FROM pending_approvals WHERE status = ? ORDER BY requested_at DESC", (status,))
    else:
        cursor.execute("SELECT * FROM pending_approvals ORDER BY requested_at DESC")

    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 11: POST /pending_approvals
# =========================================================================
class PendingApprovalCreate(BaseModel):
    approval_id: Optional[str] = None
    requested_by_staff_id: str
    action_type: str
    action_payload: Union[Dict[str, Any], str]
    status: Optional[str] = "pending"
    requested_at: Optional[str] = None


@router.post("/pending_approvals", status_code=status.HTTP_201_CREATED, summary="Insert a new pending approval record")
def create_pending_approval(payload: PendingApprovalCreate):
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    approval_id = payload.approval_id or f"APP-{uuid.uuid4().hex[:6].upper()}"
    requested_at = payload.requested_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    action_payload_str = (
        json.dumps(payload.action_payload)
        if isinstance(payload.action_payload, dict)
        else str(payload.action_payload)
    )

    try:
        cursor.execute("""
            INSERT INTO pending_approvals (approval_id, requested_by_staff_id, action_type, action_payload, status, requested_at, actioned_at, actioned_by)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)
        """, (
            approval_id,
            payload.requested_by_staff_id,
            payload.action_type,
            action_payload_str,
            payload.status or "pending",
            requested_at
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Integrity Error: {str(e)}")
    finally:
        conn.close()

    return {
        "status": "success",
        "approval_id": approval_id,
        "requested_by_staff_id": payload.requested_by_staff_id,
        "action_type": payload.action_type,
        "action_payload": payload.action_payload,
        "approval_status": payload.status or "pending",
        "requested_at": requested_at
    }


# =========================================================================
# Endpoint 12: POST /audit
# =========================================================================
class AuditLogCreate(BaseModel):
    log_id: Optional[str] = None
    timestamp: Optional[str] = None
    session_id: str
    staff_id: str
    action: str  # QUERY, WORKFLOW_STEP, TOOL_CALL, ESCALATION, APPROVAL
    entity_type: str
    entity_id: str
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    documents_cited: Optional[Union[List[str], str]] = None
    confidence_score: Optional[float] = None
    escalated: bool = False
    irreversible_action: bool = False
    human_approved: Optional[bool] = None


@router.post("/audit", status_code=status.HTTP_201_CREATED, summary="Insert an audit log entry")
def create_audit_log(entry: AuditLogCreate):
    conn = get_baseline_db_connection()
    cursor = conn.cursor()

    log_id = entry.log_id or f"LOG-{uuid.uuid4().hex[:6].upper()}"
    ts = entry.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    docs_str = (
        json.dumps(entry.documents_cited)
        if isinstance(entry.documents_cited, list)
        else (entry.documents_cited or "[]")
    )

    try:
        cursor.execute("""
            INSERT INTO audit_log (
                log_id, timestamp, session_id, staff_id, action,
                entity_type, entity_id, input_summary, output_summary,
                documents_cited, confidence_score, escalated, irreversible_action, human_approved
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            ts,
            entry.session_id,
            entry.staff_id,
            entry.action,
            entry.entity_type,
            entry.entity_id,
            entry.input_summary,
            entry.output_summary,
            docs_str,
            entry.confidence_score,
            1 if entry.escalated else 0,
            1 if entry.irreversible_action else 0,
            1 if entry.human_approved is True else (0 if entry.human_approved is False else None)
        ))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Integrity Error: {str(e)}")
    finally:
        conn.close()

    return {
        "status": "success",
        "log_id": log_id,
        "timestamp": ts,
        "action": entry.action,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id
    }


# =========================================================================
# Auxiliary Data Explorer Endpoints
# =========================================================================
@router.get("/api/stats", summary="Get row counts across all 14 baseline tables")
def get_stats():
    valid_tables = [
        "patients", "staff", "departments", "beds", "admissions",
        "discharges", "orders", "lab_results", "prescriptions",
        "bills", "insurance_claims", "tickets", "pending_approvals", "audit_log"
    ]
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    stats = {}
    for t in valid_tables:
        cursor.execute(f"SELECT count(*) FROM {t}")
        stats[t] = cursor.fetchone()[0]
    conn.close()
    return stats


@router.get("/api/tables/{table_name}", summary="Browse rows of any baseline table")
def get_table_data(table_name: str, limit: int = 50):
    valid_tables = [
        "patients", "staff", "departments", "beds", "admissions",
        "discharges", "orders", "lab_results", "prescriptions",
        "bills", "insurance_claims", "tickets", "pending_approvals", "audit_log"
    ]
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table '{table_name}'. Valid: {valid_tables}")
    conn = get_baseline_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]
