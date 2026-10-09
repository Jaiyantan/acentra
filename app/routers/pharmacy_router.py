"""
Central Pharmacy & Cold Chain API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/pharmacy", tags=["Central Pharmacy & Inventory"])

@router.get("/inventory", summary="Live pharmacy stock levels, reorder triggers, and expiry")
def get_pharmacy_inventory(category: Optional[str] = None):
    """
    Returns live inventory across Oral, Injectable, Critical Care, Cold-Chain, and Schedule-X narcotics.
    Tracks batch numbers, expiry dates, and unit costs.
    """
    query = "SELECT * FROM pharmacy_inventory WHERE 1=1"
    params = []
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    query += " ORDER BY current_stock ASC"
    items = execute_query(query, tuple(params))
    return {"total_items": len(items), "inventory": items}

@router.get("/dispensing", summary="Medication dispensing logs & DDI validation")
def get_pharmacy_dispensing(limit: int = 50):
    """
    Returns logs of dispensed medications, verified batch numbers,
    pharmacist sign-offs, and Drug-Drug Interaction (DDI) alert statuses.
    """
    rows = execute_query(
        "SELECT * FROM pharmacy_dispensing ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"total": len(rows), "dispensing_logs": rows}

@router.get("/cold-chain", summary="Continuous refrigerator temperature sensor telemetry")
def get_cold_chain_telemetry():
    """
    Returns live IoT temperature and humidity telemetry for vaccine and biological storage fridges
    (Mandated 2°C to 8°C compliance monitoring).
    """
    logs = execute_query("SELECT * FROM pharmacy_cold_chain ORDER BY timestamp DESC LIMIT 20;")
    return {"cold_chain_status": logs}

@router.get("/narcotics", summary="Schedule X / Narcotic controlled drug register")
def get_narcotic_register(limit: int = 50):
    """
    Returns legally mandated paper/digital register for Schedule X narcotics (Morphine, Fentanyl),
    including prescribing doctor, witness nurse, and remaining ampoule balance.
    """
    rows = execute_query(
        "SELECT * FROM pharmacy_narcotics ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    return {"total": len(rows), "narcotic_register": rows}
