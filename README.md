# Saveetha Medical College & Hospital (SMCH) Operations Engine

A 24/7 **live operational data engine and real-time simulation platform** for Saveetha Medical College and Hospital (SMCH) — a 1,600-bed, NABH-accredited, PM-JAY empanelled tertiary teaching hospital with robotic surgery and ECMO capabilities.

---

## 🏥 Hospital Overview & 3-Layer Data Architecture

As catalogued in the SMCH Operations Data Model:

1. **Layer 1 (Structured HIS/LIS/RIS/ERP)**: Registrations, billing invoices, lab analyzer outputs, imaging studies, pharmacy dispensing logs, OT scheduling, and queue tokens.
2. **Layer 2 (Semi-Structured Digital)**: Clinical notes, SOAP ward progress notes, discharge summaries, and PM-JAY / insurance claims.
3. **Layer 3 (Uncaptured Clinical Intelligence & Operational Gaps)**: Clinical reasoning, order-to-execution latency, oral shift handovers, 90% unreported near-misses, paramedic verbal intake remarks, and critical value telephone acknowledgment latencies.

---

## ⚡ Live Simulation Engine & Real-Time Behavior

The background simulation engine (`app/simulation/engine.py`) generates dynamic events in the exact cadence of a live hospital day:
- **Second-by-second ICU Bedside Telemetry**: Real-time multi-parameter streams (HR, Systolic/Diastolic BP, MAP, SpO2, EtCO2, CVP, Temp, Cardiac rhythm).
- **Ventilator Minute Telemetry**: Mechanical ventilation modes (PRVC, SIMV+PS, PSV), FiO2, PEEP, and Tidal Volume.
- **Continuous Environmental IoT Telemetry**: Vaccine/insulin refrigerators (2°C–8°C) and Blood Bank cold chambers (4°C & -20°C).
- **Dialysis Station Telemetry**: 16 stations running live with Blood Flow (Qb), Dialysate Flow (Qd), Venous Pressure, Transmembrane Pressure (TMP), and Ultrafiltration (UF) volume accumulation.
- **Poisson Event Dispatching**: Walk-in emergency triages, 108 ambulance arrivals, OPD consultations with ICD-10 coding, surgical milestone progression (patient-in -> knife-to-skin -> PACU), analyzer processing on Roche Cobas / Sysmex, and PM-JAY claims via the NHA TMS portal.

---

## 🌐 Departmental API Directory & Live Endpoints

All endpoints are live, active, and accessible at `http://localhost:8000`.

### 1. Emergency Department (`/api/emergency`)
- `GET /api/emergency/triage`: Active triage queue categorized by P1 (Resuscitation), P2 (Urgent), P3 (Non-urgent) with time-to-doctor metrics and Glasgow Coma Scale.
- `POST /api/emergency/triage`: Register emergency walk-in or ambulance arrivals.
- `GET /api/emergency/ambulances`: 108 Ambulance arrivals, paramedic notes, and transit vitals.
- `GET /api/emergency/dispositions`: Dispositions (ICU Admission, Ward 5A, Cath Lab, Observation, DAMA).
- `GET /api/emergency/stats`: Live emergency occupancy and door-to-doctor averages.

### 2. Outpatient Department (`/api/opd`)
- `GET /api/opd/registrations`: UHID master registration index and payment classifications.
- `GET /api/opd/tokens`: Active token queues per consultation room across 16+ clinical specialties.
- `GET /api/opd/consultations`: Doctor consultation notes with provisional diagnosis and ICD-10 coding.
- `GET /api/opd/prescriptions`: Digital e-prescriptions issued by OPD consultants.

### 3. Inpatient Department (`/api/ipd`)
- `GET /api/ipd/admissions`: Active admitted inpatient census.
- `GET /api/ipd/beds`: 1,600-bed occupancy tracker across all general wards, special rooms, and HDUs.
- `GET /api/ipd/progress-notes`: Morning and evening consultant ward rounds SOAP notes (Subjective, Objective, Assessment, Plan).
- `GET /api/ipd/nursing-charts`: Ward vital charts (q4h/q8h), intake/output (I/O) fluid balance records.

