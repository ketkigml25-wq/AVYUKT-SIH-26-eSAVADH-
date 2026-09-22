-- ============================================================================
-- eSavadh: Intelligent Legal Metrology Compliance & Inspection Platform
-- Made by Team Avyukt
-- Database Schema (Modular Relational SQLite Model)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Admin', 'Inspector', 'Retailer', 'Manufacturer')),
    organization TEXT,
    designation TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. TEAMS & MEMBERS
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    lead_user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lead_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    UNIQUE(team_id, user_id)
);

-- 3. PRODUCTS (Catalog & Scanned items)
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    brand TEXT,
    manufacturer TEXT,
    packer TEXT,
    importer TEXT,
    mfg_date TEXT, -- MM/YYYY or YYYY-MM-DD
    expiry_date TEXT,
    country_of_origin TEXT DEFAULT 'India',
    net_quantity TEXT,
    mrp TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. INSPECTIONS (Master Record for both Field and E-commerce)
CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_no TEXT UNIQUE NOT NULL,
    product_id INTEGER,
    inspector_id INTEGER NOT NULL,
    assigned_team_id INTEGER,
    retailer_id INTEGER,
    location TEXT,
    gps_lat REAL,
    gps_lng REAL,
    purpose TEXT DEFAULT 'Routine Market Surveillance',
    status TEXT DEFAULT 'Completed' CHECK (status IN ('Draft', 'In Progress', 'Review', 'Completed', 'Flagged')),
    compliance_status TEXT DEFAULT 'Needs Review' CHECK (compliance_status IN ('Compliant', 'Non-Compliant', 'Needs Review', 'Insufficient Evidence', 'Not Applicable')),
    source TEXT DEFAULT 'field' CHECK (source IN ('field', 'e-commerce')),
    overall_notes TEXT,
    sync_id TEXT UNIQUE, -- Local idempotency key for offline sync
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL,
    FOREIGN KEY (inspector_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_team_id) REFERENCES teams (id) ON DELETE SET NULL,
    FOREIGN KEY (retailer_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 5. INSPECTION IMAGES (Multi-side views & quality enhancement preservation)
CREATE TABLE IF NOT EXISTS inspection_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    view_side TEXT NOT NULL CHECK (view_side IN ('Front', 'Back', 'Left', 'Right', 'Top', 'Bottom', 'Listing Screenshot')),
    original_image_path TEXT NOT NULL,
    enhanced_image_path TEXT,
    quality_score INTEGER DEFAULT 85,
    is_enhanced INTEGER DEFAULT 0,
    enhancement_details TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
);

-- 6. OCR RESULTS
CREATE TABLE IF NOT EXISTS ocr_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    image_id INTEGER,
    raw_text TEXT NOT NULL,
    detected_languages TEXT DEFAULT 'English, Hindi',
    confidence_score REAL DEFAULT 0.90,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES inspection_images (id) ON DELETE SET NULL
);

-- 7. EXTRACTED DECLARATIONS (With Human-In-The-Loop confirmation)
CREATE TABLE IF NOT EXISTS declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    field_name TEXT NOT NULL, -- 'mrp', 'net_quantity', 'mfg_date', 'manufacturer', 'consumer_care', 'country_of_origin', 'veg_nonveg', 'unit_sale_price'
    extracted_value TEXT,
    confidence REAL DEFAULT 0.85,
    suggested_value TEXT,
    suggestion_reason TEXT,
    inspector_status TEXT DEFAULT 'Unreviewed' CHECK (inspector_status IN ('Unreviewed', 'Confirmed', 'Denied', 'Edited', 'Rescan Requested')),
    confirmed_value TEXT,
    source_view TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE
);

-- 8. LEGAL METROLOGY RULES & VERSIONING (Time-Aware)
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_code TEXT UNIQUE NOT NULL, -- e.g. "PCR-2011-R6-1-A"
    rule_name TEXT NOT NULL,
    description TEXT NOT NULL,
    effective_from DATE NOT NULL, -- Date rule came into force
    effective_to DATE,            -- NULL if currently active
    applicable_categories TEXT DEFAULT 'All', -- comma-separated
    requirement_details TEXT NOT NULL,
    penalty_clause TEXT,
    legal_section TEXT DEFAULT 'Rule 6(1), Legal Metrology (Packaged Commodities) Rules, 2011',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. COMPLIANCE FINDINGS
CREATE TABLE IF NOT EXISTS compliance_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    rule_id INTEGER,
    declaration_field TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('Compliant', 'Non-Compliant', 'Needs Review', 'Not Applicable', 'Insufficient Evidence')),
    observed_value TEXT,
    expected_value TEXT,
    finding_note TEXT,
    severity TEXT DEFAULT 'Medium' CHECK (severity IN ('Minor', 'Medium', 'Major', 'Critical')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES rules (id) ON DELETE SET NULL
);

-- 10. EVIDENCE ITEMS (Traceable Finding -> Rule -> Evidence -> Decision)
CREATE TABLE IF NOT EXISTS evidence_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    finding_id INTEGER,
    image_id INTEGER,
    description TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (finding_id) REFERENCES compliance_findings (id) ON DELETE SET NULL,
    FOREIGN KEY (image_id) REFERENCES inspection_images (id) ON DELETE SET NULL
);

