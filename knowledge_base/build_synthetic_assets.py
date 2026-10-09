"""
Saveetha Medical College and Hospital (SMCH)
Synthetic Operations Master Assets Builder

Generates:
1. knowledge_base/Operations_Synthetic_Workbook.xlsx
   Consolidated 5-sheet master workbook matching the hackathon problem statement:
   - Sheet 1: Operations Requests
   - Sheet 2: Approved Knowledge Articles
   - Sheet 3: Workflow Information
   - Sheet 4: Routing Rules
   - Sheet 5: Field Definitions
2. knowledge_base/workflow_definitions.json
   Machine-readable workflow state machines with step sequences, input fields,
   validation rules, blockers, escalations, and human-in-the-loop checkpoints.
3. Companion JSON indexes in knowledge_base/index/ for Supermemory ingestion.
"""

import sys
import json
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
KB_DIR = BASE_DIR
INDEX_DIR = BASE_DIR / "index"
INDEX_DIR.mkdir(exist_ok=True)

HOSPITAL_NAME = "Saveetha Medical College and Hospital (SMCH)"

# Excel styling constants
NAVY_HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
ROW_FONT = Font(name="Arial", size=9)
ALT_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
BORDER_THIN = Border(
    left=Side(style='thin', color='CBD5E1'),
    right=Side(style='thin', color='CBD5E1'),
    top=Side(style='thin', color='CBD5E1'),
    bottom=Side(style='thin', color='CBD5E1')
)

def format_styled_sheet(ws, title, columns, data, col_widths=None):
    ws.views.sheetView[0].showGridLines = True
    
    # Title Row
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
    title_cell = ws.cell(row=1, column=1, value=f"{HOSPITAL_NAME}  |  {title}")
    title_cell.font = Font(name="Arial", size=12, bold=True, color="1E3A8A")
    title_cell.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 28

    # Subtitle Row
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(columns))
    sub_cell = ws.cell(row=2, column=1, value="Official Synthetic Operations Environment  •  For Autonomous Workflow Automation & Grounded RAG")
    sub_cell.font = Font(name="Arial", size=8, italic=True, color="64748B")
    sub_cell.alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[2].height = 18

    # Table Header Row (Row 3)
    ws.row_dimensions[3].height = 24
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        cell.fill = NAVY_HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER_THIN

    # Data Rows (Row 4 onwards)
    for row_idx, row_values in enumerate(data, 4):
        ws.row_dimensions[row_idx].height = 20
        is_even = (row_idx % 2 == 0)
        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = ROW_FONT
            cell.border = BORDER_THIN
            if is_even:
                cell.fill = ALT_FILL
            
            # Alignments
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif str(val).startswith("REQ-") or str(val).startswith("KA-") or str(val).startswith("WF-") or str(val).startswith("R-") or str(val).startswith("TEAM-"):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Column Widths
    for col_idx, col_name in enumerate(columns, 1):
        col_letter = get_column_letter(col_idx)
        if col_widths and col_idx <= len(col_widths):
            ws.column_dimensions[col_letter].width = col_widths[col_idx - 1]
        else:
            max_len = max([len(str(ws.cell(r, col_idx).value or '')) for r in range(3, len(data) + 4)] or [len(col_name)])
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 50)


# =========================================================================
# DATA DEFINITIONS
# =========================================================================

# Sheet 1: Operations Requests Data
OPERATIONS_REQUESTS_COLS = [
    "Request ID", "Title", "Submitted By Role", "Department", "Category", 
    "Expected Intent", "Sample User Query", "Required Fields", 
    "Validation Rules", "Expected Outcome / Next Step", "Escalation Rule ID", "Assigned Team"
]

OPERATIONS_REQUESTS_DATA = [
    [
        "REQ-001", "Admit Emergency Patient to ICU", "doctor", "Emergency Department", "workflow_request",
        "create_admission", "Please admit patient UHID-000008 into the ICU under Dr. Anbarasan for acute respiratory distress.",
        "uhid, department_id, admitting_doctor_id, bed_id", "UHID exists; target bed status is vacant; admitting doctor on duty",
        "Call POST /api/admissions; change bed status to occupied; issue bed booking slip", "R-010", "Admission and Discharge"
    ],
    [
        "REQ-002", "Check Vacant Bed Availability in ICU", "nurse", "Intensive Care Unit", "workflow_request",
        "check_beds", "Are there any available beds in the ICU right now?",
        "ward / department_id", "Department exists; query returns current occupancy matrix",
        "Query GET /api/beds?ward=ICU; return list of vacant beds and total bed count", "R-010", "Admission and Discharge"
    ],
    [
        "REQ-003", "Submit Cashless Pre-Authorization Request", "admission", "Insurance and TPA", "workflow_request",
        "submit_preauth", "How do I submit an insurance pre-auth request for Star Health policy POL-STAR-7821?",
        "uhid, insurer_name, tpa_name, insurance_policy_number, estimate_amount", "Active policy; estimate breakdown itemized; clinical pre-auth form attached",
        "Generate pre-auth submission in TPA portal; initiate 48h SLA tracking", "R-004", "Insurance and TPA"
    ],
    [
        "REQ-004", "Inquire About Insurance Claim Rejection Status", "case_management", "Insurance and TPA", "workflow_request",
        "check_insurance", "Can you check the claim status and rejection reason for patient UHID-000004?",
        "uhid / claim_id", "Claim ID exists in insurance claims table",
        "Query GET /api/insurance/claims; display rejection clause; guide dispute appeal", "R-004", "Insurance and TPA"
    ],
    [
        "REQ-005", "Generate Four-Point Discharge Clearance", "discharge", "Admission and Discharge", "workflow_request",
        "discharge_clearance", "Is patient UHID-000007 cleared for discharge across billing, pharmacy, and nursing?",
        "uhid / admission_id", "Patient status is admitted; all 4 department clearance flags evaluated",
        "Evaluate clearance flags; if billing=false block gate pass and trigger R-008", "R-008", "Billing"
    ],
    [
        "REQ-006", "Order STAT Serum Electrolytes Panel", "doctor", "Laboratory", "workflow_request",
        "order_lab", "Please order a STAT Serum Electrolytes panel for patient UHID-000001 in ICU.",
        "uhid, admission_id, test_name, priority, ordering_doctor_id", "Valid UHID; patient currently admitted; test available in SMCH LIS test menu",
        "Call POST /api/orders; generate barcoded phlebotomy collection slip with STAT priority", "None", "Lab Operations"
    ],
    [
        "REQ-007", "Report Ward Patient Fall Incident", "nurse", "Quality and Patient Safety", "workflow_request",
        "report_incident", "I need to file an incident report for an elderly patient fall in General Ward Bed 03.",
        "uhid, incident_type, severity, location, reporter_staff_id, immediate_action_taken", "Incident type in approved taxonomy; reporter staff verified; immediate vitals recorded",
        "Call POST /api/tickets; dispatch notification to Nursing Superintendent and Quality Manager", "R-013", "Quality and Patient Safety"
    ],
    [
        "REQ-008", "Retrieve Historical Case File from MRD", "doctor", "Medical Records (MRD / HIM)", "knowledge_query",
        "mrd_request", "How do I request a physical archived patient case file from Medical Records?",
        "uhid, requesting_doctor_id, purpose, file_urgency", "UHID exists; requester is credentialed consultant; authorized clinical purpose",
        "Provide SOP-MRD-001 guidance; generate electronic case file requisition slip", "None", "Medical Records"
    ],
    [
        "REQ-009", "Report Frozen EMR Terminal in ICU", "nurse", "IT and HIS Support", "escalation",
        "it_support_ticket", "The EMR workstation terminal at ICU Bed 02 is frozen and not accepting entries. Raise a ticket.",
        "terminal_id, ward, issue_description, priority", "Workstation ID matches active network inventory; terminal reboot attempted",
        "Call POST /api/tickets; dispatch on-call IT hardware engineer within 15 mins", "R-011", "IT and HIS Support"
    ],
    [
        "REQ-010", "Review Current Inpatient Bill Summary", "billing", "Billing", "report_request",
        "check_bill", "What is the latest bill summary and patient payable balance for UHID-000001?",
        "uhid / admission_id", "Patient currently admitted or discharged within 30 days",
        "Query GET /api/bills/{admission_id}; return itemized bed, pharmacy, lab, and co-pay summary", "None", "Billing"
    ],
    [
        "REQ-011", "Transfer Deteriorating Patient from Ward to ICU", "doctor", "Inpatient Department", "workflow_request",
        "transfer_patient", "Transfer patient UHID-000003 from General Ward Bed 01 to an available ICU bed immediately.",
        "uhid, admission_id, current_bed_id, target_bed_id, transfer_reason", "Target ICU bed vacant; treating consultant authorization signed",
        "Update bed status in HIS; initiate dual-nurse SBAR transfer handover protocol", "R-010", "Admission and Discharge"
    ],
    [
        "REQ-012", "Requisition Emergency Packed Red Blood Cells", "doctor", "Blood Bank", "workflow_request",
        "request_blood", "Request 2 units of Packed Red Blood Cells STAT from the Blood Bank for trauma patient UHID-000005.",
        "uhid, blood_group, units_required, urgency, treating_doctor_id", "Patient crossmatch blood sample accessioned; urgency specified",
        "Submit BBIS blood requisition; trigger urgent crossmatch or issue uncrossmatched O-Neg", "None", "Blood Bank"
    ],
    [
        "REQ-013", "Check Unnotified Critical Lab Result Alert", "quality", "Laboratory Operations", "escalation",
        "critical_lab_alert", "Show me any critical lab results that have not yet been alerted to the treating physician.",
        "filter_criteria: critical_value_flag=true, doctor_alerted=false", "System query across all lab results within past 24 hours",
        "Query GET /api/lab-results; flag panic values (e.g. Potassium 6.8); trigger immediate escalation", "R-009", "Clinical Review"
    ],
    [
        "REQ-014", "Find Inpatient Admission Standard Operating Procedure", "front_office", "Admission and Discharge", "knowledge_query",
        "find_sop", "Where can I find the SOP for patient admission and what are the required documents?",
        "query_keywords: patient admission, required documents", "Text search across approved SOP documents",
        "Retrieve SOP-ADM-001; cite Section 3 (Required Documents); return link to Admission Form", "None", "Admission and Discharge"
    ],
    [
        "REQ-015", "Query How to Allocate Bed in HIS", "admission", "Admission and Discharge", "knowledge_query",
        "his_guidance", "Explain how to allocate a bed in the HIS system.",
        "system_module: HIS Bed Allocation", "Query matches approved knowledge article",
        "Retrieve KA-002; display 5-step HIS allocation sequence and error recovery instructions", "None", "Admission and Discharge"
    ],
    [
        "REQ-016", "Resolve Patient Attender Billing Dispute", "discharge", "Billing", "escalation",
        "billing_dispute", "The attender of patient UHID-000007 is disputing the final bill. What is the escalation process?",
        "uhid, admission_id, disputed_item, disputed_amount, attender_name", "Bill generated; grievance recorded by discharge desk",
        "Trigger R-006; route to Billing Manager ext. 1028; pause discharge gate pass release", "R-006", "Billing"
    ],
    [
        "REQ-017", "Verify PMJAY Ayushman Bharat Claim Protocol", "billing", "Insurance and TPA", "knowledge_query",
        "pmjay_procedure", "How do we submit a PMJAY claim through the NHA portal at discharge?",
        "scheme: PMJAY, claim_stage: discharge submission", "Valid PMJAY empanelled package code",
        "Retrieve KA-010; guide NHA TMS portal upload, biometric signoff, and discharge summary sync", "None", "Insurance and TPA"
    ],
    [
        "REQ-018", "Check Mandatory Documents Needed for Patient Discharge", "nurse", "Admission and Discharge", "knowledge_query",
        "discharge_documents", "What documents are required to complete a patient discharge according to SOP-DIS-001?",
        "document_type: discharge checklist", "Valid query against SOP-DIS-001",
        "Provide list: Discharge Summary, 4-Point Checklist, Pharmacy NOC, Settled Bill, Gate Pass", "None", "Admission and Discharge"
    ],
    [
        "REQ-019", "Identify Responsible Team for TPA Denial Dispute", "admission", "Insurance and TPA", "knowledge_query",
        "team_contact", "Who do I contact when an insurance pre-authorization claim is rejected by the TPA?",
        "issue_category: cashless insurance rejection", "Query matches internal support directory",
        "Return Insurance & TPA Team (TEAM-002, ext. 1029, tpa@smch.in, Queue: QUEUE_INSURANCE)", "R-004", "Insurance and TPA"
    ],
    [
        "REQ-020", "Clinical Escalation for Patient Refusing Life-Saving Treatment", "nurse", "Clinical Review", "escalation",
        "clinical_review_escalation", "A severe respiratory distress patient in the ICU is refusing treatment and demanding immediate discharge. What should we do?",
        "uhid, admission_id, clinical_condition, refusal_reason", "Patient medically unstable; competent adult refusal vs emergency doctrine",
        "Trigger R-001 & R-012; immediately page Treating Consultant & CMO; prepare DAMA/LAMA form", "R-001", "Clinical Review"
    ]
]

