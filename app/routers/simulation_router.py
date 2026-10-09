"""
Simulation Engine Control & Scenario Injection API Router
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

from fastapi import APIRouter, Query, Body, HTTPException
from typing import Optional, List, Dict, Any
from app.simulation.engine import sim_engine

router = APIRouter(prefix="/api/simulation", tags=["Simulation Controls & Scenarios"])

@router.get("/status", summary="Simulation engine operational status & hospital time")
def get_simulation_status():
    """
    Returns current status of the SMCH live simulation engine:
    - Running state
    - Virtual hospital time
    - Current acceleration speed factor (1x, 5x, 10x)
    - Total ticks and events generated
    """
    return {
        "status": "running" if sim_engine.is_running else "stopped",
        "hospital_time": sim_engine.hospital_time.isoformat(),
        "speed_factor": sim_engine.speed_factor,
        "total_ticks": sim_engine.total_ticks,
        "kpis": sim_engine.stats
    }

@router.post("/speed", summary="Adjust simulation speed factor (0.5x to 30x)")
def set_simulation_speed(factor: float = Query(..., ge=0.2, le=30.0, description="Speed multiplier, e.g. 1.0, 5.0, 10.0")):
    """
    Accelerate or slow down the simulated hospital day rhythm.
    """
    sim_engine.set_speed(factor)
    return {"status": "success", "new_speed_factor": sim_engine.speed_factor}

@router.post("/trigger-scenario", summary="Inject specific emergency clinical scenarios on demand")
async def trigger_clinical_scenario(
    scenario: str = Query(..., description="Scenario: code_blue, mass_casualty, critical_lab_troponin, cold_chain_breach, near_miss_intercept")
):
    """
    Manually inject live clinical events to test system responses:
    - `code_blue`: Cardiac arrest in MICU-02
    - `mass_casualty`: 6 victims highway bus collision arriving in 108 ambulances
    - `critical_lab_troponin`: Urgent 4.82 ng/mL Troponin I panic alert
    - `cold_chain_breach`: Vaccine Refrigerator temp spike to 11.4°C
    - `near_miss_intercept`: Heparin 25,000U vs 5,000U LASA drug interception
    """
    result = await sim_engine.trigger_scenario(scenario)
    return result

@router.get("/kpis", summary="High-level operational metrics across all 16 departments")
def get_hospital_kpis():
    """
    Returns high-level executive dashboard metrics.
    """
    return {
        "hospital_name": "Saveetha Medical College and Hospital",
        "stats": sim_engine.stats
    }
