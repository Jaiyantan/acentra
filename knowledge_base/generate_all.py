"""
knowledge_base/generate_all.py
Saveetha Medical College and Hospital (SMCH) Operations Knowledge Base Generator.

Generates 30 synthetic hospital documents for each category:
1. 30 SOP Word Documents (.docx) in knowledge_base/sops/
2. 30 Knowledge Article Word Documents (.docx) in knowledge_base/knowledge_articles/
3. 30 PDF Forms (.pdf) in knowledge_base/forms/
4. 30 Report Templates (.xlsx) in knowledge_base/reports/
5. 30 Hospital Policy Documents (.docx) in knowledge_base/policies/
6. Escalation Routing Matrix (.xlsx) in knowledge_base/routing_matrix/
7. 3 Core JSON Data Files in knowledge_base/ (support_directory.json, field_definitions.json, operations_requests.json)
8. Companion JSON Index Files for all generated documents in knowledge_base/index/ (for Supermemory ingestion)

Strictly pure synthetic document generation. Zero AI, zero LLM, zero agent logic.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Configure UTF-8 stdout if possible
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Document formatting libraries
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent
SOPS_DIR = BASE_DIR / "sops"
ARTICLES_DIR = BASE_DIR / "knowledge_articles"
FORMS_DIR = BASE_DIR / "forms"
REPORTS_DIR = BASE_DIR / "reports"
POLICIES_DIR = BASE_DIR / "policies"
ROUTING_DIR = BASE_DIR / "routing_matrix"
INDEX_DIR = BASE_DIR / "index"

for d in [SOPS_DIR, ARTICLES_DIR, FORMS_DIR, REPORTS_DIR, POLICIES_DIR, ROUTING_DIR, INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HOSPITAL_NAME = "Saveetha Medical College and Hospital (SMCH)"

def add_docx_header_footer(doc, doc_id, doc_title):
    section = doc.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    header = section.header
    hp = header.paragraphs[0]
    hp.text = f"{HOSPITAL_NAME}  |  {doc_id}"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.style.font.name = "Arial"
    hp.style.font.size = Pt(8.5)
    hp.style.font.color.rgb = RGBColor(100, 116, 139)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.text = f"Confidential & Proprietary — {HOSPITAL_NAME}  |  Page 1"
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.style.font.name = "Arial"
    fp.style.font.size = Pt(8)
    fp.style.font.color.rgb = RGBColor(148, 163, 184)

# =========================================================================
# 1. 30 STANDARD OPERATING PROCEDURES (SOPs)
# =========================================================================
SOPS_LIST = [
    ("SOP-ADM-001", "Patient_Admission", "Patient Admission Procedure", "Admission and Discharge", "3.1", "2026-01-10", ["front_office", "admission", "nurse", "doctor"], "Admission Form, Consent Form, Insurance Form", "Standardize inpatient admission workflow and bed allocation.", 8),
    ("SOP-DIS-001", "Patient_Discharge", "Patient Discharge Procedure", "Admission and Discharge", "2.4", "2026-01-15", ["discharge", "billing", "pharmacist", "nurse", "doctor"], "Discharge Summary, Billing Document, Prescription", "Execute 4-point discharge clearance and safe clinical handover.", 7),
    ("SOP-INS-001", "Insurance_Preauthorisation", "Insurance Pre-Authorisation Procedure", "Insurance and TPA", "4.0", "2026-02-01", ["insurance_tpa", "admission", "billing"], "Insurance Preauth Form, Clinical Justification Letter", "Ensure timely submission and tracking of cashless pre-authorizations.", 6),
    ("SOP-LAB-001", "Lab_Order_Processing", "Laboratory Order Processing Procedure", "Laboratory Operations", "2.0", "2026-01-20", ["doctor", "nurse", "lab_tech"], "Investigation Report, Barcode Requisition", "Prompt, error-free accessioning and panic value reporting.", 6),
    ("SOP-RAD-001", "Radiology_Request", "Radiology Request and Reporting Procedure", "Radiology Operations", "1.8", "2026-01-25", ["doctor", "rad_tech"], "Investigation Report, Referral Form", "Safe diagnostic imaging acquisition and urgent PACS reporting.", 5),
    ("SOP-BLD-001", "Blood_Request", "Blood Request and Transfusion Procedure", "Blood Bank", "3.2", "2026-01-12", ["doctor", "nurse", "lab_tech"], "Blood Requisition Form, Crossmatch Report", "Compatible blood component testing and dual-nurse verification.", 7),
    ("SOP-INC-001", "Incident_Reporting", "Incident Reporting and Management Procedure", "Quality and Patient Safety", "2.1", "2026-02-05", ["all_staff"], "Incident Report Form", "Non-punitive adverse event reporting within 1 hour.", 5),
    ("SOP-BIL-001", "Billing_Finalisation", "Billing Finalisation Procedure", "Billing", "3.0", "2026-01-08", ["billing", "insurance_tpa"], "Billing Document, Insurance Preauth Form", "Consolidated inpatient charge auditing and tax invoice generation.", 6),
    ("SOP-TRF-001", "Bed_Transfer", "Patient Bed and Ward Transfer Procedure", "Admission and Discharge", "1.5", "2026-02-10", ["admission", "nurse", "doctor"], "Transfer Form, SBAR Handover Note", "Intra-hospital patient transfers and HIS bed state tracking.", 5),
    ("SOP-MLC-001", "MLC_Registration", "Medico-Legal Case Registration Procedure", "Medical Records (MRD / HIM)", "2.2", "2026-01-30", ["front_office", "doctor", "medical_records"], "MLC Registration Form, Police Intimation Slip", "Statutory police intimation within 1 hour for forensic trauma cases.", 5),
    ("SOP-EMG-001", "Emergency_Triage_ESI", "Emergency Department Triage and Resuscitation", "Emergency Department", "3.0", "2026-01-05", ["doctor", "nurse", "triage_officer"], "Triage Tag, Emergency Card", "Categorize arrivals into ESI Levels 1 to 5 and direct to resuscitation bay.", 6),
    ("SOP-ICU-001", "ICU_Admission_StepDown", "ICU Clinical Admission and Step-Down Protocol", "Intensive Care Unit (ICU)", "2.5", "2026-01-18", ["doctor", "nurse", "case_management"], "Critical Care Assessment, Step-Down Note", "Prioritize hemodynamic beds and safe step-down to wards.", 6),
    ("SOP-OT-001", "Surgical_Safety_Checklist", "Operation Theatre Surgical Safety Protocol", "Operation Theatre", "4.1", "2026-01-22", ["doctor", "nurse", "anesthetist"], "WHO Surgical Safety Checklist, Consent", "Enforce Sign-In, Time-Out, and Sign-Out verification.", 7),
    ("SOP-PHM-001", "High_Alert_Medication", "High-Alert and LASA Medication Dispensing", "Pharmacy", "3.3", "2026-01-14", ["pharmacist", "nurse"], "Dual Sign-off Sheet, Narcotic Register", "Safeguard insulin, potassium, anticoagulants, and chemotherapeutics.", 6),
    ("SOP-PHM-002", "Narcotic_Drug_Control", "Schedule X and Narcotic Drug Control", "Pharmacy", "2.8", "2026-02-02", ["pharmacist", "doctor", "nurse"], "Narcotic Requisition Slip, Register Book", "Statutory double-lock storage and physical ampoule return verification.", 5),
    ("SOP-IPC-001", "Hospital_Acquired_Infection", "Infection Control and Bundle Compliance", "Quality and Patient Safety", "2.0", "2026-01-19", ["nurse", "doctor", "infection_officer"], "Infection Surveillance Chart, Bundle Audit", "Central line and catheter associated infection prevention bundles.", 6),
    ("SOP-BIO-001", "Biomedical_Breakdown", "Biomedical Equipment Defect and Breakdown", "Biomedical Engineering", "1.9", "2026-01-11", ["nurse", "biomedical_engineer"], "BME Maintenance Form, Work Order", "Rapid response within 15 minutes for critical life support equipment.", 5),
    ("SOP-MRD-001", "Death_Summary_Certification", "Inpatient Death Summary and Handover", "Medical Records (MRD / HIM)", "2.3", "2026-01-28", ["doctor", "nurse", "medical_records"], "Death Certificate, Mortuary Handover Slip", "Clinical death certification and dignified mortuary handover.", 5),
    ("SOP-FAC-001", "Terminal_Bed_Sanitization", "Terminal Bed Cleaning and Room Sanitization", "Facility Management", "1.7", "2026-02-04", ["housekeeping", "nurse"], "Bed Turnaround Checklist, Sanitization Slip", "Ultraviolet surface disinfection and 45-minute bed turnaround.", 5),
    ("SOP-DIA-001", "Hemodialysis_Session", "Hemodialysis Session Initiation and Monitoring", "Nephrology and Dialysis", "2.6", "2026-01-16", ["doctor", "dialysis_tech", "nurse"], "Dialysis Flow Sheet, Machine Log", "Dialyzer priming, vital stability monitoring, and heparinization.", 7),
    ("SOP-CAR-001", "Code_Blue_Resuscitation", "Cardiopulmonary Arrest Code Blue Response", "Cardiology", "3.5", "2026-01-08", ["doctor", "nurse", "icu_team"], "Code Blue Log Sheet, Crash Cart Audit", "Mobilize crash cart and emergency airway team under 3 minutes.", 6),
    ("SOP-CSS-001", "Sterilization_Autoclave", "CSSD Instrument Sterilization Tracking", "Operation Theatre", "2.1", "2026-01-26", ["cssd_tech", "ot_nurse"], "Autoclave Indicator Slip, Batch Register", "Biological spore indicator validation and barcode pack tracking.", 6),
    ("SOP-NUR-001", "Shift_Handover_SBAR", "Nursing Shift Changeover and SBAR Handover", "Nursing Administration", "3.0", "2026-01-09", ["nurse"], "Nursing Kardex, Vitals Flow Sheet", "Bedside verbal SBAR handover between incoming and outgoing shifts.", 5),
    ("SOP-AMB-001", "Ambulance_Emergency_Dispatch", "Emergency Ambulance Dispatch and Fleet Ops", "Emergency Department", "2.4", "2026-01-31", ["driver", "paramedic", "emergency_team"], "Ambulance Trip Sheet, Equipment Log", "Dispatch ALS ambulance within 5 minutes of emergency call receipt.", 5),
    ("SOP-DIE-001", "Therapeutic_Dietary", "Therapeutic and Inpatient Dietary Fulfillment", "Facility Management", "1.6", "2026-02-06", ["dietitian", "pantry_staff"], "Diet Prescription Slip, Meal Tag", "Standardize diabetic, renal, low-salt, and enteral nutrition trays.", 5),
    ("SOP-HR-001", "Clinical_Privileging", "Medical Staff Credentialing and Privileging", "Human Resources and Administration", "2.2", "2026-01-07", ["medical_superintendent", "hr_officer"], "Credentialing Dossier, Privilege Matrix", "Verify medical council registration and operative surgical scopes.", 5),
    ("SOP-SEC-001", "Code_Pink_Infant_Security", "Infant and Pediatric Abduction Code Pink", "Quality and Patient Safety", "2.0", "2026-01-21", ["security", "nurse", "front_office"], "Code Pink Incident Form, Security Log", "Immediate perimeter lockdown and CCTV inspection on alarm trigger.", 5),
    ("SOP-PMJ-001", "PMJAY_Claim_Enhancement", "PMJAY Cashless Enhancement Requisition", "Insurance and TPA", "3.2", "2026-02-03", ["insurance_tpa", "billing"], "NHA Enhancement Form, Clinical Note", "Submit interim package enhancements to state nodal agency within 24h.", 5),
    ("SOP-END-001", "Endoscopy_Suite_Prep", "Endoscopy and Colonoscopy Procedure Protocol", "Gastroenterology", "1.8", "2026-01-27", ["doctor", "endoscopy_nurse"], "Endoscopy Consent, Scope Wash Log", "Patient conscious sedation monitoring and enzymatic scope disinfection.", 6),
    ("SOP-RES-001", "Restraint_Monitoring", "Physical and Chemical Restraint Monitoring", "Psychiatry", "2.1", "2026-01-29", ["doctor", "nurse"], "Restraint Order Form, 2-Hour Flow Sheet", "Doctor order re-authorization every 12 hours and 2-hour limb checks.", 5)
]

def generate_sops():
    results = []
    for item in SOPS_LIST:
        doc_id, slug, title, dept, ver, app_date, roles, req_docs, purpose, num_steps = item
        filename = f"{doc_id}_{slug}.docx"
        filepath = SOPS_DIR / filename
        doc = docx.Document()
        add_docx_header_footer(doc, doc_id, title)

        p_title = doc.add_paragraph()
        run_title = p_title.add_run(title)
        run_title.font.name = "Arial"
        run_title.font.size = Pt(17)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(15, 23, 42)

        doc.add_paragraph(f"Standard Operating Procedure  •  {HOSPITAL_NAME}").italic = True

        table = doc.add_table(rows=5, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_rows = [
            ("SOP Identifier", doc_id),
            ("Department", dept),
            ("Version & Status", f"Version {ver} (Approved: {app_date})"),
            ("Applicable Roles", ", ".join(roles)),
            ("Required Documents", req_docs)
        ]
        for i, (k, v) in enumerate(meta_rows):
            cell_k = table.cell(i, 0)
            cell_v = table.cell(i, 1)
            cell_k.text = k
            cell_k.paragraphs[0].runs[0].font.bold = True
            cell_v.text = v

        doc.add_paragraph()
        doc.add_heading("1. Purpose", level=2)
        doc.add_paragraph(purpose)

        doc.add_heading("2. Scope", level=2)
        doc.add_paragraph(f"Applies to all relevant personnel and operational units in {dept} at {HOSPITAL_NAME}.")

        doc.add_heading("3. Required Documents", level=2)
        for rd in req_docs.split(", "):
            doc.add_paragraph(f"• {rd}")

        doc.add_heading("4. Procedure Steps", level=2)
        steps_text = []
        for s in range(1, num_steps + 1):
            st = f"Step {s}: Execute phase {s} of {title} in full compliance with {dept} hospital policy, verifying patient UHID and audit stamps."
            doc.add_paragraph(st)
            steps_text.append(st)

        doc.add_heading("5. Common Blockers", level=2)
        b1 = f"- [BLOCKER] System connectivity or missing documentation in {dept}."
        b2 = "- [BLOCKER] Bed, reagent, medication, or personnel resource constraints during peak hours."
        doc.add_paragraph(b1)
        doc.add_paragraph(b2)

        doc.add_heading("6. Escalation Conditions", level=2)
        e1 = "- [ESCALATION] Delays exceeding 2 hours must be escalated to the Operations Manager."
        e2 = "- [ESCALATION] Clinical complications or safety hazards must be escalated immediately to Clinical Review."
        doc.add_paragraph(e1)
        doc.add_paragraph(e2)

        doc.save(str(filepath))
        results.append((filepath, {
            "file_id": doc_id + "_" + slug,
            "title": title,
            "doc_id": doc_id,
            "department": dept,
            "version": ver,
            "approved_date": app_date,
            "roles": roles,
            "purpose": purpose,
            "req_docs": req_docs,
            "steps": steps_text,
            "blockers": [b1, b2],
            "escalations": [e1, e2],
            "tags": ["sop", doc_id.lower(), dept.lower(), slug.replace('_', ' ').lower(), "smch"]
        }))
    return results

# =========================================================================
# 2. 30 KNOWLEDGE ARTICLES
# =========================================================================
ARTICLES_LIST = [
    ("KA-001", "HIS_Patient_Registration", "How to Register a New Patient in the HIS", "HIS", "Front Office and Registration", "1.4", ["front_office", "admission"]),
    ("KA-002", "HIS_Bed_Allocation", "How to Allocate a Bed to an Admitted Patient", "HIS", "Admission and Discharge", "2.0", ["admission", "nurse"]),
    ("KA-003", "LIS_Lab_Order", "How to Submit a Lab Order in the LIS", "LIS", "Laboratory Operations", "1.8", ["doctor", "nurse", "lab_tech"]),
    ("KA-004", "RIS_Radiology_Request", "How to Submit a Radiology Request", "RIS", "Radiology Operations", "1.7", ["doctor", "rad_tech"]),
    ("KA-005", "Billing_Final_Bill", "How to Generate a Final Bill at Discharge", "Billing System", "Billing", "2.3", ["billing", "discharge"]),
    ("KA-006", "Insurance_Preauth_TPA", "How to Submit a Pre-Authorisation Request to TPA", "TPA Portal", "Insurance and TPA", "3.0", ["insurance_tpa", "billing"]),
    ("KA-007", "Incident_Report_Quality", "How to Fill and Submit an Incident Report", "Quality Portal", "Quality and Patient Safety", "2.2", ["all_staff"]),
    ("KA-008", "MRD_Case_File_Request", "How to Request a Physical Patient Case File from Medical Records", "MRD Archive", "Medical Records (MRD / HIM)", "1.5", ["doctor", "medical_records"]),
    ("KA-009", "Helpdesk_IT_Ticket", "How to Raise an IT Support Ticket for HIS or System Issues", "ITSM Helpdesk", "IT and HIS Support", "2.5", ["all_staff"]),
    ("KA-010", "PMJAY_NHA_Claim", "How to Submit a PMJAY Claim Through the NHA Portal", "NHA Portal", "Insurance and TPA", "3.1", ["insurance_tpa", "billing"]),
    ("KA-011", "EMR_Doctor_Clinical_Notes", "How to Document Daily Progress Notes in the EMR", "EMR System", "Clinical Services", "2.1", ["doctor"]),
    ("KA-012", "Nursing_Vitals_Entry_Chart", "How to Record Inpatient Vitals and Fluid Balance in HIS", "HIS Nursing", "Nursing Administration", "1.9", ["nurse"]),
    ("KA-013", "Pharmacy_ePrescription_Dispense", "How to Process and Dispense Digital Inpatient Prescriptions", "Pharmacy System", "Pharmacy", "2.4", ["pharmacist", "nurse"]),
    ("KA-014", "Blood_Bank_Crossmatch_Reserve", "How to Reserve Crossmatched Blood Units in BBIS", "Blood Bank System", "Blood Bank", "2.0", ["lab_tech", "nurse"]),
    ("KA-015", "OT_Surgery_Slot_Booking", "How to Book an Operating Theatre Suite Slot", "OT Scheduling", "Operation Theatre", "1.6", ["doctor", "nurse"]),
    ("KA-016", "Dialysis_Machine_Parameter_Log", "How to Log Dialysis Ultrafiltration and Dialysate Flow", "Dialysis System", "Nephrology and Dialysis", "2.2", ["dialysis_tech", "doctor"]),
    ("KA-017", "Dietary_Meal_Requisition", "How to Requisition Therapeutic Diets in Pantry Portal", "Dietary Portal", "Facility Management", "1.5", ["nurse", "dietitian"]),
    ("KA-018", "Biomedical_Asset_Maintenance_Log", "How to Log Equipment Preventive Maintenance in BME Portal", "BME Portal", "Biomedical Engineering", "2.3", ["biomedical_engineer"]),
    ("KA-019", "PACS_DICOM_Viewer_Troubleshoot", "How to Troubleshoot High-Resolution PACS DICOM Viewing", "PACS Viewer", "Radiology Operations", "1.8", ["rad_tech", "it_support"]),
    ("KA-020", "Housekeeping_Bed_Turnaround_Alert", "How to Dispatch Bed Turnover Requests to Housekeeping", "Housekeeping App", "Facility Management", "1.4", ["nurse", "housekeeping"]),
    ("KA-021", "Ambulance_GPS_Tracking_System", "How to Monitor and Dispatch Ambulances via Fleet GPS", "Fleet Dispatch", "Emergency Department", "2.0", ["emergency_team", "driver"]),
    ("KA-022", "CSSD_Sterile_Tray_Barcode_Scan", "How to Scan and Track Surgical Instrument Trays in CSSD", "CSSD System", "Operation Theatre", "1.7", ["cssd_tech", "nurse"]),
    ("KA-023", "Biometric_Aadhaar_eKYC_Verify", "How to Execute Biometric Aadhaar Verification at OPD Counter", "Registration Terminal", "Front Office and Registration", "2.2", ["front_office"]),
    ("KA-024", "Cashless_Enhancement_Query_Reply", "How to Upload Medical Documents for Interim Insurance Enhancement", "TPA Portal", "Insurance and TPA", "2.7", ["insurance_tpa"]),
    ("KA-025", "Lab_Panic_Value_SMS_Alert", "How to Broadcast Automated SMS Panic Alerts for Critical Labs", "LIS Engine", "Laboratory Operations", "2.1", ["lab_tech", "quality"]),
    ("KA-026", "Doctor_Duty_Roster_Management", "How to Update Consultant On-Call Roster in Hospital Portal", "Roster Portal", "Human Resources and Administration", "1.6", ["operations_manager", "hr_officer"]),
    ("KA-027", "Medication_Return_Credit_Reconcile", "How to Process Unused Inpatient Drug Return Credits", "Pharmacy System", "Pharmacy", "2.0", ["pharmacist", "billing"]),
    ("KA-028", "Discharge_Summary_Digital_Signoff", "How to Complete Digital Sign-Off for Typed Discharge Summaries", "EMR Engine", "Clinical Services", "2.5", ["doctor"]),
    ("KA-029", "Visitor_Gate_Pass_Barcode_Print", "How to Issue and Scan Barcoded Inpatient Attender Passes", "Security Terminal", "Front Office and Registration", "1.3", ["front_office", "security"]),
    ("KA-030", "Chemotherapy_Daycare_Schedule", "How to Schedule Oncology Day Care Chemotherapy Sessions", "Oncology Portal", "Oncology", "2.2", ["doctor", "nurse"])
]

def generate_knowledge_articles():
    results = []
    for item in ARTICLES_LIST:
        doc_id, slug, title, system, dept, ver, roles = item
        filename = f"{doc_id}_{slug}.docx"
        filepath = ARTICLES_DIR / filename
        doc = docx.Document()
        add_docx_header_footer(doc, doc_id, title)

        p_title = doc.add_paragraph()
        run_title = p_title.add_run(title)
        run_title.font.name = "Arial"
        run_title.font.size = Pt(17)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(30, 41, 59)

        doc.add_paragraph(f"Standard Operating Guide  •  {HOSPITAL_NAME}  •  System: {system}").italic = True

        table = doc.add_table(rows=4, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_rows = [
            ("Article Identifier", doc_id),
            ("System Covered", system),
            ("Responsible Department", dept),
            ("Version & Roles", f"v{ver}  •  {', '.join(roles)}")
        ]
        for i, (k, v) in enumerate(meta_rows):
            cell_k = table.cell(i, 0)
            cell_v = table.cell(i, 1)
            cell_k.text = k
            cell_k.paragraphs[0].runs[0].font.bold = True
            cell_v.text = v

        doc.add_paragraph()
        doc.add_heading("1. Overview & Objective", level=2)
        overview_text = f"This comprehensive operating guide details how hospital personnel should interact with the {system} module to execute {title.lower()} safely and reliably."
        doc.add_paragraph(overview_text)

        doc.add_heading("2. Step-by-Step Execution Guide", level=2)
        steps_text = [
            f"Step 1: Open the {system} client terminal on any networked SMCH workstation and log in with role credentials.",
            "Step 2: Enter the patient's unique UHID or Case Number to load active records.",
            f"Step 3: Access the designated submenu corresponding to {title} and verify current patient status.",
            "Step 4: Input all required clinical or administrative parameters, ensuring mandatory fields are validated.",
            "Step 5: Verify preview confirmation modal and click 'Submit' to persist changes to the database.",
            "Step 6: Print barcode, acknowledgement chit, or receipt as required by hospital compliance."
        ]
        for s in steps_text:
            doc.add_paragraph(s)

        doc.add_heading("3. Common Errors and Recommended Fixes", level=2)
        err1 = "- [ISSUE & FIX] Connection timeout: Verify LAN cable connection or contact IT Helpdesk."
        err2 = "- [ISSUE & FIX] Permission Denied: Ensure user account has the assigned role in staff master permissions."
        doc.add_paragraph(err1)
        doc.add_paragraph(err2)

        doc.add_heading("4. Who to Contact for Support", level=2)
        contact_text = f"Contact {dept} coordinator or IT Operations Support at Extension 1033 (Email: it@smch.in)."
        doc.add_paragraph(contact_text)

        doc.save(str(filepath))
        results.append((filepath, {
            "file_id": doc_id + "_" + slug,
            "title": title,
            "doc_id": doc_id,
            "system": system,
            "department": dept,
            "version": ver,
            "roles": roles,
            "overview": overview_text,
            "steps": steps_text,
            "errors": [err1, err2],
            "contact": contact_text,
            "tags": ["knowledge article", doc_id.lower(), system.lower(), dept.lower(), "smch", "guide"]
        }))
    return results

# =========================================================================
# 3. 30 PDF FORMS
# =========================================================================
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(54, 755, f"{HOSPITAL_NAME}  |  Official Clinical Form")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 747, 558, 747)
        self.line(54, 45, 558, 45)
        self.drawString(54, 34, f"{HOSPITAL_NAME} | Confidential & Medico-Legal Document")
        self.drawRightString(558, 34, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

FORMS_LIST = [
    ("Registration_Form_v3", "Patient Registration Form", "FORM-REG-03", "v3.0", "Patient Full Name", "Age & Gender", "Contact Number", "Residential Address", "Emergency Contact", "Aadhaar Card No"),
    ("Admission_Form_v2", "Inpatient Admission Form", "FORM-ADM-02", "v2.0", "Patient UHID", "Admitting Doctor", "Allocated Ward", "Bed Number", "Provisional Diagnosis", "Insurance Policy No"),
    ("Consent_Form_General", "General Admission & Treatment Consent", "FORM-CON-01", "v1.5", "Patient UHID", "Treating Consultant", "Procedure Name", "Risk Explanation (Y/N)", "Patient Signature", "Witness Signature"),
    ("Incident_Report_Form", "Patient Safety Incident & Adverse Event Form", "FORM-INC-02", "v2.1", "Incident ID", "Department / Ward", "Incident Category", "Severity (L/M/H/C)", "Immediate Action", "Reporter Staff ID"),
    ("Referral_Form", "Inter-Departmental Clinical Referral Form", "FORM-REF-01", "v1.2", "Patient UHID", "Referring Doctor", "Referred Specialty", "Urgency (Routine/STAT)", "Clinical Summary", "Specialist Notes"),
    ("Transfer_Form", "Patient Bed and Ward Transfer Form", "FORM-TRF-01", "v1.3", "Patient UHID", "Current Bed ID", "Destination Bed ID", "Transfer Type", "Vitals at Handover", "Nurse Signature"),
    ("Insurance_Preauth_Form", "Cashless Insurance Pre-Authorization Requisition", "FORM-INS-04", "v4.0", "Patient UHID", "Policy Number", "TPA Name", "Estimated Cost (Rs)", "Preauth Sanction", "TPA Docket ID"),
    ("Discharge_Checklist_Form", "Four-Point Discharge Clearance Checklist", "FORM-DIS-02", "v2.4", "Patient UHID", "Admission ID", "Doctor Order (Y/N)", "Billing Cleared (Y/N)", "Pharmacy Cleared", "Nursing Cleared"),
    ("Blood_Request_Form", "Blood Component Requisition & Transfusion Record", "FORM-BLD-03", "v3.2", "Patient UHID", "Blood Group / Rh", "Component (PRBC/FFP)", "Units Required", "Crossmatch Bag No", "Transfusion Nurse"),
    ("MLC_Registration_Form", "Medico-Legal Case (MLC) Registration Record", "FORM-MLC-02", "v2.2", "MLC Number", "Patient UHID", "Nature of Case", "Police Station Name", "Time Intimated", "Doctor on Duty"),
    ("Surgical_Safety_Checklist_Form", "WHO Surgical Safety Sign-In & Time-Out", "FORM-SUR-01", "v2.0", "Patient UHID", "Surgical Procedure", "Site Marked (Y/N)", "Sign-In Verified", "Time-Out Confirmed", "Sign-Out Swab Count"),
    ("High_Risk_Informed_Consent_Form", "High-Risk Surgical / Anesthesia Consent", "FORM-HRC-01", "v3.0", "Patient UHID", "Surgery Name", "High Risk Factors", "Blood Loss Risk", "Surgeon Signature", "Anesthetist Seal"),
    ("Anesthesia_PreOp_Evaluation_Form", "Pre-Anesthesia Assessment & Airway Evaluation", "FORM-ANE-01", "v2.5", "Patient UHID", "Mallampati Class", "ASA Physical Status", "NPO Hours Verified", "Allergy History", "Anesthetist ID"),
    ("DAMA_LAMA_Discharge_Refusal_Form", "Discharge Against Medical Advice (DAMA/LAMA)", "FORM-DAM-01", "v2.1", "Patient UHID", "Clinical Warnings", "Refusal Rationale", "Complication Risks", "Attender Signature", "Witness Name"),
    ("Code_Blue_Resuscitation_Record_Form", "Cardiopulmonary Arrest Code Blue Flowsheet", "FORM-CBL-01", "v2.8", "Patient UHID", "Arrest Rhythm", "CPR Start Time", "Defibrillation Joules", "Epinephrine Doses", "ROSC Achieved (Y/N)"),
    ("Death_Intimation_Certification_Form", "Hospital Death Intimation & Summary Record", "FORM-DTH-01", "v1.8", "Patient UHID", "Time of Death", "Immediate Cause", "Antecedent Cause", "Police Case (Y/N)", "Mortuary Release"),
    ("Narcotic_Drug_Requisition_Form", "Schedule X Narcotic Drug Issue Voucher", "FORM-NAR-01", "v3.1", "Patient UHID", "Drug Name & Dose", "Prescribing Doctor", "Administering Nurse", "Empty Ampoule Ret", "Pharmacist Sign"),
    ("Restraint_Order_Monitoring_Form", "Physical & Chemical Restraint Order Chart", "FORM-RST-01", "v1.9", "Patient UHID", "Clinical Indication", "Restraint Type", "Circulation Check", "Doctor Re-eval", "Nurse Check 2h"),
    ("Dialysis_Session_Flow_Sheet", "Hemodialysis Pre- & Post-Session Flow Sheet", "FORM-DIA-01", "v2.2", "Patient UHID", "Pre-Dialysis Weight", "Post-Dialysis Weight", "Ultrafiltration Goal", "Heparin Units", "Vascular Access"),
    ("Chemotherapy_Administration_Chart", "Cytotoxic Chemotherapy Administration Protocol", "FORM-ONC-01", "v2.4", "Patient UHID", "Chemo Regimen", "BSA Calculation", "Pre-Medications Given", "Extravasation Check", "Oncology Nurse"),
    ("Blood_Transfusion_Reaction_Form", "Adverse Transfusion Reaction Investigation", "FORM-BTR-01", "v1.7", "Patient UHID", "Bag Number", "Symptoms Observed", "Stop Time", "Urine Free Hb", "Pathologist Report"),
    ("Ambulance_Emergency_Trip_Sheet", "ALS Ambulance Trip & Pre-Hospital Care Record", "FORM-AMB-01", "v2.0", "Patient UHID / Name", "Dispatch Time", "On-Scene Vitals", "Interventions Given", "Arrival Hospital", "Paramedic Sign"),
    ("Patient_Dietary_Assessment_Form", "Clinical Nutrition & Dietary Requisition", "FORM-DIE-01", "v1.5", "Patient UHID", "Diet Category", "Calorie Requirement", "Food Allergies", "Feeding Tube (Y/N)", "Dietitian ID"),
    ("Biomedical_Defect_Requisition_Form", "Biomedical Equipment Fault & Repair Slip", "FORM-BME-01", "v1.6", "Device Asset Tag", "Ward / ICU Bed", "Defect Description", "Safety Hazard (Y/N)", "Replacement Given", "Engineer Status"),
    ("CSSD_Sterilization_Batch_Record", "CSSD Autoclave Biological Indicator Log", "FORM-CSS-01", "v2.0", "Autoclave Chamber", "Cycle Number", "Biological Spore Pass", "Chemical Integrator", "Tray Barcode List", "CSSD Supervisor"),
    ("Pediatric_Vaccination_Record_Form", "Pediatric Immunization & Growth Tracker", "FORM-PED-01", "v1.8", "Patient UHID", "Child Name & DOB", "Vaccine Administered", "Batch & Expiry", "Adverse Event (Y/N)", "Pediatrician Sign"),
    ("ICU_Central_Line_Insertion_Bundle", "Central Venous Catheter Insertion Checklist", "FORM-CVC-01", "v2.3", "Patient UHID", "Insertion Site", "Maximal Barrier Used", "Chlorhexidine Prep", "Post-Xray Confirmed", "Operator Doctor"),
    ("MRD_Archived_File_Requisition_Slip", "Medical Records Physical Archive Requisition", "FORM-MRD-01", "v1.4", "Patient UHID", "Previous Admission", "Requisition Purpose", "Requesting Doctor", "Token Number", "Return Due Date"),
    ("Staff_Needlestick_Injury_Report", "Occupational Needlestick / Sharps Exposure", "FORM-NSI-01", "v2.1", "Staff ID & Name", "Exposure Source UHID", "Device Involved", "First Aid Administered", "HIV/HBV Source Stat", "Infection Lead"),
    ("Patient_Attender_Feedback_Form", "Inpatient Discharge Experience & Feedback", "FORM-CSAT-01", "v1.5", "Patient UHID", "Nursing Care Rating", "Doctor Care Rating", "Cleanliness Rating", "Food Quality Rating", "Overall Score")
]

def generate_forms():
    results = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FormTitle", parent=styles["Heading1"], fontSize=14, leading=17,
        textColor=colors.HexColor("#0f172a"), alignment=1, spaceAfter=3
    )
    sub_style = ParagraphStyle(
        "FormSub", parent=styles["Normal"], fontSize=8.5, leading=11,
        textColor=colors.HexColor("#64748b"), alignment=1, spaceAfter=12
    )
    cell_h_style = ParagraphStyle(
        "CellH", parent=styles["Normal"], fontSize=8, leading=10,
        textColor=colors.HexColor("#475569"), fontName="Helvetica-Bold"
    )

    for item in FORMS_LIST:
        filename_base, title, doc_id, ver, *fields = item
        filename = f"{filename_base}.pdf"
        filepath = FORMS_DIR / filename

        doc = SimpleDocTemplate(str(filepath), pagesize=A4, leftMargin=40, rightMargin=40, topMargin=55, bottomMargin=55)
        story = []
        story.append(Paragraph(title.upper(), title_style))
        story.append(Paragraph(f"{HOSPITAL_NAME}  •  Form Code: {doc_id}  •  Version: {ver}", sub_style))

        # Build table with field labels
        table_data = []
        for i in range(0, len(fields), 3):
            chunk = fields[i:i+3]
            row_cells = []
            for col_text in chunk:
                p = Paragraph(f"{col_text}:<br/><font color='#94a3b8'>___________________________________</font>", cell_h_style)
                row_cells.append(p)
            while len(row_cells) < 3:
                row_cells.append(Paragraph("", cell_h_style))
            table_data.append(row_cells)

        col_w = 515 / 3
        t = Table(table_data, colWidths=[col_w, col_w, col_w])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        doc.build(story, canvasmaker=NumberedCanvas)

        results.append((filepath, {
            "file_id": filename_base,
            "title": title,
            "doc_id": doc_id,
            "version": ver,
            "fields": fields,
            "tags": ["form", "pdf", doc_id.lower(), "template", "smch"]
        }))
    return results

# =========================================================================
# 4. 30 EXCEL REPORTS
# =========================================================================
HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FFFFFF")
ROW_FONT = Font(name="Arial", size=9)
ALT_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
BORDER_THIN = Border(
    left=Side(style='thin', color='CBD5E1'), right=Side(style='thin', color='CBD5E1'),
    top=Side(style='thin', color='CBD5E1'), bottom=Side(style='thin', color='CBD5E1')
)

def format_excel_sheet(ws, title, columns, data):
    ws.views.sheetView[0].showGridLines = True
    ws.merge_cells("A1:G1")
    ws["A1"] = f"{HOSPITAL_NAME}  |  {title}"
    ws["A1"].font = Font(name="Arial", size=12, bold=True, color="1E3A8A")
    ws["A1"].alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 25

    ws.row_dimensions[3].height = 22
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=3, column=col_idx, value=col_name)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER_THIN

    for row_idx, row_values in enumerate(data, 4):
        ws.row_dimensions[row_idx].height = 18
        for col_idx, val in enumerate(row_values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = ROW_FONT
            cell.border = BORDER_THIN
            if row_idx % 2 == 0:
                cell.fill = ALT_FILL
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row >= 3 and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

REPORTS_METADATA = [
    ("Patient_Census_Report_Template", "Daily Inpatient & Outpatient Census", ["Date", "Total Registered", "Total Admitted", "Discharged Today", "OPD Count", "Emergency Count", "ICU Count"]),
    ("Bed_Occupancy_Report_Template", "Ward Bed Occupancy Breakdown", ["Ward", "Total Beds", "Occupied", "Available", "Maintenance", "Occupancy %"]),
    ("Insurance_Claim_Status_Report_Template", "Cashless Insurance Claims Registry", ["Claim ID", "Patient UHID", "Patient Name", "Insurer", "TPA", "Claim Status", "Claim Amount"]),
    ("Discharge_Clearance_Status_Report_Template", "Four-Point Discharge Clearance Audit", ["Patient UHID", "Patient Name", "Ward", "Billing Cleared", "Pharmacy Cleared", "Nursing Cleared", "Blocker"]),
    ("Critical_Lab_Alerts_Report_Template", "Panic Lab Value Alert Audit", ["Lab Order ID", "Patient UHID", "Test Name", "Result Value", "Critical Flag", "Alert Sent", "Doctor Notified"]),
    ("Daily_Billing_Collection_Report_Template", "Daily Revenue & Mode-Wise Collections", ["Date", "Cash Collected", "Card Collected", "Insurance Settled", "PMJAY Settled", "Total"]),
    ("Ticket_Resolution_Report_Template", "Operational Ticket Resolution Registry", ["Ticket ID", "Team", "Ticket Type", "Priority", "Status", "SLA Hours", "Resolution Hours"]),
    ("Incident_Summary_Report_Template", "Patient Safety Adverse Event Summary", ["Incident ID", "Date", "Department", "Incident Type", "Severity", "Patient Involved", "Status"]),
    ("Emergency_Department_TAT_Report", "Emergency Triage Door-to-Doctor TAT", ["Date", "Total Triage Arrivals", "ESI Level 1 (mins)", "ESI Level 2 (mins)", "Admission Conversion %"]),
    ("Operation_Theatre_Utilization_Report", "Operating Suite Utilization Hours", ["OT Suite ID", "Surgery Specialty", "Scheduled Hours", "Actual Knife Time", "Turnaround Delay (mins)"]),
    ("Pharmacy_Stockout_Expiry_Report", "Inpatient Pharmacy Stockout & Expiry Audit", ["Drug Code", "Generic Drug Name", "Current Stock", "Reorder Level", "Near Expiry Batches", "Status"]),
    ("Hospital_Acquired_Infection_HAI_Report", "HAI Infection Surveillance Metrics", ["Ward", "Inpatient Days", "CLABSI Incidents", "CAUTI Incidents", "VAP Rate / 1000 Days"]),
    ("Doctor_OPD_Consultation_Footfall", "Specialist OPD Clinic Footfall Audit", ["Doctor Name", "Specialty Department", "Scheduled Slots", "Completed Visits", "Average Wait (mins)"]),
    ("Blood_Bank_Component_Inventory_Report", "Blood Bank Stock & Crossmatch Summary", ["Blood Group", "PRBC Units", "FFP Units", "Platelet Units", "Cryoprecipitate", "Status"]),
    ("Biomedical_Equipment_Uptime_Report", "Life-Support Equipment Uptime & Downtime", ["Device Name", "Asset Tag", "Location", "Uptime %", "Mean Time to Repair (hrs)", "PM Status"]),
    ("Dialysis_Unit_Monthly_Registry", "Hemodialysis Sessions & Serology Register", ["Date", "Total Sessions", "Hepatitis B Isolated", "Hepatitis C Isolated", "Vascular Complications"]),
    ("Radiology_Reporting_TAT_Report", "Imaging Turnaround & PACS Reporting Lag", ["Modality", "Total Scans", "STAT Reporting TAT", "Routine TAT (hrs)", "Critical Alert Findings"]),
    ("Discharge_Turnaround_Time_Audit", "Discharge Order to Physical Exit TAT", ["Ward", "Total Discharges", "Average Order-to-Bill (hrs)", "Bill-to-Exit (hrs)", "Target TAT Met %"]),
    ("PMJAY_Claim_Settlement_Ledger", "Ayushman Bharat PMJAY Financial Claims", ["TMS Preauth ID", "Patient UHID", "Package Code", "Package Amount", "State Sanction Status", "Settled Amount"]),
    ("Unbilled_Consumables_Revenue_Leakage", "Consumables Audit & Revenue Leakage", ["Department", "Unbilled Items Found", "Estimated Variance (Rs)", "Reconciled Status", "Auditor Name"]),
    ("Hospital_Mortality_Review_Register", "Inpatient Mortality Audit & Root Cause", ["Death ID", "Patient UHID", "Ward", "Primary Diagnosis", "Mortality Category", "Committee Review Status"]),
    ("Patient_Satisfaction_CSAT_Survey_Report", "Patient Experience CSAT Scoring", ["Department", "Responses Received", "Doctor Rating (1-5)", "Nursing Rating (1-5)", "Cleanliness (1-5)", "Net CSAT %"]),
    ("CSSD_Sterilization_Efficiency_Report", "CSSD Autoclave Cycles & Pack Integrity", ["Date", "Total Trays Processed", "Biological Spore Failures", "Rapid Readout Integrators", "OT Turnaround"]),
    ("Ambulance_Response_Time_Audit", "Ambulance Emergency Dispatch Response", ["Trip ID", "Caller Location", "Call-to-Dispatch (mins)", "On-Scene Arrival (mins)", "Transport Destination"]),
    ("Clinical_Readmission_Within_30Days_Report", "30-Day Unplanned Inpatient Readmissions", ["Patient UHID", "Initial Admission ID", "Readmission Date", "Primary Diagnosis", "Preventable Index"]),
    ("High_Alert_Narcotic_Audit_Report", "Schedule X Narcotic Stock Reconciliation", ["Drug Name", "Opening Balance", "Dispensed Units", "Ampoules Returned", "Closing Physical Balance"]),
    ("Dietary_Meal_Fulfillment_Audit", "Inpatient Meal Delivery & Diet Accuracy", ["Ward", "Meals Requisitioned", "On-Time Delivery %", "Therapeutic Accuracy %", "Grievances Raised"]),
    ("Staff_Needlestick_Occupational_Report", "Occupational Needlestick & Biohazard Exposures", ["Incident Date", "Staff Department", "Source Serology Known", "PEP Commenced", "Follow-Up Outcome"]),
    ("Bed_Turnaround_Housekeeping_TAT", "Housekeeping Terminal Bed Cleaning TAT", ["Ward", "Beds Vacated", "Average Turnover (mins)", "Beds Ready <45m %", "UV Disinfection Done"]),
    ("Corporate_Insurance_Denial_Analysis", "Corporate Health Insurance Denial Causes", ["Insurer Name", "Claims Submitted", "Deductions (Rs)", "Pre-Existing Exclusion %", "Appeal Reversals"])
]

def generate_reports():
    results = []
    for rep in REPORTS_METADATA:
        filename_base, title, cols = rep
        filename = f"{filename_base}.xlsx"
        filepath = REPORTS_DIR / filename
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Summary"

        # Generate sample rows
        sample_rows = []
        for r in range(1, 6):
            row_vals = []
            for c_idx, c in enumerate(cols):
                if "Date" in c:
                    row_vals.append(f"2026-10-{r:02d}")
                elif "UHID" in c:
                    row_vals.append(f"UHID-0000{r:02d}")
                elif "Amount" in c or "Collected" in c:
                    row_vals.append(r * 25000)
                elif "%" in c or "Rate" in c:
                    row_vals.append(f"{80 + r}%")
                elif "Status" in c:
                    row_vals.append("Active" if r % 2 == 0 else "Cleared")
                elif "Cleared" in c:
                    row_vals.append(True if r != 2 else False)
                else:
                    row_vals.append(f"Data-{r}")
            sample_rows.append(row_vals)

        format_excel_sheet(ws, title, cols, sample_rows)
        wb.save(str(filepath))
        results.append((filepath, {
            "file_id": filename_base,
            "title": title,
            "tags": ["report", "excel", "metrics", "analytics", "smch"]
        }))
    return results

# =========================================================================
# 5. 30 HOSPITAL POLICIES
# =========================================================================
POLICIES_LIST = [
    ("POL-001", "Visitor_Management_Policy", "Hospital Visitor and Attender Management Policy", "Operations", "1.3", ["all_staff"]),
    ("POL-002", "MRD_Data_Privacy_Policy", "Medical Records Privacy and Data Governance Policy", "Medical Records (MRD / HIM)", "2.0", ["medical_records", "doctor"]),
    ("POL-003", "Cashless_Insurance_Policy", "TPA and Cashless Hospitalization Authorization Policy", "Insurance and TPA", "1.5", ["insurance_tpa", "billing"]),
    ("POL-004", "Emergency_Triage_Policy", "Emergency Severity Index (ESI) Prioritization Policy", "Emergency Department", "2.1", ["doctor", "nurse"]),
    ("POL-005", "ICU_Admission_Discharge_Criteria", "Critical Care Admission and Discharge Priority Policy", "Intensive Care Unit (ICU)", "2.4", ["doctor", "nurse"]),
    ("POL-006", "Surgical_Informed_Consent_Policy", "Informed Surgical and Anesthesia Consent Policy", "Operation Theatre", "3.0", ["doctor", "nurse"]),
    ("POL-007", "High_Alert_Narcotic_Policy", "Schedule X and High-Alert Medication Custody Policy", "Pharmacy", "2.8", ["pharmacist", "nurse", "doctor"]),
    ("POL-008", "Blood_Transfusion_Safety_Policy", "Hemovigilance and Blood Transfusion Safety Policy", "Blood Bank", "2.5", ["doctor", "nurse", "lab_tech"]),
    ("POL-009", "Patient_Identification_Wristband", "Two-Identifier Patient Wristband Safety Policy", "Quality and Patient Safety", "2.2", ["all_staff"]),
    ("POL-010", "Critical_Lab_Panic_Reporting", "Critical Panic Laboratory Values Notification Policy", "Laboratory Operations", "3.1", ["lab_tech", "doctor", "nurse"]),
    ("POL-011", "Hospital_Acquired_Infection_Control", "Infection Prevention and Hand Hygiene Compliance Policy", "Quality and Patient Safety", "2.6", ["all_staff"]),
    ("POL-012", "Biomedical_Equipment_Maintenance", "Biomedical Equipment Planned Preventive Maintenance Policy", "Biomedical Engineering", "1.8", ["biomedical_engineer", "nurse"]),
    ("POL-013", "Medico_Legal_Case_Protocol", "Statutory Medico-Legal Case Forensic Custody Policy", "Medical Records (MRD / HIM)", "2.3", ["doctor", "front_office"]),
    ("POL-014", "Discharge_Against_Medical_Advice", "Patient Discharge Against Medical Advice (DAMA/LAMA) Policy", "Admission and Discharge", "2.0", ["doctor", "nurse", "operations_manager"]),
    ("POL-015", "Patient_Grievance_Redressal", "Patient and Attender Grievance Redressal Mechanism Policy", "Quality and Patient Safety", "1.7", ["operations_manager", "front_office"]),
    ("POL-016", "Billing_Dispute_Waiver_Authority", "Inpatient Billing Concession and Dispute Authority Policy", "Billing", "2.2", ["billing", "operations_manager"]),
    ("POL-017", "Bed_Reservation_Buffer_Override", "Emergency Bed Buffer and Surge Bed Allocation Policy", "Admission and Discharge", "2.4", ["admission", "operations_manager"]),
    ("POL-018", "Clinical_Research_Ethics_DISHA", "Ethical Clinical Research and Health Data Privacy Policy", "Clinical Services", "1.5", ["doctor", "medical_records"]),
    ("POL-019", "Ambulance_Emergency_Dispatch", "Emergency Fleet Response and Inter-Hospital Transfer Policy", "Emergency Department", "2.1", ["emergency_team", "driver"]),
    ("POL-020", "End_Of_Life_Palliative_Care", "Palliative Care and Do-Not-Resuscitate (DNR) Protocol Policy", "Clinical Services", "2.0", ["doctor", "nurse"]),
    ("POL-021", "Needlestick_Injury_Post_Exposure", "Occupational Post-Exposure Prophylaxis (PEP) Policy", "Quality and Patient Safety", "2.3", ["all_staff"]),
    ("POL-022", "Chemotherapy_Spill_Safety", "Cytotoxic Chemotherapeutic Drug Handling and Spill Policy", "Oncology", "2.1", ["pharmacist", "nurse"]),
    ("POL-023", "Hemodialysis_Water_Quality_Standards", "AAMI Hemodialysis Reverse Osmosis Water Quality Policy", "Nephrology and Dialysis", "2.5", ["dialysis_tech", "biomedical_engineer"]),
    ("POL-024", "Code_Blue_Cardiopulmonary_Response", "Hospital-Wide Cardiopulmonary Resuscitation Response Policy", "Cardiology", "3.2", ["all_staff"]),
    ("POL-025", "Code_Pink_Infant_Abduction_Plan", "Infant and Pediatric Security Lockdown Code Pink Policy", "Quality and Patient Safety", "1.9", ["security", "nurse"]),
    ("POL-026", "Fire_Disaster_Evacuation_Policy", "Code Red Fire Safety and Mass Casualty Evacuation Policy", "Facility Management", "2.8", ["all_staff"]),
    ("POL-027", "Clinical_Privileging_Doctor_Roster", "Medical Staff Credentialing and Scope of Practice Policy", "Human Resources and Administration", "2.4", ["doctor", "hr_officer"]),
    ("POL-028", "PMJAY_CMCHIS_Empanelment_Compliance", "Government Subsidized Scheme Compliance & Audit Policy", "Insurance and TPA", "3.0", ["insurance_tpa", "billing"]),
    ("POL-029", "CSSD_Packaging_Validation", "Sterile Reprocessing Packaging and Expiry Dating Policy", "Operation Theatre", "2.0", ["cssd_tech", "nurse"]),
    ("POL-030", "Physical_Chemical_Restraint_Policy", "Least-Restrictive Patient Restraint and Human Rights Policy", "Psychiatry", "2.2", ["doctor", "nurse"])
]

def generate_policies():
    results = []
    for item in POLICIES_LIST:
        doc_id, slug, title, dept, ver, roles = item
        filename = f"{doc_id}_{slug}.docx"
        filepath = POLICIES_DIR / filename
        doc = docx.Document()
        add_docx_header_footer(doc, doc_id, title)

        p_title = doc.add_paragraph()
        run_title = p_title.add_run(title)
        run_title.font.name = "Arial"
        run_title.font.size = Pt(17)
        run_title.font.bold = True
        run_title.font.color.rgb = RGBColor(15, 23, 42)

        doc.add_paragraph(f"Hospital Institutional Policy  •  {HOSPITAL_NAME}").italic = True

        table = doc.add_table(rows=4, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_rows = [
            ("Policy Identifier", doc_id),
            ("Department / Committee", dept),
            ("Effective Version", f"v{ver} (Approved 2026)"),
            ("Enforcement Roles", ", ".join(roles))
        ]
        for i, (k, v) in enumerate(meta_rows):
            cell_k = table.cell(i, 0)
            cell_v = table.cell(i, 1)
            cell_k.text = k
            cell_k.paragraphs[0].runs[0].font.bold = True
            cell_v.text = v

        doc.add_paragraph()
        doc.add_heading("1. Policy Statement", level=2)
        doc.add_paragraph(f"It is the official policy of {HOSPITAL_NAME} that all clinical and operational activities governing {title.lower()} adhere strictly to regulatory standards, NABH accreditation criteria, and patient rights.")

        doc.add_heading("2. Core Principles & Rules", level=2)
        doc.add_paragraph(f"• Rule 1: All personnel in {dept} must enforce compliance with documented procedural workflows.")
        doc.add_paragraph("• Rule 2: Mandatory documentation must be maintained in the electronic hospital information system.")
        doc.add_paragraph("• Rule 3: Zero tolerance for unauthorized procedural deviation without written Medical Superintendent sign-off.")

        doc.add_heading("3. Regulatory & Statutory Compliance", level=2)
        doc.add_paragraph(f"Complies with National Medical Commission (NMC), NABH 5th Edition Standards, and Tamil Nadu Clinical Establishments Act.")

        doc.add_heading("4. Exceptions & Escalation", level=2)
        doc.add_paragraph("Any emergency exception must be documented in writing and escalated to the Operations Manager and Medical Superintendent within 24 hours.")

        doc.save(str(filepath))
        results.append((filepath, {
            "file_id": doc_id + "_" + slug,
            "title": title,
            "doc_id": doc_id,
            "department": dept,
            "version": ver,
            "roles": roles,
            "tags": ["policy", doc_id.lower(), dept.lower(), slug.replace('_', ' ').lower(), "smch"]
        }))
    return results

# =========================================================================
# 6. ROUTING MATRIX & CORE JSON FILES
# =========================================================================
def generate_routing_matrix():
    p = ROUTING_DIR / "Escalation_Routing_Matrix.xlsx"
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Routing Rules"
    c1 = ["Rule ID", "Trigger", "Trigger Type", "Condition Description", "Route To Team", "Team Contact Extension", "Priority", "SLA Hours", "Escalation Reason", "Example Query 1", "Example Query 2"]
    d1 = [
        ["R-001", "Clinical question detected", "Intent", "Medical advice or diagnosis asked", "clinical_review", "1012", "urgent", 1, "Non-clinicians/AI cannot prescribe medical advice", "What antibiotic should I prescribe?", "Does this patient need immediate intubation?"],
        ["R-002", "Medication dosage asked", "Intent", "Dosage calculation inquiry", "clinical_review", "1012", "urgent", 1, "Risk of drug toxicity", "What is the pediatric dose of amikacin?", "How many units of insulin should I give?"],
        ["R-003", "Diagnosis question asked", "Intent", "Interpretation of clinical symptoms", "clinical_review", "1012", "urgent", 1, "Diagnostic responsibility lies with doctor", "Can you confirm if this ECG shows STEMI?", "What is the diagnosis for this patient?"],
        ["R-004", "Insurance claim rejected", "Data State", "Cashless claim status updated to rejected", "insurance_tpa", "1029", "high", 2, "Requires urgent dispute filing or counseling", "Claim CLM-002 rejected citing clause 4.2", "Why did Star Health deny cashless approval?"],
        ["R-005", "Pre-auth pending over 48 hours", "Time Threshold", "Pre-auth unacknowledged after 48h", "insurance_tpa", "1029", "high", 2, "Unreasonable insurer delay", "Preauth for UHID-000002 has had no response for 2 days", "Status still submitted after 50 hours"],
        ["R-006", "Bill disputed by patient", "Intent", "Attender disputes itemized charges", "billing", "1028", "high", 2, "Financial grievance requiring audit", "Patient attender refuses to pay extra consumables", "Why are we being charged for ICU support?"],
        ["R-007", "UHID not found in system", "Data State", "Query yields zero results across DB", "front_office", "1026", "normal", 4, "Demographic reconciliation needed", "I cannot find patient Senthil Kumar with UHID-999999", "Patient card says UHID-000088 but no records"],
        ["R-008", "Discharge blocked by billing", "Data State", "Discharge signed but billing is FALSE", "billing", "1028", "high", 2, "Causes inpatient bed blockage", "Discharge for Bed 07 blocked because bill is not generated", "Nursing cleared but stuck waiting for bill"],
        ["R-009", "Critical lab result unalerted", "Data State", "critical_value_flag is TRUE but alerted is FALSE", "clinical_review", "1012", "urgent", 0.5, "Severe patient safety hazard", "Potassium is 6.8 mmol/L but doctor not alerted for 30m", "Platelets under 20000 with alert unexecuted"],
        ["R-010", "Bed unavailable in requested ward", "Data State", "No vacant beds matching admission", "operations_manager", "1032", "high", 1, "Requires buffer override or transfer", "Zero ICU beds available for emergency patient", "Need General Ward bed but all 15 occupied"],
        ["R-011", "IT system down reported", "Incident", "Workstation or HIS connectivity failure", "it_support", "1033", "urgent", 1, "Hospital operational continuity at risk", "EMR workstation in ICU Bed 02 freezing", "Cannot access HIS admission portal from counter"],
        ["R-012", "MLC case registration needed", "Event", "Trauma, poisoning, or assault presentation", "medical_records", "1030", "urgent", 1, "Police intimation mandatory within 1h", "Road traffic accident victim in emergency bay", "Suspected domestic assault requires MLC"],
        ["R-013", "Patient complaint about staff", "Grievance", "Attender registers service complaint", "quality", "1032", "high", 4, "Service recovery protocol", "Attender complained of delay in breakfast", "Complaint regarding rude behavior at counter"],
        ["R-014", "Narcotic drug query", "Drug Schedule", "Schedule X / Fentanyl query", "clinical_review", "1012", "urgent", 0.5, "Strict statutory narcotic register compliance", "Need emergency dose of Inj Morphine 10mg", "How do I request Fentanyl ampoule?"],
        ["R-015", "Low confidence score under 0.6", "System Logic", "Confidence falls below 0.60 threshold", "general_triage", "1026", "normal", 4, "Escalate ambiguous queries to human", "I need that document about the thing from last month", "Can you process the green file for room five?"]
    ]
    format_excel_sheet(ws1, "Hospital Operations Escalation & Routing Matrix", c1, d1)

    ws2 = wb.create_sheet(title="Team Directory")
    c2 = ["Team ID", "Team Name", "Handles", "Contact Extension", "Email", "Helpdesk Queue", "SLA Hours", "Escalation To"]
    d2 = [
        ["TEAM-001", "IT and HIS Support", "HIS workstation faults, network, printers", "1033", "it@smch.in", "QUEUE_IT_SUPPORT", 1, "TEAM-011"],
        ["TEAM-002", "Insurance and TPA", "Cashless approvals, TPA queries, PMJAY", "1029", "tpa@smch.in", "QUEUE_INSURANCE", 2, "TEAM-011"],
        ["TEAM-003", "Pharmacy Operations", "Medication dispensing, return credits, narcotics", "1023", "pharmacy@smch.in", "QUEUE_PHARMACY", 1, "TEAM-012"],
        ["TEAM-004", "Lab Operations", "Blood tests, STAT processing, critical panic values", "1021", "lab@smch.in", "QUEUE_LAB", 1, "TEAM-012"],
        ["TEAM-005", "Radiology Operations", "X-Ray, CT, MRI, PACS DICOM viewing", "1022", "radiology@smch.in", "QUEUE_RADIOLOGY", 1, "TEAM-012"],
        ["TEAM-006", "Billing", "Final bills, tariff calculations, co-pay receipts", "1028", "billing@smch.in", "QUEUE_BILLING", 2, "TEAM-011"],
        ["TEAM-007", "Admission and Discharge", "Bed allocation, ward transfers, 4-point gate pass", "1027", "admissions@smch.in", "QUEUE_ADMISSIONS", 1, "TEAM-011"],
        ["TEAM-008", "Front Office", "Patient registration, UHID creation, OPD triage", "1026", "frontoffice@smch.in", "QUEUE_FRONTOFFICE", 4, "TEAM-011"],
        ["TEAM-009", "Medical Records", "Archived case file retrieval, MLC records", "1030", "mrd@smch.in", "QUEUE_MRD", 2, "TEAM-011"],
        ["TEAM-010", "Facility Management", "Housekeeping, linen supply, ward cleaning", "1035", "facility@smch.in", "QUEUE_FACILITY", 2, "TEAM-011"],
        ["TEAM-011", "Biomedical Engineering", "Ventilators, monitors, defibrillators maintenance", "1036", "biomedical@smch.in", "QUEUE_BIOMEDICAL", 1, "TEAM-011"],
        ["TEAM-012", "Clinical Review", "Medical decisions, panic lab values, physician reviews", "1012", "clinicalreview@smch.in", "QUEUE_CLINICAL", 0.5, "TEAM-012"]
    ]
    format_excel_sheet(ws2, "Hospital Operations Internal Team Directory", c2, d2)
    wb.save(str(p))
    return [(p, {"file_id": "Escalation_Routing_Matrix", "title": "Escalation Routing Matrix", "tags": ["routing", "matrix", "escalation", "teams"]})]

# =========================================================================
# 7. GENERATE COMPANION JSON INDEXES (For Supermemory Ingestion)
# =========================================================================
def generate_indexes(sops_meta, articles_meta, forms_meta, reports_meta, policies_meta, routing_meta):
    indexes_created = []

    # 1. SOPs (30)
    for p, meta in sops_meta:
        idx_p = INDEX_DIR / f"{meta['file_id']}.json"
        content_text = f"SOP: {meta['title']} ({meta['doc_id']})\nDEPARTMENT: {meta['department']}\nVERSION: {meta['version']}\nROLES: {', '.join(meta['roles'])}\nPURPOSE: {meta['purpose']}\nSTEPS:\n" + "\n".join(meta['steps']) + "\n" + "\n".join(meta['blockers']) + "\n" + "\n".join(meta['escalations'])
        obj = {
            "file_id": meta['file_id'],
            "title": meta['title'],
            "file_path": Path(p).relative_to(BASE_DIR).as_posix(),
            "file_type": "docx",
            "category": "sop",
            "department": meta['department'],
            "applicable_roles": meta['roles'],
            "version": meta['version'],
            "content": content_text,
            "tags": meta['tags'],
            "source_citation": f"{meta['doc_id']} {meta['title']} v{meta['version']}, Section 4"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    # 2. Knowledge Articles (30)
    for p, meta in articles_meta:
        idx_p = INDEX_DIR / f"{meta['file_id']}.json"
        content_text = f"ARTICLE: {meta['title']} ({meta['doc_id']})\nSYSTEM: {meta['system']}\nDEPARTMENT: {meta['department']}\nVERSION: {meta['version']}\nOVERVIEW: {meta['overview']}\nSTEPS:\n" + "\n".join(meta['steps']) + "\n" + "\n".join(meta['errors']) + f"\n{meta['contact']}"
        obj = {
            "file_id": meta['file_id'],
            "title": meta['title'],
            "file_path": Path(p).relative_to(BASE_DIR).as_posix(),
            "file_type": "docx",
            "category": "knowledge_article",
            "department": meta['department'],
            "applicable_roles": meta['roles'],
            "version": meta['version'],
            "content": content_text,
            "tags": meta['tags'],
            "source_citation": f"{meta['doc_id']} {meta['title']} v{meta['version']}"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    # 3. Forms (30)
    for p, meta in forms_meta:
        idx_p = INDEX_DIR / f"{meta['file_id']}.json"
        content_text = f"FORM: {meta['title']} ({meta['doc_id']})\nVERSION: {meta['version']}\nFIELDS:\n" + "\n".join([f"- {f}" for f in meta['fields']])
        obj = {
            "file_id": meta['file_id'],
            "title": meta['title'],
            "file_path": Path(p).relative_to(BASE_DIR).as_posix(),
            "file_type": "pdf",
            "category": "form",
            "department": "Clinical Operations",
            "applicable_roles": ["doctor", "nurse", "admission", "discharge", "front_office"],
            "version": meta['version'],
            "content": content_text,
            "tags": meta['tags'],
            "source_citation": f"{meta['doc_id']} {meta['title']} {meta['version']}"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    # 4. Reports (30)
    for p, meta in reports_meta:
        idx_p = INDEX_DIR / f"{meta['file_id']}.json"
        content_text = f"EXCEL REPORT: {meta['title']}\nMETRICS: Standard operational audit report template for {HOSPITAL_NAME}."
        obj = {
            "file_id": meta['file_id'],
            "title": meta['title'],
            "file_path": Path(p).relative_to(BASE_DIR).as_posix(),
            "file_type": "xlsx",
            "category": "report",
            "department": "Operations Management",
            "applicable_roles": ["operations_manager", "quality", "billing", "nurse", "doctor"],
            "version": "1.0",
            "content": content_text,
            "tags": meta['tags'],
            "source_citation": f"{meta['title']} v1.0, SMCH Central Reporting"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    # 5. Policies (30)
    for p, meta in policies_meta:
        idx_p = INDEX_DIR / f"{meta['file_id']}.json"
        content_text = f"POLICY: {meta['title']} ({meta['doc_id']})\nDEPARTMENT: {meta['department']}\nVERSION: {meta['version']}\nROLES: {', '.join(meta['roles'])}\nENFORCEMENT: Official institutional compliance policy at {HOSPITAL_NAME}."
        obj = {
            "file_id": meta['file_id'],
            "title": meta['title'],
            "file_path": Path(p).relative_to(BASE_DIR).as_posix(),
            "file_type": "docx",
            "category": "policy",
            "department": meta['department'],
            "applicable_roles": meta['roles'],
            "version": meta['version'],
            "content": content_text,
            "tags": meta['tags'],
            "source_citation": f"{meta['doc_id']} {meta['title']} v{meta['version']}"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    # 6. Core Matrix & Spec Indexes
    core_specs = [
        ("Escalation_Routing_Matrix", "Hospital Escalation and Routing Matrix", "routing_matrix/Escalation_Routing_Matrix.xlsx", "xlsx", "routing", ["routing", "sla", "teams"]),
        ("support_directory", "Hospital Support and Team Directory", "support_directory.json", "json", "support_directory", ["teams", "extensions", "helpdesk"]),
        ("field_definitions", "Hospital Operations Field Definitions Schema", "field_definitions.json", "json", "field_definition", ["schema", "fields", "regex"]),
        ("operations_requests", "Hospital Operations Sample Requests Scenario Suite", "operations_requests.json", "json", "operations_request", ["scenarios", "queries", "intents"]),
        ("workflow_sessions_placeholder", "Workflow Sessions Session Storage Placeholder", "workflow_sessions_placeholder.json", "json", "workflow_session", ["workflow", "session", "runtime"])
    ]
    for fid, ftitle, fpath, ftype, fcat, ftags in core_specs:
        idx_p = INDEX_DIR / f"{fid}.json"
        obj = {
            "file_id": fid,
            "title": ftitle,
            "file_path": fpath,
            "file_type": ftype,
            "category": fcat,
            "department": "Operations Management",
            "applicable_roles": ["all_staff"],
            "version": "1.0",
            "content": f"CORE SPECIFICATION: {ftitle} ({fpath}) for {HOSPITAL_NAME}.",
            "tags": ftags + ["smch"],
            "source_citation": f"{ftitle} v1.0"
        }
        with open(idx_p, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        indexes_created.append(idx_p)

    return indexes_created

def main():
    print("=" * 80)
    print("SAVEETHA MEDICAL COLLEGE AND HOSPITAL (SMCH)")
    print("KNOWLEDGE BASE SCALE-UP GENERATOR (30 FILES PER CATEGORY)")
    print("=" * 80)

    # 1. SOPs (30)
    print("\n[1/7] Generating 30 SOP Word Documents in knowledge_base/sops/ ...")
    sops_meta = generate_sops()
    print(f"  [OK] Generated {len(sops_meta)} SOPs.")

    # 2. Knowledge Articles (30)
    print("\n[2/7] Generating 30 Knowledge Articles in knowledge_base/knowledge_articles/ ...")
    articles_meta = generate_knowledge_articles()
    print(f"  [OK] Generated {len(articles_meta)} Knowledge Articles.")

    # 3. PDF Forms (30)
    print("\n[3/7] Generating 30 PDF Forms in knowledge_base/forms/ ...")
    forms_meta = generate_forms()
    print(f"  [OK] Generated {len(forms_meta)} PDF Forms.")

    # 4. Reports (30)
    print("\n[4/7] Generating 30 Excel Reports in knowledge_base/reports/ ...")
    reports_meta = generate_reports()
    print(f"  [OK] Generated {len(reports_meta)} Excel Reports.")

    # 5. Policies (30)
    print("\n[5/7] Generating 30 Hospital Policies in knowledge_base/policies/ ...")
    policies_meta = generate_policies()
    print(f"  [OK] Generated {len(policies_meta)} Policies.")

    # Routing Matrix
    routing_meta = generate_routing_matrix()
    print(f"  [OK] Generated Escalation Routing Matrix.")

    # 6. Companion JSON Indexes
    print("\n[6/7] Generating Companion JSON Indexes in knowledge_base/index/ ...")
    indexes_created = generate_indexes(sops_meta, articles_meta, forms_meta, reports_meta, policies_meta, routing_meta)
    print(f"  [OK] Generated {len(indexes_created)} companion JSON index files.")

    # 7. Master Synthetic Workbook & Workflow State Machines
    print("\n[7/7] Generating Master Synthetic Workbook & Workflow State Machines ...")
    try:
        from knowledge_base.build_synthetic_assets import build_master_workbook, build_workflow_definitions_json, build_companion_indexes
        build_master_workbook()
        build_workflow_definitions_json()
        extra_indexes = build_companion_indexes()
        indexes_created.extend(extra_indexes)
        print(f"  [OK] Generated Master Workbook, Workflow State Machines & Indexes.")
    except Exception as exc:
        print(f"  [WARNING] Could not run build_synthetic_assets: {exc}")

    # Summary
    total_docs = len(sops_meta) + len(articles_meta) + len(forms_meta) + len(reports_meta) + len(policies_meta) + len(routing_meta) + 1
    total_indexes = len(indexes_created)

    print("\n" + "=" * 80)
    print("GENERATION SUMMARY:")
    print("=" * 80)
    print(f"SOPs (.docx):                         {len(sops_meta)}")
    print(f"Knowledge Articles (.docx):           {len(articles_meta)}")
    print(f"Forms (.pdf):                         {len(forms_meta)}")
    print(f"Reports (.xlsx):                      {len(reports_meta)}")
    print(f"Policies (.docx):                     {len(policies_meta)}")
    print(f"Routing Matrix (.xlsx):               {len(routing_meta)}")
    print(f"Operations Master Workbook (.xlsx):   1")
    print(f"Workflow State Machines (.json):      1 (8 workflows)")
    print(f"Total Document Files:                 {total_docs}")
    print(f"Total Companion Indexes:              {total_indexes}")
    print("=" * 80)
    print("All categories scaled to 30 files each with full SMCH branding and Supermemory indexes!")

if __name__ == "__main__":
    main()
