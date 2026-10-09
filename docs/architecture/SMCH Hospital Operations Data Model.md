# SMCH Hospital Operations Data Model

Oct 8, 2026 · @Jaiyantan

## Overview

Saveetha Medical College and Hospital is a NABH-accredited, PM-JAY empanelled tertiary care hospital with 1,500 to 1,700 beds, 30+ clinical departments, and capabilities including robotic surgery and ECMO. If you held all its operations data, you would hold three distinct layers.

The first layer is structured and mostly queryable: patient registrations, billing records, lab results from the LIS, radiology reports from the RIS, pharmacy dispensing logs, OT scheduling, and appointment records. This is what the Hospital Information System (HIS) tracks.

The second layer is semi-structured and partially digital: clinical notes (mix of typed and scanned), discharge summaries, insurance claim records. Queryable with effort, but inconsistent.

The third layer is paper-only or not captured at all: nursing charts, narcotic registers, duty rosters, incident reports, consent forms, MLC records, clinical reasoning, verbal handovers, near-misses, and informal consultant calls.

The agent's value lives in the gap between layers one and three. The departments below are catalogued with: what they do day-to-day, what data they produce, where that data lives today, and what is not captured anywhere.

## Emergency Department

**Day-to-day:** Triage every walk-in and ambulance arrival, assess severity, initiate first-line treatment, decide admission or discharge. Runs 24x7 with separate fast-track and resuscitation bays.

**Data produced:**

- Triage records: arrival time, chief complaint, vitals at arrival, triage score (P1/P2/P3)
- Nurse assessment notes (free text, partially structured)
- Initial doctor orders: investigations, drugs, IV lines
- Time-to-doctor timestamps
- Disposition decisions: admitted, discharged, referred, or DAMA (Discharged Against Medical Advice)
- Ambulance arrival logs: vehicle ID, paramedic notes, transfer-from-hospital details

**Where it lives:** Partially in the HIS. Triage notes are often paper in Indian hospitals. Vitals may sit in a bedside monitoring system that is disconnected from the HIS.

**What is not captured:** The clinical reasoning during triage. Time lost between nurse assessment and doctor review. Paramedic handover information, which is almost always verbal and never written.

## OPD (Outpatient Department)

**Day-to-day:** Register patients, route them to the right specialty, run consultations, issue prescriptions, book follow-ups. Handles the highest patient volume of any department.

**Data produced:**

- Patient registration records: demographics, UHID (Universal Health ID)
- Token and queue allocation logs
- Consultation notes per doctor: complaints, examination findings, diagnosis, ICD-10 code
- Prescription data: drug name, dose, frequency, duration
- Investigation orders: lab tests and imaging requests
- Follow-up appointment records
- Referral letters: to specialist within hospital or outside

**Where it lives:** HIS registration module. Prescriptions are in EMR if digital, otherwise paper. Appointment scheduling is in a separate scheduling module or a spreadsheet.

**What is not captured:** Patient-reported outcomes. Whether the patient actually filled the prescription. No-show reasons for missed appointments.

## IPD (Inpatient Department)

**Day-to-day:** Admit patients, assign beds, run daily ward rounds, manage treatment plans, coordinate investigations, plan discharge.

**Data produced:**

- Admission order: admitting diagnosis, admitting doctor, ward, bed number
- Daily progress notes (SOAP format: Subjective, Objective, Assessment, Plan)
- Nursing charts: vitals every 4 to 8 hours, intake/output records, medication administration records (MAR)
- Ward round notes: doctor, date, clinical findings, plan changes
- Consultant visit notes
- Transfer notes: when patient moves between ward and ICU
- Discharge summary: final diagnosis, procedures done, discharge drugs, follow-up plan

**Where it lives:** EMR if the hospital is digitized. Nursing charts are almost universally paper in Indian hospitals. Discharge summaries are typed in Word and scanned to PDF.

**What is not captured:** Actual nursing workload per patient. Time between a doctor order and nurse execution. Verbal instruction changes that never get written down.