# Sheet 2: Approved Knowledge Articles Data
KNOWLEDGE_ARTICLES_COLS = [
    "Article ID", "Article Title", "Host System", "Department", "Version", 
    "Approved Date", "Applicable Roles", "Overview / Scope", 
    "Key Procedures / Steps", "Common Errors & Workarounds", "Contact Extension"
]

KNOWLEDGE_ARTICLES_DATA = [
    [
        "KA-001", "How to Register a New Patient in the HIS", "HIS", "Front Office and Registration", "1.4",
        "2026-01-15", "front_office, admission",
        "Standard sequence for generating a Unique Hospital Identification (UHID) and demographic profile at OPD counter.",
        "1. Open HIS Registration module; 2. Enter Aadhaar/ID and demographic details; 3. Enter contact and emergency numbers; 4. Take digital photo; 5. Print UHID barcode card.",
        "Error: 'Duplicate Aadhaar Found' -> Search existing UHID and merge records; Error: 'Terminal Offline' -> Switch to local buffer mode.",
        "ext. 1026"
    ],
    [
        "KA-002", "How to Allocate a Bed to an Admitted Patient", "HIS", "Admission and Discharge", "2.0",
        "2026-01-18", "admission, nurse",
        "Procedure for assigning vacant ward or ICU beds to registered admissions in the HIS Bed Management module.",
        "1. Open HIS Bed Management; 2. Filter by ward and bed type; 3. Select vacant bed (green); 4. Enter UHID and admission ID; 5. Confirm bed lock and print admission face sheet.",
        "Error: 'Bed Already Reserved' -> Refresh bed grid; Error: 'Ward Capacity Full' -> Escalate to Operations Manager for buffer bed override.",
        "ext. 1027"
    ],
    [
        "KA-003", "How to Submit a Lab Order in the LIS", "LIS", "Laboratory Operations", "1.8",
        "2026-01-20", "doctor, nurse, lab_tech",
        "Electronic test requisition workflow for routine and STAT biochemistry, hematology, and microbiology investigations.",
        "1. Open LIS Order Entry; 2. Select patient UHID; 3. Choose test panels from catalogue; 4. Set priority (Routine/STAT); 5. Enter clinical diagnosis; 6. Generate collection barcode.",
        "Error: 'Invalid Sample Tube Type' -> Check lab catalogue color code; Error: 'STAT Flag Disabled' -> Verify clinical urgency flag.",
        "ext. 1021"
    ],
    [
        "KA-004", "How to Submit a Radiology Request", "RIS", "Radiology Operations", "1.7",
        "2026-01-22", "doctor, rad_tech",
        "Digital ordering protocol for X-Ray, Ultrasound, CT, and MRI scans in the Radiology Information System.",
        "1. Open RIS Request module; 2. Enter UHID and clinical history; 3. Select anatomical modality; 4. Check contrast contraindications; 5. Book scanner appointment slot.",
        "Error: 'Creatinine Value Missing for Contrast' -> Order STAT Serum Creatinine prior to CT/MRI; Error: 'Pregnancy Status Unchecked' -> Mandatory screening required.",
        "ext. 1022"
    ],
    [
        "KA-005", "How to Generate a Final Bill at Discharge", "Billing System", "Billing", "2.3",
        "2026-01-25", "billing, discharge",
        "Complete protocol for reconciling pharmacy, room rent, procedure fees, and generating final itemized inpatient invoices.",
        "1. Open Billing Module; 2. Retrieve patient admission ID; 3. Perform unbilled consumables reconciliation; 4. Apply approved insurance deduction; 5. Collect patient co-pay; 6. Print final bill receipt.",
        "Error: 'Pharmacy Unclosed Return Credit' -> Call pharmacy to finalize medication return ledger; Error: 'Tariff Mismatch' -> Verify insurance tariff schedule.",
        "ext. 1028"
    ],
    [
        "KA-006", "How to Submit a Pre-Authorisation Request to TPA", "TPA Portal", "Insurance and TPA", "3.0",
        "2026-01-28", "insurance_tpa, billing",
        "Submission protocol for cashless health insurance pre-authorizations via web portal and NHA gateway.",
        "1. Open TPA Gateway; 2. Upload signed Pre-Auth Form; 3. Attach treating doctor's estimate and diagnostic reports; 4. Enter proposed package ICD-10 code; 5. Submit packet and track SLA.",
        "Error: 'Document Attachment Exceeds 10MB' -> Compress PDF files; Error: 'Policy Expired' -> Request updated physical policy copy from attender.",
        "ext. 1029"
    ],
    [
        "KA-007", "How to Fill and Submit an Incident Report", "Quality Portal", "Quality and Patient Safety", "2.2",
        "2026-02-01", "all_staff",
        "Hospital-wide adverse event, medication error, needle-stick, and near-miss documentation protocol.",
        "1. Log in to Quality Portal; 2. Select incident category (Fall, Medication, Equipment, Security); 3. Enter date, time, location, UHID; 4. Describe event objectively; 5. Submit to Quality Head.",
        "Error: 'Mandatory Immediate Action Blank' -> Enter first-aid measures taken; Note: Incident reports are protected quality documents and must never be saved in medical chart.",
        "ext. 1032"
    ],
    [
        "KA-008", "How to Request a Physical Patient Case File from Medical Records", "MRD Archive", "Medical Records (MRD / HIM)", "1.5",
        "2026-02-04", "doctor, medical_records",
        "Requisition protocol for retrieving archived physical inpatient charts for readmissions, audits, or legal inquiries.",
        "1. Open MRD Requisition module; 2. Enter patient UHID; 3. Select clinical purpose (Readmission, Clinical Audit, Legal); 4. Enter doctor ID; 5. Submit request slip.",
        "Error: 'File Marked Sealed / MLC' -> Requires written approval from Medical Superintendent; Standard turnaround time is 2 hours for routine, 15 mins for emergency.",
        "ext. 1030"
    ],
    [
        "KA-009", "How to Raise an IT Support Ticket for HIS or System Issues", "ITSM Helpdesk", "IT and HIS Support", "2.5",
        "2026-02-07", "all_staff",
        "Ticketing procedure for software crashes, network outages, printer malfunctions, and hardware breakdowns.",
        "1. Open Helpdesk Portal; 2. Choose category (HIS Software, Hardware, Network, Printer); 3. Select department and workstation tag; 4. Attach screenshot of error; 5. Submit ticket.",
        "Error: 'System Down' -> Call emergency IT helpline ext. 1033; Critical ICU terminals receive priority 1 dispatch within 15 minutes.",
        "ext. 1033"
    ],
    [
        "KA-010", "How to Submit a PMJAY Claim Through the NHA Portal", "NHA Portal", "Insurance and TPA", "3.1",
        "2026-02-10", "insurance_tpa, billing",
        "Standard operating procedure for processing Ayushman Bharat PMJAY and CMCHIS government health scheme claims.",
        "1. Open NHA Transaction Management System; 2. Verify beneficiary Aadhaar eKYC; 3. Select package surgical/medical code; 4. Upload pre-auth documents; 5. Sync discharge summary at exit.",
        "Error: 'Biometric Auth Failed' -> Use OTP verification or Iris scan; Error: 'Package Balance Exhausted' -> Request family floater enhancement.",
        "ext. 1029"
    ],
    [
        "KA-011", "How to Document Daily Progress Notes in the EMR", "EMR System", "Clinical Services", "2.1",
        "2026-02-12", "doctor",
        "Clinical documentation guideline for daily inpatient rounds, SOAP format notes, and treatment plan changes.",
        "1. Open EMR Patient Chart; 2. Select Progress Notes tab; 3. Enter Subjective, Objective, Assessment, and Plan; 4. Update provisional diagnosis; 5. Digitally sign note.",
        "Error: 'Unsaved Draft Lost' -> EMR autosaves every 60 seconds in local storage; Notes cannot be altered after digital sign-off (addendum required).",
        "ext. 1012"
    ],
    [
        "KA-012", "How to Record Inpatient Vitals and Fluid Balance in HIS", "HIS Nursing", "Nursing Administration", "1.9",
        "2026-02-14", "nurse",
        "Nursing workflow for recording blood pressure, pulse, SpO2, respiratory rate, temperature, and fluid intake/output.",
        "1. Open Nursing Station Vitals module; 2. Scan patient wristband barcode; 3. Enter vital signs; 4. Input intake (IV/Oral) and output (Urine/Drain); 5. Save and check MEWS score.",
        "Error: 'Abnormal Vitals Warning' -> System triggers automated alert to ward resident doctor if Modified Early Warning Score (MEWS) >= 4.",
        "ext. 1025"
    ],
    [
        "KA-013", "How to Process and Dispense Digital Inpatient Prescriptions", "Pharmacy System", "Pharmacy", "2.4",
        "2026-02-16", "pharmacist, nurse",
        "Inpatient pharmacy dispensing protocol from physician e-prescription to ward delivery cart.",
        "1. Open Pharmacy Dispense Queue; 2. Review active prescription orders; 3. Check drug allergies and interactions; 4. Pick medications from shelf; 5. Scan medication barcode; 6. Dispense to ward box.",
        "Error: 'Drug Out of Stock' -> Initiate therapeutic substitution protocol or emergency local purchase; High-alert medications require dual sign-off.",
        "ext. 1023"
    ],
    [
        "KA-014", "How to Reserve Crossmatched Blood Units in BBIS", "Blood Bank System", "Blood Bank", "2.0",
        "2026-02-18", "lab_tech, nurse",
        "Protocol for crossmatching and holding packed red blood cells, fresh frozen plasma, or platelets for OT and ICU.",
        "1. Open BBIS Blood Reservation; 2. Verify patient blood group test record; 3. Enter units required; 4. Perform major/minor crossmatch; 5. Tag reserve unit with patient UHID.",
        "Error: 'Unit Expired' -> BBIS automatically removes units expiring within 24h; Blood units reserved for surgery are held for maximum 24 hours.",
        "ext. 1024"
    ],
    [
        "KA-015", "How to Book an Operating Theatre Suite Slot", "OT Scheduling", "Operation Theatre", "1.6",
        "2026-02-20", "doctor, nurse",
        "Procedure for booking elective and emergency surgical slots across 12 SMCH operation theatre suites.",
        "1. Open OT Scheduling module; 2. Select theatre suite; 3. Choose date and time slot; 4. Enter surgery name and surgeon team; 5. Verify pre-op PAC clearance; 6. Confirm slot.",
        "Error: 'PAC Clearance Missing' -> Cannot confirm booking without Anaesthesia pre-op clearance; Emergency cases override elective slots via OT Superintendent.",
        "ext. 1015"
    ],
    [
        "KA-016", "How to Log Dialysis Ultrafiltration and Dialysate Flow", "Dialysis System", "Nephrology and Dialysis", "2.2",
        "2026-02-22", "dialysis_tech, doctor",
        "Monitoring protocol for logging pre-dialysis weight, ultrafiltration rate, heparinization, and post-dialysis parameters.",
        "1. Open Dialysis Flow Sheet; 2. Enter pre-weight and target UF goal; 3. Record hourly vitals and venous pressure; 4. Log heparin dose; 5. Record post-weight and Kt/V score.",
        "Error: 'Hypotension During Run' -> Reduce UF rate and infuse normal saline bolus; notify nephrologist immediately.",
        "ext. 1018"
    ],
    [
        "KA-017", "How to Requisition Therapeutic Diets in Pantry Portal", "Dietary Portal", "Facility Management", "1.5",
        "2026-02-24", "nurse, dietitian",
        "Daily meal ordering workflow for diabetic, renal, salt-restricted, soft, and liquid inpatient diet plans.",
        "1. Open Dietary Portal; 2. Select patient bed; 3. Choose therapeutic diet category prescribed by doctor; 4. Specify food allergies; 5. Submit cut-off order before 07:00 / 12:00 / 18:00.",
        "Error: 'NPO (Nil by Mouth) Override' -> System prevents meal dispatch if patient is flagged NPO for surgery or procedure.",
        "ext. 1035"
    ],
    [
        "KA-018", "How to Log Equipment Preventive Maintenance in BME Portal", "BME Portal", "Biomedical Engineering", "2.3",
        "2026-02-26", "biomedical_engineer",
        "Maintenance logging for ventilators, multipara monitors, defibrillators, dialysis machines, and infusion pumps.",
        "1. Open BME Maintenance Portal; 2. Scan equipment asset barcode; 3. Enter PM checklist values (Electrical safety, calibration); 4. Log battery status; 5. Affix calibration sticker.",
        "Error: 'Calibration Out of Tolerance' -> Tag equipment OUT OF SERVICE; transfer backup unit immediately to clinical unit.",
        "ext. 1036"
    ],
    [
        "KA-019", "How to Troubleshoot High-Resolution PACS DICOM Viewing", "PACS Viewer", "Radiology Operations", "1.8",
        "2026-02-28", "rad_tech, it_support",
        "Guide for resolving workstation cache, network lag, and display rendering issues on PACS viewing terminals.",
        "1. Open PACS Diagnostics; 2. Clear local browser image cache; 3. Verify DICOM network node connectivity (Ping AE Title); 4. Reset 3D MPR slice rendering; 5. Relaunch study viewer.",
        "Error: 'Study Incomplete' -> Verify modalities have completed push from scanner console to central archive.",
        "ext. 1022"
    ],
    [
        "KA-020", "How to Dispatch Bed Turnover Requests to Housekeeping", "Housekeeping App", "Facility Management", "1.4",
        "2026-03-02", "nurse, housekeeping",
        "Notification procedure when an inpatient vacates a bed to trigger terminal room cleaning and sanitization.",
        "1. Open Nursing Ward View; 2. Mark bed as 'Dirty / Discharged'; 3. Select cleaning type (Routine terminal clean or Isolation fogging); 4. Housekeeping team dispatched; 5. Mark 'Ready'.",
        "Target turnaround time is 45 minutes for General Ward beds and 60 minutes for ICU isolation suites.",
        "ext. 1035"
    ],
    [
        "KA-021", "How to Monitor and Dispatch Ambulances via Fleet GPS", "Fleet Dispatch", "Emergency Department", "2.0",
        "2026-03-04", "emergency_team, driver",
        "Real-time GPS dispatch protocol for BLS, ALS, and Neonatal emergency transport ambulances.",
        "1. Open Fleet Dispatch Dashboard; 2. Receive emergency distress call; 3. Enter pickup geolocation; 4. Select closest available ALS/BLS ambulance; 5. Transmit destination coordinates.",
        "Emergency ambulance response dispatch target is <= 3 minutes from initial emergency call receipt.",
        "ext. 1011"
    ],
    [
        "KA-022", "How to Scan and Track Surgical Instrument Trays in CSSD", "CSSD System", "Operation Theatre", "1.7",
        "2026-03-06", "cssd_tech, nurse",
        "Barcode tracking workflow for autoclave sterilization batches, biological indicators, and instrument tray dispatch.",
        "1. Open CSSD Tracker; 2. Scan instrument tray barcode; 3. Assign autoclave batch number; 4. Verify Bowie-Dick and biological indicator results; 5. Issue sterile dispatch green label.",
        "Error: 'Biological Indicator Positive' -> Quarantine entire autoclave load immediately; notify Infection Control Officer.",
        "ext. 1037"
    ],
    [
        "KA-023", "How to Execute Biometric Aadhaar Verification at OPD Counter", "Registration Terminal", "Front Office and Registration", "2.2",
        "2026-03-08", "front_office",
        "Guide for performing UIDAI Aadhaar biometric fingerprint and iris verification during patient onboarding.",
        "1. Open Registration Terminal; 2. Connect RD Service optical scanner; 3. Enter patient 12-digit Aadhaar number; 4. Capture fingerprint scan; 5. Auto-populate verified demographics.",
        "Error: 'RD Service Not Ready' -> Reconnect USB scanner and restart UIDAI service; For senior citizens, use IRIS scanner if fingerprint fails.",
        "ext. 1026"
    ],
    [
        "KA-024", "How to Upload Medical Documents for Interim Insurance Enhancement", "TPA Portal", "Insurance and TPA", "2.7",
        "2026-03-10", "insurance_tpa",
        "Process for requesting additional cashless insurance approval when inpatient hospital bill exceeds initial authorized amount.",
        "1. Open Active Claim in TPA Portal; 2. Select 'Request Enhancement'; 3. Enter current incurred bill and requested amount; 4. Attach daily clinical notes and ICU charts; 5. Submit.",
        "Enhancement requests must be submitted at least 24 hours prior to planned discharge to avoid checkout delays.",
        "ext. 1029"
    ],
    [
        "KA-025", "How to Broadcast Automated SMS Panic Alerts for Critical Labs", "LIS Engine", "Laboratory Operations", "2.1",
        "2026-03-12", "lab_tech, quality",
        "Protocol for triggering priority SMS and push notifications when laboratory findings fall within life-threatening panic ranges.",
        "1. LIS flags panic value automatically upon analyzer run; 2. Tech reviews result and confirms calibration; 3. Click 'Broadcast Critical Panic Alert'; 4. System pages treating doctor; 5. Log readback.",
        "Mandatory requirement: Verbal telephone readback must be documented within 15 minutes of critical result generation.",
        "ext. 1021"
    ],
    [
        "KA-026", "How to Update Consultant On-Call Roster in Hospital Portal", "Roster Portal", "Human Resources and Administration", "1.6",
        "2026-03-14", "operations_manager, hr_officer",
        "Administrative guide for publishing and modifying 24x7 emergency on-call consultant schedules across 37 departments.",
        "1. Open Roster Portal; 2. Select Department and Specialty; 3. Assign Primary On-Call and Secondary Backup Consultants; 4. Enter contact numbers; 5. Publish weekly roster.",
        "Emergency swap requests require mutual digital acceptance from both consultants and notification to Medical Superintendent.",
        "ext. 1031"
    ],
    [
        "KA-027", "How to Process Unused Inpatient Drug Return Credits", "Pharmacy System", "Pharmacy", "2.0",
        "2026-03-16", "pharmacist, billing",
        "Workflow for returning unadministered, sealed inpatient medications to central pharmacy and issuing billing ledger credits.",
        "1. Open Pharmacy Return module; 2. Scan medication barcode; 3. Verify sealed blister package and expiry date; 4. Enter patient UHID; 5. Confirm return quantity; 6. Ledger credit auto-applied.",
        "Cut-off rule: Medications cannot be returned once opened, reconstituted, or cold-chain broken; Returns must be finalized before final bill.",
        "ext. 1023"
    ],
    [
        "KA-028", "How to Complete Digital Sign-Off for Typed Discharge Summaries", "EMR Engine", "Clinical Services", "2.5",
        "2026-03-18", "doctor",
        "Protocol for consultant digital review, signature lock, and publishing of final inpatient discharge summaries.",
        "1. Open EMR Discharge Summary draft; 2. Review course in hospital, surgical procedures, and discharge medications; 3. Enter follow-up instructions; 4. Enter DSC pin / digital signature; 5. Lock summary.",
        "Once locked, summary is permanently archived and cannot be edited; amendments require formal clinical addendum note.",
        "ext. 1012"
    ],
    [
        "KA-029", "How to Issue and Scan Barcoded Inpatient Attender Passes", "Security Terminal", "Front Office and Registration", "1.3",
        "2026-03-20", "front_office, security",
        "Issuance, renewal, and security barrier scanning protocol for inpatient visitor passes.",
        "1. Open Security Pass module; 2. Scan patient admission barcode; 3. Enter primary attender name, photo, and mobile; 4. Print thermal barcoded pass; 5. Security scans pass at ward entrance.",
        "Maximum 2 visitor passes issued per private room; 1 pass per general ward bed; Visiting hours are strictly 16:00 to 19:00.",
        "ext. 1034"
    ],
    [
        "KA-030", "How to Schedule Oncology Day Care Chemotherapy Sessions", "Oncology Portal", "Oncology", "2.2",
        "2026-03-22", "doctor, nurse",
        "Booking and clinical pre-requisite verification for outpatient day care chemotherapy infusion chairs.",
        "1. Open Oncology Daycare Scheduler; 2. Select chemo chair and infusion protocol; 3. Verify CBC, LFT, and RFT clearance; 4. Verify medical oncologist sign-off; 5. Confirm pharmacy pre-mix indent.",
        "Safety rule: Chemotherapy cannot be mixed until patient arrives and baseline vitals and absolute neutrophil count (ANC) are confirmed.",
        "ext. 1019"
    ]
]

