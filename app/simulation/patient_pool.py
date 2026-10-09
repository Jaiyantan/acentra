"""
Master Clinical Pools, Realistic Indian Names, Doctors, Specialties, and Drugs
Saveetha Medical College and Hospital (SMCH) Operations Engine
"""

import random

FIRST_NAMES = [
    "Murugan", "Priya", "Ramachandran", "Lakshmi", "Jayakumar", "Karthik", "Meenakshi", 
    "Saravanan", "Devi", "Subramanian", "Anand", "Divya", "Suresh", "Kavitha", "Vignesh", 
    "Bhuvaneshwari", "Balaji", "Deepa", "Manikandan", "Sangeetha", "Ramesh", "Revathi", 
    "Aravind", "Gayathri", "Dinesh", "Shanthi", "Praveen", "Malathi", "Ganesh", "Poornima",
    "Mohamed", "Fatima", "Arun", "Saraswathi", "Gopal", "Vijayalakshmi", "Senthil", "Usha",
    "Rajesh", "Kalyani", "Naveen", "Swetha", "Venkatesh", "Pavithra", "Selvam", "Geetha"
]

LAST_NAMES = [
    "Kuppuswamy", "Natarajan", "Sundaram", "Krishnan", "Iyer", "Rao", "Pillai", "Mudaliar",
    "Chettiar", "Gounder", "Naidu", "Reddy", "Verma", "Menon", "Nair", "Babu", "Chari",
    "Swaminathan", "Venkataraman", "Pandian", "Sethuraman", "Ranganathan", "Thyagarajan"
]

INSURANCE_TYPES = [
    "PM-JAY (Ayushman Bharat)",
    "PM-JAY (Ayushman Bharat)",
    "CMCHIS (Tamil Nadu Govt)",
    "Star Health Insurance (TPA)",
    "ICICI Lombard Health (TPA)",
    "HDFC ERGO General Insurance",
    "Self-Paying (Cash/UPI)"
]

DOCTORS = [
    {"id": "DOC-CARD-01", "name": "Dr. R. Shanmugam", "dept": "Cardiology", "phone": "+91-98401-22301"},
    {"id": "DOC-CARD-02", "name": "Dr. P. Sundararajan", "dept": "Cardiology", "phone": "+91-98401-22302"},
    {"id": "DOC-EMERG-01", "name": "Dr. K. Venkatraman", "dept": "Emergency Medicine", "phone": "+91-98401-22310"},
    {"id": "DOC-EMERG-02", "name": "Dr. T. Hariprasad", "dept": "Emergency Medicine", "phone": "+91-98401-22311"},
    {"id": "DOC-ICU-01", "name": "Dr. A. Shalini", "dept": "Critical Care Medicine", "phone": "+91-98401-22320"},
    {"id": "DOC-ICU-02", "name": "Dr. C. Mohan Raj", "dept": "Critical Care Medicine", "phone": "+91-98401-22321"},
    {"id": "DOC-SURG-01", "name": "Dr. M. Jayaprakash", "dept": "General & Laparoscopic Surgery", "phone": "+91-98401-22330"},
    {"id": "DOC-SURG-02", "name": "Dr. G. Radhakrishnan", "dept": "Surgical Oncology", "phone": "+91-98401-22331"},
    {"id": "DOC-ORTHO-01", "name": "Dr. S. Senthil Kumar", "dept": "Orthopedics & Joint Replacement", "phone": "+91-98401-22340"},
    {"id": "DOC-NEPH-01", "name": "Dr. V. Balaji", "dept": "Nephrology", "phone": "+91-98401-22350"},
    {"id": "DOC-NEUR-01", "name": "Dr. K. Anand Babu", "dept": "Neurology", "phone": "+91-98401-22360"},
    {"id": "DOC-GAST-01", "name": "Dr. D. Chandrasekar", "dept": "Gastroenterology", "phone": "+91-98401-22370"},
    {"id": "DOC-PULM-01", "name": "Dr. N. Vijay", "dept": "Pulmonology & Chest Medicine", "phone": "+91-98401-22380"},
    {"id": "DOC-ANES-01", "name": "Dr. S. Anitha", "dept": "Anesthesiology", "phone": "+91-98401-22390"},
    {"id": "DOC-RAD-01", "name": "Dr. L. Balamurugan", "dept": "Radiology & Imaging", "phone": "+91-98401-22401"},
    {"id": "DOC-PATH-01", "name": "Dr. Meera Vasudevan", "dept": "Pathology & Transfusion", "phone": "+91-98401-22410"}
]

WARDS = [
    "Triage - Resuscitation Bay",
    "Triage - Acute Bay",
    "MICU - Medical Intensive Care",
    "SICU - Surgical Intensive Care",
    "CCU - Coronary Care Unit",
    "Neuro ICU",
    "Ward 3A - Male General Medical",
    "Ward 3B - Female General Medical",
    "Ward 4A - General Surgery Post-Op",
    "Ward 5A - Orthopedics & Trauma",
    "Ward 6A - Super Specialty PM-JAY",
    "Ward 7B - Private Deluxe Ward",
    "Dialysis Day Care Suite",
    "Daycare Chemotherapy Infusion"
]