## ICU / Critical Care

**Day-to-day:** Manage ventilated, hemodynamically unstable, or post-surgical critical patients. Continuous monitoring, specialist-driven management, family counseling.

**Data produced:**

- Ventilator parameters: mode, FiO2, PEEP, tidal volume, logged by the machine every minute
- Continuous vitals from bedside monitors: HR, BP, SpO2, EtCO2, CVP
- Hourly nursing assessment notes
- Fluid balance charts: input and output tracked every hour
- Sedation and vasopressor titration logs
- ABG (Arterial Blood Gas) results and trending
- APACHE II and SOFA illness severity scores
- Family counseling records
- ICU discharge or death summaries

**Where it lives:** Bedside monitors store data locally in the machine. Almost no Indian ICU has these feeds integrated into the HIS. Data is manually transcribed from monitor to paper chart.

**What is not captured:** The gap between what the monitor shows and what actually gets written. Clinical decision reasoning. Near-miss events, which go almost entirely unreported.

## Operation Theatre

**Day-to-day:** Schedule surgeries, conduct pre-op assessment, perform procedures, send patients to recovery. SMCH has robotic surgery capability.

**Data produced:**

- OT scheduling records: procedure type, surgeon, OT number, scheduled time
- Pre-op checklist: fasting status, consent, site marking, allergy verification
- Anaesthesia record: drug doses, airway management, intra-op vitals minute by minute
- Operative notes: what was done, findings, implants used with batch numbers
- Implant and device tracking: serial numbers, vendor, lot number (regulatory requirement)
- Post-op nursing notes: recovery vitals, pain score, nausea
- Time logs: patient-in, knife-to-skin, procedure-end, patient-out
- Surgical count records: sponges and instruments counted before and after

**Where it lives:** OT scheduling is in HIS. Anaesthesia record is paper in most hospitals. Operative notes are dictated or typed. Implant records are often in a separate paper register.

**What is not captured:** Delays in OT start time and their reasons. Instrument tracking beyond the count sheet. Post-op pain scores are rarely digitized.

## Laboratory

**Day-to-day:** Receive samples, process tests across Pathology, Microbiology, Biochemistry, and Haematology, report results back to the requesting clinician.

**Data produced:**

- Test orders: test name, urgency, requesting doctor, patient ID
- Sample collection logs: phlebotomist ID, time of collection, sample type, tube type
- Sample transport logs: time in transit, temperature if required
- Analyzer raw output: machine-generated numeric results with reference ranges
- Pathologist and microbiologist reports: culture results, sensitivity patterns, histopathology findings
- Critical value alerts: when a result crosses a dangerous threshold, a phone call to the doctor is mandated
- Quality control logs: daily QC runs on analyzers

**Where it lives:** LIS (Laboratory Information System), often separate from the HIS. Analyzer outputs integrate via HL7. Microbiology culture results may be in a separate register.

**What is not captured:** Time from order to collection. Time from collection to result. Whether the critical value alert actually reached the doctor and when.

## Radiology and Imaging

**Day-to-day:** Receive imaging requests, acquire images (X-ray, CT, MRI, USG, Interventional Radiology), have radiologists report, send reports back to the requesting clinician.

**Data produced:**

- Radiology order records: modality, body part, clinical indication, contrast or no contrast
- Image acquisition metadata: machine used, technologist, acquisition parameters, time
- DICOM image files: the actual images, extremely large, stored in PACS
- Radiologist reports: structured or free text, with findings and impression
- Turnaround time logs: order-to-acquisition and acquisition-to-report
- Radiation dose records: CT dose index, a regulatory requirement

**Where it lives:** RIS (Radiology Information System) for workflow. PACS (Picture Archiving and Communication System) for images. Reports may be in HIS or a separate document system.

**What is not captured:** Communication between radiologist and clinician when a finding is unexpected. Peer review of reports. Equipment downtime and its downstream patient impact.

## Pharmacy