# Sheet 3: Workflow Information Data
WORKFLOW_INFO_COLS = [
    "Workflow ID", "Workflow Name", "Step Number", "Step Name", "Actor Role", 
    "Input Data Fields", "System Action / Endpoint", "Success Transition", 
    "Blocker / Condition", "Escalation Route", "Human Approval Required?"
]

WORKFLOW_INFO_DATA = [
    # WF-001: Patient Emergency and Inpatient Admission (5 steps)
    ["WF-001", "Patient Emergency & Inpatient Admission", 1, "Patient Demographic & UHID Verification", "front_office",
     "uhid, patient_name, age, gender, contact, address", "GET /api/patients/{uhid} or POST /api/patients", "Proceed to Step 2 (Clinical Triage)",
     "UHID missing or demographic mismatch", "R-007 -> Front Office Supervisor (ext. 1026)", "No"],
    ["WF-001", "Patient Emergency & Inpatient Admission", 2, "Clinical Triage & Department Assessment", "doctor",
     "uhid, admitting_doctor_id, department_id, admitting_diagnosis, admission_type", "GET /api/departments", "Proceed to Step 3 (Bed Availability Check)",
     "Incomplete clinical diagnosis or uncredentialed doctor", "R-001 -> Clinical Review (ext. 1012)", "Yes"],
    ["WF-001", "Patient Emergency & Inpatient Admission", 3, "Bed Availability Check & Ward Allocation", "admission",
     "ward, bed_id, admission_type", "GET /api/beds?ward={ward}", "Proceed to Step 4 (Financial & Insurance Check)",
     "Zero vacant beds in requested ward category", "R-010 -> Operations Manager (ext. 1032)", "No"],
    ["WF-001", "Patient Emergency & Inpatient Admission", 4, "Financial & Insurance Pre-Authorization Verification", "insurance_tpa",
     "insurance_policy_number, insurer_name, tpa_name, estimate_amount", "GET /api/insurance/claims", "Proceed to Step 5 (Admission Finalization)",
     "Pre-auth rejected or cashless eligibility unconfirmed", "R-004 -> Insurance TPA Desk (ext. 1029)", "Yes"],
    ["WF-001", "Patient Emergency & Inpatient Admission", 5, "Admission Finalization & Inpatient Check-In", "admission",
     "uhid, bed_id, admitting_doctor_id, department_id, admission_type", "POST /api/admissions", "Inpatient admission active; bed marked occupied",
     "Bed occupied by another patient during transaction", "R-010 -> Bed Allocation Lead (ext. 1027)", "Yes"],

    # WF-002: Four-Point Inpatient Discharge Clearance (4 steps)
    ["WF-002", "Four-Point Inpatient Discharge Clearance", 1, "Clinical Discharge Order & Summary Sign-off", "doctor",
     "admission_id, final_diagnosis, discharge_type, discharge_summary", "GET /api/admissions/{id}", "Proceed to Step 2 (Pharmacy Return Reconciliation)",
     "Doctor discharge order not electronically signed", "R-001 -> Treating Consultant (ext. 1012)", "Yes"],
    ["WF-002", "Four-Point Inpatient Discharge Clearance", 2, "Pharmacy Medication Audit & Return Reconciliation", "nurse",
     "admission_id, clearance_pharmacy, unreturned_medications", "GET /api/prescriptions", "Proceed to Step 3 (Billing & Co-pay Settlement)",
     "Unreturned inpatient medicines pending in ward", "R-002 -> Central Pharmacy (ext. 1023)", "No"],
    ["WF-002", "Four-Point Inpatient Discharge Clearance", 3, "Central Billing Tariff Audit & Co-pay Settlement", "billing",
     "admission_id, clearance_billing, total_bill, paid_amount, insurance_settled", "GET /api/bills/{admission_id}", "Proceed to Step 4 (Nursing Clearance & Gate Pass)",
     "Outstanding balance pending or insurance approval delayed", "R-008 -> Billing Team (ext. 1028)", "Yes"],
    ["WF-002", "Four-Point Inpatient Discharge Clearance", 4, "Nursing Ward Clearance & Physical Gate Pass Generation", "discharge",
     "admission_id, uhid, clearance_nursing, clearance_billing, clearance_pharmacy", "POST /api/discharges", "Discharge complete; bed marked dirty for housekeeping",
     "Any of the 4 clearances false (e.g. clearance_billing=false)", "R-008 -> Discharge Coordinator (ext. 1027)", "Yes"],

    # WF-003: Cashless Insurance Pre-Authorization & Query Resolution (4 steps)
    ["WF-003", "Cashless Insurance Pre-Authorization & Query Resolution", 1, "Policy Demographic & Card Verification", "insurance_tpa",
     "uhid, insurance_policy_number, insurer_name, tpa_name", "GET /api/patients/{uhid}", "Proceed to Step 2 (Treatment Estimate Assembly)",
     "Insurance card expired or name mismatch with Aadhaar", "R-004 -> Insurance TPA Desk (ext. 1029)", "No"],
    ["WF-003", "Cashless Insurance Pre-Authorization & Query Resolution", 2, "Treatment Estimate & Pre-Auth Packet Assembly", "billing",
     "admission_id, claim_amount, diagnosis_code, estimate_breakdown", "POST /api/insurance/claims", "Proceed to Step 3 (TPA Query Monitoring)",
     "Incomplete clinical diagnostic evidence attached", "R-005 -> Treating Doctor / TPA Desk", "No"],
    ["WF-003", "Cashless Insurance Pre-Authorization & Query Resolution", 3, "TPA Query Response & Additional Documents (RFI)", "insurance_tpa",
     "claim_id, query_description, uploaded_documents, clinical_justification", "GET /api/insurance/claims", "Proceed to Step 4 (Final Pre-Auth Approval)",
     "TPA query unanswered beyond 24 hours", "R-005 -> Senior Insurance Officer (ext. 1029)", "No"],
    ["WF-003", "Cashless Insurance Pre-Authorization & Query Resolution", 4, "Final Pre-Auth Approval & Co-pay Confirmation", "insurance_tpa",
     "claim_id, approved_amount, co_pay_amount, claim_status", "GET /api/insurance/claims", "Cashless pre-auth confirmed in HIS billing module",
     "Claim rejected citing exclusions or non-disclosure", "R-004 -> TPA Dispute Desk (ext. 1029)", "Yes"],

    # WF-004: Inpatient Ward and ICU Bed Transfer (4 steps)
    ["WF-004", "Inpatient Ward and ICU Bed Transfer", 1, "Clinical Bed Transfer Requisition", "doctor",
     "admission_id, uhid, current_bed_id, target_ward, transfer_reason", "GET /api/admissions/{id}", "Proceed to Step 2 (Target Bed Vacancy Verification)",
     "Transfer reason clinically unjustified or missing doctor signature", "R-001 -> Clinical Review (ext. 1012)", "Yes"],
    ["WF-004", "Inpatient Ward and ICU Bed Transfer", 2, "Target Ward Bed Vacancy Verification", "admission",
     "target_ward, target_bed_id", "GET /api/beds?ward={ward}", "Proceed to Step 3 (Buffer Override Authorization)",
     "Zero vacant beds available in target ward", "R-010 -> Operations Manager (ext. 1032)", "No"],
    ["WF-004", "Inpatient Ward and ICU Bed Transfer", 3, "Buffer Override & Transfer Approval", "operations_manager",
     "admission_id, target_bed_id, override_authorized, approver_staff_id", "GET /api/approvals", "Proceed to Step 4 (Physical Handover & HIS Shift)",
     "Buffer override declined due to maximum facility load", "R-010 -> Medical Superintendent (ext. 1031)", "Yes"],
    ["WF-004", "Inpatient Ward and ICU Bed Transfer", 4, "SBAR Clinical Handover & Bed Status Update", "nurse",
     "admission_id, previous_bed_id, target_bed_id, handover_notes", "POST /api/admissions/transfer", "Patient transferred; previous bed set to dirty",
     "SBAR vital sign deterioration during transfer prep", "R-001 -> Rapid Response Team (ext. 1012)", "Yes"],

    # WF-005: STAT Critical Lab Investigation & Panic Alert (4 steps)
    ["WF-005", "STAT Critical Lab Investigation & Panic Alert", 1, "Physician Electronic STAT Lab Order", "doctor",
     "uhid, admission_id, test_name, priority, ordering_doctor_id", "POST /api/orders", "Proceed to Step 2 (Sample Collection & Accessioning)",
     "Invalid test panel name or patient inactive", "R-009 -> Lab Helpdesk (ext. 1021)", "No"],
    ["WF-005", "STAT Critical Lab Investigation & Panic Alert", 2, "Bedside Phlebotomy & Barcode Accessioning", "nurse",
     "order_id, sample_barcode, accession_timestamp, phlebotomist_id", "GET /api/orders", "Proceed to Step 3 (Analyzer Run & Critical Detection)",
     "Sample hemolyzed, clotted, or insufficient quantity", "R-009 -> Phlebotomy Supervisor (ext. 1021)", "No"],
    ["WF-005", "STAT Critical Lab Investigation & Panic Alert", 3, "Analyzer Run & Critical Panic Value Detection", "lab_tech",
     "order_id, test_name, result_value, critical_value_flag", "GET /api/lab-results", "Proceed to Step 4 (Mandatory 15-Min Phone Alert)",
     "Quality control failure or analyzer calibration fault", "R-011 -> Lab Tech Lead (ext. 1021)", "No"],
    ["WF-005", "STAT Critical Lab Investigation & Panic Alert", 4, "Mandatory 15-Minute Physician Phone Alert & Readback", "lab_tech",
     "result_id, notified_doctor_id, readback_confirmed, alert_timestamp", "POST /api/approvals", "Panic alert logged; clinical intervention initiated",
     "Doctor unavailable / unalerted beyond 15 minutes", "R-009 -> Chief Medical Officer (ext. 1012)", "Yes"],

    # WF-006: Adverse Clinical & Operational Incident Reporting (4 steps)
    ["WF-006", "Adverse Incident & Sentinel Event Reporting", 1, "Immediate First-Aid & Patient Stabilization", "nurse",
     "uhid, incident_location, patient_injury_status, first_aid_given", "GET /api/patients/{uhid}", "Proceed to Step 2 (Mandatory Incident Logging)",
     "Patient requires emergency resuscitation (Code Blue)", "R-001 -> Emergency Code Blue (ext. 1011)", "Yes"],
    ["WF-006", "Adverse Incident & Sentinel Event Reporting", 2, "Mandatory Incident Form Submission in HIS", "all_staff",
     "incident_type, severity, description, reporter_staff_id, location", "POST /api/tickets", "Proceed to Step 3 (Quality Risk Classification)",
     "Failure to report incident within mandatory 2-hour window", "R-013 -> Quality Manager (ext. 1032)", "No"],
    ["WF-006", "Adverse Incident & Sentinel Event Reporting", 3, "Quality Department Risk Classification & Triage", "quality",
     "ticket_id, risk_rating, sentinel_event_flag, immediate_actions", "GET /api/tickets", "Proceed to Step 4 (Root Cause Analysis & CAPA)",
     "Sentinel event identified (permanent harm or mortality)", "R-013 -> Clinical Governance Board", "Yes"],
    ["WF-006", "Adverse Incident & Sentinel Event Reporting", 4, "Root Cause Analysis & CAPA Signoff", "operations_manager",
     "ticket_id, root_cause_category, corrective_action, closure_signoff", "GET /api/approvals", "Incident closed; preventive policy updated",
     "Corrective action plan unexecuted beyond 30 days", "R-013 -> Quality Director (ext. 1032)", "Yes"],

    # WF-007: Medico-Legal Case (MLC) Protocol & Intimation (4 steps)
    ["WF-007", "Medico-Legal Case (MLC) Protocol & Intimation", 1, "Emergency MLC Identification & Trauma Stabilization", "doctor",
     "uhid, trauma_type, mlc_flag, brought_by, police_station_jurisdiction", "GET /api/patients/{uhid}", "Proceed to Step 2 (Police Intimation Dispatch)",
     "Attender refuses MLC declaration for accident/assault", "R-012 -> Casualty Medical Officer (ext. 1011)", "Yes"],
    ["WF-007", "Medico-Legal Case (MLC) Protocol & Intimation", 2, "Police Intimation Memo Dispatch within 1 Hour", "medical_records",
     "uhid, police_memo_number, police_station, dispatch_timestamp", "POST /api/tickets", "Proceed to Step 3 (Forensic Evidence Sealing)",
     "Police acknowledgement delayed beyond statutory 1-hour window", "R-012 -> Medical Superintendent (ext. 1030)", "Yes"],
    ["WF-007", "Medico-Legal Case (MLC) Protocol & Intimation", 3, "Forensic Evidence Collection & Chain-of-Custody Sealing", "doctor",
     "evidence_tag, sealing_officer, forensic_label, seal_timestamp", "GET /api/patients/{uhid}", "Proceed to Step 4 (MRD Record Sealing)",
     "Broken evidence envelope seal or missing witness signature", "R-012 -> Forensic Medicine Lead (ext. 1030)", "Yes"],
    ["WF-007", "Medico-Legal Case (MLC) Protocol & Intimation", 4, "MRD Archive Sealing & Legal File Lock", "medical_records",
     "uhid, mrd_case_file_id, legal_lock_status, police_officer_badge", "GET /api/approvals", "Case file locked; physical chart stored in secure vault",
     "Unauthorized request to alter or delete MLC record", "R-012 -> Legal Advisor / MS (ext. 1030)", "Yes"],

    # WF-008: High-Alert & Schedule X Narcotic Requisition (4 steps)
    ["WF-008", "High-Alert & Schedule X Narcotic Requisition", 1, "Senior Consultant Electronic Narcotic Requisition", "doctor",
     "uhid, drug_name, dosage, route, indication, prescribing_doctor_id", "POST /api/prescriptions", "Proceed to Step 2 (Bedside Dual-Nurse Witnessing)",
     "Doctor lacks Schedule X prescribing privilege", "R-014 -> Clinical Review / CMO (ext. 1012)", "Yes"],
    ["WF-008", "High-Alert & Schedule X Narcotic Requisition", 2, "Bedside Dual-Nurse Witnessing & Identification", "nurse",
     "prescription_id, primary_nurse_id, witness_nurse_id", "GET /api/prescriptions", "Proceed to Step 3 (Vault Physical Register Log)",
     "Second witness nurse unavailable at bedside", "R-014 -> Nursing Supervisor (ext. 1025)", "Yes"],
    ["WF-008", "High-Alert & Schedule X Narcotic Requisition", 3, "Central Pharmacy Vault Physical Register Log & Dispense", "pharmacist",
     "prescription_id, vault_register_page, batch_number, pharmacist_signoff", "GET /api/prescriptions", "Proceed to Step 4 (Empty Ampoule Return)",
     "Narcotic safe key-holder unavailable or count mismatch", "R-014 -> Chief Pharmacist (ext. 1023)", "Yes"],
    ["WF-008", "High-Alert & Schedule X Narcotic Requisition", 4, "Empty Ampoule Return & Wastage Reconciliation", "nurse",
     "prescription_id, ampoule_returned, unused_wastage_witness", "POST /api/approvals", "Narcotic ledger balanced and reconciled",
     "Broken ampoule or unreturned narcotic residue unaccounted", "R-014 -> Pharmacy Narcotic Audit (ext. 1023)", "Yes"]
]

