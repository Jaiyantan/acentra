"""
Configuration settings for Saveetha Medical College and Hospital (SMCH)
Operations & Simulation Engine
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Resilient database path resolution (data/ -> db/ -> root)
_CANDIDATE_PATHS = [
    BASE_DIR / "data" / "smch_hospital.db",
    BASE_DIR / "db" / "smch_hospital.db",
    BASE_DIR / "smch_hospital.db",
]
DB_PATH = str(next((p for p in _CANDIDATE_PATHS if p.exists()), _CANDIDATE_PATHS[0]))

HOSPITAL_METADATA = {
    "name": "Saveetha Medical College and Hospital (SMCH)",
    "code": "SMCH-TN",
    "location": "Thandalam, Chennai, Tamil Nadu, India",
    "total_beds": 1600,
    "icu_beds": 120,
    "ot_rooms": 14,
    "dialysis_stations": 18,
    "opd_rooms": 45,
    "accreditation": ["NABH 5th Edition", "NABL Accredited Central Labs", "PM-JAY Empanelled (Ayushman Bharat)", "CMCHIS Empanelled"],
    "tier": "Tertiary Care Teaching Hospital",
    "capabilities": ["Robotic Surgery (DaVinci Xi)", "ECMO", "Level 1 Trauma Care", "Cath Lab", "3T MRI", "128-Slice CT", "Comprehensive Cancer Center", "Renal Transplant"]
}

DEPARTMENTS = [
    {"id": "emergency", "name": "Emergency & Trauma Care", "code": "ED", "category": "Acute Care"},
    {"id": "opd", "name": "Outpatient Department", "code": "OPD", "category": "Ambulatory"},
    {"id": "ipd", "name": "Inpatient Department", "code": "IPD", "category": "Inpatient"},
    {"id": "icu", "name": "Intensive Care & Critical Care", "code": "ICU", "category": "Critical Care"},
    {"id": "ot", "name": "Operation Theatre Complex", "code": "OT", "category": "Surgical"},
    {"id": "laboratory", "name": "Central Diagnostic Laboratory (LIS)", "code": "LIS", "category": "Diagnostics"},
    {"id": "radiology", "name": "Radiology & Imaging (RIS/PACS)", "code": "RIS", "category": "Diagnostics"},
    {"id": "pharmacy", "name": "Central Pharmacy & Inventory", "code": "PHARM", "category": "Therapeutics"},
    {"id": "blood_bank", "name": "Blood Centre & Transfusion Medicine", "code": "BBIS", "category": "Therapeutics"},
    {"id": "dialysis", "name": "Hemodialysis & Nephrology Unit", "code": "DIAL", "category": "Specialized Care"},
    {"id": "specialty_clinics", "name": "Specialty & Super-Specialty Clinics", "code": "SPEC", "category": "Specialized Care"},
    {"id": "billing", "name": "Billing, TPA & PM-JAY Insurance", "code": "BILL", "category": "Revenue Cycle"},
    {"id": "nursing_admin", "name": "Nursing Administration & Quality", "code": "NURSE", "category": "Clinical Operations"},
    {"id": "mrd", "name": "Medical Records Department (MRD)", "code": "MRD", "category": "Health Information"},
    {"id": "biomedical", "name": "Biomedical Engineering & Administration", "code": "BME", "category": "Support & Infrastructure"},
    {"id": "uncaptured_gaps", "name": "Layer 3: Uncaptured Clinical Intelligence", "code": "GAP3", "category": "Intelligence Layer"}
]

# Simulation runtime configuration
DEFAULT_SIMULATION_SPEED = 1.0  # 1.0 = real-time, 5.0 = 5x speed
EVENT_BUFFER_SIZE = 1000
