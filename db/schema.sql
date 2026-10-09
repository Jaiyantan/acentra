-- =========================================================================
-- Hospital Operations Simulation Database Schema (SQLite)
-- Exactly 14 Tables as specified. Pure static data layer. No AI/LLM/Agents.
-- =========================================================================

-- 1. Patients Table
CREATE TABLE IF NOT EXISTS patients (
    uhid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    gender TEXT NOT NULL,
    contact TEXT NOT NULL,
    address TEXT NOT NULL,
    registration_date TIMESTAMP NOT NULL,
    status TEXT CHECK(status IN ('registered', 'admitted', 'discharged', 'deceased')) NOT NULL
);

-- 2. Staff Table
CREATE TABLE IF NOT EXISTS staff (
    staff_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT CHECK(role IN (
        'front_office', 'admission', 'discharge', 'billing', 'insurance_tpa',
        'medical_records', 'case_management', 'quality', 'operations_manager',
        'it_support', 'nurse', 'doctor', 'pharmacist', 'lab_tech', 'rad_tech'
    )) NOT NULL,
    permissions TEXT NOT NULL, -- JSON array of strings
    is_active BOOLEAN NOT NULL DEFAULT 1
);

-- 3. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    dept_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('clinical', 'clinical_support', 'administrative', 'support')) NOT NULL,
    location TEXT NOT NULL,
    head_staff_id TEXT,
    FOREIGN KEY(head_staff_id) REFERENCES staff(staff_id)
);

-- 4. Beds Table
CREATE TABLE IF NOT EXISTS beds (
    bed_id TEXT PRIMARY KEY,
    ward TEXT NOT NULL,
    status TEXT CHECK(status IN ('available', 'occupied', 'maintenance', 'reserved')) NOT NULL,
    current_patient_uhid TEXT,
    FOREIGN KEY(current_patient_uhid) REFERENCES patients(uhid)
);

-- 5. Admissions Table
CREATE TABLE IF NOT EXISTS admissions (
    admission_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    admission_date TIMESTAMP NOT NULL,
    admitting_doctor_id TEXT NOT NULL,
    admitting_diagnosis TEXT NOT NULL,
    ward TEXT NOT NULL,
    bed_id TEXT NOT NULL,
    status TEXT CHECK(status IN ('active', 'discharged', 'transferred')) NOT NULL,
    insurance_policy_number TEXT,
    insurance_preauth_status TEXT CHECK(insurance_preauth_status IN ('pending', 'approved', 'rejected', 'not_required')) NOT NULL,
    FOREIGN KEY(uhid) REFERENCES patients(uhid),
    FOREIGN KEY(admitting_doctor_id) REFERENCES staff(staff_id),
    FOREIGN KEY(bed_id) REFERENCES beds(bed_id)
);

-- 6. Discharges Table
CREATE TABLE IF NOT EXISTS discharges (
    discharge_id TEXT PRIMARY KEY,
    admission_id TEXT NOT NULL,
    discharge_date TIMESTAMP NOT NULL,
    discharge_type TEXT CHECK(discharge_type IN ('regular', 'lama', 'dama', 'death', 'transfer')) NOT NULL,
    final_diagnosis TEXT NOT NULL,
    follow_up_date TEXT,
    follow_up_doctor_id TEXT,
    discharge_medications TEXT NOT NULL, -- JSON array
    clearance_status TEXT NOT NULL,     -- JSON object: {"billing": bool, "pharmacy": bool, "nursing": bool, "mrd": bool}
    FOREIGN KEY(admission_id) REFERENCES admissions(admission_id),
    FOREIGN KEY(follow_up_doctor_id) REFERENCES staff(staff_id)
);

-- 7. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    admission_id TEXT NOT NULL,
    order_type TEXT CHECK(order_type IN ('lab', 'radiology', 'medication', 'diet', 'physio')) NOT NULL,
    order_details TEXT NOT NULL, -- JSON object
    ordered_by_staff_id TEXT NOT NULL,
    ordered_at TIMESTAMP NOT NULL,
    executed_at TIMESTAMP,
    status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')) NOT NULL,
    FOREIGN KEY(uhid) REFERENCES patients(uhid),
    FOREIGN KEY(admission_id) REFERENCES admissions(admission_id),
    FOREIGN KEY(ordered_by_staff_id) REFERENCES staff(staff_id)
);

