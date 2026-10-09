"""
Database management and SQLite schema definitions for
Saveetha Medical College and Hospital (SMCH) Operations Engine.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import DB_PATH

logger = logging.getLogger("smch.database")

def get_db_connection():
    """Returns a connection with dictionary row access enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes all tables for all 16 departments and the live simulation."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable WAL mode for concurrent read/write performance
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    # 1. Patients Master
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        uhid TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER NOT NULL,
        gender TEXT NOT NULL,
        blood_group TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        insurance_type TEXT NOT NULL,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Emergency Department
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_cases (
        case_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        arrival_mode TEXT NOT NULL,
        ambulance_id TEXT,
        paramedic_notes TEXT,
        triage_level TEXT NOT NULL,
        chief_complaint TEXT NOT NULL,
        hr INTEGER,
        bp_sys INTEGER,
        bp_dia INTEGER,
        spo2 INTEGER,
        rr INTEGER,
        temp REAL,
        gcs INTEGER,
        arrival_time TIMESTAMP NOT NULL,
        doctor_seen_time TIMESTAMP,
        time_to_doctor_min INTEGER,
        assigned_doctor TEXT,
        disposition TEXT,
        status TEXT NOT NULL,
        clinical_reasoning TEXT,
        FOREIGN KEY (uhid) REFERENCES patients(uhid)
    );
    """)

    # 3. OPD Consultations & Tokens
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opd_consultations (
        consultation_id TEXT PRIMARY KEY,
        token_no INTEGER NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        specialty TEXT NOT NULL,
        doctor_id TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        queue_time TIMESTAMP NOT NULL,
        consultation_time TIMESTAMP,
        chief_complaints TEXT,
        examination_findings TEXT,
        provisional_diagnosis TEXT,
        icd10_code TEXT,
        status TEXT NOT NULL,
        FOREIGN KEY (uhid) REFERENCES patients(uhid)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opd_prescriptions (
        rx_id TEXT PRIMARY KEY,
        consultation_id TEXT,
        uhid TEXT NOT NULL,
        doctor_id TEXT,
        drug_name TEXT NOT NULL,
        dosage TEXT NOT NULL,
        frequency TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        instructions TEXT,
        status TEXT NOT NULL,
        prescribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (uhid) REFERENCES patients(uhid)
    );
    """)

    # 4. IPD Admissions, Beds & Rounds
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ipd_beds (
        bed_id TEXT PRIMARY KEY,
        ward_name TEXT NOT NULL,
        bed_no TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT NOT NULL,
        current_uhid TEXT,
        current_patient_name TEXT,
        admission_id TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ipd_admissions (
        admission_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        ward_name TEXT NOT NULL,
        bed_no TEXT NOT NULL,
        admitting_doctor TEXT NOT NULL,
        admitting_diagnosis TEXT NOT NULL,
        icd10_code TEXT,
        admission_time TIMESTAMP NOT NULL,
        discharge_time TIMESTAMP,
        status TEXT NOT NULL,
        discharge_summary TEXT,
        FOREIGN KEY (uhid) REFERENCES patients(uhid)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ipd_nursing_charts (
        chart_id TEXT PRIMARY KEY,
        admission_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        nurse_id TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        hr INTEGER,
        bp_sys INTEGER,
        bp_dia INTEGER,
        spo2 INTEGER,
        temp REAL,
        rr INTEGER,
        urine_output_ml INTEGER,
        intake_fluid_ml INTEGER,
        medication_administered TEXT,
        notes TEXT,
        FOREIGN KEY (admission_id) REFERENCES ipd_admissions(admission_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ipd_progress_notes (
        note_id TEXT PRIMARY KEY,
        admission_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        doctor_id TEXT NOT NULL,
        doctor_name TEXT NOT NULL,
        round_type TEXT NOT NULL,
        soap_subjective TEXT,
        soap_objective TEXT,
        soap_assessment TEXT,
        soap_plan TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admission_id) REFERENCES ipd_admissions(admission_id)
    );
    """)

    # 5. ICU / Critical Care
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS icu_beds (
        bed_id TEXT PRIMARY KEY,
        icu_name TEXT NOT NULL,
        bed_no TEXT NOT NULL,
        uhid TEXT,
        patient_name TEXT,
        apache2_score INTEGER,
        sofa_score INTEGER,
        ventilator_id TEXT,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS icu_telemetry (
        telemetry_id TEXT PRIMARY KEY,
        bed_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT,
        timestamp TIMESTAMP NOT NULL,
        heart_rate INTEGER NOT NULL,
        bp_systolic INTEGER NOT NULL,
        bp_diastolic INTEGER NOT NULL,
        map INTEGER NOT NULL,
        spo2 INTEGER NOT NULL,
        respiratory_rate INTEGER NOT NULL,
        etco2 INTEGER,
        cvp INTEGER,
        temperature REAL NOT NULL,
        cardiac_rhythm TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS icu_ventilator_telemetry (
        vent_log_id TEXT PRIMARY KEY,
        bed_id TEXT NOT NULL,
        ventilator_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        mode TEXT NOT NULL,
        fio2_pct INTEGER NOT NULL,
        peep_cmh2o REAL NOT NULL,
        tidal_volume_ml INTEGER NOT NULL,
        minute_volume_l REAL NOT NULL,
        peak_pressure_cmh2o REAL NOT NULL,
        respiratory_rate_actual INTEGER NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS icu_infusion_titrations (
        titration_id TEXT PRIMARY KEY,
        bed_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        drug_name TEXT NOT NULL,
        dose_rate REAL NOT NULL,
        dose_unit TEXT NOT NULL,
        indication TEXT NOT NULL,
        titrated_by TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS icu_abg_reports (
        abg_id TEXT PRIMARY KEY,
        bed_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        ph REAL NOT NULL,
        pco2 REAL NOT NULL,
        po2 REAL NOT NULL,
        hco3 REAL NOT NULL,
        base_excess REAL NOT NULL,
        lactate REAL NOT NULL,
        interpretation TEXT NOT NULL
    );
    """)

    # 6. Operation Theatre
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ot_surgeries (
        surgery_id TEXT PRIMARY KEY,
        ot_room TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        procedure_name TEXT NOT NULL,
        primary_surgeon TEXT NOT NULL,
        anesthesiologist TEXT NOT NULL,
        scheduled_time TIMESTAMP NOT NULL,
        patient_in_time TIMESTAMP,
        knife_to_skin_time TIMESTAMP,
        procedure_end_time TIMESTAMP,
        patient_out_time TIMESTAMP,
        status TEXT NOT NULL,
        preop_diagnosis TEXT,
        postop_diagnosis TEXT,
        delays_recorded TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ot_checklists (
        checklist_id TEXT PRIMARY KEY,
        surgery_id TEXT NOT NULL,
        sign_in_completed INTEGER DEFAULT 1,
        time_out_completed INTEGER DEFAULT 1,
        sign_out_completed INTEGER DEFAULT 1,
        allergy_verified INTEGER DEFAULT 1,
        site_marked INTEGER DEFAULT 1,
        sponge_needle_count_correct INTEGER DEFAULT 1,
        implants_verified INTEGER DEFAULT 1,
        verified_by_nurse TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (surgery_id) REFERENCES ot_surgeries(surgery_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ot_implants (
        implant_id TEXT PRIMARY KEY,
        surgery_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        implant_name TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        lot_number TEXT NOT NULL,
        serial_number TEXT NOT NULL,
        regulatory_barcode TEXT NOT NULL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (surgery_id) REFERENCES ot_surgeries(surgery_id)
    );
    """)

    # 7. Laboratory Information System
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_orders (
        order_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        department TEXT NOT NULL,
        test_name TEXT NOT NULL,
        test_code TEXT NOT NULL,
        urgency TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        order_time TIMESTAMP NOT NULL,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_samples (
        sample_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        tube_barcode TEXT NOT NULL,
        sample_type TEXT NOT NULL,
        phlebotomist_id TEXT NOT NULL,
        collection_time TIMESTAMP NOT NULL,
        transit_time_min INTEGER,
        reception_time TIMESTAMP,
        status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES lab_orders(order_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_results (
        result_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        analyzer_id TEXT NOT NULL,
        parameter_name TEXT NOT NULL,
        numeric_value REAL,
        text_value TEXT,
        unit TEXT,
        reference_range TEXT,
        flag TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        pathologist_verified INTEGER DEFAULT 1,
        FOREIGN KEY (order_id) REFERENCES lab_orders(order_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_critical_alerts (
        alert_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        parameter_name TEXT NOT NULL,
        critical_value TEXT NOT NULL,
        alert_time TIMESTAMP NOT NULL,
        doctor_contacted TEXT NOT NULL,
        doctor_phone TEXT NOT NULL,
        ack_status TEXT NOT NULL,
        ack_time TIMESTAMP
    );
    """)

    # 8. Radiology & Imaging
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiology_orders (
        order_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        modality TEXT NOT NULL,
        body_part TEXT NOT NULL,
        clinical_indication TEXT NOT NULL,
        contrast_needed INTEGER DEFAULT 0,
        urgency TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        order_time TIMESTAMP NOT NULL,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiology_acquisitions (
        study_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        modality TEXT NOT NULL,
        machine_name TEXT NOT NULL,
        technologist_id TEXT NOT NULL,
        dicom_study_uid TEXT NOT NULL,
        series_count INTEGER NOT NULL,
        instances_count INTEGER NOT NULL,
        ctdi_vol_mgy REAL,
        dlp_mgy_cm REAL,
        acquisition_time TIMESTAMP NOT NULL,
        FOREIGN KEY (order_id) REFERENCES radiology_orders(order_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS radiology_reports (
        report_id TEXT PRIMARY KEY,
        study_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        radiologist_name TEXT NOT NULL,
        findings TEXT NOT NULL,
        impression TEXT NOT NULL,
        is_critical_finding INTEGER DEFAULT 0,
        turnaround_time_min INTEGER NOT NULL,
        reported_time TIMESTAMP NOT NULL,
        FOREIGN KEY (study_id) REFERENCES radiology_acquisitions(study_id)
    );
    """)

    # 9. Pharmacy & Cold Chain
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacy_prescriptions (
        intake_id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        doctor_id TEXT NOT NULL,
        drugs_json TEXT NOT NULL,
        status TEXT NOT NULL,
        intake_time TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacy_dispensing (
        dispense_id TEXT PRIMARY KEY,
        intake_id TEXT,
        uhid TEXT NOT NULL,
        drug_name TEXT NOT NULL,
        batch_no TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        qty_dispensed INTEGER NOT NULL,
        pharmacist_name TEXT NOT NULL,
        ddi_warning TEXT,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacy_inventory (
        item_id TEXT PRIMARY KEY,
        drug_name TEXT NOT NULL,
        category TEXT NOT NULL,
        current_stock INTEGER NOT NULL,
        reorder_threshold INTEGER NOT NULL,
        unit_cost_inr REAL NOT NULL,
        batch_no TEXT NOT NULL,
        expiry_date TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacy_cold_chain (
        log_id TEXT PRIMARY KEY,
        fridge_id TEXT NOT NULL,
        temperature_celsius REAL NOT NULL,
        humidity_pct REAL NOT NULL,
        status TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pharmacy_narcotics (
        register_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        drug_name TEXT NOT NULL,
        dose_administered TEXT NOT NULL,
        stock_remaining INTEGER NOT NULL,
        prescribing_doctor TEXT NOT NULL,
        witness_nurse TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 10. Blood Bank (BBIS)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_bank_units (
        unit_barcode TEXT PRIMARY KEY,
        component TEXT NOT NULL,
        blood_group TEXT NOT NULL,
        donation_date TEXT NOT NULL,
        expiry_date TEXT NOT NULL,
        tested_serology_negative INTEGER DEFAULT 1,
        storage_location TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_bank_crossmatch (
        crossmatch_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        unit_barcode TEXT NOT NULL,
        requested_dept TEXT NOT NULL,
        patient_blood_group TEXT NOT NULL,
        compatibility TEXT NOT NULL,
        technician_name TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_bank_issues (
        issue_id TEXT PRIMARY KEY,
        unit_barcode TEXT NOT NULL,
        uhid TEXT NOT NULL,
        destination_dept TEXT NOT NULL,
        issuing_tech TEXT NOT NULL,
        receiving_nurse TEXT NOT NULL,
        issue_time TIMESTAMP NOT NULL,
        bedside_verified INTEGER DEFAULT 1
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blood_bank_temp_logs (
        log_id TEXT PRIMARY KEY,
        equipment TEXT NOT NULL,
        temperature_celsius REAL NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 11. Dialysis Unit
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dialysis_sessions (
        session_id TEXT PRIMARY KEY,
        station_no INTEGER NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        machine_id TEXT NOT NULL,
        dialyzer_model TEXT NOT NULL,
        vascular_access TEXT NOT NULL,
        start_time TIMESTAMP NOT NULL,
        scheduled_duration_hrs REAL NOT NULL,
        blood_flow_rate_qb INTEGER NOT NULL,
        dialysate_flow_qd INTEGER NOT NULL,
        venous_pressure_mmhg INTEGER NOT NULL,
        tmp_mmhg INTEGER NOT NULL,
        conductivity_ms_cm REAL NOT NULL,
        total_uf_removed_ml INTEGER NOT NULL,
        pre_weight_kg REAL NOT NULL,
        post_weight_kg REAL,
        status TEXT NOT NULL
    );
    """)

    # 12. Specialty Clinics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS specialty_records (
        record_id TEXT PRIMARY KEY,
        specialty TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        procedure_or_event TEXT NOT NULL,
        clinical_metrics_json TEXT NOT NULL,
        consultant_name TEXT NOT NULL,
        notes TEXT,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS oncology_chemo_sessions (
        chemo_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        cancer_type TEXT NOT NULL,
        regimen_name TEXT NOT NULL,
        cycle_number INTEGER NOT NULL,
        drugs_infused TEXT NOT NULL,
        adverse_reaction_grade TEXT NOT NULL,
        oncologist_name TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tumor_board_records (
        board_id TEXT PRIMARY KEY,
        case_title TEXT NOT NULL,
        uhid TEXT NOT NULL,
        tumor_type TEXT NOT NULL,
        multidisciplinary_team TEXT NOT NULL,
        consensus_recommendation TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 13. Billing, Insurance & PM-JAY
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS billing_invoices (
        invoice_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        encounter_type TEXT NOT NULL,
        total_amount_inr REAL NOT NULL,
        discount_inr REAL DEFAULT 0,
        net_amount_inr REAL NOT NULL,
        payer_type TEXT NOT NULL,
        payment_status TEXT NOT NULL,
        itemized_breakdown_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insurance_claims (
        claim_id TEXT PRIMARY KEY,
        invoice_id TEXT NOT NULL,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        scheme TEXT NOT NULL,
        preauth_amount_inr REAL NOT NULL,
        claimed_amount_inr REAL NOT NULL,
        approved_amount_inr REAL NOT NULL,
        preauth_code TEXT NOT NULL,
        status TEXT NOT NULL,
        denial_reason TEXT,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 14. Nursing Administration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nursing_rosters (
        roster_id TEXT PRIMARY KEY,
        ward_name TEXT NOT NULL,
        shift TEXT NOT NULL,
        nurse_id TEXT NOT NULL,
        nurse_name TEXT NOT NULL,
        patients_assigned_count INTEGER NOT NULL,
        nurse_to_patient_ratio TEXT NOT NULL,
        date TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nursing_incidents (
        incident_id TEXT PRIMARY KEY,
        ward_name TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT NOT NULL,
        reported_by TEXT NOT NULL,
        investigation_status TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nursing_shift_handovers (
        handover_id TEXT PRIMARY KEY,
        ward_name TEXT NOT NULL,
        outgoing_nurse TEXT NOT NULL,
        incoming_nurse TEXT NOT NULL,
        shift_from_to TEXT NOT NULL,
        verbal_handover_notes TEXT NOT NULL,
        high_risk_patients_json TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 15. Medical Records Department (MRD)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mrd_physical_files (
        file_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        physical_rack_id TEXT NOT NULL,
        box_number TEXT NOT NULL,
        file_status TEXT NOT NULL,
        borrowed_by_dept TEXT,
        borrowed_date TIMESTAMP,
        expected_return TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mrd_mlc_records (
        mlc_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        police_station TEXT NOT NULL,
        fir_number TEXT,
        investigating_officer TEXT,
        injury_category TEXT NOT NULL,
        police_intimation_time TIMESTAMP NOT NULL,
        status TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mrd_death_certificates (
        cert_id TEXT PRIMARY KEY,
        uhid TEXT NOT NULL,
        patient_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        immediate_cause TEXT NOT NULL,
        antecedent_cause TEXT,
        time_of_death TIMESTAMP NOT NULL,
        certifying_doctor TEXT NOT NULL
    );
    """)

    # 16. Biomedical Engineering & Administration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS biomedical_equipment (
        asset_id TEXT PRIMARY KEY,
        equipment_name TEXT NOT NULL,
        department TEXT NOT NULL,
        manufacturer TEXT NOT NULL,
        model TEXT NOT NULL,
        serial_no TEXT NOT NULL,
        status TEXT NOT NULL,
        uptime_pct REAL NOT NULL,
        last_pm_date TEXT NOT NULL,
        next_pm_date TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS biomedical_breakdowns (
        breakdown_id TEXT PRIMARY KEY,
        asset_id TEXT NOT NULL,
        equipment_name TEXT NOT NULL,
        department TEXT NOT NULL,
        reported_fault TEXT NOT NULL,
        priority TEXT NOT NULL,
        reported_at TIMESTAMP NOT NULL,
        engineer_assigned TEXT NOT NULL,
        resolution_time TIMESTAMP,
        status TEXT NOT NULL,
        clinical_impact TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff_master (
        staff_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT NOT NULL,
        council_registration_no TEXT,
        license_valid_until TEXT,
        contact_no TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)

    # 17. Layer 3: Uncaptured Gaps & Clinical Intelligence
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uncaptured_gaps_log (
        gap_id TEXT PRIMARY KEY,
        gap_category TEXT NOT NULL,
        department TEXT NOT NULL,
        uhid TEXT,
        patient_name TEXT,
        summary TEXT NOT NULL,
        structured_data_json TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        timestamp TIMESTAMP NOT NULL
    );
    """)

    # 18. Live Hospital Event Feed (Bus storage)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospital_events_feed (
        event_id TEXT PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        department TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        uhid TEXT,
        patient_name TEXT,
        summary TEXT NOT NULL,
        details_json TEXT NOT NULL
    );
    """)

    # 19. Patient Journey States Tracking (10-State Lifecycle)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_journeys (
        uhid TEXT PRIMARY KEY,
        patient_name TEXT NOT NULL,
        current_state TEXT NOT NULL,
        last_transition_time TIMESTAMP NOT NULL,
        assigned_doctor TEXT,
        ward_name TEXT,
        history_json TEXT,
        FOREIGN KEY (uhid) REFERENCES patients(uhid)
    );
    """)

    # 20. Stateful Workflow Instances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_workflow_instances (
        instance_id TEXT PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        workflow_name TEXT NOT NULL,
        initiator_role TEXT NOT NULL,
        uhid TEXT NOT NULL,
        status TEXT NOT NULL,
        current_step_id TEXT NOT NULL,
        collected_fields_json TEXT NOT NULL,
        missing_fields_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 21. Human Approval Queue (Irreversible Action Gating)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS human_approval_queue (
        approval_id TEXT PRIMARY KEY,
        workflow_instance_id TEXT,
        action_name TEXT NOT NULL,
        patient_uhid TEXT NOT NULL,
        requested_by_role TEXT NOT NULL,
        required_approver_role TEXT NOT NULL,
        action_payload_json TEXT NOT NULL,
        status TEXT NOT NULL,
        decision_by TEXT,
        decision_timestamp TIMESTAMP,
        notes TEXT
    );
    """)

    # 22. Security & Append-Only Audit Log
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_audit_log (
        log_id TEXT PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        user_role TEXT NOT NULL,
        event_type TEXT NOT NULL,
        user_input TEXT,
        intent_classified TEXT,
        tool_called TEXT,
        confidence_score REAL,
        rbac_status TEXT NOT NULL,
        irreversible_gated INTEGER DEFAULT 0,
        security_alert_flag INTEGER DEFAULT 0,
        details_json TEXT
    );
    """)

    # 23. Escalations Log (5 Distinct Human Teams)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS escalations_log (
        escalation_id TEXT PRIMARY KEY,
        ticket_id TEXT,
        timestamp TIMESTAMP NOT NULL,
        trigger_type TEXT NOT NULL,
        target_team_id TEXT NOT NULL,
        target_team_name TEXT NOT NULL,
        urgency_level TEXT NOT NULL,
        summary TEXT NOT NULL,
        brief_text TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully with all 16 departments and tables.")

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Helper to run a SELECT query and return rows as dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def execute_insert(query: str, params: tuple = ()) -> None:
    """Helper to run an INSERT, UPDATE or DELETE query."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
    finally:
        conn.close()

def execute_many(query: str, params_list: List[tuple]) -> None:
    """Helper to run executemany."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()
