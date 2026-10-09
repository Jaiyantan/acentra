"""
db/seed.py
Synthetic seed data generator for Hospital Operations Simulation.
Populates SQLite database according to the exact specification:
- 15 patients with Tamil names (UHID-000001 through UHID-000015)
- 12 staff members covering all operational roles with JSON permissions
- 4 departments (Emergency, IPD, OPD, Billing)
- 30 beds across 3 wards (General Ward: 15, ICU: 5, Emergency: 10)
- 5 active admissions in varying states
- 3 insurance claims (one approved, one rejected with reason, one pending)
- 4 open tickets (one IT issue, one billing query, one insurance query, one patient complaint)
- 6 lab results (two normal, two abnormal, one critical unalerted gap, one verified)
- 2 discharges (one with all clearances true, one with billing=false blocker)
- 3 pending approvals (all status pending)
- 10 audit log entries
- Supporting orders, prescriptions, and bills for active admissions
"""

import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
_SCHEMA_CANDIDATES = [
    ROOT_DIR / "data" / "schema.sql",
    ROOT_DIR / "db" / "schema.sql",
]
SCHEMA_PATH = next((p for p in _SCHEMA_CANDIDATES if p.exists()), _SCHEMA_CANDIDATES[0])
DB_PATHS = [
    ROOT_DIR / "data" / "hospital.db",
    ROOT_DIR / "db" / "hospital.db",
]

def get_connection(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: Path):
    if db_path.exists():
        db_path.unlink()
    
    conn = get_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