### 4. ICU & Critical Care (`/api/icu`)
- `GET /api/icu/beds`: Critical care beds with APACHE II and SOFA severity scoring.
- `GET /api/icu/telemetry/live`: Real-time bedside monitor telemetry (HR, BP, SpO2, EtCO2, CVP, Temp).
- `GET /api/icu/ventilators`: Live mechanical ventilator telemetry (mode, FiO2 %, PEEP, tidal volume).
- `GET /api/icu/titration`: Infusion pump titration logs (Noradrenaline, Vasopressin, Propofol, Insulin).
- `GET /api/icu/abg`: Arterial Blood Gas (ABG) panels (pH, pCO2, pO2, HCO3, Base Excess, Lactate).

### 5. Operation Theatre Complex (`/api/ot`)
- `GET /api/ot/schedule`: Master surgical slate across OT 1 to OT 6 (including DaVinci Xi Robotic Suite).
- `GET /api/ot/checklists`: WHO Surgical Safety Checklist compliance (Sign In, Time Out, Sign Out).
- `GET /api/ot/implants`: Regulatory implant and prosthetics tracking (batch number, serial number, lot number, regulatory barcode).

### 6. Laboratory Information System (`/api/laboratory`)
- `GET /api/laboratory/orders`: Lab requisitions across Pathology, Biochemistry, Hematology, Microbiology.
- `GET /api/laboratory/samples`: Phlebotomy barcode logs and courier transit latency tracking.
- `GET /api/laboratory/analyzer-raw`: Raw automated machine results from Roche Cobas 8000 and Sysmex XN-1000 with reference ranges and abnormal flags.
- `GET /api/laboratory/critical-alerts`: Mandatory NABH Critical Value telephone panic alerts.
- `POST /api/laboratory/critical-alerts/{alert_id}/acknowledge`: Doctor telephone acknowledgment log.

### 7. Radiology & Imaging RIS/PACS (`/api/radiology`)
- `GET /api/radiology/orders`: Imaging worklist (CT 128-slice, 3T MRI, Digital X-Ray, Ultrasound).
- `GET /api/radiology/acquisitions`: PACS DICOM study index and radiation dosimetry (CTDIvol mGy, DLP mGy*cm).
- `GET /api/radiology/reports`: Radiologist structured reports, findings, impressions, and turnaround time analytics.

### 8. Pharmacy & Cold Chain (`/api/pharmacy`)
- `GET /api/pharmacy/inventory`: Live stock levels, automated reorder triggers, and expiry tracking.
- `GET /api/pharmacy/dispensing`: Dispensing logs, batch verification, and Drug-Drug Interaction (DDI) checks.
- `GET /api/pharmacy/cold-chain`: Real-time vaccine and biological refrigerator IoT temperature telemetry (2°C–8°C).
- `GET /api/pharmacy/narcotics`: Schedule X controlled substance register (Morphine, Fentanyl) with witness nurse logs.

### 9. Blood Centre BBIS (`/api/blood-bank`)
- `GET /api/blood-bank/inventory`: Component inventory (PRBC, FFP, Platelets, Cryo) by ABO/Rh group.
- `GET /api/blood-bank/crossmatch`: Crossmatch requests and compatibility clearance.
- `GET /api/blood-bank/issues`: Unit issue logs with bedside administration verification.
- `GET /api/blood-bank/temperature-logs`: Cold room and -20°C deep freezer temperature logs.

### 10. Hemodialysis Unit (`/api/dialysis`)
- `GET /api/dialysis/sessions`: 16 hemodialysis stations running live with Blood flow (Qb), Dialysate flow (Qd), Venous pressure, TMP, and accumulated ultrafiltration (UF) volume.