OT_ROOMS = [
    {"id": "OT-01", "name": "General Laparoscopy Suite", "type": "General"},
    {"id": "OT-02", "name": "Orthopedic Laminar Flow OT", "type": "Ortho"},
    {"id": "OT-03", "name": "Neurosurgery Micro-OT", "type": "Neuro"},
    {"id": "OT-04", "name": "DaVinci Xi Robotic Surgery Suite", "type": "Robotic"},
    {"id": "OT-05", "name": "Cardiothoracic Bypass OT", "type": "Cardiac"},
    {"id": "OT-06", "name": "Emergency 24x7 Trauma OT", "type": "Trauma"}
]

ICU_BED_IDS = [
    "MICU-01", "MICU-02", "MICU-03", "MICU-04",
    "SICU-01", "SICU-02", "SICU-03", "SICU-04",
    "CCU-01",  "CCU-02",  "CCU-03",  "CCU-04"
]

DIALYSIS_STATIONS = [f"STATION-{i:02d}" for i in range(1, 17)]

CLINICAL_SCENARIOS = [
    {
        "dept": "Cardiology",
        "complaint": "Acute onset crushing retrosternal chest pain radiating to left arm with diaphoresis",
        "diagnosis": "Acute Anterior Wall ST-Elevation Myocardial Infarction (STEMI)",
        "icd10": "I21.0",
        "triage": "P1",
        "stat_tests": ["High Sensitivity Troponin I", "12-Lead ECG", "Serum Electrolytes", "Echocardiogram"],
        "critical_parameter": "Troponin I",
        "critical_val": "2.85 ng/mL",
        "surgery": "Emergency Primary Percutaneous Coronary Intervention (PTCA) with Drug Eluting Stent",
        "implant": "Resolute Onyx 3.0 x 24mm Zotarolimus-Eluting Stent"
    },
    {
        "dept": "Neurology",
        "complaint": "Sudden onset right-sided hemiparesis with slurred speech and facial droop since 45 mins",
        "diagnosis": "Acute Ischemic Stroke within Thrombolytic Window",
        "icd10": "I63.9",
        "triage": "P1",
        "stat_tests": ["NCCT Brain Emergency", "Blood Glucose STAT", "PT/INR", "CBC"],
        "critical_parameter": "INR",
        "critical_val": "1.05",
        "surgery": "Mechanical Thrombectomy / IV Alteplase Thrombolysis Protocol",
        "implant": "Solitaire 2 Revascularization Device 4x20mm"
    },
    {
        "dept": "Trauma & Ortho",
        "complaint": "RTA on NH-48 highway, severe deformity of right thigh with bone protrusion and hypotension",
        "diagnosis": "Grade 3B Open Fracture Right Femur Shaft with Hypovolemic Shock",
        "icd10": "S72.301B",
        "triage": "P1",
        "stat_tests": ["X-Ray Pelvis & Right Thigh AP/Lat", "Crossmatch 4 Units PRBC", "CBC", "ABG"],
        "critical_parameter": "Hemoglobin",
        "critical_val": "6.2 g/dL",
        "surgery": "Emergency Wound Debridement and External Fixator Placement",
        "implant": "AO Modular Large Fragment External Fixator System"
    },
    {
        "dept": "Gastroenterology",
        "complaint": "Massive hematemesis (2 episodes) with melena, known case of Chronic Liver Disease",
        "diagnosis": "Upper GI Bleed secondary to Bleeding Esophageal Varices",
        "icd10": "I85.01",
        "triage": "P1",
        "stat_tests": ["Emergency Upper GI Endoscopy", "Crossmatch 2 Units PRBC", "LFT", "Platelet Count"],
        "critical_parameter": "Platelets",
        "critical_val": "34,000 /uL",
        "surgery": "Endoscopic Variceal Ligation (EVL Banding)",
        "implant": "Multi-Band Ligator 6-Band Kit"
    },
    {
        "dept": "Pulmonology",
        "complaint": "Severe breathlessness, cough with purulent expectoration, high fever, SpO2 84% on room air",
        "diagnosis": "Severe Community Acquired Pneumonia with Type 1 Respiratory Failure",
        "icd10": "J18.9",
        "triage": "P2",
        "stat_tests": ["Arterial Blood Gas (ABG)", "Chest X-Ray PA", "Blood Sputum Culture", "CRP"],
        "critical_parameter": "pO2 (ABG)",
        "critical_val": "52 mmHg",
        "surgery": "Non-Invasive High Flow Nasal Cannula / Endotracheal Intubation Protocol",
        "implant": "None"
    },
    {
        "dept": "Nephrology",
        "complaint": "Bilateral pedal edema, decreased urine output (<200ml/24h), facial puffiness and lethargy",
        "diagnosis": "End Stage Renal Disease (ESRD) with Severe Hyperkalemia and Volume Overload",
        "icd10": "N18.6",
        "triage": "P1",
        "stat_tests": ["Serum Potassium STAT", "Renal Function Test (BUN/Creatinine)", "ECG"],
        "critical_parameter": "Potassium",
        "critical_val": "7.1 mEq/L",
        "surgery": "Emergency Hemodialysis via Temporary Right Internal Jugular Dual Lumen Catheter",
        "implant": "Medcomp 12Fr x 20cm Double Lumen Hemodialysis Catheter"
    },
    {
        "dept": "General Surgery",
        "complaint": "Severe colicky right lower quadrant pain with nausea, rebound tenderness at McBurney's point",
        "diagnosis": "Acute Appendicitis with Localized Peritonitis",
        "icd10": "K35.80",
        "triage": "P2",
        "stat_tests": ["Ultrasound Abdomen", "Total WBC Count", "CRP", "Urine Routine"],
        "critical_parameter": "WBC Count",
        "critical_val": "18,400 /uL",
        "surgery": "Emergency Laparoscopic Appendectomy",
        "implant": "Endoloop Polyglactin Ligature"
    },
    {
        "dept": "Surgical Oncology",
        "complaint": "Post-op follow up, biopsy-proven Carcinoma Rectum planned for robotic anterior resection",
        "diagnosis": "Adenocarcinoma Rectum Stage IIIB (cT3N1M0)",
        "icd10": "C20",
        "triage": "P3",
        "stat_tests": ["MRI Pelvis High-Resolution", "CEA Level", "Histopathology", "PET-CT"],
        "critical_parameter": "CEA",
        "critical_val": "24.6 ng/mL",
        "surgery": "DaVinci Xi Robotic Low Anterior Resection (LAR) with Total Mesorectal Excision",
        "implant": "Ethicon Contour Curved Cutter Stapler 40mm"
    }
]

