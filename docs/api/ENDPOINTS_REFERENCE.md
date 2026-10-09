# SMCH Operations Engine — Complete API Reference & Endpoint Catalog

Comprehensive directory of all 23 departmental, simulation, stream, and governance API endpoints for the Saveetha Medical College & Hospital (SMCH) Operations Engine.

---

## 1. Emergency Department (`/api/emergency`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/emergency/triage` | Active triage queue categorized by P1 (Resuscitation), P2 (Urgent), P3 (Non-urgent) with time-to-doctor metrics and GCS score. |
| `POST` | `/api/emergency/triage` | Register emergency walk-in or ambulance arrivals. |
| `GET` | `/api/emergency/ambulances` | 108 Ambulance arrivals, paramedic notes, and transit vitals. |
| `GET` | `/api/emergency/dispositions` | Dispositions (ICU Admission, Ward 5A, Cath Lab, Observation, DAMA). |
| `GET` | `/api/emergency/stats` | Live emergency occupancy and door-to-doctor averages. |

---

## 2. Outpatient Department (`/api/opd`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/opd/registrations` | UHID master registration index and payment classifications. |
| `GET` | `/api/opd/tokens` | Active token queues per consultation room across 16+ clinical specialties. |
| `GET` | `/api/opd/consultations` | Doctor consultation notes with provisional diagnosis and ICD-10 coding. |
| `GET` | `/api/opd/prescriptions` | Digital e-prescriptions issued by OPD consultants. |

---

## 3. Inpatient Department (`/api/ipd`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/ipd/admissions` | Active admitted inpatient census across all wards. |
| `GET` | `/api/ipd/beds` | 1,600-bed occupancy tracker across all general wards, special rooms, and HDUs. |
| `GET` | `/api/ipd/progress-notes` | Morning and evening consultant ward rounds SOAP notes (Subjective, Objective, Assessment, Plan). |
| `GET` | `/api/ipd/nursing-charts` | Ward vital charts (q4h/q8h), intake/output (I/O) fluid balance records. |

---

## 4. ICU & Critical Care (`/api/icu`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/icu/beds` | Critical care beds with APACHE II and SOFA severity scoring. |
| `GET` | `/api/icu/telemetry/live` | Real-time bedside monitor telemetry (HR, BP, SpO2, EtCO2, CVP, Temp). |
| `GET` | `/api/icu/ventilators` | Live mechanical ventilator telemetry (mode, FiO2 %, PEEP, tidal volume). |
| `GET` | `/api/icu/titration` | Infusion pump titration logs (Noradrenaline, Vasopressin, Propofol, Insulin). |
| `GET` | `/api/icu/abg` | Arterial Blood Gas (ABG) panels (pH, pCO2, pO2, HCO3, Base Excess, Lactate). |

---

## 5. Operation Theatre Complex (`/api/ot`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/ot/schedule` | Master surgical slate across OT 1 to OT 6 (including DaVinci Xi Robotic Suite). |
| `GET` | `/api/ot/checklists` | WHO Surgical Safety Checklist compliance (Sign In, Time Out, Sign Out). |
| `GET` | `/api/ot/implants` | Regulatory implant and prosthetics tracking (batch number, serial number, lot number, regulatory barcode). |

---

## 6. Laboratory Information System (`/api/laboratory`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/laboratory/orders` | Lab requisitions across Pathology, Biochemistry, Hematology, Microbiology. |
| `GET` | `/api/laboratory/samples` | Phlebotomy barcode logs and courier transit latency tracking. |
| `GET` | `/api/laboratory/analyzer-raw` | Raw automated machine results from Roche Cobas 8000 and Sysmex XN-1000 with reference ranges and abnormal flags. |
| `GET` | `/api/laboratory/critical-alerts` | Mandatory NABH Critical Value telephone panic alerts. |
| `POST` | `/api/laboratory/critical-alerts/{alert_id}/acknowledge` | Doctor telephone acknowledgment log. |

---

## 7. Radiology & Imaging RIS/PACS (`/api/radiology`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/radiology/orders` | Imaging worklist (CT 128-slice, 3T MRI, Digital X-Ray, Ultrasound). |
| `GET` | `/api/radiology/acquisitions` | PACS DICOM study index and radiation dosimetry (CTDIvol mGy, DLP mGy*cm). |
| `GET` | `/api/radiology/reports` | Radiologist structured reports, findings, impressions, and turnaround time analytics. |

---