### 11. Specialty Clinics (`/api/specialty`)
- `GET /api/specialty/records`: Cath lab coronary angiograms, endoscopy reports, and neurology studies.
- `GET /api/specialty/oncology/chemotherapy`: Daycare chemotherapy cycles with CTCAE adverse event grading.
- `GET /api/specialty/oncology/tumor-boards`: Multidisciplinary Tumor Board meeting consensus records.

### 12. Billing & PM-JAY Insurance (`/api/billing`)
- `GET /api/billing/invoices`: Itemized hospital invoices broken down by beds, pharmacy, diagnostics, and procedures.
- `GET /api/billing/claims`: PM-JAY (Ayushman Bharat) and private TPA claim status with TMS pre-authorization codes and settled sums.
- `GET /api/billing/revenue-summary`: Revenue cycle and collection breakdown.

### 13. Nursing Administration (`/api/nursing`)
- `GET /api/nursing/rosters`: Shift duty rosters and live nurse-to-patient ratios per ward.
- `GET /api/nursing/handovers`: SBAR shift-to-shift handovers with verbal nuances and high-risk flags.
- `GET /api/nursing/incidents`: NABH incident reports (falls, medication errors, pressure injuries).

### 14. Medical Records Department MRD (`/api/mrd`)
- `GET /api/mrd/mpi`: Master Patient Index search by UHID, patient name, or phone number.
- `GET /api/mrd/physical-files`: Physical paper case file archive rack location and borrowing log.
- `GET /api/mrd/mlc`: Medico-Legal Cases (MLC) register and police station intimations.

### 15. Biomedical Engineering & CMMS (`/api/biomedical`)
- `GET /api/biomedical/equipment`: Critical asset register (DaVinci Xi, MRI, CT, ECMO) with uptime % and calibration dates.
- `GET /api/biomedical/breakdowns`: Equipment breakdown tickets, assigned engineers, and clinical impact logs.
- `GET /api/biomedical/staff`: Staff credentialing master with Tamil Nadu Medical Council license expiry monitoring.

### 16. Layer 3: Uncaptured Clinical Intelligence (`/api/uncaptured-gaps`)
- `GET /api/uncaptured-gaps/all`: Live feed of clinical events unrecorded in traditional HIS.
- `GET /api/uncaptured-gaps/order-execution-latency`: Real-time tracking of delay between doctor orders and nurse administration (e.g. 195 min delay flag).
- `GET /api/uncaptured-gaps/near-misses`: The 90% unreported near-miss events (e.g. LASA drug swaps caught before harm).
- `GET /api/uncaptured-gaps/clinical-reasoning`: Doctor verbal diagnostic rationale and differential decisions.

---

## 🤖 AI Operations Assistant, Second Brain & Security Layer (4-Layer Hackathon Architecture)

Built directly on top of the live hospital simulation substrate matching **[PS Deep Dive Word by Word.md]** and **[Hack to Care Build Plan.pdf]**:

### 17. Workflow Automation Engine (`/api/workflows`)
Configured entirely via JSON definitions in `app/workflows/configs/`:
- `GET /api/workflows/configs`: Inspect all 8 JSON-configured hospital workflows (`admission_workflow`, `consultation_request`, `lab_scan_order`, `medication_dispensing`, `insurance_preauth`, `discharge_workflow`, `billing_checkout`, `surgery_clearance`).
- `GET /api/workflows/configs/{workflow_id}`: Step definitions, required fields, and irreversible action flags.
- `POST /api/workflows/initiate`: Initiates multi-step workflow with **Missing-Field Detection**. If parameters are missing, automatically transitions to `BLOCKED` status and prompts for required fields rather than making unsupported assumptions.
- `POST /api/workflows/advance`: Advances active workflow step upon parameter provision, gating irreversible actions on human verification.
- `GET /api/workflows/active`: Real-time tracking of running workflow instances.
- `GET /api/workflows/escalations`: 5-Team human escalation log with structured briefs and urgency levels.