DRUG_CATALOG = [
    {"name": "Inj Noradrenaline 4mg/50ml", "cat": "Critical Care", "stock": 140, "cost": 320.0},
    {"name": "Inj Meropenem 1g IV", "cat": "Injectable", "stock": 450, "cost": 890.0},
    {"name": "Inj Piperacillin-Tazobactam 4.5g IV", "cat": "Injectable", "stock": 380, "cost": 480.0},
    {"name": "Inj Pantoprazole 40mg IV", "cat": "Injectable", "stock": 1200, "cost": 45.0},
    {"name": "Inj Ondansetron 4mg IV", "cat": "Injectable", "stock": 800, "cost": 28.0},
    {"name": "Inj Enoxaparin 40mg/0.4ml SC", "cat": "Injectable", "stock": 250, "cost": 360.0},
    {"name": "Inj Morphine Sulfate 10mg/ml", "cat": "Schedule-X Narcotic", "stock": 85, "cost": 65.0},
    {"name": "Inj Fentanyl 100mcg/2ml", "cat": "Schedule-X Narcotic", "stock": 110, "cost": 95.0},
    {"name": "Covishield Recombinant Vaccine", "cat": "Cold-Chain Refrigerator", "stock": 300, "cost": 780.0},
    {"name": "Inj Human Actrapid Insulin 100IU/ml", "cat": "Cold-Chain Refrigerator", "stock": 420, "cost": 185.0},
    {"name": "Tab Atorvastatin 20mg", "cat": "Oral", "stock": 3500, "cost": 8.5},
    {"name": "Tab Clopidogrel 75mg", "cat": "Oral", "stock": 4200, "cost": 6.2},
    {"name": "Tab Telmisartan 40mg", "cat": "Oral", "stock": 5000, "cost": 7.0},
    {"name": "Tab Metformin 500mg SR", "cat": "Oral", "stock": 6200, "cost": 3.8},
    {"name": "Tab Paracetamol 650mg", "cat": "Oral", "stock": 15000, "cost": 2.1}
]

def generate_random_patient():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    full_name = f"{first} {last}"
    age = random.randint(18, 82)
    gender = random.choice(["Male", "Female"])
    blood_group = random.choice(["A+", "B+", "O+", "AB+", "A-", "B-", "O-"])
    phone = f"+91-9{random.randint(100000000, 999999999)}"
    districts = ["Kanchipuram", "Tiruvallur", "Chennai", "Vellore", "Chengalpattu", "Ranipet"]
    address = f"Door #{random.randint(1, 140)}, Gandhi Road, {random.choice(districts)}, Tamil Nadu"
    insurance = random.choice(INSURANCE_TYPES)
    uhid = f"SMCH-{random.randint(100000, 999999)}"
    return {
        "uhid": uhid,
        "name": full_name,
        "age": age,
        "gender": gender,
        "blood_group": blood_group,
        "phone": phone,
        "address": address,
        "insurance_type": insurance
    }