-- 11. REPORTS & IMMUTABLE REPORT REVISIONS
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER UNIQUE NOT NULL,
    report_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    observations TEXT,
    remarks TEXT,
    corrective_actions TEXT,
    recommendations TEXT,
    final_status TEXT NOT NULL,
    generated_by INTEGER NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_no INTEGER DEFAULT 1,
    is_revised INTEGER DEFAULT 0,
    last_edited_by INTEGER,
    last_edited_at TIMESTAMP,
    last_edit_reason TEXT,
    pdf_path TEXT,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (last_edited_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS report_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    inspection_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    previous_version_id INTEGER,
    changed_fields TEXT NOT NULL, -- JSON array of modified field names
    old_values TEXT NOT NULL,     -- JSON object of previous field values
    new_values TEXT NOT NULL,     -- JSON object of updated field values
    edited_by INTEGER NOT NULL,
    edited_role TEXT,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edit_reason TEXT NOT NULL,
    snapshot_data TEXT,           -- JSON snapshot of complete report state
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (edited_by) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_edits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    edited_by INTEGER NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE CASCADE,
    FOREIGN KEY (edited_by) REFERENCES users (id) ON DELETE CASCADE
);

-- 12. DRAFT LEGAL NOTICES & REVISIONS
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    notice_ref_no TEXT UNIQUE NOT NULL,
    issued_to TEXT NOT NULL,
    recipient_type TEXT DEFAULT 'Manufacturer', -- 'Manufacturer', 'Packer', 'Retailer'
    recipient_address TEXT,
    violation_summary TEXT NOT NULL,
    legal_provisions TEXT NOT NULL,
    draft_text TEXT NOT NULL,
    status TEXT DEFAULT 'Draft' CHECK (status IN ('Draft', 'Pending Approval', 'Approved', 'Dispatched', 'Closed')),
    officer_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_no INTEGER DEFAULT 1,
    is_revised INTEGER DEFAULT 0,
    last_edited_by INTEGER,
    last_edited_at TIMESTAMP,
    last_edit_reason TEXT,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (officer_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (last_edited_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS notice_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id INTEGER NOT NULL,
    inspection_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    changed_fields TEXT NOT NULL,
    old_values TEXT NOT NULL,
    new_values TEXT NOT NULL,
    edited_by INTEGER NOT NULL,
    edited_role TEXT,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edit_reason TEXT NOT NULL,
    snapshot_data TEXT,
    FOREIGN KEY (notice_id) REFERENCES notices (id) ON DELETE CASCADE,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (edited_by) REFERENCES users (id) ON DELETE CASCADE
);

-- 13. COMPOUNDING & SETTLEMENT RECORDS & REVISIONS
CREATE TABLE IF NOT EXISTS compounding_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL,
    notice_id INTEGER,
    offense_section TEXT NOT NULL,
    proposed_fee REAL NOT NULL,
    calculated_amount REAL NOT NULL,
    status TEXT DEFAULT 'Proposed' CHECK (status IN ('Proposed', 'Under Review', 'Compounded', 'Rejected', 'Referred to Court')),
    approved_by INTEGER,
    audit_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_no INTEGER DEFAULT 1,
    is_revised INTEGER DEFAULT 0,
    last_edited_by INTEGER,
    last_edited_at TIMESTAMP,
    last_edit_reason TEXT,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (notice_id) REFERENCES notices (id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (last_edited_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS compounding_revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compounding_id INTEGER NOT NULL,
    inspection_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    changed_fields TEXT NOT NULL,
    old_values TEXT NOT NULL,
    new_values TEXT NOT NULL,
    edited_by INTEGER NOT NULL,
    edited_role TEXT,
    edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    edit_reason TEXT NOT NULL,
    snapshot_data TEXT,
    FOREIGN KEY (compounding_id) REFERENCES compounding_records (id) ON DELETE CASCADE,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE CASCADE,
    FOREIGN KEY (edited_by) REFERENCES users (id) ON DELETE CASCADE
);

-- 14. TASKS & WORKLOAD
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    assigned_to INTEGER NOT NULL,
    assigned_by INTEGER NOT NULL,
    inspection_id INTEGER,
    priority TEXT DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Urgent')),
    due_date DATE,
    status TEXT DEFAULT 'Assigned' CHECK (status IN ('Assigned', 'In Progress', 'Completed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (inspection_id) REFERENCES inspections (id) ON DELETE SET NULL
);

-- 15. AUDIT & INTEGRITY LOGS (Immutable)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT NOT NULL,
    ip_address TEXT DEFAULT '127.0.0.1',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 16. NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info' CHECK (type IN ('info', 'warning', 'success', 'urgent')),
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 17. E-COMMERCE LISTINGS (Section 46)
CREATE TABLE IF NOT EXISTS ecommerce_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL, -- 'Amazon India', 'Flipkart', 'Blinkit', 'Zepto', 'JioMart', 'Direct Storefront'
    seller_name TEXT NOT NULL,
    listing_url TEXT NOT NULL,
    product_title TEXT NOT NULL,
    product_category TEXT NOT NULL,
    declared_mrp TEXT,
    declared_net_qty TEXT,
    declared_country TEXT,
    declared_mfr TEXT,
    content_hash TEXT NOT NULL,
    compliance_status TEXT DEFAULT 'Needs Review' CHECK (compliance_status IN ('Compliant', 'Non-Compliant', 'Needs Review')),
    last_checked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 18. LISTING SNAPSHOTS
CREATE TABLE IF NOT EXISTS listing_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    image_path TEXT,
    extracted_text TEXT,
    compliance_result_json TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES ecommerce_listings (id) ON DELETE CASCADE
);