## 8. Pharmacy & Cold Chain (`/api/pharmacy`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/pharmacy/inventory` | Live stock levels, automated reorder triggers, and expiry tracking. |
| `GET` | `/api/pharmacy/dispensing` | Dispensing logs, batch verification, and Drug-Drug Interaction (DDI) checks. |
| `GET` | `/api/pharmacy/cold-chain` | Real-time vaccine and biological refrigerator IoT temperature telemetry (2°C–8°C). |
| `GET` | `/api/pharmacy/narcotics` | Schedule X controlled substance register (Morphine, Fentanyl) with witness nurse logs. |

---

## 9. Blood Centre BBIS (`/api/blood-bank`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/blood-bank/inventory` | Component inventory (PRBC, FFP, Platelets, Cryo) by ABO/Rh group. |
| `GET` | `/api/blood-bank/crossmatch` | Crossmatch requests and compatibility clearance. |
| `GET` | `/api/blood-bank/issues` | Unit issue logs with bedside administration verification. |
| `GET` | `/api/blood-bank/temperature-logs` | Cold room and -20°C deep freezer temperature logs. |

---

## 10. Hemodialysis Unit (`/api/dialysis`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/dialysis/sessions` | 18 hemodialysis stations running live with Blood flow (Qb), Dialysate flow (Qd), Venous pressure, TMP, and accumulated ultrafiltration (UF) volume. |

---

## 11. Specialty Clinics (`/api/specialty`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/specialty/records` | Cath lab coronary angiograms, endoscopy reports, and neurology studies. |
| `GET` | `/api/specialty/oncology/chemotherapy` | Daycare chemotherapy cycles with CTCAE adverse event grading. |
| `GET` | `/api/specialty/oncology/tumor-boards` | Multidisciplinary Tumor Board meeting consensus records. |

---

## 12. Billing & PM-JAY Insurance (`/api/billing`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/billing/invoices` | Itemized hospital invoices broken down by beds, pharmacy, diagnostics, and procedures. |
| `GET` | `/api/billing/claims` | PM-JAY (Ayushman Bharat) and private TPA claim status with TMS pre-authorization codes and settled sums. |
| `GET` | `/api/billing/revenue-summary` | Revenue cycle and collection breakdown. |

---

## 13. Nursing Administration (`/api/nursing`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/nursing/rosters` | Shift duty rosters and live nurse-to-patient ratios per ward. |
| `GET` | `/api/nursing/handovers` | SBAR shift-to-shift handovers with verbal nuances and high-risk flags. |
| `GET` | `/api/nursing/incidents` | NABH incident reports (falls, medication errors, pressure injuries). |

---

## 14. Medical Records Department MRD (`/api/mrd`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/mrd/mpi` | Master Patient Index search by UHID, patient name, or phone number. |
| `GET` | `/api/mrd/physical-files` | Physical paper case file archive rack location and borrowing log. |
| `GET` | `/api/mrd/mlc` | Medico-Legal Cases (MLC) register and police station intimations. |

---

## 15. Biomedical Engineering & CMMS (`/api/biomedical`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/biomedical/equipment` | Critical asset register (DaVinci Xi, MRI, CT, ECMO) with uptime % and calibration dates. |
| `GET` | `/api/biomedical/breakdowns` | Equipment breakdown tickets, assigned engineers, and clinical impact logs. |
| `GET` | `/api/biomedical/staff` | Staff credentialing master with Tamil Nadu Medical Council license expiry monitoring. |

---

## 16. Layer 3: Uncaptured Clinical Intelligence (`/api/uncaptured-gaps`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/uncaptured-gaps/all` | Live feed of clinical events unrecorded in traditional HIS. |
| `GET` | `/api/uncaptured-gaps/order-execution-latency` | Real-time tracking of delay between doctor orders and nurse administration (e.g. 195 min delay flag). |
| `GET` | `/api/uncaptured-gaps/near-misses` | The 90% unreported near-miss events (e.g. LASA drug swaps caught before harm). |
| `GET` | `/api/uncaptured-gaps/clinical-reasoning` | Doctor verbal diagnostic rationale and differential decisions. |

---

## 17. Workflow Automation Engine (`/api/workflows`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/workflows/configs` | Inspect all 8 JSON-configured hospital workflows (`admission_workflow`, `consultation_request`, `lab_scan_order`, `medication_dispensing`, `insurance_preauth`, `discharge_workflow`, `billing_checkout`, `surgery_clearance`). |
| `GET` | `/api/workflows/configs/{workflow_id}` | Step definitions, required fields, and irreversible action flags. |
| `POST` | `/api/workflows/initiate` | Initiates multi-step workflow with **Missing-Field Detection**. |
| `POST` | `/api/workflows/advance` | Advances active workflow step upon parameter provision, gating irreversible actions on human verification. |
| `GET` | `/api/workflows/active` | Real-time tracking of running workflow instances. |
| `GET` | `/api/workflows/escalations` | 5-Team human escalation log with structured briefs and urgency levels. |

