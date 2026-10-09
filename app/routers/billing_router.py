"""
Billing, TPA & PM-JAY Insurance API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.database import execute_query, execute_insert
from app.simulation.events_bus import event_bus

router = APIRouter(prefix="/api/billing", tags=["Billing & PM-JAY Insurance"])

@router.get("/invoices", summary="Itemized patient billing invoices")
def get_billing_invoices(payer_type: Optional[str] = None, limit: int = 50):
    """
    Returns itemized billing invoices broken down by Bed Charges, Pharmacy, Diagnostics,
    and Doctor/Surgical fees.
    """
    query = "SELECT * FROM billing_invoices WHERE 1=1"
    params = []
    if payer_type:
        query += " AND payer_type LIKE ?"
        params.append(f"%{payer_type}%")
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    invoices = execute_query(query, tuple(params))
    return {"total": len(invoices), "invoices": invoices}

@router.get("/claims", summary="Insurance & PM-JAY (Ayushman Bharat) claim status")
def get_insurance_claims(scheme: Optional[str] = None, status: Optional[str] = None, limit: int = 50):
    """
    Returns PM-JAY and Private TPA claim submissions, TMS pre-authorization codes,
    approved sums, and denial reasons.
    """
    query = "SELECT * FROM insurance_claims WHERE 1=1"
    params = []
    if scheme:
        query += " AND scheme LIKE ?"
        params.append(f"%{scheme}%")
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    claims = execute_query(query, tuple(params))
    return {"total": len(claims), "claims": claims}

@router.get("/revenue-summary", summary="Daily collection and revenue cycle KPIs")
def get_revenue_summary():
    """
    Calculates total billed revenue, PM-JAY settled claims, and payer distribution.
    """
    rev_by_payer = execute_query(
        "SELECT payer_type, COUNT(*) as invoice_count, SUM(net_amount_inr) as total_inr FROM billing_invoices GROUP BY payer_type;"
    )
    total_rev = sum(r["total_inr"] for r in rev_by_payer if r["total_inr"])
    return {
        "total_revenue_inr": round(total_rev, 2),
        "payer_breakdown": rev_by_payer
    }