-- 8. Lab Results Table
CREATE TABLE IF NOT EXISTS lab_results (
    result_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    test_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    reference_range TEXT NOT NULL,
    abnormal_flag TEXT CHECK(abnormal_flag IN ('H', 'L', 'HH', 'LL') OR abnormal_flag IS NULL),
    critical_value_flag BOOLEAN NOT NULL DEFAULT 0,
    critical_value_alerted BOOLEAN NOT NULL DEFAULT 0,
    result_status TEXT CHECK(result_status IN ('pending', 'resulted', 'verified')) NOT NULL,
    resulted_at TIMESTAMP,
    FOREIGN KEY(uhid) REFERENCES patients(uhid)
);

-- 9. Prescriptions Table
CREATE TABLE IF NOT EXISTS prescriptions (
    rx_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    dose TEXT NOT NULL,
    frequency TEXT NOT NULL,
    route TEXT NOT NULL,
    duration TEXT NOT NULL,
    prescribed_by TEXT NOT NULL,
    prescribed_at TIMESTAMP NOT NULL,
    dispensing_status TEXT CHECK(dispensing_status IN ('pending', 'dispensed', 'cancelled')) NOT NULL,
    FOREIGN KEY(uhid) REFERENCES patients(uhid),
    FOREIGN KEY(prescribed_by) REFERENCES staff(staff_id)
);

-- 10. Bills Table
CREATE TABLE IF NOT EXISTS bills (
    bill_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    admission_id TEXT NOT NULL,
    bill_date TIMESTAMP NOT NULL,
    total_amount REAL NOT NULL,
    paid_amount REAL NOT NULL,
    insurance_covered_amount REAL NOT NULL,
    patient_payable REAL NOT NULL,
    status TEXT CHECK(status IN ('draft', 'final', 'paid', 'partially_paid', 'disputed')) NOT NULL,
    items TEXT NOT NULL, -- JSON array of line items
    FOREIGN KEY(uhid) REFERENCES patients(uhid),
    FOREIGN KEY(admission_id) REFERENCES admissions(admission_id)
);

-- 11. Insurance Claims Table
CREATE TABLE IF NOT EXISTS insurance_claims (
    claim_id TEXT PRIMARY KEY,
    uhid TEXT NOT NULL,
    admission_id TEXT NOT NULL,
    insurer_name TEXT NOT NULL,
    policy_number TEXT NOT NULL,
    tpa_name TEXT NOT NULL,
    preauth_requested_at TIMESTAMP NOT NULL,
    preauth_approved_at TIMESTAMP,
    preauth_amount REAL,
    claim_status TEXT CHECK(claim_status IN ('draft', 'submitted', 'approved', 'rejected', 'resubmitted')) NOT NULL,
    rejection_reason TEXT,
    pmjay_flag BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY(uhid) REFERENCES patients(uhid),
    FOREIGN KEY(admission_id) REFERENCES admissions(admission_id)
);

-- 12. Tickets Table
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    raised_by_staff_id TEXT NOT NULL,
    ticket_type TEXT CHECK(ticket_type IN ('it_issue', 'billing_query', 'insurance_query', 'patient_complaint', 'maintenance', 'clinical_support')) NOT NULL,
    priority TEXT CHECK(priority IN ('low', 'normal', 'high', 'urgent')) NOT NULL,
    status TEXT CHECK(status IN ('open', 'in_progress', 'escalated', 'resolved', 'closed')) NOT NULL,
    assigned_to_team TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    FOREIGN KEY(raised_by_staff_id) REFERENCES staff(staff_id)
);

-- 13. Pending Approvals Table
CREATE TABLE IF NOT EXISTS pending_approvals (
    approval_id TEXT PRIMARY KEY,
    requested_by_staff_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_payload TEXT NOT NULL, -- JSON payload of the action
    status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    actioned_at TIMESTAMP,
    actioned_by TEXT,
    FOREIGN KEY(requested_by_staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY(actioned_by) REFERENCES staff(staff_id)
);

-- 14. Audit Log Table
CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    session_id TEXT NOT NULL,
    staff_id TEXT NOT NULL,
    action TEXT CHECK(action IN ('QUERY', 'WORKFLOW_STEP', 'TOOL_CALL', 'ESCALATION', 'APPROVAL')) NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    input_summary TEXT,
    output_summary TEXT,
    documents_cited TEXT, -- JSON array of strings
    confidence_score REAL,
    escalated BOOLEAN NOT NULL DEFAULT 0,
    irreversible_action BOOLEAN NOT NULL DEFAULT 0,
    human_approved BOOLEAN,
    FOREIGN KEY(staff_id) REFERENCES staff(staff_id)
);
