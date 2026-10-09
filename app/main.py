"""
Main FastAPI Application for Saveetha Medical College and Hospital (SMCH) Operations Engine
Live, dynamic simulation across all 16 clinical, diagnostic, and administrative departments.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import HOSPITAL_METADATA, DEPARTMENTS
from app.database import init_db
from app.simulation.engine import sim_engine

# Import all departmental routers
from app.routers.emergency_router import router as emergency_router
from app.routers.opd_router import router as opd_router
from app.routers.ipd_router import router as ipd_router
from app.routers.icu_router import router as icu_router
from app.routers.ot_router import router as ot_router
from app.routers.laboratory_router import router as laboratory_router
from app.routers.radiology_router import router as radiology_router
from app.routers.pharmacy_router import router as pharmacy_router
from app.routers.blood_bank_router import router as blood_bank_router
from app.routers.dialysis_router import router as dialysis_router
from app.routers.specialty_router import router as specialty_router
from app.routers.billing_router import router as billing_router
from app.routers.nursing_router import router as nursing_router
from app.routers.mrd_router import router as mrd_router
from app.routers.biomedical_router import router as biomedical_router
from app.routers.uncaptured_router import router as uncaptured_router
from app.routers.simulation_router import router as simulation_router
from app.routers.stream_router import router as stream_router
from app.routers.workflow_router import router as workflow_router
from app.routers.knowledge_router import router as knowledge_router
from app.routers.security_router import router as security_router
from app.routers.patient_journey_router import router as patient_journey_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes SQLite schema and kicks off the 24/7 background hospital simulation."""
    init_db()
    await sim_engine.start()
    yield
    await sim_engine.stop()

app = FastAPI(
    title="Saveetha Medical College and Hospital (SMCH) Operations Engine",
    description="""
    ## Live Operational APIs & Data Streams for 1,600-Bed Tertiary Teaching Hospital
    
    This system provides **live, dynamically generating endpoints** across all 16 clinical,
    diagnostic, and administrative departments as outlined in the SMCH Operations Data Model:
    
    1. **Emergency & Trauma Care**: Live triage (P1/P2/P3), ambulance telemetry, time-to-doctor counters, dispositions
    2. **OPD (Outpatient)**: Registration master, queue tokens, doctor consultations, ICD-10 coding, prescriptions
    3. **IPD (Inpatient)**: 1,600-bed occupancy, admissions, daily SOAP progress notes, nursing charts, I/O balances
    4. **ICU & Critical Care**: Multi-bed continuous telemetry (HR, BP, SpO2, EtCO2, CVP), ventilator telemetry, titration logs, ABG reports
    5. **Operation Theatre Complex**: Master schedule, WHO surgical checklists, implant tracking with regulatory barcodes
    6. **Laboratory Information System (LIS)**: Analyzer machine feeds (Roche Cobas / Sysmex), phlebotomy tracking, mandatory Critical Value telephone alerts
    7. **Radiology & Imaging (RIS/PACS)**: Imaging worklist, DICOM acquisition metadata, CT radiation dosimetry, radiologist reports
    8. **Pharmacy & Cold Chain**: Inventory stock, automated reorders, DDI checks, cold-chain IoT temperature sensors, Schedule-X narcotic registers
    9. **Blood Centre (BBIS)**: Component inventory, donor serology testing, crossmatch requests, blood issues, storage temperature logs
    10. **Hemodialysis Unit**: 16 stations running live with dialysate parameters, ultrafiltration volume, transmembrane pressure
    11. **Specialty & Super-Specialty**: Cath lab coronary angiograms/PTCA, daycare chemotherapy infusion, Multidisciplinary Tumor Boards
    12. **Billing & PM-JAY Insurance**: Itemized billings, Ayushman Bharat PM-JAY claim adjudication via NHA portal, TPA approvals
    13. **Nursing Administration**: Ward shift rosters, nurse-to-patient ratios, SBAR shift handovers, NABH incident audits
    14. **Medical Records Department (MRD)**: Master Patient Index (MPI), physical file rack warehouse tracking, MLC registers
    15. **Biomedical Engineering & Admin**: Equipment asset registers, uptime %, preventive maintenance, breakdown tickets, staff council credentials
    16. **Layer 3: Uncaptured Intelligence**: Order-to-execution latency tracking, unwritten clinical reasoning, near-misses, verbal paramedic remarks
    17. **Workflow Automation & Agent Gating**: JSON workflow configs, missing-field detection, irreversible action gating, human approval queue
    18. **Knowledge Base & Second Brain**: Synthetic workbook, approved policy articles, source citations, uncertainty communication
    19. **Security & Governance**: Prompt injection filter, RBAC matrix across 8 roles, append-only security audit log, 5-team escalation router
    20. **Patient Journey Lifecycle**: 10-state standardized patient journey state tracking
    """,
    version="2.1.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All 22 Routers
app.include_router(emergency_router)
app.include_router(opd_router)
app.include_router(ipd_router)
app.include_router(icu_router)
app.include_router(ot_router)
app.include_router(laboratory_router)
app.include_router(radiology_router)
app.include_router(pharmacy_router)
app.include_router(blood_bank_router)
app.include_router(dialysis_router)
app.include_router(specialty_router)
app.include_router(billing_router)
app.include_router(nursing_router)
app.include_router(mrd_router)
app.include_router(biomedical_router)
app.include_router(uncaptured_router)
app.include_router(simulation_router)
app.include_router(stream_router)
app.include_router(workflow_router)
app.include_router(knowledge_router)
app.include_router(security_router)
app.include_router(patient_journey_router)

from app.routers.ontology_api import router as ontology_router
app.include_router(ontology_router)

from app.routers.agent_api import router as agent_router
app.include_router(agent_router)

from app.routers.dashboard_api import router as dashboard_router
app.include_router(dashboard_router)

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", summary="Hospital Command Center Web Dashboard")
async def serve_dashboard():
    """Serves the interactive Hospital Command Center dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Welcome to SMCH Operations Engine. Navigate to /docs for interactive Swagger API UI."}

@app.get("/api/departments", summary="Metadata directory of all 16 departments")
def get_departments_directory():
    """Returns the metadata of all 16 departments and capabilities of SMCH."""
    return {
        "hospital": HOSPITAL_METADATA,
        "departments_count": len(DEPARTMENTS),
        "departments": DEPARTMENTS
    }