### 18. Second Brain & Synthetic Knowledge Base (`/api/knowledge`)
- `GET /api/knowledge/articles`: Approved SOP articles and operational guidelines with explicit policy citations (`[SMCH Policy Manual §ADM.101]`, `[NABH Emergency Standards §ED.401]`, `[SMCH Cardiology SOP §CARD.601]`).
- `GET /api/knowledge/workbook`: Complete synthetic workbook containing approved knowledge articles, representative sample requests, routing rules, and field definitions.
- `POST /api/knowledge/query`: Source-grounded RAG retrieval evaluating Prompt Injection, Clinical Boundaries, Irreversible Actions, and communicating uncertainty explicitly when information is incomplete.

### 19. Security, RBAC & Human-in-the-Loop (`/api/security`)
Implements all 6 Agentic Security Defenses:
1. **Prompt Injection & Jailbreak Filter**: Strict data/instruction plane separation blocking DAN mode, instruction overrides, and balance zeroing.
2. **8-Role RBAC Matrix Enforcement**: Fine-grained role permissions for Receptionist, Nurse, Doctor, Specialist, Pharmacist, Lab/Radiology Tech, Billing Staff, Admin.
3. **Clinical Boundary Enforcement**: Automatically guards against autonomous drug dosing, escalating to Clinical Review Board.
4. **Irreversible Action Gating**: High-consequence actions (`discharge_patient`, `approve_insurance_claim`, `cancel_surgery`, `authorize_surgical_entry`) are halted until human clearance.
5. **Grounding Safety Anchors**: Strict citation-grounded RAG preventing hallucinations.
6. **Append-Only Security Audit Log**: Immutable record of user inputs, classified intents, tool calls, and RBAC evaluations.

- `GET /api/security/audit-log`: Immutable security and operations audit ledger.
- `GET /api/security/approvals`: Human Approval Queue for gated irreversible actions.
- `POST /api/security/approvals/{id}/decide`: 1-click Approve / Reject action verifying reviewer role permissions.

### 20. 10-State Comprehensive Patient Journey Pipeline (`/api/patient-journey`)
- `GET /api/patient-journey/states`: Defined 10 lifecycle stages:
  `REGISTERED → TRIAGED → ADMITTED → UNDER_TREATMENT → INVESTIGATION → SURGERY → RECOVERY → DISCHARGE_PENDING → DISCHARGED → FOLLOW_UP`
- `GET /api/patient-journey/census`: Live hospital-wide patient count across all 10 stages.
- `GET /api/patient-journey/active`: Active patient journey tracker.
- `POST /api/patient-journey/transition`: Advance patient lifecycle state with audit validation.

---

## 📡 Real-Time WebSockets & Streaming Feeds

| Stream | Protocol | Description |
| :--- | :--- | :--- |
| `/ws/live` | WebSocket | High-frequency hospital event bus broadcasting all departmental actions |
| `/ws/icu` | WebSocket | Millisecond-level ICU multi-bed telemetry stream (HR, BP, SpO2, EtCO2, Temp) |
| `/api/stream/events` | Server-Sent Events | Standard HTTP SSE stream for browser integrations |
| `/api/stream/recent` | REST GET | Ring buffer of recent hospital events |

---

## 🕹️ Interactive Simulation Controls & Scenario Injection

- `POST /api/simulation/speed?factor={0.5 to 30.0}`: Speed up or slow down simulated hospital clock.
- `POST /api/simulation/trigger-scenario?scenario={name}`:
  - `code_blue`: Cardiac arrest in MICU-02 (Ventricular Fibrillation, CPR team dispatch).
  - `mass_casualty`: NH-48 Highway bus collision alert (6 severe trauma victims via 108 ambulances).
  - `critical_lab_troponin`: STAT High-Sensitivity Troponin I = 4.82 ng/mL panic alert to Cardiologist.
  - `cold_chain_breach`: Vaccine Refrigerator temp spike to 11.4°C compressor alert.
  - `near_miss_intercept`: High-alert Heparin 25,000U vs 5,000U double-check interception.

---

## 🖥️ Running Locally

```bash
# Start live simulation server
python run_server.py
```

- **Operations Command Center UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

