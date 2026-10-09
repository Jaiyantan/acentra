"""
Radiology & Imaging (RIS / PACS) API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/radiology", tags=["Radiology & Imaging (RIS/PACS)"])

@router.get("/orders", summary="Diagnostic imaging requisitions worklist")
def get_radiology_orders(modality: Optional[str] = None, limit: int = 50):
    """
    Returns imaging worklist across CT 128-slice, 3T MRI, Digital X-Ray, and Ultrasound.
    """
    query = "SELECT * FROM radiology_orders WHERE 1=1"
    params = []
    if modality:
        query += " AND modality = ?"
        params.append(modality)
    query += " ORDER BY order_time DESC LIMIT ?"
    params.append(limit)
    orders = execute_query(query, tuple(params))
    return {"total": len(orders), "orders": orders}

@router.get("/acquisitions", summary="PACS DICOM acquisition metadata & radiation dosimetry")
def get_radiology_acquisitions(limit: int = 50):
    """
    Returns image acquisition details including machine identifier, technologist ID,
    DICOM study UID, and regulatory radiation dose logs (CTDIvol mGy, DLP mGy*cm).
    """
    acquisitions = execute_query(
        "SELECT * FROM radiology_acquisitions ORDER BY acquisition_time DESC LIMIT ?",
        (limit,)
    )
    return {"acquisitions": acquisitions}

@router.get("/reports", summary="Radiologist structured reports and impressions")
def get_radiology_reports(uhid: Optional[str] = None, limit: int = 50):
    """
    Returns consultant radiologist findings, diagnostic impressions,
    critical abnormality flags, and turnaround time analytics.
    """
    query = "SELECT * FROM radiology_reports WHERE 1=1"
    params = []
    if uhid:
        query += " AND uhid = ?"
        params.append(uhid)
    query += " ORDER BY reported_time DESC LIMIT ?"
    params.append(limit)
    reports = execute_query(query, tuple(params))
    return {"reports": reports}