---

## 18. Second Brain & Knowledge Base (`/api/knowledge`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/knowledge/articles` | Approved SOP articles and operational guidelines with explicit policy citations (`[SMCH Policy Manual §ADM.101]`, etc.). |
| `GET` | `/api/knowledge/workbook` | Complete synthetic workbook containing approved knowledge articles, representative sample requests, routing rules, and field definitions. |
| `POST` | `/api/knowledge/query` | Source-grounded RAG retrieval evaluating Prompt Injection, Clinical Boundaries, Irreversible Actions, and communicating uncertainty explicitly. |

---

## 19. Security, RBAC & Human-in-the-Loop (`/api/security`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/security/audit-log` | Immutable security and operations audit ledger. |
| `GET` | `/api/security/approvals` | Human Approval Queue for gated irreversible actions. |
| `POST` | `/api/security/approvals/{id}/decide` | 1-click Approve / Reject action verifying reviewer role permissions. |

---

## 20. 10-State Comprehensive Patient Journey Pipeline (`/api/patient-journey`)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/patient-journey/states` | Defined 10 lifecycle stages (`REGISTERED` through `FOLLOW_UP`). |
| `GET` | `/api/patient-journey/census` | Live hospital-wide patient count across all 10 stages. |
| `GET` | `/api/patient-journey/active` | Active patient journey tracker. |
| `POST` | `/api/patient-journey/transition` | Advance patient lifecycle state with audit validation. |

---

## 21. Real-Time WebSockets & Streaming Feeds

| Stream | Protocol | Description |
| :--- | :--- | :--- |
| `/ws/live` | WebSocket | High-frequency hospital event bus broadcasting all departmental actions. |
| `/ws/icu` | WebSocket | Millisecond-level ICU multi-bed telemetry stream (HR, BP, SpO2, EtCO2, Temp). |
| `/api/stream/events` | SSE | Standard HTTP Server-Sent Events stream for browser integrations. |
| `/api/stream/recent` | REST GET | Ring buffer of recent hospital events. |

---

## 22. Baseline Static RBAC Endpoints (`/` root & baseline)

| Method | Endpoint | Required Permission | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/patient/{uhid}` | `patient:read` | Patient profile lookup. |
| `GET` | `/patient/search` | `patient:read` | Patient search by query. |
| `GET` | `/admission/{admission_id}` | `admission:read` | Admission record lookup. |
| `GET` | `/admissions` | `admission:read` | Admissions filtered by status. |
| `GET` | `/beds/available` | `bed:read` | Available beds filtered by ward. |
| `GET` | `/bill/{uhid}` | `billing:read` | Itemized bill lookup. |
| `GET` | `/insurance/{uhid}` | `insurance:read` | Insurance claim status. |
| `GET` | `/tickets` | `ticket:read` | Operational ticket queue. |
| `GET` | `/audit` | `audit:read` | Security and event audit trail. |
| `POST` | `/audit` | `audit:write` | Write audit entry. |
| `GET` | `/pending_approvals` | `approval:read` | Pending approval queue. |
| `POST` | `/pending_approvals` | `approval:write` | Submit pending approval. |
| `GET` | `/api/stats` | None (Public) | Summary row counts across tables. |
| `GET` | `/api/tables/{table_name}` | None (Public) | Table inspector for debugging. |

---

## 23. Operational Ontology & Governed Agent Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/ontology` | Interactive Vis.js Knowledge Graph Command Center. |
| `GET` | `/api/v1/ontology/graph/live` | Perspective graph data (`bottlenecks`, `patient_360`, `beds`, `governance`). |
| `GET` | `/api/v1/ontology/bottlenecks` | Real-time cross-departmental bottleneck radar. |
| `POST` | `/api/v1/ontology/sync` | Re-sync full graph pipeline into Kùzu & LanceDB. |
| `POST` | `/api/v1/agent/query` | Natural language operational assistant query with policy citations & safety gating. |
| `GET` | `/dashboard` | Hospital Operations Command Center HTML dashboard. |
| `GET` | `/api/v1/dashboard/live` | Real-time telemetry feed for dashboard UI. |
