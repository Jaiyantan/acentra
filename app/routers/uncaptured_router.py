"""
Layer 3: Uncaptured Clinical Intelligence API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
Directly addresses data gaps not captured in traditional HIS/EMR systems.
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/uncaptured-gaps", tags=["Layer 3: Uncaptured Clinical Intelligence"])

@router.get("/all", summary="Feed of all uncaptured clinical events & workflow gaps")
def get_all_uncaptured_gaps(
    category: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50
):
    """
    Returns uncaptured clinical intelligence events:
    - Order-Execution-Latency (Order placed vs Medication administered delay)
    - Clinical-Reasoning (Doctor verbal differential diagnosis)
    - Verbal-Handover (Shift handover nuances)
    - Near-Misses (LASA drug swaps, wristband mismatches caught before harm)
    - Paramedic-Verbal-Handover (Ambulance bay verbal remarks)
    - Critical-Alert-Ack (Time lag in telephone critical value notification)
    - Bedside-Transfusion (Blood unit issued vs actual bedside transfusion verification)
    """
    query = "SELECT * FROM uncaptured_gaps_log WHERE 1=1"
    params = []
    if category:
        query += " AND gap_category LIKE ?"
        params.append(f"%{category}%")
    if risk_level:
        query += " AND risk_level = ?"
        params.append(risk_level)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    gaps = execute_query(query, tuple(params))
    return {"total": len(gaps), "uncaptured_gaps": gaps}

@router.get("/order-execution-latency", summary="Latencies between doctor orders and nurse execution")
def get_order_execution_latencies(limit: int = 30):
    """
    Returns specific tracking of order-to-administration delays (e.g. order placed 10:00 AM, drug given 13:45 PM).
    """
    rows = execute_query(
        "SELECT * FROM uncaptured_gaps_log WHERE gap_category = 'Order-Execution-Latency' ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"latencies": rows}

@router.get("/near-misses", summary="Intercepted near-miss clinical incidents (The 90% unreported)")
def get_near_miss_incidents(limit: int = 30):
    """
    Returns high-value near-miss incidents captured before patient harm occurred.
    """
    rows = execute_query(
        "SELECT * FROM uncaptured_gaps_log WHERE gap_category = 'Near-Miss' ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"near_misses": rows}

@router.get("/clinical-reasoning", summary="Doctor clinical rationale and verbal thought process")
def get_clinical_reasoning_logs(limit: int = 30):
    """
    Returns documented doctor clinical reasoning and differential diagnostic thought processes.
    """
    rows = execute_query(
        "SELECT * FROM uncaptured_gaps_log WHERE gap_category = 'Clinical-Reasoning' ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"reasoning_logs": rows}
