"""
Laboratory Information System (LIS) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/laboratory", tags=["Laboratory Information System (LIS)"])

@router.get("/orders", summary="Diagnostic lab test requisitions")
def get_lab_orders(status: Optional[str] = None, urgency: Optional[str] = None, limit: int = 50):
    """
    Returns diagnostic test orders across Pathology, Biochemistry, Hematology, and Microbiology.
    """
    query = "SELECT * FROM lab_orders WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if urgency:
        query += " AND urgency = ?"
        params.append(urgency)
    query += " ORDER BY order_time DESC LIMIT ?"
    params.append(limit)
    orders = execute_query(query, tuple(params))
    return {"total": len(orders), "orders": orders}

@router.get("/samples", summary="Phlebotomy collection & specimen transport tracking")
def get_lab_samples(limit: int = 50):
    """
    Returns specimen collection barcodes, vacutainer tube types (EDTA, SST, Citrate),
    phlebotomist IDs, and courier transit latency minutes.
    """
    samples = execute_query(
        "SELECT * FROM lab_samples ORDER BY collection_time DESC LIMIT ?",
        (limit,)
    )
    return {"samples": samples}

@router.get("/analyzer-raw", summary="Automated analyzer numeric results & flags")
def get_lab_analyzer_results(flag: Optional[str] = None, limit: int = 50):
    """
    Returns automated machine outputs from Roche Cobas 8000 and Sysmex XN-1000
    with reference ranges and abnormality flags (NORMAL, HIGH, LOW, PANIC_CRITICAL).
    """
    query = "SELECT * FROM lab_results WHERE 1=1"
    params = []
    if flag:
        query += " AND flag = ?"
        params.append(flag)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    results = execute_query(query, tuple(params))
    return {"total": len(results), "results": results}

@router.get("/critical-alerts", summary="Mandatory NABH Critical Panic Value call alerts")
def get_lab_critical_alerts(ack_status: Optional[str] = None):
    """
    Returns high-severity clinical panic values requiring mandatory telephone notification
    to the treating clinician with phone log and acknowledgment timestamps.
    """
    query = "SELECT * FROM lab_critical_alerts WHERE 1=1"
    params = []
    if ack_status:
        query += " AND ack_status = ?"
        params.append(ack_status)
    query += " ORDER BY alert_time DESC LIMIT 50"
    alerts = execute_query(query, tuple(params))
    return {"total_alerts": len(alerts), "critical_alerts": alerts}

@router.post("/critical-alerts/{alert_id}/acknowledge", summary="Doctor phone acknowledgment of critical alert")
async def acknowledge_critical_alert(alert_id: str):
    """
    Acknowledge receipt of a telephone critical lab value.
    """
    execute_insert(
        "UPDATE lab_critical_alerts SET ack_status = 'Acknowledged', ack_time = CURRENT_TIMESTAMP WHERE alert_id = ?;",
        (alert_id,)
    )
    await event_bus.publish_event(
        department="Laboratory (LIS)",
        event_type="Critical Value Alert Acknowledged",
        severity="SUCCESS",
        summary=f"Critical alert #{alert_id} acknowledged by treating consultant via telephone log."
    )
    return {"status": "success", "alert_id": alert_id, "ack_status": "Acknowledged"}