# Sheet 4: Routing Rules Data
ROUTING_RULES_COLS = [
    "Rule ID", "Trigger Event / Query", "Trigger Type", "Condition Description", 
    "Target Department / Team", "Contact Extension", "Helpdesk Queue", "Priority", 
    "SLA Hours", "Escalation Rationale", "Sample User Query 1", "Sample User Query 2"
]

ROUTING_RULES_DATA = [
    ["R-001", "Clinical question detected", "Intent", "Medical advice or diagnosis asked", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Non-clinicians and automated AI systems cannot prescribe medical advice", "What antibiotic should I prescribe?", "Does this patient need immediate intubation?"],
    ["R-002", "Medication dosage asked", "Intent", "Dosage calculation inquiry", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Severe risk of drug toxicity or dosing error", "What is the pediatric dose of amikacin?", "How many units of insulin should I give?"],
    ["R-003", "Diagnosis question asked", "Intent", "Interpretation of clinical symptoms", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 1.0, "Diagnostic responsibility lies exclusively with licensed physician", "Can you confirm if this ECG shows STEMI?", "What is the diagnosis for this patient?"],
    ["R-004", "Insurance claim rejected", "Data State", "Cashless claim status updated to rejected", "Insurance and TPA", "1029", "QUEUE_INSURANCE", "high", 2.0, "Requires urgent dispute filing, RFI appeal, or financial counseling", "Claim CLM-002 rejected citing clause 4.2", "Why did Star Health deny cashless approval?"],
    ["R-005", "Pre-auth pending over 48 hours", "Time Threshold", "Pre-auth unacknowledged after 48h", "Insurance and TPA", "1029", "QUEUE_INSURANCE", "high", 2.0, "Unreasonable insurer delay threatening planned admission", "Preauth for UHID-000002 has had no response for 2 days", "Status still submitted after 50 hours"],
    ["R-006", "Bill disputed by patient", "Intent", "Attender disputes itemized charges", "Billing", "1028", "QUEUE_BILLING", "high", 2.0, "Financial grievance requiring itemized tariff audit", "Patient attender refuses to pay extra consumables", "Why are we being charged for ICU support?"],
    ["R-007", "UHID not found in system", "Data State", "Query yields zero results across DB", "Front Office and Registration", "1026", "QUEUE_FRONTOFFICE", "normal", 4.0, "Demographic reconciliation and master patient index check needed", "I cannot find patient Senthil Kumar with UHID-999999", "Patient card says UHID-000088 but no records"],
    ["R-008", "Discharge blocked by billing", "Data State", "Discharge signed but billing is FALSE", "Billing", "1028", "QUEUE_BILLING", "high", 2.0, "Causes inpatient bed blockage and delay in admissions", "Discharge for Bed 07 blocked because bill is not generated", "Nursing cleared but stuck waiting for bill"],
    ["R-009", "Critical lab result unalerted", "Data State", "critical_value_flag is TRUE but alerted is FALSE", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 0.5, "Severe patient safety hazard requiring immediate verbal readback", "Potassium is 6.8 mmol/L but doctor not alerted for 30m", "Platelets under 20000 with alert unexecuted"],
    ["R-010", "Bed unavailable in requested ward", "Data State", "No vacant beds matching admission", "Operations Management", "1032", "QUEUE_FACILITY", "high", 1.0, "Requires buffer override or inter-ward step-down transfer", "Zero ICU beds available for emergency patient", "Need General Ward bed but all 15 occupied"],
    ["R-011", "IT system down reported", "Incident", "Workstation or HIS connectivity failure", "IT and HIS Support", "1033", "QUEUE_IT_SUPPORT", "urgent", 1.0, "Hospital operational continuity and care delivery at risk", "EMR workstation in ICU Bed 02 freezing", "Cannot access HIS admission portal from counter"],
    ["R-012", "MLC case registration needed", "Event", "Trauma, poisoning, or assault presentation", "Medical Records (MRD / HIM)", "1030", "QUEUE_MRD", "urgent", 1.0, "Statutory police intimation mandatory within 1 hour", "Road traffic accident victim in emergency bay", "Suspected domestic assault requires MLC"],
    ["R-013", "Patient complaint about staff", "Grievance", "Attender registers service complaint", "Quality and Patient Safety", "1032", "QUEUE_QUALITY", "high", 4.0, "Patient satisfaction and service recovery protocol", "Attender complained of delay in breakfast", "Complaint regarding rude behavior at counter"],
    ["R-014", "Narcotic drug query", "Drug Schedule", "Schedule X / Fentanyl / Morphine query", "Clinical Review", "1012", "QUEUE_CLINICAL", "urgent", 0.5, "Strict statutory narcotic register compliance and dual signoff", "Need emergency dose of Inj Morphine 10mg", "How do I request Fentanyl ampoule?"],
    ["R-015", "Low confidence score under 0.6", "System Logic", "Confidence falls below 0.60 threshold", "Front Office and Registration", "1026", "QUEUE_FRONTOFFICE", "normal", 4.0, "Escalate ambiguous queries to human triage", "I need that document about the thing from last month", "Can you process the green file for room five?"]
]

# Sheet 5: Field Definitions Data
def load_field_definitions():
    json_path = KB_DIR / "field_definitions.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rows = []
    for item in data.get("fields", []):
        opts = ", ".join(str(x) for x in (item.get("select_options") or [])) if item.get("select_options") else "-"
        docs = ", ".join(str(x) for x in (item.get("used_in_documents") or [])) if item.get("used_in_documents") else "-"
        rows.append([
            item.get("field_name"),
            item.get("display_name"),
            item.get("type"),
            "Yes" if item.get("required") else "No",
            item.get("validation_pattern") or "-",
            opts,
            item.get("on_missing_message"),
            docs
        ])
    return rows

FIELD_DEFINITIONS_COLS = [
    "Field ID / Name", "Display Name", "Data Type", "Is Required?", 
    "Validation Pattern / Regex", "Select Options", "Missing Prompt / Clarification Message", 
    "Used In Documents & Workflows"
]

# =========================================================================
# WORKBOOK GENERATION
# =========================================================================
def build_master_workbook():
    wb_path = KB_DIR / "Operations_Synthetic_Workbook.xlsx"
    wb = openpyxl.Workbook()

    # 1. Operations Requests
    ws1 = wb.active
    ws1.title = "Operations Requests"
    format_styled_sheet(
        ws1, "Operational Request Scenarios & User Intent Catalog", 
        OPERATIONS_REQUESTS_COLS, OPERATIONS_REQUESTS_DATA,
        col_widths=[14, 32, 18, 22, 18, 22, 45, 30, 32, 35, 16, 22]
    )

    # 2. Approved Knowledge Articles
    ws2 = wb.create_sheet(title="Approved Knowledge Articles")
    format_styled_sheet(
        ws2, "30 Approved Knowledge Base Articles & SOP Guides",
        KNOWLEDGE_ARTICLES_COLS, KNOWLEDGE_ARTICLES_DATA,
        col_widths=[14, 35, 18, 26, 10, 14, 25, 45, 55, 45, 16]
    )

    # 3. Workflow Information
    ws3 = wb.create_sheet(title="Workflow Information")
    format_styled_sheet(
        ws3, "Core Operational Workflow State Machine & Step Specifications",
        WORKFLOW_INFO_COLS, WORKFLOW_INFO_DATA,
        col_widths=[14, 32, 12, 35, 18, 35, 26, 32, 35, 30, 20]
    )

    # 4. Routing Rules
    ws4 = wb.create_sheet(title="Routing Rules")
    format_styled_sheet(
        ws4, "Escalation Routing Rules & Support Helpdesk Taxonomy",
        ROUTING_RULES_COLS, ROUTING_RULES_DATA,
        col_widths=[12, 28, 16, 32, 24, 16, 20, 12, 12, 38, 38, 38]
    )

    # 5. Field Definitions
    ws5 = wb.create_sheet(title="Field Definitions")
    field_rows = load_field_definitions()
    format_styled_sheet(
        ws5, "Hospital Operations Standard Data Field Definitions & Schemas",
        FIELD_DEFINITIONS_COLS, field_rows,
        col_widths=[22, 28, 14, 14, 30, 28, 48, 38]
    )

    wb.save(str(wb_path))
    print(f"  [OK] Generated Master Workbook: {wb_path.name} (5 sheets)")
    return wb_path


# =========================================================================
# WORKFLOW DEFINITIONS JSON GENERATION
# =========================================================================
def build_workflow_definitions_json():
    json_path = KB_DIR / "workflow_definitions.json"
    
    # Structure the 8 workflows programmatically
    workflows = [
        {
            "workflow_id": "WF-001",
            "slug": "patient_admission",
            "name": "Patient Emergency and Inpatient Admission",
            "department": "Admission and Discharge",
            "category": "clinical_operations",
            "trigger_intents": ["create_admission", "admit_patient", "emergency_admission", "book_bed"],
            "allowed_roles": ["doctor", "front_office", "admission", "nurse"],
            "description": "Standard five-step admission sequence for emergency and elective inpatients at SMCH.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 5: Admission Order Finalization",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Demographic & UHID Verification",
                    "actor": "front_office",
                    "required_fields": ["uhid", "patient_name", "contact"],
                    "optional_fields": ["age", "gender", "address"],
                    "endpoint": "GET /api/patients/{uhid}",
                    "validation_rules": {"uhid": "^UHID-\\d{6}$"},
                    "on_missing_message": "Please provide the patient UHID in the format UHID-000001.",
                    "blockers": ["UHID not registered in system"],
                    "escalation_rule": "R-007",
                    "requires_human_approval": False,
                    "next_state": "Clinical Triage & Department Assessment"
                },
                {
                    "step_number": 2,
                    "state_name": "Clinical Triage & Department Assessment",
                    "actor": "doctor",
                    "required_fields": ["admitting_doctor_id, admitting_diagnosis, department_id"],
                    "optional_fields": ["admission_type"],
                    "endpoint": "GET /api/departments",
                    "validation_rules": {"department_id": "^DEPT-\\d{3}$"},
                    "on_missing_message": "Admitting consultant and provisional diagnosis are required.",
                    "blockers": ["Consultant credentials expired or unassigned"],
                    "escalation_rule": "R-001",
                    "requires_human_approval": True,
                    "next_state": "Bed Availability Check & Ward Allocation"
                },
                {
                    "step_number": 3,
                    "state_name": "Bed Availability Check & Ward Allocation",
                    "actor": "admission",
                    "required_fields": ["ward", "bed_id"],
                    "optional_fields": [],
                    "endpoint": "GET /api/beds?ward={ward}",
                    "validation_rules": {"bed_id": "^BED-\\d{4}$"},
                    "on_missing_message": "Specify target ward and vacant bed identifier.",
                    "blockers": ["Ward at 100% capacity", "Target bed already reserved"],
                    "escalation_rule": "R-010",
                    "requires_human_approval": False,
                    "next_state": "Financial & Insurance Pre-Authorization Check"
                },
                {
                    "step_number": 4,
                    "state_name": "Financial & Insurance Pre-Authorization Check",
                    "actor": "insurance_tpa",
                    "required_fields": ["insurance_policy_number", "insurer_name"],
                    "optional_fields": ["tpa_name", "estimate_amount"],
                    "endpoint": "GET /api/insurance/claims",
                    "validation_rules": {},
                    "on_missing_message": "Provide insurance policy number or select self-paying status.",
                    "blockers": ["TPA rejection or query pending"],
                    "escalation_rule": "R-004",
                    "requires_human_approval": False,
                    "next_state": "Admission Finalization & Inpatient Check-In"
                },
                {
                    "step_number": 5,
                    "state_name": "Admission Finalization & Inpatient Check-In",
                    "actor": "admission",
                    "required_fields": ["uhid", "bed_id", "admitting_doctor_id", "department_id"],
                    "optional_fields": ["admission_type"],
                    "endpoint": "POST /api/admissions",
                    "validation_rules": {"admission_type": ["emergency", "elective", "transfer"]},
                    "on_missing_message": "Confirm final admission details to allocate bed.",
                    "blockers": ["Race condition: bed claimed during form submission"],
                    "escalation_rule": "R-010",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-002",
            "slug": "patient_discharge",
            "name": "Four-Point Inpatient Discharge Clearance",
            "department": "Admission and Discharge",
            "category": "clinical_operations",
            "trigger_intents": ["discharge_patient", "discharge_clearance", "check_discharge_status", "generate_gate_pass"],
            "allowed_roles": ["doctor", "nurse", "discharge", "billing"],
            "description": "Rigorous four-tier clearance protocol (Clinical, Pharmacy, Billing, Nursing) required before patient discharge.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: Nursing Ward Clearance & Physical Gate Pass Generation",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Clinical Discharge Order & Summary Sign-off",
                    "actor": "doctor",
                    "required_fields": ["admission_id", "final_diagnosis", "discharge_type"],
                    "optional_fields": ["discharge_summary"],
                    "endpoint": "GET /api/admissions/{id}",
                    "validation_rules": {"discharge_type": ["Normal", "DAMA", "LAMA", "Absconded", "Transfer", "Death"]},
                    "on_missing_message": "Treating consultant must provide digital sign-off and final diagnosis.",
                    "blockers": ["Patient clinically unstable", "Summary unsigned"],
                    "escalation_rule": "R-001",
                    "requires_human_approval": True,
                    "next_state": "Pharmacy Medication Audit & Return Reconciliation"
                },
                {
                    "step_number": 2,
                    "state_name": "Pharmacy Medication Audit & Return Reconciliation",
                    "actor": "nurse",
                    "required_fields": ["admission_id", "clearance_pharmacy"],
                    "optional_fields": ["unreturned_medications"],
                    "endpoint": "GET /api/prescriptions",
                    "validation_rules": {"clearance_pharmacy": "boolean"},
                    "on_missing_message": "Confirm unused medication returns to central pharmacy.",
                    "blockers": ["Unreturned injectable or oral doses in ward tray"],
                    "escalation_rule": "R-002",
                    "requires_human_approval": False,
                    "next_state": "Central Billing Tariff Audit & Co-pay Settlement"
                },
                {
                    "step_number": 3,
                    "state_name": "Central Billing Tariff Audit & Co-pay Settlement",
                    "actor": "billing",
                    "required_fields": ["admission_id", "clearance_billing"],
                    "optional_fields": ["bill_amount", "paid_amount"],
                    "endpoint": "GET /api/bills/{admission_id}",
                    "validation_rules": {"clearance_billing": "boolean"},
                    "on_missing_message": "Itemized billing audit and co-pay settlement required.",
                    "blockers": ["Outstanding co-pay variance", "Pending TPA final settlement"],
                    "escalation_rule": "R-008",
                    "requires_human_approval": True,
                    "next_state": "Nursing Ward Clearance & Physical Gate Pass Generation"
                },
                {
                    "step_number": 4,
                    "state_name": "Nursing Ward Clearance & Physical Gate Pass Generation",
                    "actor": "discharge",
                    "required_fields": ["admission_id", "uhid", "clearance_nursing"],
                    "optional_fields": ["gate_pass_number"],
                    "endpoint": "POST /api/discharges",
                    "validation_rules": {"clearance_nursing": "boolean"},
                    "on_missing_message": "Nursing discharge checklist and IV cannula removal confirmation required.",
                    "blockers": ["Clearance billing is FALSE", "Clearance pharmacy is FALSE"],
                    "escalation_rule": "R-008",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-003",
            "slug": "insurance_preauth",
            "name": "Cashless Insurance Pre-Authorization & Query Resolution",
            "department": "Insurance and TPA",
            "category": "financial_operations",
            "trigger_intents": ["submit_preauth", "check_insurance", "tpa_enhancement", "insurance_query"],
            "allowed_roles": ["admission", "insurance_tpa", "billing"],
            "description": "Pre-admission and concurrent insurance eligibility verification and query reply protocol.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: Final Pre-Auth Approval & Co-pay Confirmation",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Policy Demographic & Card Verification",
                    "actor": "insurance_tpa",
                    "required_fields": ["uhid", "insurance_policy_number", "insurer_name"],
                    "optional_fields": ["tpa_name"],
                    "endpoint": "GET /api/patients/{uhid}",
                    "validation_rules": {},
                    "on_missing_message": "Provide valid cashless policy number and insurer name.",
                    "blockers": ["Policy inactive or expired"],
                    "escalation_rule": "R-004",
                    "requires_human_approval": False,
                    "next_state": "Treatment Estimate & Pre-Auth Packet Assembly"
                },
                {
                    "step_number": 2,
                    "state_name": "Treatment Estimate & Pre-Auth Packet Assembly",
                    "actor": "billing",
                    "required_fields": ["admission_id", "claim_amount", "diagnosis_code"],
                    "optional_fields": ["estimate_breakdown"],
                    "endpoint": "POST /api/insurance/claims",
                    "validation_rules": {"claim_amount": "number > 0"},
                    "on_missing_message": "Attach medical package estimate and ICD-10 diagnosis code.",
                    "blockers": ["Treating consultant medical certificate missing"],
                    "escalation_rule": "R-005",
                    "requires_human_approval": False,
                    "next_state": "TPA Query Response & Additional Documents"
                },
                {
                    "step_number": 3,
                    "state_name": "TPA Query Response & Additional Documents",
                    "actor": "insurance_tpa",
                    "required_fields": ["claim_id"],
                    "optional_fields": ["query_description", "uploaded_documents"],
                    "endpoint": "GET /api/insurance/claims",
                    "validation_rules": {},
                    "on_missing_message": "Address specific queries raised by TPA auditor.",
                    "blockers": ["Query SLA exceeded (>24h delay)"],
                    "escalation_rule": "R-005",
                    "requires_human_approval": False,
                    "next_state": "Final Pre-Auth Approval & Co-pay Confirmation"
                },
                {
                    "step_number": 4,
                    "state_name": "Final Pre-Auth Approval & Co-pay Confirmation",
                    "actor": "insurance_tpa",
                    "required_fields": ["claim_id", "approved_amount", "claim_status"],
                    "optional_fields": ["co_pay_amount"],
                    "endpoint": "GET /api/insurance/claims",
                    "validation_rules": {"claim_status": ["approved", "rejected", "query_raised"]},
                    "on_missing_message": "Confirm sanctioned amount and patient co-pay responsibility.",
                    "blockers": ["Claim rejected citing exclusion clause"],
                    "escalation_rule": "R-004",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-004",
            "slug": "bed_transfer",
            "name": "Inpatient Ward and ICU Bed Transfer",
            "department": "Admission and Discharge",
            "category": "clinical_operations",
            "trigger_intents": ["transfer_patient", "step_up_icu", "step_down_ward", "change_bed"],
            "allowed_roles": ["doctor", "nurse", "admission", "operations_manager"],
            "description": "Clinical transfer procedure between General Ward, Private Rooms, and Intensive Care Units.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 3: Buffer Override & Transfer Approval",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Clinical Bed Transfer Requisition",
                    "actor": "doctor",
                    "required_fields": ["admission_id", "uhid", "current_bed_id", "target_ward", "transfer_reason"],
                    "optional_fields": [],
                    "endpoint": "GET /api/admissions/{id}",
                    "validation_rules": {},
                    "on_missing_message": "Enter transfer indication (clinical step-up, patient request, or step-down).",
                    "blockers": ["Treating consultant sign-off missing"],
                    "escalation_rule": "R-001",
                    "requires_human_approval": True,
                    "next_state": "Target Ward Bed Vacancy Verification"
                },
                {
                    "step_number": 2,
                    "state_name": "Target Ward Bed Vacancy Verification",
                    "actor": "admission",
                    "required_fields": ["target_ward", "target_bed_id"],
                    "optional_fields": [],
                    "endpoint": "GET /api/beds?ward={ward}",
                    "validation_rules": {"target_bed_id": "^BED-\\d{4}$"},
                    "on_missing_message": "Select available vacant bed in destination unit.",
                    "blockers": ["Zero vacant beds in target unit"],
                    "escalation_rule": "R-010",
                    "requires_human_approval": False,
                    "next_state": "Buffer Override & Transfer Approval"
                },
                {
                    "step_number": 3,
                    "state_name": "Buffer Override & Transfer Approval",
                    "actor": "operations_manager",
                    "required_fields": ["admission_id", "target_bed_id"],
                    "optional_fields": ["override_authorized"],
                    "endpoint": "GET /api/approvals",
                    "validation_rules": {},
                    "on_missing_message": "Operations Manager authorization needed for ICU transfer.",
                    "blockers": ["Facility buffer limit exceeded"],
                    "escalation_rule": "R-010",
                    "requires_human_approval": True,
                    "next_state": "SBAR Clinical Handover & Bed Status Update"
                },
                {
                    "step_number": 4,
                    "state_name": "SBAR Clinical Handover & Bed Status Update",
                    "actor": "nurse",
                    "required_fields": ["admission_id", "previous_bed_id", "target_bed_id"],
                    "optional_fields": ["handover_notes"],
                    "endpoint": "POST /api/admissions/transfer",
                    "validation_rules": {},
                    "on_missing_message": "Complete dual-nurse SBAR clinical handover in HIS.",
                    "blockers": ["Patient vitals unstable for physical transport"],
                    "escalation_rule": "R-001",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-005",
            "slug": "stat_lab_panic_alert",
            "name": "STAT Critical Lab Investigation & Panic Alert Escalation",
            "department": "Laboratory Operations",
            "category": "clinical_operations",
            "trigger_intents": ["order_lab", "stat_lab", "check_critical_lab", "panic_value_alert"],
            "allowed_roles": ["doctor", "nurse", "lab_tech", "quality"],
            "description": "Urgent diagnostic ordering, analyzer processing, and statutory 15-minute panic notification workflow.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: Mandatory 15-Minute Physician Phone Alert & Readback",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Physician Electronic STAT Lab Order",
                    "actor": "doctor",
                    "required_fields": ["uhid", "admission_id", "test_name", "priority"],
                    "optional_fields": ["ordering_doctor_id"],
                    "endpoint": "POST /api/orders",
                    "validation_rules": {"priority": ["stat", "urgent", "routine"]},
                    "on_missing_message": "Specify test panel name and priority (STAT/Routine).",
                    "blockers": ["Inactive admission or invalid test name"],
                    "escalation_rule": "R-009",
                    "requires_human_approval": False,
                    "next_state": "Bedside Phlebotomy & Barcode Accessioning"
                },
                {
                    "step_number": 2,
                    "state_name": "Bedside Phlebotomy & Barcode Accessioning",
                    "actor": "nurse",
                    "required_fields": ["order_id", "sample_barcode"],
                    "optional_fields": ["phlebotomist_id"],
                    "endpoint": "GET /api/orders",
                    "validation_rules": {},
                    "on_missing_message": "Scan sample vial barcode and confirm accession.",
                    "blockers": ["Sample hemolyzed or incorrect vial color"],
                    "escalation_rule": "R-009",
                    "requires_human_approval": False,
                    "next_state": "Analyzer Run & Critical Panic Value Detection"
                },
                {
                    "step_number": 3,
                    "state_name": "Analyzer Run & Critical Panic Value Detection",
                    "actor": "lab_tech",
                    "required_fields": ["order_id", "test_name", "result_value"],
                    "optional_fields": ["critical_value_flag"],
                    "endpoint": "GET /api/lab-results",
                    "validation_rules": {},
                    "on_missing_message": "Verify analyzer calibration and input findings.",
                    "blockers": ["Analyzer internal quality control out of limits"],
                    "escalation_rule": "R-011",
                    "requires_human_approval": False,
                    "next_state": "Mandatory 15-Minute Physician Phone Alert & Readback"
                },
                {
                    "step_number": 4,
                    "state_name": "Mandatory 15-Minute Physician Phone Alert & Readback",
                    "actor": "lab_tech",
                    "required_fields": ["result_id", "notified_doctor_id", "readback_confirmed"],
                    "optional_fields": ["alert_timestamp"],
                    "endpoint": "POST /api/approvals",
                    "validation_rules": {"readback_confirmed": "boolean"},
                    "on_missing_message": "Document verbal readback confirmation from treating doctor.",
                    "blockers": ["Treating physician unreachable for >15 minutes"],
                    "escalation_rule": "R-009",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-006",
            "slug": "incident_reporting",
            "name": "Adverse Clinical & Operational Incident Reporting",
            "department": "Quality and Patient Safety",
            "category": "quality_safety",
            "trigger_intents": ["report_incident", "patient_fall", "medication_error", "sentinel_event"],
            "allowed_roles": ["all_staff", "nurse", "doctor", "quality", "operations_manager"],
            "description": "Incident identification, immediate clinical containment, risk triage, and CAPA resolution.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: Root Cause Analysis & CAPA Signoff",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Immediate First-Aid & Patient Stabilization",
                    "actor": "nurse",
                    "required_fields": ["uhid", "location"],
                    "optional_fields": ["immediate_action_taken"],
                    "endpoint": "GET /api/patients/{uhid}",
                    "validation_rules": {},
                    "on_missing_message": "Document first-aid or immediate clinical containment.",
                    "blockers": ["Severe injury requiring emergency code alert"],
                    "escalation_rule": "R-001",
                    "requires_human_approval": True,
                    "next_state": "Mandatory Incident Form Submission in HIS"
                },
                {
                    "step_number": 2,
                    "state_name": "Mandatory Incident Form Submission in HIS",
                    "actor": "all_staff",
                    "required_fields": ["incident_type", "severity", "description", "reporter_staff_id"],
                    "optional_fields": ["location"],
                    "endpoint": "POST /api/tickets",
                    "validation_rules": {"severity": ["minor", "moderate", "severe", "sentinel"]},
                    "on_missing_message": "Provide objective factual description and severity rating.",
                    "blockers": ["Reporting delayed beyond 2-hour window"],
                    "escalation_rule": "R-013",
                    "requires_human_approval": False,
                    "next_state": "Quality Department Risk Classification & Triage"
                },
                {
                    "step_number": 3,
                    "state_name": "Quality Department Risk Classification & Triage",
                    "actor": "quality",
                    "required_fields": ["ticket_id", "risk_rating"],
                    "optional_fields": ["sentinel_event_flag"],
                    "endpoint": "GET /api/tickets",
                    "validation_rules": {},
                    "on_missing_message": "Quality audit classification required.",
                    "blockers": ["Sentinel event requiring immediate board notification"],
                    "escalation_rule": "R-013",
                    "requires_human_approval": True,
                    "next_state": "Root Cause Analysis & CAPA Signoff"
                },
                {
                    "step_number": 4,
                    "state_name": "Root Cause Analysis & CAPA Signoff",
                    "actor": "operations_manager",
                    "required_fields": ["ticket_id", "corrective_action"],
                    "optional_fields": ["root_cause_category"],
                    "endpoint": "GET /api/approvals",
                    "validation_rules": {},
                    "on_missing_message": "Final CAPA closure plan must be logged.",
                    "blockers": ["Root cause unassigned"],
                    "escalation_rule": "R-013",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-007",
            "slug": "medico_legal_case",
            "name": "Medico-Legal Case (MLC) Protocol & Intimation",
            "department": "Medical Records (MRD / HIM)",
            "category": "legal_compliance",
            "trigger_intents": ["register_mlc", "police_intimation", "trauma_case", "legal_lock"],
            "allowed_roles": ["doctor", "medical_records", "operations_manager"],
            "description": "Statutory trauma/assault documentation, mandatory 1-hour police intimation, and forensic sealing.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: MRD Archive Sealing & Legal File Lock",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Emergency MLC Identification & Trauma Stabilization",
                    "actor": "doctor",
                    "required_fields": ["uhid", "trauma_type"],
                    "optional_fields": ["brought_by", "police_station_jurisdiction"],
                    "endpoint": "GET /api/patients/{uhid}",
                    "validation_rules": {},
                    "on_missing_message": "Flag patient as MLC and record external trauma injury details.",
                    "blockers": ["Attender refusal to register MLC"],
                    "escalation_rule": "R-012",
                    "requires_human_approval": True,
                    "next_state": "Police Intimation Memo Dispatch"
                },
                {
                    "step_number": 2,
                    "state_name": "Police Intimation Memo Dispatch",
                    "actor": "medical_records",
                    "required_fields": ["uhid", "police_memo_number", "police_station"],
                    "optional_fields": ["dispatch_timestamp"],
                    "endpoint": "POST /api/tickets",
                    "validation_rules": {},
                    "on_missing_message": "Transmit written intimation memo to local jurisdiction police station.",
                    "blockers": ["Police acknowledgement delayed beyond statutory 1h SLA"],
                    "escalation_rule": "R-012",
                    "requires_human_approval": True,
                    "next_state": "Forensic Evidence Collection & Sealing"
                },
                {
                    "step_number": 3,
                    "state_name": "Forensic Evidence Collection & Sealing",
                    "actor": "doctor",
                    "required_fields": ["evidence_tag", "sealing_officer"],
                    "optional_fields": ["seal_timestamp"],
                    "endpoint": "GET /api/patients/{uhid}",
                    "validation_rules": {},
                    "on_missing_message": "Seal clothing, toxicological samples, or foreign bodies with dual witness.",
                    "blockers": ["Broken chain-of-custody envelope"],
                    "escalation_rule": "R-012",
                    "requires_human_approval": True,
                    "next_state": "MRD Archive Sealing & Legal File Lock"
                },
                {
                    "step_number": 4,
                    "state_name": "MRD Archive Sealing & Legal File Lock",
                    "actor": "medical_records",
                    "required_fields": ["uhid", "mrd_case_file_id"],
                    "optional_fields": ["legal_lock_status"],
                    "endpoint": "GET /api/approvals",
                    "validation_rules": {},
                    "on_missing_message": "Place digital and physical lock on MLC case chart.",
                    "blockers": ["Unauthorized attempt to modify clinical entries"],
                    "escalation_rule": "R-012",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        },
        {
            "workflow_id": "WF-008",
            "slug": "narcotic_requisition",
            "name": "High-Alert & Schedule X Narcotic Requisition",
            "department": "Pharmacy Operations",
            "category": "clinical_operations",
            "trigger_intents": ["request_narcotic", "morphine_indent", "fentanyl_order", "schedule_x"],
            "allowed_roles": ["doctor", "nurse", "pharmacist"],
            "description": "Dual-physician prescription, bedside witnessing, vault logging, and empty ampoule return.",
            "requires_human_approval": True,
            "human_approval_checkpoint": "Step 4: Empty Ampoule Return & Wastage Reconciliation",
            "states": [
                {
                    "step_number": 1,
                    "state_name": "Senior Consultant Electronic Narcotic Requisition",
                    "actor": "doctor",
                    "required_fields": ["uhid", "drug_name", "dosage", "prescribing_doctor_id"],
                    "optional_fields": ["route", "indication"],
                    "endpoint": "POST /api/prescriptions",
                    "validation_rules": {},
                    "on_missing_message": "Schedule X narcotics require senior consultant digital token sign-off.",
                    "blockers": ["Doctor lacks Schedule X prescribing privileges"],
                    "escalation_rule": "R-014",
                    "requires_human_approval": True,
                    "next_state": "Bedside Dual-Nurse Witnessing & Identification"
                },
                {
                    "step_number": 2,
                    "state_name": "Bedside Dual-Nurse Witnessing & Identification",
                    "actor": "nurse",
                    "required_fields": ["prescription_id", "primary_nurse_id", "witness_nurse_id"],
                    "optional_fields": [],
                    "endpoint": "GET /api/prescriptions",
                    "validation_rules": {},
                    "on_missing_message": "Two registered nurses must countersign administration indent.",
                    "blockers": ["Second witness nurse absent at bedside"],
                    "escalation_rule": "R-014",
                    "requires_human_approval": True,
                    "next_state": "Central Pharmacy Vault Physical Register Log & Dispense"
                },
                {
                    "step_number": 3,
                    "state_name": "Central Pharmacy Vault Physical Register Log & Dispense",
                    "actor": "pharmacist",
                    "required_fields": ["prescription_id", "vault_register_page", "batch_number"],
                    "optional_fields": ["pharmacist_signoff"],
                    "endpoint": "GET /api/prescriptions",
                    "validation_rules": {},
                    "on_missing_message": "Record vault register serial number and ampoule batch.",
                    "blockers": ["Narcotic vault physical balance discrepancy"],
                    "escalation_rule": "R-014",
                    "requires_human_approval": True,
                    "next_state": "Empty Ampoule Return & Wastage Reconciliation"
                },
                {
                    "step_number": 4,
                    "state_name": "Empty Ampoule Return & Wastage Reconciliation",
                    "actor": "nurse",
                    "required_fields": ["prescription_id", "ampoule_returned"],
                    "optional_fields": ["unused_wastage_witness"],
                    "endpoint": "POST /api/approvals",
                    "validation_rules": {"ampoule_returned": "boolean"},
                    "on_missing_message": "Empty glass ampoule must be returned to pharmacy within 24h.",
                    "blockers": ["Broken ampoule without dual-witness incident memo"],
                    "escalation_rule": "R-014",
                    "requires_human_approval": True,
                    "next_state": "COMPLETED"
                }
            ]
        }
    ]

    output_data = {
        "hospital_name": HOSPITAL_NAME,
        "version": "1.0",
        "description": "Standardized hospital operations state machine definitions for autonomous agent execution and human-in-the-loop governance.",
        "workflows": workflows
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"  [OK] Generated Workflow Definitions JSON: {json_path.name} ({len(workflows)} workflows)")
    return json_path


# =========================================================================
# COMPANION INDEX GENERATION
# =========================================================================
def build_companion_indexes():
    indexes_created = []

    # 1. Operations_Synthetic_Workbook.json
    idx_wb = INDEX_DIR / "Operations_Synthetic_Workbook.json"
    wb_content = (
        f"MASTER WORKBOOK: {HOSPITAL_NAME} Operations Master Synthetic Workbook (Operations_Synthetic_Workbook.xlsx).\n"
        f"CONSOLIDATED SHEETS:\n"
        f"1. Operations Requests: 20 comprehensive operational request scenarios spanning Admissions, Discharges, LIS, RIS, Billing, Insurance Preauth, Equipment Breakdowns, Bed Transfers, and Incident Reporting.\n"
        f"2. Approved Knowledge Articles: 30 approved knowledge base articles (KA-001 to KA-030) covering step-by-step system interactions across HIS, LIS, RIS, Billing, EMR, TPA, CSSD, and PACS.\n"
        f"3. Workflow Information: Complete state machine specifications for 8 core workflows (WF-001 Admission, WF-002 Discharge Clearance, WF-003 Insurance Preauth, WF-004 Bed Transfer, WF-005 STAT Lab Panic Value, WF-006 Incident Reporting, WF-007 Medico-Legal Case, WF-008 Narcotic Drug Control).\n"
        f"4. Routing Rules: 15 routing rules (R-001 to R-015) defining operational triggers, target teams, SLA hours, priority levels, and escalation criteria.\n"
        f"5. Field Definitions: 25 structured healthcare operational data field definitions including validation regex patterns, display labels, missing prompts, and document usage."
    )
    obj_wb = {
        "file_id": "Operations_Synthetic_Workbook",
        "title": "SMCH Operations Master Synthetic Workbook",
        "file_path": "Operations_Synthetic_Workbook.xlsx",
        "file_type": "xlsx",
        "category": "master_workbook",
        "department": "Operations Management",
        "applicable_roles": ["all_staff"],
        "version": "1.0",
        "content": wb_content,
        "tags": ["master", "workbook", "synthetic", "operations", "requests", "workflows", "routing", "fields", "smch"],
        "source_citation": "SMCH Operations Master Synthetic Workbook v1.0, Operations Management"
    }
    with open(idx_wb, "w", encoding="utf-8") as f:
        json.dump(obj_wb, f, indent=2)
    indexes_created.append(idx_wb)

    # 2. workflow_definitions.json
    idx_wf = INDEX_DIR / "workflow_definitions.json"
    wf_content = (
        f"WORKFLOW STATE MACHINE DEFINITIONS: {HOSPITAL_NAME} Operational Workflow State Machine Definitions (workflow_definitions.json).\n"
        f"SPECIFIED WORKFLOWS:\n"
        f"- WF-001: Patient Emergency and Inpatient Admission (5 states: Demographic Check, Clinical Triage, Bed Allocation, Pre-Auth Check, Admission Finalization)\n"
        f"- WF-002: Four-Point Inpatient Discharge Clearance (4 states: Clinical Order, Pharmacy Audit, Billing Settlement, Nursing Gate Pass Release)\n"
        f"- WF-003: Cashless Insurance Pre-Authorization & Query Resolution (4 states: Card Verification, Estimate Packet, TPA Query Reply, Approval Confirmation)\n"
        f"- WF-004: Inpatient Ward and ICU Bed Transfer (4 states: Clinical Requisition, Vacancy Check, Buffer Override, SBAR Handover)\n"
        f"- WF-005: STAT Critical Lab Investigation & Panic Alert Escalation (4 states: STAT Order, Accessioning, Critical Trigger, Mandatory 15-Min Phone Readback)\n"
        f"- WF-006: Adverse Clinical & Operational Incident Reporting (4 states: Containment, Incident Logging, Quality Classification, CAPA Signoff)\n"
        f"- WF-007: Medico-Legal Case (MLC) Protocol & Intimation (4 states: Trauma Stabilization, Police Intimation Memo, Forensic Sealing, Legal Chart Lock)\n"
        f"- WF-008: High-Alert & Schedule X Narcotic Requisition (4 states: Consultant Indent, Bedside Dual-Witness, Vault Register Log, Ampoule Reconciliation)\n"
        f"All workflows enforce human-in-the-loop checkpoints, validation schemas, and automated escalation to support teams."
    )
    obj_wf = {
        "file_id": "workflow_definitions",
        "title": "SMCH Operational Workflow State Machine Definitions",
        "file_path": "workflow_definitions.json",
        "file_type": "json",
        "category": "workflow_definition",
        "department": "Operations Management",
        "applicable_roles": ["all_staff"],
        "version": "1.0",
        "content": wf_content,
        "tags": ["workflow", "state_machine", "automation", "human_in_the_loop", "escalations", "smch"],
        "source_citation": "SMCH Operational Workflow State Machine Specifications v1.0, Operations Management"
    }
    with open(idx_wf, "w", encoding="utf-8") as f:
        json.dump(obj_wf, f, indent=2)
    indexes_created.append(idx_wf)

    print(f"  [OK] Generated {len(indexes_created)} companion JSON indexes.")
    return indexes_created


def main():
    print("=" * 80)
    print("SAVEETHA MEDICAL COLLEGE AND HOSPITAL (SMCH)")
    print("SYNTHETIC MASTER WORKBOOK & WORKFLOW ASSETS BUILDER")
    print("=" * 80)

    print("\n[1/3] Generating Master Synthetic Workbook (5 sheets) ...")
    build_master_workbook()

    print("\n[2/3] Generating Machine-Readable Workflow State Machines JSON ...")
    build_workflow_definitions_json()

    print("\n[3/3] Generating Companion JSON Indexes in knowledge_base/index/ ...")
    build_companion_indexes()

    print("\n" + "=" * 80)
    print("BUILD COMPLETE: All requested operational assets generated successfully.")
    print("=" * 80)

if __name__ == "__main__":
    main()