**Day-to-day:** Receive prescriptions, validate them, dispense drugs to wards and outpatients, manage inventory.

**Data produced:**

- Prescription intake records: inpatient indent and outpatient prescription
- Dispensing records: drug, batch number, expiry, quantity dispensed, pharmacist ID, time
- Drug-drug interaction and allergy check logs (if system-supported)
- Inventory records: stock levels, reorder triggers, expiry tracking
- Cold chain logs: for vaccines and biologicals requiring refrigeration
- Return and wastage records
- Narcotic and controlled substance register: legally mandated, always paper

**Where it lives:** Pharmacy Management System or HIS pharmacy module. Inventory in a separate ERP. Narcotic register is always paper by regulation.

**What is not captured:** Whether the dispensed drug was actually administered. Near-miss dispensing errors. Patient counseling time.

## Blood Bank

**Day-to-day:** Screen donors, test and process units, store inventory, crossmatch and issue to patients.

**Data produced:**

- Donor records: demographics, donation history, deferral reasons
- Blood unit processing records: group, type, component, tested for HIV/HBV/HCV/Malaria/Syphilis
- Crossmatch request and result records
- Issue records: unit number, patient, ward, issuing technician, time
- Temperature monitoring logs: 2 to 6C for RBCs, -18C for FFP
- Transfusion reaction reports: when a patient reacts to a unit
- Wastage and discard records

**Where it lives:** BBIS (Blood Bank Information System), often standalone and not integrated with the main HIS. Crossmatch results may be paper.

**What is not captured:** Whether the transfusion was actually administered at the bedside. Post-transfusion response. Time from issue to bedside.

## Dialysis Unit

**Day-to-day:** Run scheduled and acute hemodialysis sessions for patients with kidney failure. SMCH has a Nephrology department with dialysis services.

**Data produced:**

- Session records: patient, machine number, date, duration, access used
- Pre and post vitals: weight, BP, pulse
- Dialysate parameters: bicarbonate, conductivity, flow rates
- Machine logs: auto-generated by the dialysis machine per session
- Complication logs: intradialytic hypotension, cramps, access issues
- Cumulative session count per patient

**Where it lives:** Dialysis machine internal memory. Manually transcribed to paper in most units. Rarely integrated with the HIS.

**What is not captured:** Vascular access long-term outcomes. Adequacy of dialysis trending over time. Patient symptoms between sessions.

## Specialty Clinics

SMCH runs specialist outpatient and procedure clinics across Cardiology, Neurology, Oncology, Nephrology, Gastroenterology, Rheumatology, Pulmonology, Dermatology, Ophthalmology, ENT, Psychiatry, and more.

**Day-to-day:** Specialist consultations, procedure clinics, chemotherapy infusion sessions, follow-up appointments, tumor board meetings.

**Data produced:**

- Specialist consultation notes with subspecialty-specific structured fields (e.g., cardiology: NYHA class, LVEF; oncology: cancer staging, regimen name, cycle number)
- Procedure reports: cardiac catheterization, endoscopy, bronchoscopy
- Echo, EEG, EMG reports
- Chemotherapy administration records: drug, dose, route, infusion time, adverse effects
- Tumor board meeting records: multidisciplinary decision documentation

**Where it lives:** EMR if integrated. Otherwise specialty-specific paper registers or Word documents stored locally on clinic computers.

**What is not captured:** Tumor board verbal discussions. Adverse event grading consistency across oncology cycles. Ophthalmology and ENT procedural findings are often recorded in proprietary equipment formats that never reach the HIS.

## Billing and Insurance

**Day-to-day:** Generate itemized bills, process insurance claims, collect payments, reconcile accounts. SMCH is PM-JAY empanelled.

**Data produced:**

- Itemized bill records: every service, drug, consumable, and procedure billed
- Insurance pre-authorization records: insurer, policy number, approved amount, approval code
- Claim submission records: submitted date, claim amount, supporting documents
- Payment receipt records: mode of payment, amount, date
- Rejection and re-submission records
- TPA (Third Party Administrator) correspondence
- PM-JAY claim records: submitted through the NHA portal
- Daily collection reports