def seed_data(db_path: Path):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Patients (15 patients with Tamil names, UHID-000001 to UHID-000015)
    patients = [
        ("UHID-000001", "Senthil Kumar", 54, "Male", "+91-9840112341", "12, Bharathiyar St, Mylapore, Chennai", "2026-10-01 08:30:00", "admitted"),
        ("UHID-000002", "Meenakshi Sundaram", 62, "Female", "+91-9840223452", "45, Gandhi Road, T Nagar, Chennai", "2026-10-02 09:15:00", "admitted"),
        ("UHID-000003", "Karthik Raja", 38, "Male", "+91-9840334563", "8, Anna Nagar West, Madurai", "2026-10-03 10:45:00", "admitted"),
        ("UHID-000004", "Anitha Selvam", 29, "Female", "+91-9840445674", "77, Kamarajar Salai, Tiruchirappalli", "2026-10-04 11:20:00", "admitted"),
        ("UHID-000005", "Muthuvel Pandian", 47, "Male", "+91-9840556785", "3/19, Netaji Road, Salem", "2026-10-05 14:00:00", "admitted"),
        ("UHID-000006", "Revathi Natarajan", 41, "Female", "+91-9840667896", "56, Periyar St, Erode", "2026-09-25 15:10:00", "discharged"),
        ("UHID-000007", "Subramanian Ramasamy", 68, "Male", "+91-9840778907", "102, VOC Nagar, Tirunelveli", "2026-09-27 16:30:00", "discharged"),
        ("UHID-000008", "Kavitha Murugan", 34, "Female", "+91-9840889018", "21, South Car St, Chidambaram", "2026-10-06 09:00:00", "registered"),
        ("UHID-000009", "Vigneshwaran Palani", 25, "Male", "+91-9840990129", "88, West Mada St, Thanjavur", "2026-10-06 10:15:00", "registered"),
        ("UHID-000010", "Priya Dharshini", 31, "Female", "+91-9841001230", "14, Raja St, Kanchipuram", "2026-10-06 11:45:00", "registered"),
        ("UHID-000011", "Dinesh Chandran", 45, "Male", "+91-9841112341", "67, Cross Cut Road, Coimbatore", "2026-10-07 08:20:00", "registered"),
        ("UHID-000012", "Lakshmi Narayanan", 73, "Male", "+91-9841223452", "9, Big Bazaar St, Dindigul", "2026-10-07 09:50:00", "registered"),
        ("UHID-000013", "Saravanan Velu", 52, "Male", "+91-9841334563", "34, College Road, Vellore", "2026-10-07 13:10:00", "registered"),
        ("UHID-000014", "Bhuvaneshwari Kannan", 39, "Female", "+91-9841445674", "112, Trunk Road, Poonamallee, Chennai", "2026-10-08 07:30:00", "registered"),
        ("UHID-000015", "Thirunavukkarasu Pillai", 60, "Male", "+91-9841556785", "5, Temple View, Kumbakonam", "2026-10-08 08:15:00", "registered")
    ]
    cursor.executemany("""
        INSERT INTO patients (uhid, name, age, gender, contact, address, registration_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, patients)

    # 2. Staff (12 staff members mapped to DEPT-026 through DEPT-033)
    staff = [
        ("STF-001", "Dr. K. Anbarasan", "DEPT-027", "doctor",
         json.dumps(["patient:read", "admission:read", "beds:read", "approvals:read"]), 1),
        ("STF-002", "Deepa Ramanathan", "DEPT-027", "nurse",
         json.dumps(["patient:read", "admission:read", "beds:read"]), 1),
        ("STF-003", "G. Sridhar", "DEPT-026", "front_office",
         json.dumps(["patient:read", "beds:read"]), 1),
        ("STF-004", "R. Malathi", "DEPT-027", "admission",
         json.dumps(["patient:read", "admission:read", "beds:read", "insurance:read"]), 1),
        ("STF-005", "V. Vijayakumar", "DEPT-027", "discharge",
         json.dumps(["patient:read", "admission:read", "billing:read"]), 1),
        ("STF-006", "A. Shankaran", "DEPT-028", "billing",
         json.dumps(["patient:read", "billing:read", "insurance:read"]), 1),
        ("STF-007", "N. Jayashree", "DEPT-029", "insurance_tpa",
         json.dumps(["patient:read", "insurance:read", "billing:read"]), 1),
        ("STF-008", "T. Elango", "DEPT-030", "medical_records",
         json.dumps(["patient:read", "admission:read", "audit:read"]), 1),
        ("STF-009", "M. Radhika", "DEPT-032", "quality",
         json.dumps(["patient:read", "admission:read", "audit:read", "tickets:read"]), 1),
        ("STF-010", "K. Ramesh", "DEPT-033", "it_support",
         json.dumps(["tickets:read", "audit:read"]), 1),
        ("STF-011", "P. Soundarrajan", "DEPT-032", "operations_manager",
         json.dumps(["*"]), 1),
        ("STF-012", "C. Banumathi", "DEPT-031", "case_management",
         json.dumps(["patient:read", "admission:read", "insurance:read", "tickets:read"]), 1)
    ]
    cursor.executemany("""
        INSERT INTO staff (staff_id, name, department, role, permissions, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, staff)

    # 3. Departments (All 37 departments: Clinical, Clinical Support, Administrative)
    departments = [
        # Clinical Departments (DEPT-001 to DEPT-020)
        ("DEPT-001", "Emergency Department", "clinical", "Block A, Ground Floor", None),
        ("DEPT-002", "Outpatient Department (OPD)", "clinical", "Block A, 1st Floor", None),
        ("DEPT-003", "Inpatient Department (IPD)", "clinical", "Block B, 2nd-4th Floors", None),
        ("DEPT-004", "Intensive Care Unit (ICU)", "clinical", "Block B, 3rd Floor", None),
        ("DEPT-005", "Operation Theatre", "clinical", "Block B, 2nd Floor", None),
        ("DEPT-006", "Cardiology", "clinical", "Block C, 1st Floor", None),
        ("DEPT-007", "Neurology", "clinical", "Block C, 2nd Floor", None),
        ("DEPT-008", "Oncology", "clinical", "Block D, 1st Floor", None),
        ("DEPT-009", "Nephrology and Dialysis", "clinical", "Block C, 3rd Floor", None),
        ("DEPT-010", "Gastroenterology", "clinical", "Block C, 4th Floor", None),
        ("DEPT-011", "Pulmonology", "clinical", "Block B, 1st Floor", None),
        ("DEPT-012", "Orthopaedics", "clinical", "Block A, 2nd Floor", None),
        ("DEPT-013", "Obstetrics and Gynaecology", "clinical", "Block D, 2nd Floor", None),
        ("DEPT-014", "Paediatrics", "clinical", "Block D, 3rd Floor", None),
        ("DEPT-015", "Psychiatry", "clinical", "Block A, 4th Floor", None),
        ("DEPT-016", "Dermatology", "clinical", "Block A, 3rd Floor", None),
        ("DEPT-017", "Ophthalmology", "clinical", "Block A, 2nd Floor", None),
        ("DEPT-018", "ENT", "clinical", "Block A, 3rd Floor", None),
        ("DEPT-019", "Urology", "clinical", "Block C, 3rd Floor", None),
        ("DEPT-020", "General Surgery", "clinical", "Block B, 2nd Floor", None),

        # Clinical Support Departments (DEPT-021 to DEPT-025)
        ("DEPT-021", "Laboratory", "clinical_support", "Block B, Ground Floor", None),
        ("DEPT-022", "Radiology and Imaging", "clinical_support", "Block A, Ground Floor", None),
        ("DEPT-023", "Pharmacy", "clinical_support", "Block A, Ground Floor", None),
        ("DEPT-024", "Blood Bank", "clinical_support", "Block B, 1st Floor", None),
        ("DEPT-025", "Physiotherapy and Rehabilitation", "clinical_support", "Block D, Ground Floor", None),

        # Administrative and Operations Departments (DEPT-026 to DEPT-037)
        ("DEPT-026", "Front Office and Registration", "administrative", "Block A, Main Lobby", None),
        ("DEPT-027", "Admission and Discharge", "administrative", "Block A, Ground Floor", None),
        ("DEPT-028", "Billing", "administrative", "Block C, Ground Floor", None),
        ("DEPT-029", "Insurance and TPA", "administrative", "Block C, Ground Floor", None),
        ("DEPT-030", "Medical Records (MRD / HIM)", "administrative", "Block B, Basement 1", None),
        ("DEPT-031", "Case Management", "administrative", "Block B, 1st Floor", None),
        ("DEPT-032", "Quality and Patient Safety", "administrative", "Block A, 4th Floor", None),
        ("DEPT-033", "IT and HIS Support", "administrative", "Block C, Basement 1", None),
        ("DEPT-034", "Human Resources and Administration", "administrative", "Block A, 5th Floor", None),
        ("DEPT-035", "Facility Management", "administrative", "Service Block, Ground Floor", None),
        ("DEPT-036", "Biomedical Engineering", "administrative", "Service Block, 1st Floor", None),
        ("DEPT-037", "Nursing Administration", "administrative", "Block B, 1st Floor", None)
    ]
    cursor.executemany("""
        INSERT INTO departments (dept_id, name, type, location, head_staff_id)
        VALUES (?, ?, ?, ?, ?)
    """, departments)

    # 4. Beds (30 beds across 3 wards: General Ward: 15, ICU: 5, Emergency: 10)
    beds = []
    # General Ward: 15 beds (BED-GW-01 to BED-GW-15)
    for i in range(1, 16):
        bed_id = f"BED-GW-{i:02d}"
        status = "available"
        current_uhid = None
        if bed_id == "BED-GW-01":
            status = "occupied"
            current_uhid = "UHID-000003"
        elif bed_id == "BED-GW-02":
            status = "occupied"
            current_uhid = "UHID-000004"
        beds.append((bed_id, "General Ward", status, current_uhid))

    # ICU: 5 beds (BED-ICU-01 to BED-ICU-05)
    for i in range(1, 6):
        bed_id = f"BED-ICU-{i:02d}"
        status = "available"
        current_uhid = None
        if bed_id == "BED-ICU-01":
            status = "occupied"
            current_uhid = "UHID-000001"
        elif bed_id == "BED-ICU-02":
            status = "occupied"
            current_uhid = "UHID-000002"
        beds.append((bed_id, "ICU", status, current_uhid))

    # Emergency: 10 beds (BED-ER-01 to BED-ER-10)
    for i in range(1, 11):
        bed_id = f"BED-ER-{i:02d}"
        status = "available"
        current_uhid = None
        if bed_id == "BED-ER-01":
            status = "occupied"
            current_uhid = "UHID-000005"
        beds.append((bed_id, "Emergency", status, current_uhid))

    cursor.executemany("""
        INSERT INTO beds (bed_id, ward, status, current_patient_uhid)
        VALUES (?, ?, ?, ?)
    """, beds)

    # 5. Admissions (5 active admissions + 2 past discharged admissions for discharges table)
    admissions = [
        ("ADM-001", "UHID-000001", "2026-10-01 10:00:00", "STF-001", "Severe Acute Respiratory Distress", "ICU", "BED-ICU-01", "active", "POL-STAR-7821", "approved"),
        ("ADM-002", "UHID-000002", "2026-10-02 11:30:00", "STF-001", "Acute Decompensated Heart Failure", "ICU", "BED-ICU-02", "active", "POL-REL-3912", "pending"),
        ("ADM-003", "UHID-000003", "2026-10-03 14:15:00", "STF-001", "Dengue Fever with Thrombocytopenia", "General Ward", "BED-GW-01", "active", None, "not_required"),
        ("ADM-004", "UHID-000004", "2026-10-04 16:00:00", "STF-001", "Uncontrolled Type 2 Diabetes with Foot Ulcer", "General Ward", "BED-GW-02", "active", "POL-MAX-9011", "rejected"),
        ("ADM-005", "UHID-000005", "2026-10-05 18:45:00", "STF-001", "Polytrauma post Road Traffic Accident", "Emergency", "BED-ER-01", "active", "POL-HDFC-4412", "pending"),
        ("ADM-006", "UHID-000006", "2026-09-25 16:00:00", "STF-001", "Acute Gastroenteritis with Moderate Dehydration", "General Ward", "BED-GW-03", "discharged", "POL-STAR-6611", "approved"),
        ("ADM-007", "UHID-000007", "2026-09-27 17:30:00", "STF-001", "Acute Appendicitis - Post Laparoscopic Surgery", "General Ward", "BED-GW-04", "discharged", "POL-NIC-5522", "approved")
    ]
    cursor.executemany("""
        INSERT INTO admissions (admission_id, uhid, admission_date, admitting_doctor_id, admitting_diagnosis, ward, bed_id, status, insurance_policy_number, insurance_preauth_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, admissions)

    # 6. Discharges (2 discharges: one with all clearances true, one with billing=false blocker)
    discharges = [
        ("DIS-001", "ADM-006", "2026-09-29 11:30:00", "regular", "Acute Gastroenteritis resolved",
         "2026-10-06", "STF-001",
         json.dumps(["Tab Ciprofloxacin 500mg BD x 3d", "Tab Pantoprazole 40mg OD x 5d", "ORS sachet prn"]),
         json.dumps({"billing": True, "pharmacy": True, "nursing": True, "mrd": True})),
        ("DIS-002", "ADM-007", "2026-10-01 14:00:00", "regular", "Post-op Laparoscopic Appendectomy recovery",
         "2026-10-08", "STF-001",
         json.dumps(["Tab Augmentin 625mg BD x 5d", "Tab Paracetamol 650mg TDS x 3d"]),
         json.dumps({"billing": False, "pharmacy": True, "nursing": True, "mrd": True}))
    ]
    cursor.executemany("""
        INSERT INTO discharges (discharge_id, admission_id, discharge_date, discharge_type, final_diagnosis, follow_up_date, follow_up_doctor_id, discharge_medications, clearance_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, discharges)

    # 7. Orders
    orders = [
        ("ORD-001", "UHID-000001", "ADM-001", "lab", json.dumps({"panel": "Electrolytes", "urgency": "STAT"}), "STF-001", "2026-10-08 10:15:00", "2026-10-08 11:00:00", "completed"),
        ("ORD-002", "UHID-000002", "ADM-002", "lab", json.dumps({"panel": "CBC", "urgency": "Routine"}), "STF-001", "2026-10-08 09:30:00", "2026-10-08 10:30:00", "completed"),
        ("ORD-003", "UHID-000003", "ADM-003", "lab", json.dumps({"test": "Hemoglobin", "urgency": "Routine"}), "STF-001", "2026-10-08 08:00:00", "2026-10-08 09:00:00", "completed"),
        ("ORD-004", "UHID-000004", "ADM-004", "medication", json.dumps({"drug": "Inj Human Actrapid", "units": "8 IU"}), "STF-001", "2026-10-08 08:30:00", "2026-10-08 09:00:00", "completed"),
        ("ORD-005", "UHID-000005", "ADM-005", "radiology", json.dumps({"scan": "CT Brain plain", "protocol": "Trauma"}), "STF-001", "2026-10-08 11:00:00", None, "in_progress")
    ]
    cursor.executemany("""
        INSERT INTO orders (order_id, uhid, admission_id, order_type, order_details, ordered_by_staff_id, ordered_at, executed_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders)

    # 8. Lab Results (6 lab results: 2 normal, 2 abnormal, 1 critical gap unalerted, 1 verified)
    lab_results = [
        ("RES-001", "UHID-000003", "Hemoglobin", 14.2, "g/dL", "13.0 - 17.0", None, 0, 0, "verified", "2026-10-08 09:00:00"),
        ("RES-002", "UHID-000004", "Serum Creatinine", 0.9, "mg/dL", "0.7 - 1.3", None, 0, 0, "verified", "2026-10-08 09:15:00"),
        ("RES-003", "UHID-000005", "Random Blood Glucose", 245.0, "mg/dL", "70.0 - 140.0", "H", 0, 0, "verified", "2026-10-08 10:00:00"),
        ("RES-004", "UHID-000002", "Platelet Count", 85000.0, "/uL", "150000 - 450000", "L", 0, 0, "resulted", "2026-10-08 10:30:00"),
        ("RES-005", "UHID-000001", "Serum Potassium", 6.8, "mmol/L", "3.5 - 5.1", "HH", 1, 0, "verified", "2026-10-08 11:00:00"),
        ("RES-006", "UHID-000002", "WBC Total Count", 16500.0, "/uL", "4000 - 11000", "H", 0, 0, "resulted", "2026-10-08 11:20:00")
    ]
    cursor.executemany("""
        INSERT INTO lab_results (result_id, uhid, test_name, value, unit, reference_range, abnormal_flag, critical_value_flag, critical_value_alerted, result_status, resulted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, lab_results)

    # 9. Prescriptions
    prescriptions = [
        ("RX-001", "UHID-000001", "Inj Furosemide", "40mg", "OD", "IV", "3 days", "STF-001", "2026-10-01 10:30:00", "dispensed"),
        ("RX-002", "UHID-000002", "Tab Enalapril", "5mg", "BD", "Oral", "7 days", "STF-001", "2026-10-02 12:00:00", "dispensed"),
        ("RX-003", "UHID-000003", "Tab Paracetamol", "650mg", "TDS", "Oral", "5 days", "STF-001", "2026-10-03 15:00:00", "dispensed"),
        ("RX-004", "UHID-000004", "Inj Insulin Glargine", "14 IU", "HS", "Subcutaneous", "10 days", "STF-001", "2026-10-04 16:30:00", "dispensed"),
        ("RX-005", "UHID-000005", "Inj Tramadol", "50mg", "SOS", "IV", "2 days", "STF-001", "2026-10-05 19:00:00", "dispensed")
    ]
    cursor.executemany("""
        INSERT INTO prescriptions (rx_id, uhid, drug_name, dose, frequency, route, duration, prescribed_by, prescribed_at, dispensing_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, prescriptions)

    # 10. Bills
    bills = [
        ("BIL-001", "UHID-000001", "ADM-001", "2026-10-08 10:00:00", 145000.0, 0.0, 145000.0, 0.0, "final",
         json.dumps([{"item": "ICU Bed Charges (7 days)", "amount": 70000.0}, {"item": "Ventilator Support", "amount": 35000.0}, {"item": "Pharmacy & Infusions", "amount": 40000.0}])),
        ("BIL-002", "UHID-000002", "ADM-002", "2026-10-08 10:30:00", 82000.0, 20000.0, 0.0, 62000.0, "draft",
         json.dumps([{"item": "ICU Charges (6 days)", "amount": 60000.0}, {"item": "Cardiology Consultations", "amount": 12000.0}, {"item": "Lab Investigations", "amount": 10000.0}])),
        ("BIL-003", "UHID-000003", "ADM-003", "2026-10-08 11:00:00", 28500.0, 28500.0, 0.0, 0.0, "paid",
         json.dumps([{"item": "General Ward (5 days)", "amount": 12500.0}, {"item": "IV Fluids & Meds", "amount": 9000.0}, {"item": "Lab Tests", "amount": 7000.0}])),
        ("BIL-004", "UHID-000004", "ADM-004", "2026-10-08 11:15:00", 42000.0, 10000.0, 0.0, 32000.0, "partially_paid",
         json.dumps([{"item": "General Ward (4 days)", "amount": 10000.0}, {"item": "Diabetic Wound Dressing & Debridement", "amount": 22000.0}, {"item": "Pharmacy", "amount": 10000.0}])),
        ("BIL-005", "UHID-000007", "ADM-007", "2026-10-01 13:00:00", 68000.0, 0.0, 68000.0, 0.0, "disputed",
         json.dumps([{"item": "Laparoscopic Appendectomy Package", "amount": 55000.0}, {"item": "Extra Pharmacy Consumables", "amount": 13000.0}]))
    ]
    cursor.executemany("""
        INSERT INTO bills (bill_id, uhid, admission_id, bill_date, total_amount, paid_amount, insurance_covered_amount, patient_payable, status, items)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, bills)

    # 11. Insurance Claims (3 claims: one approved, one rejected with a reason, one pending)
    insurance_claims = [
        ("CLM-001", "UHID-000001", "ADM-001", "Star Health & Allied Insurance", "POL-STAR-7821", "Medi Assist TPA", "2026-10-01 11:00:00", "2026-10-01 15:30:00", 150000.0, "approved", None, 0),
        ("CLM-002", "UHID-000004", "ADM-004", "Max Bupa Health Insurance", "POL-MAX-9011", "Vidal Health TPA", "2026-10-04 17:00:00", None, None, "rejected", "Pre-existing diabetes complications excluded under Section 4.2 of policy terms; 24-month waiting period not satisfied.", 0),
        ("CLM-003", "UHID-000002", "ADM-002", "Reliance General Insurance", "POL-REL-3912", "Paramount TPA", "2026-10-02 13:00:00", None, None, "submitted", None, 0)
    ]
    cursor.executemany("""
        INSERT INTO insurance_claims (claim_id, uhid, admission_id, insurer_name, policy_number, tpa_name, preauth_requested_at, preauth_approved_at, preauth_amount, claim_status, rejection_reason, pmjay_flag)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insurance_claims)

    # 12. Tickets (4 open tickets: one IT issue, one billing query, one insurance query, one patient complaint)
    tickets = [
        ("TCK-001", "STF-002", "it_issue", "high", "open", "IT Support",
         "EMR workstation terminal in ICU Bed 02 freezing intermittently during vital entry.", "2026-10-08 08:30:00", None),
        ("TCK-002", "STF-005", "billing_query", "urgent", "open", "Billing",
         "Discharge clearance blocked for UHID-000007 due to pending pharmacy consumable reconciliation of Rs 13,000.", "2026-10-08 09:15:00", None),
        ("TCK-003", "STF-004", "insurance_query", "normal", "open", "Insurance TPA",
         "Pre-auth query response pending for UHID-000002 from Paramount TPA regarding ICU justification letter.", "2026-10-08 10:00:00", None),
        ("TCK-004", "STF-003", "patient_complaint", "normal", "open", "Operations Management",
         "Attender of UHID-000003 complained of delay in dietary breakfast delivery in General Ward Bed 01.", "2026-10-08 10:45:00", None)
    ]
    cursor.executemany("""
        INSERT INTO tickets (ticket_id, raised_by_staff_id, ticket_type, priority, status, assigned_to_team, description, created_at, resolved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tickets)

    # 13. Pending Approvals (3 pending approvals: all status pending)
    pending_approvals = [
        ("APP-001", "STF-001", "create_admission",
         json.dumps({"uhid": "UHID-000008", "ward": "ICU", "admitting_diagnosis": "Acute Coronary Syndrome", "bed_id": "BED-ICU-03"}),
         "pending", "2026-10-08 11:30:00", None, None),
        ("APP-002", "STF-005", "discharge_patient",
         json.dumps({"uhid": "UHID-000007", "admission_id": "ADM-007", "discharge_type": "regular", "billing_override": True, "reason": "Patient settled bill via bank guarantee"}),
         "pending", "2026-10-08 12:00:00", None, None),
        ("APP-003", "STF-007", "approve_claim",
         json.dumps({"claim_id": "CLM-003", "uhid": "UHID-000002", "requested_amount": 95000.0, "tpa_approval_number": "PA-788912"}),
         "pending", "2026-10-08 12:15:00", None, None)
    ]
    cursor.executemany("""
        INSERT INTO pending_approvals (approval_id, requested_by_staff_id, action_type, action_payload, status, requested_at, actioned_at, actioned_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, pending_approvals)

    # 14. Audit Log (10 audit log entries)
    audit_logs = [
        ("LOG-001", "2026-10-08 08:35:00", "SES-9001", "STF-002", "QUERY", "patients", "UHID-000002", "Searched patient record by UHID", "Patient record returned", json.dumps(["HIS_PATIENT_INDEX"]), 1.0, 0, 0, None),
        ("LOG-002", "2026-10-08 08:40:00", "SES-9002", "STF-001", "WORKFLOW_STEP", "admissions", "ADM-002", "Initiated ICU admission clinical review", "Clinical review completed", json.dumps(["SOP-ADM-001"]), 1.0, 0, 0, None),
        ("LOG-003", "2026-10-08 09:10:00", "SES-9003", "STF-006", "TOOL_CALL", "bills", "BIL-002", "Generated interim bill calculation", "Interim bill summary created", json.dumps(["BILLING_FEE_SCHEDULE_2026"]), 1.0, 0, 0, None),
        ("LOG-004", "2026-10-08 09:45:00", "SES-9004", "STF-007", "QUERY", "insurance_claims", "CLM-002", "Checked pre-auth denial reason", "Denial clause 4.2 retrieved", json.dumps(["TPA_DENIAL_LETTER_MAX"]), 1.0, 0, 0, None),
        ("LOG-005", "2026-10-08 10:15:00", "SES-9005", "STF-005", "ESCALATION", "discharges", "DIS-002", "Escalated discharge blocker: billing clearance false", "Ticket TCK-002 dispatched to Billing Desk", json.dumps(["SOP-DIS-002"]), 0.95, 1, 0, None),
        ("LOG-006", "2026-10-08 10:50:00", "SES-9006", "STF-003", "QUERY", "beds", "BED-GW-01", "Checked bed status for General Ward", "Bed availability list retrieved", json.dumps(["BED_ALLOCATION_GRID"]), 1.0, 0, 0, None),
        ("LOG-007", "2026-10-08 11:05:00", "SES-9007", "STF-001", "TOOL_CALL", "lab_results", "RES-005", "Critical potassium value (6.8 mmol/L) flagged in LIS", "Critical flag set, SMS alert pending execution", json.dumps(["LAB_CRITICAL_PANEL_SOP"]), 0.98, 1, 0, None),
        ("LOG-008", "2026-10-08 11:35:00", "SES-9008", "STF-001", "APPROVAL", "pending_approvals", "APP-001", "Submitted emergency admission request for UHID-000008", "Approval record created", json.dumps(["EMG_TRIAGE_POLICY"]), 1.0, 0, 1, 0),
        ("LOG-009", "2026-10-08 12:05:00", "SES-9009", "STF-005", "APPROVAL", "pending_approvals", "APP-002", "Submitted billing waiver request for UHID-000007 discharge", "Approval record created", json.dumps(["DISCHARGE_CLEARANCE_POLICY"]), 1.0, 0, 1, 0),
        ("LOG-010", "2026-10-08 12:20:00", "SES-9010", "STF-007", "APPROVAL", "pending_approvals", "APP-003", "Submitted TPA approval authorization for CLM-003", "Approval record created", json.dumps(["INSURANCE_TPA_POLICY"]), 1.0, 0, 1, 0)
    ]
    cursor.executemany("""
        INSERT INTO audit_log (log_id, timestamp, session_id, staff_id, action, entity_type, entity_id, input_summary, output_summary, documents_cited, confidence_score, escalated, irreversible_action, human_approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, audit_logs)

    conn.commit()
    conn.close()

def main():
    for db_path in DB_PATHS:
        print(f"Initializing database at: {db_path}")
        init_db(db_path)
        seed_data(db_path)
        print(f"Database seeded successfully at {db_path} with exactly the specified synthetic dataset.")

if __name__ == "__main__":
    main()
