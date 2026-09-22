# eSavadh (ई-सावध)
> **Intelligent Packaged Commodity Compliance & Inspection Platform**  
> **Statutory Framework:** Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011  
> **Credit:** Made by Team Avyukt

---

## 1. Overview & Objectives

**eSavadh** is an intelligent compliance and inspection platform designed for enforcement authorities, field inspectors, retailers, manufacturers, and administrators to verify packaged commodities against statutory Indian Legal Metrology requirements.

### Key Architectural Highlights
- **Time-Aware Rule Engine:** Evaluates commodities based on the rules applicable on their **manufacturing/packing date**, preventing retroactive misapplication of newer amendments (such as the 2021 Unit Sale Price rule).
- **Multilingual OCR & Vision Enhancement:** Extracts Principal Display Panel (PDP) declarations in English and Hindi while preserving original evidence images separately from enhanced analysis copies.
- **Human-in-the-Loop Verification:** AI assists with confidence scoring and intelligent value suggestions for degraded text (e.g. `₹1?9` $\rightarrow$ `₹199`), but authorized inspectors retain mandatory **Confirm / Deny** verification authority.
- **Offline-First Field Resilience:** Local storage queue, network status detection, and background auto-synchronization with duplicate prevention.
- **E-Commerce Surveillance (Section 46):**
  - **Tier 1 (Interactive Verification):** Ingestion of marketplace URLs (Amazon, Flipkart, etc.) or listing screenshots with automated declaration checks.
  - **Tier 2 (Production Roadmap):** Documented scheduled crawler architecture and hash-based deduplication (`New`, `Unchanged`, `Changed`).
- **Anti-Corruption & Transparency:** Immutable append-only audit trail, draft Section 18 / 49 legal notices, and Section 48 compounding fee calculations.

---

## 2. Quickstart & Local Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
*(Dependencies: `Flask`, `Pillow`, `requests`, `reportlab`, `opencv-python-headless`, `pytesseract`)*

### Step 2: Initialize Database & Run Server
```bash
python app.py
```
Open your browser at **[http://127.0.0.1:5000](http://127.0.0.1:5000)**.

---

## 3. Verified Demo Accounts (4 Role Workspaces)

Use the 1-click quick-fill buttons on the [Sign In Page](http://127.0.0.1:5000/login) for instant testing:

| Role | Official Email | Password | Access & Workspace |
| :--- | :--- | :--- | :--- |
| **Inspector** | `inspector@esavadh.gov.in` | `inspector123` | Field Workbench, Camera Scanner, 9-Step Inspection, HITL Review, Offline Sync |
| **Admin** | `admin@esavadh.gov.in` | `admin123` | National Directorate Oversight, Rule Version Publisher, Team Allocation, Audit Logs |
| **Retailer** | `retailer@esavadh.gov.in` | `retailer123` | Store Compliance Rating, Inspected SKU Audits, Notice Responses |
| **Manufacturer** | `manufacturer@esavadh.gov.in` | `manufacturer123` | Regulatory Compliance Hub, Registered Commodities, Declaration Verification |

---

## 4. End-to-End Operational Workflow

```
Login 
  └── Dashboard 
        └── New Inspection 
              ├── Step 1: Dossier Metadata (Location, Product, Category, Mfg Date)
              ├── Step 2: Multi-side PDP Capture (Front, Back, Lateral with Viewfinder Guide)
              ├── Step 3: Quality Enhancement & Multilingual OCR Extraction (Eng + Hin)
              ├── Step 4: Human-in-the-Loop Review (Confirm / Deny AI Value Suggestions)
              ├── Step 5: Time-Aware Rule Assessment (PCR 2011 + Amendments)
              ├── Step 6: Evidence Linking (Finding → Rule → Evidence → Decision)
              ├── Step 7: Official Dossier & Printable Certificate Generation
              ├── Step 8: Section 18 / 49 Draft Legal Notice & Sec 48 Compounding
              └── Step 9: Immutable Audit Logging & Offline Sync
```

---

## 5. E-Commerce Monitoring (Section 46)

- **Tier 1 (Active & Functional):** Navigate to **E-Commerce Monitoring**, select Sample 1 (Compliant Edible Oil) or Sample 2 (Non-Compliant Cleanser) or paste any marketplace URL, and click **Analyze Listing Compliance**.
- **Tier 2 (Production Scope):** Formally specified in the UI and documentation covering distributed API ingestion and content-hash deduplication.

---

## 6. Project Architecture

```
eSavadh/
├── app.py                     # Flask application routes, session auth & API controllers
├── database.py                # SQLite database management, seeding & ORM helpers
├── schema.sql                 # 18-table relational schema
├── requirements.txt           # Python dependencies
├── README.md                  # System manual
├── core/
│   ├── ocr_engine.py          # Multilingual OCR parser & intelligent suggestions
│   ├── image_enhancer.py      # Quality analysis & adaptive contrast enhancement
│   ├── rule_engine.py         # Time-aware rule evaluation & date-matching
│   ├── legal_notices.py       # Section 18 draft notices & Sec 48 compounding calculator
│   └── ecommerce_engine.py    # Section 46 listing parser & hash deduplicator
├── static/
│   ├── css/
│   │   ├── style.css          # Government register ledger design system
│   │   └── mobile.css         # Mobile camera viewfinder & side selector chips
│   ├── js/
│   │   ├── main.js            # Tab navigation & HITL AJAX handlers
│   │   ├── camera.js          # Multi-side camera stream & frame capture
│   │   └── offline_sync.js    # Local storage queue & background auto-sync
│   └── uploads/               # Original evidence & enhanced image copies
└── templates/
    ├── base.html              # Government masthead, role navigation & sync badge
    ├── landing.html           # Platform landing page & visual overview
    ├── login.html             # Multi-role sign-in with 1-click test fill
    ├── how_it_works.html      # 9-step interactive compliance workflow guide
    ├── dashboard_inspector.html # Inspector field workbench & surveillance queue
    ├── dashboard_admin.html   # National oversight, analytics & audit controls
    ├── dashboard_retailer.html# Retail store compliance desk
    ├── dashboard_manufacturer.html # Manufacturer regulatory compliance hub
    ├── inspection_new.html    # Guided 9-step multi-side inspection form
    ├── inspection_detail.html # 360-degree inspection detail dossier (6 tabs)
    ├── inspections_list.html  # Master inspection repository with smart filters
    ├── ecommerce_monitor.html # Section 46 E-Commerce surveillance (Tier 1 & Tier 2)
    ├── rules_center.html      # Rules catalog & quick rule lookup
    ├── reports_center.html    # Monthly & yearly compliance analytics
    ├── draft_notice.html      # Section 18 / 49 Draft Legal Notice generator
    ├── compounding.html       # Section 48 Compounding Settlement Calculator
    ├── team_management.html   # Inspection team allocation & task roster
    ├── audit_integrity.html   # Immutable audit trail & anti-corruption register
    └── printable_dossier.html # Official printable compliance certificate
```

---
**Made by Team Avyukt**