**Where it lives:** Hospital ERP or HIS billing module. Insurance claims go through insurer portals. PM-JAY claims go through the National Health Authority portal.

**What is not captured:** Time from service delivery to billing. Denial reasons in a structured format. Patient financial distress signals that lead to treatment abandonment.

## Nursing Administration

**Day-to-day:** Manage nurse-to-patient ratios, shift scheduling, skill assignments, training, and incident reporting across all wards.

**Data produced:**

- Duty roster records
- Nurse-to-patient ratio logs per ward per shift
- Incident reports: patient falls, medication errors, pressure injuries
- Nursing competency assessment records
- In-service training attendance logs

**Where it lives:** HR system for rosters. Incident reports are paper in almost all Indian hospitals.

**What is not captured:** Actual nursing workload per patient (not just the ratio). The content of verbal handovers between shifts. Near-miss events, which are systematically underreported.

## Medical Records Department (MRD)

**Day-to-day:** Maintain the master patient index, manage physical case files, issue medical certificates, handle medico-legal cases.

**Data produced:**

- UHID (Universal Health ID) master register
- Case file tracking logs: file location, borrowing records
- Death certificate records
- MLC (Medico-Legal Case) records
- Discharge summary repository
- ICD-10 coding records per episode

**Where it lives:** HIS master patient index. Physical files in a rack system. MLC records are paper with legal custody requirements.

**What is not captured:** File retrieval time and delays. ICD-10 coding accuracy rates. MLC case outcomes and legal follow-up.

## Administration and HR

**Day-to-day:** Manage staff records, payroll, credentialing, vendor contracts, regulatory compliance filings, and equipment maintenance.

**Data produced:**

- Staff master records: doctor, nurse, technician, support staff
- Attendance and leave records
- Medical council registration and renewal records
- Vendor contracts and SLAs
- NABH audit records and non-conformance reports
- Equipment maintenance logs: preventive maintenance schedules and breakdown records

**Where it lives:** HR software, sometimes Excel. Credentialing is paper files. Maintenance logs are in a separate CMMS (Computerized Maintenance Management System) or paper.

**What is not captured:** Doctor credentialing gaps until the next renewal. Equipment downtime linked to clinical impact. Vendor SLA breach follow-up.

## What Is NOT Captured Anywhere

This is the most important column for your agent. These gaps are where the intelligence layer adds value, because the HIS has no record of any of them.

| Gap | Department | Why It Matters |
| --- | --- | --- |
| Clinical reasoning behind a decision | All clinical | Doctor's thought process is verbal, never documented |
| Time between order and nurse execution | IPD, ICU | Order placed at 10am, drug given at 2pm, nobody tracked this |
| Verbal shift handover content | Nursing, ICU | Shift handovers are oral, nothing is written |
| Patient-reported outcomes | OPD, Discharge | How the patient felt after discharge is never fed back |
| Near-miss events | All departments | 90% go unreported in Indian hospitals |
| Equipment downtime impact on patients | Radiology, OT, ICU | Tracked in maintenance, never linked to clinical records |
| Informal consultant calls | All clinical | Doctor calls a colleague, acts on advice, no note exists |
| Care coordination gaps | IPD, Discharge | Who was supposed to follow up and whether they did |
| Paramedic handover at emergency | Emergency | Verbal at ambulance bay, no structured record |
| Tumor board verbal decisions | Oncology | Only the final decision is recorded, not the discussion |
| Critical value alert receipt confirmation | Lab | Whether the alert actually reached the doctor and when |
| Transfusion bedside administration | Blood Bank | Unit issued from bank but never confirmed as given |
| Dialysis adequacy trending | Nephrology | Machine logs exist but are not analyzed longitudinally |

These gaps define the simulation's hard problems. An agent operating on the structured layer must know when to flag that a critical piece of state is missing from a workflow, rather than silently proceeding on incomplete information.
