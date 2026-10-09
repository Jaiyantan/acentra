"""
api/main.py
FastAPI layer for Hospital Operations Simulation.
A pure static data environment exposing SQLite database records.
Contains exactly 12 endpoints as specified with RBAC header verification.
Includes an interactive Simulation Dashboard at http://localhost:8000/ to view the 14 tables.
No AI, no LLM, no agent loop, no workflow reasoning.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

from fastapi import FastAPI, Header, HTTPException, Query, Request, WebSocket, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

_log = logging.getLogger(__name__)

# Locate database
ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "hospital.db"
if not DB_PATH.exists():
    DB_PATH = ROOT_DIR / "db" / "hospital.db"


async def _background_sync():
    """Re-sync ontology graph every 5 min, re-stamp TTLs, and prune expired nodes."""
    await asyncio.sleep(30)  # initial delay after startup
    while True:
        try:
            from app.ontology.graph_service import get_ontology_graph_service
            svc = get_ontology_graph_service()
            if svc and svc.builder:
                from app.ontology.node_lifecycle import prune_builder
                prune_result = prune_builder(svc.builder)
                if prune_result.get("pruned_total", 0):
                    _log.info("Background pruner: %s", prune_result)
                # Re-embed mutated nodes incrementally
                try:
                    from app.ontology.kb_ingestion import ingest_operational_twin_contexts
                    await ingest_operational_twin_contexts(svc.builder)
                except Exception:
                    pass
        except Exception as e:
            _log.debug("Background sync error (non-fatal): %s", e)
        await asyncio.sleep(300)  # 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_background_sync())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Hospital Operations Simulation API",
    description="Static data environment simulating hospital backend HIS/LIS/Billing systems.",
    version="1.0.0",
    lifespan=lifespan,
)

from app.routers.ontology_api import router as ontology_router
app.include_router(ontology_router)

from app.routers.agent_api import router as agent_router
app.include_router(agent_router)

from app.routers.dashboard_api import router as dashboard_router
app.include_router(dashboard_router)

def get_db_connection():
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database file not found at {DB_PATH}. Please run python db/seed.py."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    if row is None:
        return {}
    d = dict(row)
    # Parse JSON fields if present
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
    
    conn = get_db_connection()
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
# Endpoint 1: GET /patient/{uhid}
# =========================================================================
@app.get("/patient/{uhid}", summary="Get patient row")
def get_patient(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("patient:read", x_staff_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE uhid = ?", (uhid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Patient with UHID '{uhid}' not found.")
    return dict_from_row(row)


# =========================================================================
# Endpoint 2: GET /patient/search?name=&dob=
# =========================================================================
@app.get("/patient/search", summary="Search matching patients")
def search_patients(
    name: Optional[str] = Query(None, description="Patient name substring"),
    dob: Optional[str] = Query(None, description="Date of birth / Registration date filter"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("patient:read", x_staff_id)
    conn = get_db_connection()
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
# Endpoint 3: GET /admission/{admission_id}
# =========================================================================
@app.get("/admission/{admission_id}", summary="Get admission row")
def get_admission(admission_id: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("admission:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/admissions", summary="List admissions filtered by status")
def list_admissions(
    status: Optional[str] = Query("active", description="Admission status (e.g. active, discharged, transferred)"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("admission:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/beds/available", summary="List available beds in ward")
def get_available_beds(
    ward: Optional[str] = Query(None, description="Ward name: 'General Ward', 'ICU', 'Emergency'"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("beds:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/bill/{uhid}", summary="Get latest bill for patient")
def get_latest_bill(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("billing:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/insurance/{uhid}", summary="Get insurance claim for patient")
def get_insurance_claim(uhid: str, x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")):
    verify_staff_permission("insurance:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/tickets", summary="List tickets filtered by team and status")
def list_tickets(
    team: Optional[str] = Query(None, description="Assigned team"),
    status: Optional[str] = Query("open", description="Ticket status (open, in_progress, escalated, resolved, closed)"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("tickets:read", x_staff_id)
    conn = get_db_connection()
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
@app.get("/audit", summary="Get last N audit log entries")
def get_audit_logs(
    limit: int = Query(20, ge=1, le=100, description="Max number of entries to return"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("audit:read", x_staff_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [dict_from_row(r) for r in rows]


# =========================================================================
# Endpoint 10: GET /pending_approvals?status=pending
# =========================================================================
@app.get("/pending_approvals", summary="List pending approval records")
def get_pending_approvals(
    status: Optional[str] = Query("pending", description="Status: pending, approved, rejected"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-ID")
):
    verify_staff_permission("approvals:read", x_staff_id)
    conn = get_db_connection()
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

@app.post("/pending_approvals", status_code=status.HTTP_201_CREATED, summary="Insert a new pending approval record")
def create_pending_approval(payload: PendingApprovalCreate):
    conn = get_db_connection()
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

@app.post("/audit", status_code=status.HTTP_201_CREATED, summary="Insert an audit log entry")
def create_audit_log(entry: AuditLogCreate):
    conn = get_db_connection()
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
# Auxiliary Data Explorer Endpoints (For UI and Data Inspection)
# =========================================================================
@app.get("/api/stats", summary="Get row counts across all 14 simulation tables")
def get_stats():
    valid_tables = [
        "patients", "staff", "departments", "beds", "admissions",
        "discharges", "orders", "lab_results", "prescriptions",
        "bills", "insurance_claims", "tickets", "pending_approvals", "audit_log"
    ]
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}
    for t in valid_tables:
        cursor.execute(f"SELECT count(*) FROM {t}")
        stats[t] = cursor.fetchone()[0]
    conn.close()
    return stats


@app.get("/api/tables/{table_name}", summary="Browse rows of any simulation table")
def get_table_data(table_name: str, limit: int = 50):
    valid_tables = [
        "patients", "staff", "departments", "beds", "admissions",
        "discharges", "orders", "lab_results", "prescriptions",
        "bills", "insurance_claims", "tickets", "pending_approvals", "audit_log"
    ]
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table '{table_name}'. Valid: {valid_tables}")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict_from_row(r) for r in rows]


# Legacy endpoint silence handlers (prevents console error floods from old open browser tabs)
@app.get("/api/simulation/status")
def legacy_status():
    return {"status": "running", "simulation": "static_data_layer", "docs": "/docs"}

@app.websocket("/ws/{full_path:path}")
async def legacy_ws(websocket: WebSocket, full_path: str):
    await websocket.accept()
    await websocket.send_json({"event": "simulation_ready", "note": "Simulation is operating in static API mode."})
    await websocket.close()


# =========================================================================
# Root Endpoint: Interactive HTML Simulation Inspector or JSON status
# =========================================================================
@app.get("/", summary="Simulation Status & Interactive Inspector")
def root(request: Request):
    accept_header = request.headers.get("accept", "")
    
    # If request is from a browser, render an interactive HTML Simulation Inspector
    if "text/html" in accept_header:
        conn = get_db_connection()
        cursor = conn.cursor()
        counts = {}
        for tbl in ["patients", "staff", "departments", "beds", "admissions", "discharges",
                    "orders", "lab_results", "prescriptions", "bills", "insurance_claims",
                    "tickets", "pending_approvals", "audit_log"]:
            cursor.execute(f"SELECT count(*) FROM {tbl}")
            counts[tbl] = cursor.fetchone()[0]
        conn.close()

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospital Operations Simulation — Static Data Environment</title>
    <style>
        :root {{
            --bg: #090d16;
            --surface: #131b2e;
            --surface-hover: #1b2640;
            --border: #23314f;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #10b981;
            --accent-purple: #a855f7;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: var(--font);
            line-height: 1.5;
            padding: 24px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px 30px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-title h1 {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .header-title p {{ color: var(--text-muted); font-size: 14px; margin-top: 4px; }}
        .badge {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: var(--accent-blue);
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 9999px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .btn-group {{ display: flex; gap: 10px; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            text-decoration: none;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s ease;
        }}
        .btn-primary {{
            background: #2563eb;
            color: #ffffff;
        }}
        .btn-primary:hover {{ background: #1d4ed8; }}
        .btn-secondary {{
            background: var(--surface-hover);
            color: var(--text-main);
            border-color: var(--border);
        }}
        .btn-secondary:hover {{ background: #223050; border-color: #3b82f6; }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px 20px;
            cursor: pointer;
            transition: transform 0.15s, border-color 0.15s;
        }}
        .kpi-card:hover {{
            transform: translateY(-2px);
            border-color: var(--accent-blue);
        }}
        .kpi-label {{
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        .kpi-val {{
            font-size: 28px;
            font-weight: 800;
            margin-top: 4px;
            color: var(--text-main);
        }}
        .kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 2px; }}

        .main-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 700;
            color: var(--text-main);
        }}
        .tab-bar {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 14px;
        }}
        .tab-btn {{
            background: var(--surface-hover);
            color: var(--text-muted);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 14px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .tab-btn:hover {{
            color: var(--text-main);
            border-color: var(--accent-blue);
        }}
        .tab-btn.active {{
            background: #1e3a8a;
            color: #ffffff;
            border-color: #3b82f6;
        }}
        .table-responsive {{
            overflow-x: auto;
            border: 1px solid var(--border);
            border-radius: 8px;
            max-height: 520px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }}
        th {{
            background: #162038;
            color: #cbd5e1;
            padding: 12px 14px;
            font-weight: 600;
            position: sticky;
            top: 0;
            border-bottom: 2px solid var(--border);
            white-space: nowrap;
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            color: #e2e8f0;
            white-space: nowrap;
        }}
        tr:hover td {{
            background: var(--surface-hover);
        }}
        .json-cell {{
            font-family: monospace;
            font-size: 11px;
            color: #a5b4fc;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .status-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }}
        .status-active {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .status-pending {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .status-rejected {{ background: rgba(244, 63, 94, 0.2); color: #f87171; }}
        
        .api-tester {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media(max-width: 900px) {{ .api-tester {{ grid-template-columns: 1fr; }} }}
        .test-btn {{
            display: block;
            width: 100%;
            text-align: left;
            background: var(--surface-hover);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .test-btn:hover {{
            background: #202d4a;
            border-color: var(--accent-blue);
        }}
        .test-btn span {{
            font-weight: 700;
            color: var(--accent-blue);
            margin-right: 8px;
        }}
        .code-box {{
            background: #0b0f19;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            font-family: monospace;
            font-size: 12px;
            color: #38bdf8;
            max-height: 280px;
            overflow-y: auto;
            white-space: pre-wrap;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">
                <h1>🏥 Hospital Operations Simulation Engine</h1>
                <p>Pure Static Data Environment • SQLite 14 Tables • 12 RBAC REST Endpoints</p>
            </div>
            <div class="btn-group">
                <a href="/docs" target="_blank" class="btn btn-primary">📖 Open Swagger API Docs</a>
                <a href="/redoc" target="_blank" class="btn btn-secondary">📑 ReDoc</a>
            </div>
        </header>

        <!-- KPI Metrics Grid -->
        <div class="kpi-grid">
            <div class="kpi-card" onclick="loadTable('patients')">
                <div class="kpi-label">Patients</div>
                <div class="kpi-val" style="color: #38bdf8;">{counts['patients']}</div>
                <div class="kpi-sub">Tamil Cohort (UHID-001..15)</div>
            </div>
            <div class="kpi-card" onclick="loadTable('staff')">
                <div class="kpi-label">Staff</div>
                <div class="kpi-val" style="color: #10b981;">{counts['staff']}</div>
                <div class="kpi-sub">Roles + JSON RBAC</div>
            </div>
            <div class="kpi-card" onclick="loadTable('beds')">
                <div class="kpi-label">Beds</div>
                <div class="kpi-val" style="color: #a855f7;">{counts['beds']}</div>
                <div class="kpi-sub">GW (15) • ICU (5) • ER (10)</div>
            </div>
            <div class="kpi-card" onclick="loadTable('admissions')">
                <div class="kpi-label">Admissions</div>
                <div class="kpi-val" style="color: #f59e0b;">5 Active</div>
                <div class="kpi-sub">{counts['admissions']} Total in Database</div>
            </div>
            <div class="kpi-card" onclick="loadTable('insurance_claims')">
                <div class="kpi-label">Insurance Claims</div>
                <div class="kpi-val" style="color: #38bdf8;">{counts['insurance_claims']}</div>
                <div class="kpi-sub">1 Apprv, 1 Reject, 1 Pend</div>
            </div>
            <div class="kpi-card" onclick="loadTable('lab_results')">
                <div class="kpi-label">Lab Results</div>
                <div class="kpi-val" style="color: #f43f5e;">{counts['lab_results']}</div>
                <div class="kpi-sub">1 Critical Gap (Unalerted)</div>
            </div>
            <div class="kpi-card" onclick="loadTable('discharges')">
                <div class="kpi-label">Discharges</div>
                <div class="kpi-val" style="color: #10b981;">{counts['discharges']}</div>
                <div class="kpi-sub">1 Blocked (Billing=False)</div>
            </div>
            <div class="kpi-card" onclick="loadTable('tickets')">
                <div class="kpi-label">Open Tickets</div>
                <div class="kpi-val" style="color: #f59e0b;">{counts['tickets']}</div>
                <div class="kpi-sub">IT, Billing, Ins, Attender</div>
            </div>
            <div class="kpi-card" onclick="loadTable('pending_approvals')">
                <div class="kpi-label">Approvals</div>
                <div class="kpi-val" style="color: #a855f7;">{counts['pending_approvals']}</div>
                <div class="kpi-sub">All Pending</div>
            </div>
            <div class="kpi-card" onclick="loadTable('audit_log')">
                <div class="kpi-label">Audit Log</div>
                <div class="kpi-val" style="color: #94a3b8;">{counts['audit_log']}</div>
                <div class="kpi-sub">10 Seeded Traces</div>
            </div>
        </div>

        <!-- Interactive 14-Table Browser -->
        <div class="main-card">
            <div class="section-header">
                <div class="section-title">📊 Live SQLite Table Browser (14 Tables)</div>
                <div id="tableRecordCount" class="badge">Loading...</div>
            </div>
            <div class="tab-bar">
                <button class="tab-btn active" onclick="loadTable('patients', this)">Patients (15)</button>
                <button class="tab-btn" onclick="loadTable('staff', this)">Staff (12)</button>
                <button class="tab-btn" onclick="loadTable('beds', this)">Beds (30)</button>
                <button class="tab-btn" onclick="loadTable('admissions', this)">Admissions (7)</button>
                <button class="tab-btn" onclick="loadTable('discharges', this)">Discharges (2)</button>
                <button class="tab-btn" onclick="loadTable('orders', this)">Orders (5)</button>
                <button class="tab-btn" onclick="loadTable('lab_results', this)">Lab Results (6)</button>
                <button class="tab-btn" onclick="loadTable('prescriptions', this)">Prescriptions (5)</button>
                <button class="tab-btn" onclick="loadTable('bills', this)">Bills (5)</button>
                <button class="tab-btn" onclick="loadTable('insurance_claims', this)">Claims (3)</button>
                <button class="tab-btn" onclick="loadTable('tickets', this)">Tickets (4)</button>
                <button class="tab-btn" onclick="loadTable('pending_approvals', this)">Approvals (3)</button>
                <button class="tab-btn" onclick="loadTable('audit_log', this)">Audit Log (10)</button>
                <button class="tab-btn" onclick="loadTable('departments', this)">Departments ({counts['departments']})</button>
            </div>
            <div class="table-responsive">
                <table id="dataTable">
                    <thead id="tableHead"></thead>
                    <tbody id="tableBody"></tbody>
                </table>
            </div>
        </div>

        <!-- Live RBAC API Quick Tester -->
        <div class="main-card">
            <div class="section-header">
                <div class="section-title">🧪 Live RBAC API Tester (12 Endpoints)</div>
                <span class="badge">Header: X-Staff-ID Verification</span>
            </div>
            <div class="api-tester">
                <div>
                    <button class="test-btn" onclick="runApiTest('/patient/UHID-000001', 'STF-001')">
                        <span>GET</span> /patient/UHID-000001 (Doctor STF-001 → 200 OK)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/patient/UHID-000001', null)">
                        <span style="color: #f43f5e;">GET</span> /patient/UHID-000001 (No Header → 403 Forbidden)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/admissions?status=active', 'STF-001')">
                        <span>GET</span> /admissions?status=active (5 Active Admissions)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/beds/available?ward=ICU', 'STF-001')">
                        <span>GET</span> /beds/available?ward=ICU (3 Available ICU Beds)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/bill/UHID-000001', 'STF-006')">
                        <span>GET</span> /bill/UHID-000001 (Billing STF-006 → 200 OK)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/tickets?team=IT Support&status=open', 'STF-010')">
                        <span>GET</span> /tickets?team=IT Support&status=open (IT STF-010)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/pending_approvals?status=pending', 'STF-001')">
                        <span>GET</span> /pending_approvals?status=pending (3 Pending)
                    </button>
                    <button class="test-btn" onclick="runApiTest('/audit?limit=5', 'STF-008')">
                        <span>GET</span> /audit?limit=5 (MRD STF-008)
                    </button>
                </div>
                <div>
                    <div style="font-size: 13px; font-weight: 600; color: #94a3b8; margin-bottom: 8px;" id="testOutputHeader">Live API Response Output:</div>
                    <pre class="code-box" id="testOutput">Click any test button on the left to execute live against FastAPI endpoints.</pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function loadTable(tableName, btnElement) {{
            if (btnElement) {{
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btnElement.classList.add('active');
            }}
            document.getElementById('tableRecordCount').textContent = 'Loading ' + tableName + '...';
            try {{
                const res = await fetch('/api/tables/' + tableName);
                const data = await res.json();
                document.getElementById('tableRecordCount').textContent = data.length + ' rows in ' + tableName;
                
                const thead = document.getElementById('tableHead');
                const tbody = document.getElementById('tableBody');
                thead.innerHTML = '';
                tbody.innerHTML = '';

                if (data.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding: 20px;">No rows found</td></tr>';
                    return;
                }}

                const cols = Object.keys(data[0]);
                let headHtml = '<tr>';
                cols.forEach(c => headHtml += '<th>' + c + '</th>');
                headHtml += '</tr>';
                thead.innerHTML = headHtml;

                let bodyHtml = '';
                data.forEach(row => {{
                    bodyHtml += '<tr>';
                    cols.forEach(c => {{
                        let val = row[c];
                        if (typeof val === 'object' && val !== null) {{
                            bodyHtml += '<td class="json-cell">' + JSON.stringify(val) + '</td>';
                        }} else if (val === null || val === undefined) {{
                            bodyHtml += '<td style="color: #64748b;">NULL</td>';
                        }} else {{
                            bodyHtml += '<td>' + String(val) + '</td>';
                        }}
                    }});
                    bodyHtml += '</tr>';
                }});
                tbody.innerHTML = bodyHtml;
            }} catch (err) {{
                document.getElementById('tableRecordCount').textContent = 'Error loading table';
            }}
        }}

        async function runApiTest(endpoint, staffId) {{
            const out = document.getElementById('testOutput');
            const hdr = document.getElementById('testOutputHeader');
            hdr.textContent = 'Calling: ' + endpoint + ' (Header: ' + (staffId ? 'X-Staff-ID: ' + staffId : 'None') + ')';
            out.textContent = 'Loading...';

            const headers = {{}};
            if (staffId) headers['X-Staff-ID'] = staffId;

            try {{
                const res = await fetch(endpoint, {{ headers }});
                const body = await res.json();
                out.textContent = 'HTTP ' + res.status + ' ' + (res.ok ? 'OK' : 'Error') + '\\n\\n' + JSON.stringify(body, null, 2);
                out.style.borderColor = res.ok ? '#10b981' : '#f43f5e';
            }} catch (err) {{
                out.textContent = 'Network or parsing error: ' + err;
                out.style.borderColor = '#f43f5e';
            }}
        }}

        // Initial load
        window.addEventListener('DOMContentLoaded', () => {{
            loadTable('patients');
        }});
    </script>
</body>
</html>"""
        return HTMLResponse(content=html_content)

    return {
        "status": "active",
        "mode": "simulation_static_data_layer",
        "description": "Hospital Operations Simulation: SQLite Backend + FastAPI RBAC Layer",
        "endpoints_count": 12,
        "docs_url": "/docs"
    }
