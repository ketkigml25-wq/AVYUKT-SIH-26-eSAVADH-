"""
eSavadh - Database Access & Seeder Layer
Made by Team Avyukt

Manages SQLite connection, schema bootstrap, and realistic sample data seeding.
Clearly distinguishes sample data from real records.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")

def get_effective_db_path():
    """
    Determines effective SQLite database path.
    On Vercel/Serverless Linux with read-only root directories, redirects to /tmp/esavadh.db
    and bootstraps initial database copy if needed.
    """
    local_db = os.path.join(BASE_DIR, "esavadh.db")
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(BASE_DIR, os.W_OK))

    if is_serverless:
        tmp_db = "/tmp/esavadh.db"
        if not os.path.exists(tmp_db):
            if os.path.exists(local_db):
                try:
                    shutil.copy2(local_db, tmp_db)
                except Exception as e:
                    print(f"[eSavadh DB] Notice copying local db to /tmp: {e}")
        return tmp_db
    return local_db


def get_db():
    """Returns an active SQLite connection with WAL mode, busy timeout, and dictionary row access."""
    db_path = get_effective_db_path()
    conn = sqlite3.connect(db_path, timeout=60.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    conn.execute("PRAGMA busy_timeout = 60000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Executes schema.sql and populates realistic demo seed data across all 4 roles."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.executescript(schema_sql)

        # Execute any schema migrations on existing database
        _run_migrations(cursor, conn)

        # Check if users exist
        cursor.execute("SELECT COUNT(*) as count FROM users")
        count = cursor.fetchone()["count"]

        if count == 0:
            _seed_demo_data(cursor, conn)
            print("[eSavadh DB] Successfully bootstrapped schema and seeded realistic demo data.")
        else:
            cursor.execute("DELETE FROM users WHERE role NOT IN ('Admin', 'Inspector')")
            conn.commit()
    finally:
        conn.close()


def _seed_demo_data(cursor, conn):
    """Populates realistic demo datasets clearly marked as sample data."""
    # 1. Users for 2 roles: Admin and Inspector
    users = [
        # Admin
        ("Director Anita Roy", "admin@esavadh.gov.in", generate_password_hash("admin123"), "Admin", "Directorate of Legal Metrology", "Director General", "9811002233"),
        # Inspector
        ("Officer Rajesh Sharma", "inspector@esavadh.gov.in", generate_password_hash("inspector123"), "Inspector", "Delhi Enforcement Unit 01", "Senior Legal Metrology Officer", "9822003344"),
        ("Officer Sunita Menon", "sunita.menon@esavadh.gov.in", generate_password_hash("inspector123"), "Inspector", "South Zone Enforcement Unit", "Legal Metrology Inspector", "9833004455"),
    ]
    cursor.executemany(
        "INSERT INTO users (name, email, password_hash, role, organization, designation, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
        users
    )

    # 2. Teams
    teams = [
        ("Northern Zone Surveillance Unit A", "Delhi NCR & Haryana", 2),
        ("Western Zone Industrial Verification Team", "Maharashtra & Gujarat", 3)
    ]
    cursor.executemany("INSERT INTO teams (name, jurisdiction, lead_user_id) VALUES (?, ?, ?)", teams)

    # Team members
    cursor.execute("INSERT INTO team_members (team_id, user_id) VALUES (1, 2), (1, 3)")

    # 3. Rules & Rule Versions (Time-Aware)
    rules = [
        (
            "PCR-2011-R6-1-A", 
            "Mandatory Manufacturer / Packer Name & Complete Address",
            "Every package must bear the name and complete physical address of the manufacturer, packer, or importer.",
            "2011-04-01", 
            None, 
            "All", 
            "Name of mfr/packer, physical premises address, city, state, and postal pincode must be declared on PDP.",
            "Section 36(1) of Legal Metrology Act, 2009 - Fine up to ₹25,000.",
            "Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2011-R6-1-D", 
            "Net Quantity Declaration in Standard Metric Units",
            "Net quantity must be declared in standard metric units (g, kg, ml, l, or number N).",
            "2011-04-01", 
            None, 
            "All", 
            "Weight or volume declared with permissible standard SI symbols. Non-standard symbols (e.g. 'gms', 'kilo') prohibited.",
            "Section 36(1) & Rule 11 - Fine up to ₹25,000.",
            "Rule 6(1)(d) & Rule 11, Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2011-R6-1-E", 
            "Maximum Retail Price (MRP) Declaration (Inclusive of All Taxes)",
            "Maximum Retail Price in Indian Rupees inclusive of all taxes must be prominently declared on Principal Display Panel.",
            "2011-04-01", 
            None, 
            "All", 
            "Clear currency symbol (₹ or Rs.) with price and mandatory statement 'Inclusive of all taxes'. Dual pricing prohibited.",
            "Section 36(1) - Fine up to ₹25,000 for first offense, ₹50,000 for second.",
            "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2011-R6-1-C", 
            "Month and Year of Manufacture / Pre-packing",
            "Month and year in which the commodity is manufactured, packed, or imported must be printed.",
            "2011-04-01", 
            None, 
            "All", 
            "Format: MM/YYYY or Month YYYY (e.g. '05/2024' or 'MAY 2024').",
            "Section 36(1) - Fine up to ₹25,000.",
            "Rule 6(1)(c), Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2011-R6-1-F", 
            "Consumer Care Details Declaration",
            "Name, address, telephone number, and email address of person/cell in case of consumer complaints.",
            "2011-04-01", 
            None, 
            "All", 
            "Complete contact helpline number, email ID, and postal address of consumer grievance officer.",
            "Section 36(1) - Fine up to ₹25,000.",
            "Rule 6(1)(f), Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2011-R6-10", 
            "Country of Origin Declaration",
            "Country of origin or manufacture must be declared on every pre-packaged imported or domestically manufactured commodity.",
            "2017-06-23", 
            None, 
            "All", 
            "Mandatory declaration: 'Country of Origin: [Country Name]' on PDP and e-commerce listings.",
            "Section 36(1) & Rule 6(10) - Fine up to ₹25,000.",
            "Rule 6(10), Legal Metrology (Packaged Commodities) Rules, 2011"
        ),
        (
            "PCR-2021-AMEND-R6-11", 
            "Unit Sale Price (USP) Declaration Requirement",
            "For packages containing commodities more than 1 kg/1 litre, unit sale price per g/kg/ml/litre must be declared.",
            "2022-01-01", 
            None, 
            "Packaged Commodities > 1g/1ml", 
            "Mandatory Unit Sale Price (e.g. '₹ 0.50 per g' or '₹ 25.00 per 100 ml') rounded off to nearest two decimal places.",
            "Section 36(1) read with PCR Amendment 2021 - Fine up to ₹25,000.",
            "Rule 6(11), Legal Metrology (Packaged Commodities) (Amendment) Rules, 2021"
        )
    ]
    cursor.executemany(
        """
        INSERT INTO rules (rule_code, rule_name, description, effective_from, effective_to, applicable_categories, requirement_details, penalty_clause, legal_section)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rules
    )

    # 4. Products (Sample Demo Catalog)
    products = [
        ("8901234567890", "Himalayan Sunrise Herbal Darjeeling Tea (250g)", "Beverages / Food", "Himalayan Sunrise", "Himalayan Pure Harvest Ltd.", "05/2024", "11/2025", "India", "250 g", "₹ 240.00"),
        ("8909876543210", "NutriPure Cold Pressed Organic Sesame Oil (1L)", "Edible Oils", "NutriPure Edibles", "NutriPure Agritech Pvt Ltd", "02/2024", "02/2025", "India", "1 L", "₹ 380.00"),
        ("8905544332211", "SilkCare Hydrating Facial Cleanser (100ml)", "Cosmetics / Personal Care", "SilkCare Labs", "CosmoPure Formulations India", "01/2024", "01/2026", "India", "100 ml", "₹ 199.00"),
        ("8901122334455", "Heritage Gold Basmati Rice (5kg)", "Grains & Cereals", "Heritage Agro", "Heritage Mills India Pvt Ltd", "06/2019", "06/2021", "India", "5 kg", "₹ 450.00"), # Historical product example
    ]
    cursor.executemany(
        """
        INSERT INTO products (barcode, name, category, brand, manufacturer, mfg_date, expiry_date, country_of_origin, net_quantity, mrp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        products
    )

    # 5. Completed Sample Inspections (Field & E-Commerce)
    inspections = [
        (
            "INSP-2026-DEL-001", 1, 2, 1, 4, 
            "Connaught Place Central Market, New Delhi", 28.6315, 77.2167,
            "Routine Market Surveillance", "Completed", "Compliant", "field",
            "Physical package verified on all four display panels. All 7 mandatory declarations under Rule 6 verified compliant.",
            "OFFLINE-SYNC-LOCAL-001"
        ),
        (
            "INSP-2026-DEL-002", 2, 2, 1, 4,
            "Vasant Kunj Mega Mart, New Delhi", 28.5355, 77.1578,
            "Targeted Enforcement Audit", "Completed", "Non-Compliant", "field",
            "Unit Sale Price (USP) and complete consumer care email missing on principal display panel.",
            "OFFLINE-SYNC-LOCAL-002"
        ),
        (
            "INSP-2026-ECOM-001", 3, 2, 1, None,
            "E-Commerce Digital Listing Verification", None, None,
            "Digital Marketplace Surveillance", "Completed", "Needs Review", "e-commerce",
            "Online listing on Amazon India checked under Tier 1 module. Country of Origin declared; MRP currency format requires officer review.",
            "ECOM-SYNC-001"
        )
    ]
    cursor.executemany(
        """
        INSERT INTO inspections (ref_no, product_id, inspector_id, assigned_team_id, retailer_id, location, gps_lat, gps_lng, purpose, status, compliance_status, source, overall_notes, sync_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        inspections
    )

    # 6. Sample Declarations for Inspection 1
    sample_decls = [
        (1, "mrp", "₹ 240.00 (incl. of all taxes)", 0.95, "₹ 240.00", "Verified with currency symbol", "Confirmed", "₹ 240.00", "Back"),
        (1, "net_quantity", "250 g", 0.94, "250 g", "Standard metric SI unit", "Confirmed", "250 g", "Back"),
        (1, "mfg_date", "05/2024", 0.91, "05/2024", "Standard MM/YYYY format", "Confirmed", "05/2024", "Back"),
        (1, "manufacturer", "Himalayan Pure Harvest Ltd., Khasra 412, Solan, HP - 173212", 0.96, None, None, "Confirmed", "Himalayan Pure Harvest Ltd., Khasra 412, Solan, HP - 173212", "Back"),
        (1, "consumer_care", "care@himalayanpure.in | 1800-200-8899", 0.93, None, None, "Confirmed", "care@himalayanpure.in | 1800-200-8899", "Back"),
        (1, "country_of_origin", "India", 0.95, "India", "Valid country declaration", "Confirmed", "India", "Front"),
        (1, "unit_sale_price", "₹ 0.96 / g", 0.90, "₹ 0.96 / g", "Valid USP declaration", "Confirmed", "₹ 0.96 / g", "Back"),
    ]
    cursor.executemany(
        """
        INSERT INTO declarations (inspection_id, field_name, extracted_value, confidence, suggested_value, suggestion_reason, inspector_status, confirmed_value, source_view)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        sample_decls
    )

    # 7. Sample Compliance Findings for Inspection 1
    findings = [
        (1, 1, "manufacturer", "Compliant", "Himalayan Pure Harvest Ltd., Khasra 412, Solan, HP", "Complete Name & Postal Address", "Compliant under Rule 6(1)(a)", "Minor"),
        (1, 2, "net_quantity", "Compliant", "250 g", "Standard SI Metric Representation", "Compliant under Rule 6(1)(d)", "Minor"),
        (1, 3, "mrp", "Compliant", "₹ 240.00 (incl. of all taxes)", "MRP with Currency & Taxes Included", "Compliant under Rule 6(1)(e)", "Minor"),
        (1, 4, "mfg_date", "Compliant", "05/2024", "Month & Year of Manufacture", "Compliant under Rule 6(1)(c)", "Minor"),
        (1, 5, "consumer_care", "Compliant", "care@himalayanpure.in | 1800-200-8899", "Helpline & Grievance Contact", "Compliant under Rule 6(1)(f)", "Minor"),
        (1, 6, "country_of_origin", "Compliant", "India", "Declared Country of Origin", "Compliant under Rule 6(10)", "Minor"),
        (1, 7, "unit_sale_price", "Compliant", "₹ 0.96 / g", "Unit Sale Price per g/kg", "Compliant under Rule 6(11)", "Minor"),
    ]
    cursor.executemany(
        """
        INSERT INTO compliance_findings (inspection_id, rule_id, declaration_field, status, observed_value, expected_value, finding_note, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        findings
    )

    # 8. Sample Inspection Report & Audit Log
    cursor.execute(
        """
        INSERT INTO reports (inspection_id, report_number, title, summary, final_status, generated_by)
        VALUES (1, 'RPT-2026-DEL-001', 'Legal Metrology Compliance Certificate - Himalayan Herbal Tea', 'Full physical packaging audit conducted. All 7 mandatory declarations verified compliant under PCR 2011.', 'Compliant', 2)
        """
    )
    cursor.execute(
        """
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
        VALUES (2, 'GENERATE_REPORT', 'Inspection', 1, 'Officer Rajesh Sharma finalized inspection dossier INSP-2026-DEL-001 as Compliant.', '127.0.0.1')
        """
    )

    # 9. Sample E-Commerce Listings (Section 46)
    ecom_listings = [
        ("Amazon India", "CloudRetail Solutions India Pvt Ltd", "https://amazon.in/dp/B09XTEST12", "NutriPure Cold Pressed Organic Sesame Oil (1 Litre)", "Edible Oils", "₹ 380.00", "1 L", "India", "NutriPure Agritech Pvt Ltd", "hash_amz_9921", "Compliant"),
        ("Flipkart", "HealthFirst Organics Hub", "https://flipkart.com/item/itm129847192", "SilkCare Hydrating Herbal Face Cleanser 100ml", "Cosmetics", "₹ 199.00", "100 ml", "Not Declared", "CosmoPure Formulations", "hash_flp_3312", "Non-Compliant"),
        ("Blinkit", "FreshDaily QuickCommerce Node 4", "https://blinkit.com/prn/himalayan-tea-250g", "Himalayan Sunrise Herbal Darjeeling Tea 250g", "Beverages", "₹ 240.00", "250 g", "India", "Himalayan Harvest Ltd", "hash_blk_7718", "Compliant")
    ]
    cursor.executemany(
        """
        INSERT INTO ecommerce_listings (platform, seller_name, listing_url, product_title, product_category, declared_mrp, declared_net_qty, declared_country, declared_mfr, content_hash, compliance_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ecom_listings
    )

    # 10. Sample Tasks & Notifications
    cursor.execute(
        """
        INSERT INTO tasks (title, description, assigned_to, assigned_by, priority, due_date, status)
        VALUES ('Market Surveillance: Vasant Kunj Mega Stores', 'Conduct inspection of edible oils and packaged spices under PCR 2011 Unit Sale Price rule.', 2, 1, 'High', '2026-09-30', 'Assigned')
        """
    )
    cursor.execute(
        """
        INSERT INTO notifications (user_id, title, message, type, link)
        VALUES (2, 'New Inspection Dossier Assigned', 'Surveillance task assigned by Director General for Vasant Kunj Sector 4.', 'info', '/tasks')
        """
    )

    conn.commit()


# ============================================================================
# Helper Query Methods
# ============================================================================

def _run_migrations(cursor, conn):
    """Safely adds new revision columns and tables to existing database without data loss."""
    migrations = [
        # reports columns
        "ALTER TABLE reports ADD COLUMN observations TEXT;",
        "ALTER TABLE reports ADD COLUMN remarks TEXT;",
        "ALTER TABLE reports ADD COLUMN corrective_actions TEXT;",
        "ALTER TABLE reports ADD COLUMN recommendations TEXT;",
        "ALTER TABLE reports ADD COLUMN version_no INTEGER DEFAULT 1;",
        "ALTER TABLE reports ADD COLUMN is_revised INTEGER DEFAULT 0;",
        "ALTER TABLE reports ADD COLUMN last_edited_by INTEGER;",
        "ALTER TABLE reports ADD COLUMN last_edited_at TIMESTAMP;",
        "ALTER TABLE reports ADD COLUMN last_edit_reason TEXT;",
        # notices columns
        "ALTER TABLE notices ADD COLUMN version_no INTEGER DEFAULT 1;",
        "ALTER TABLE notices ADD COLUMN is_revised INTEGER DEFAULT 0;",
        "ALTER TABLE notices ADD COLUMN last_edited_by INTEGER;",
        "ALTER TABLE notices ADD COLUMN last_edited_at TIMESTAMP;",
        "ALTER TABLE notices ADD COLUMN last_edit_reason TEXT;",
        # compounding_records columns
        "ALTER TABLE compounding_records ADD COLUMN version_no INTEGER DEFAULT 1;",
        "ALTER TABLE compounding_records ADD COLUMN is_revised INTEGER DEFAULT 0;",
        "ALTER TABLE compounding_records ADD COLUMN last_edited_by INTEGER;",
        "ALTER TABLE compounding_records ADD COLUMN last_edited_at TIMESTAMP;",
        "ALTER TABLE compounding_records ADD COLUMN last_edit_reason TEXT;"
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists


def get_user_by_email(email):
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),)).fetchone()
        return user
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return user
    finally:
        conn.close()


def get_all_rules(active_only=True):
    conn = get_db()
    try:
        query = "SELECT * FROM rules" + (" WHERE is_active = 1" if active_only else "") + " ORDER BY id ASC"
        rules = conn.execute(query).fetchall()
        return rules
    finally:
        conn.close()


def get_inspections(limit=50, role_filter=None, user_id=None, source_filter=None):
    conn = get_db()
    try:
        query = """
            SELECT i.*, p.name as product_name, p.barcode as product_barcode, p.category as product_category,
                   u.name as inspector_name
            FROM inspections i
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON i.inspector_id = u.id
            WHERE 1=1
        """
        params = []
        if source_filter:
            query += " AND i.source = ?"
            params.append(source_filter)
        if role_filter == "Inspector" and user_id:
            query += " AND (i.inspector_id = ? OR i.inspector_id IS NOT NULL)"
            params.append(user_id)
            
        query += " ORDER BY i.id DESC LIMIT ?"
        params.append(limit)
        
        rows = conn.execute(query, tuple(params)).fetchall()
        return rows
    finally:
        conn.close()


def _restore_dossier_to_db(dossier, conn):
    """Restores a session-cached dossier into the local database instance if missing."""
    if not dossier or not isinstance(dossier, dict):
        return
    insp = dossier.get("inspection")
    if not insp:
        return
    
    cursor = conn.cursor()
    actual_id = insp.get("id")
    if not actual_id:
        return
    
    # 1. Product
    prod_id = insp.get("product_id") or actual_id
    cursor.execute("""
        INSERT OR REPLACE INTO products (id, name, category, brand, manufacturer, mfg_date, expiry_date, country_of_origin, net_quantity, mrp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        prod_id,
        insp.get("product_name", "Packaged Commodity"),
        insp.get("product_category", "Beverages / Food"),
        insp.get("product_brand"),
        insp.get("product_manufacturer"),
        insp.get("product_mfg_date", "05/2024"),
        insp.get("product_expiry_date"),
        insp.get("product_country_of_origin", "India"),
        insp.get("net_quantity"),
        insp.get("mrp")
    ))
    
    # 2. Inspection
    cursor.execute("""
        INSERT OR REPLACE INTO inspections (id, ref_no, product_id, inspector_id, location, compliance_status, source, overall_notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')))
    """, (
        actual_id,
        insp.get("ref_no", f"INSP-2026-DEL-{actual_id:04d}"),
        prod_id,
        insp.get("inspector_id", 2),
        insp.get("location", "Field Surveillance"),
        insp.get("compliance_status", "Needs Review"),
        insp.get("source", "field"),
        insp.get("overall_notes", "Restored dossier snapshot"),
        insp.get("created_at")
    ))
    
    # 3. Declarations
    for d in dossier.get("declarations", []):
        cursor.execute("""
            INSERT OR REPLACE INTO declarations (id, inspection_id, field_name, extracted_value, confidence, suggested_value, suggestion_reason, inspector_status, confirmed_value, source_view)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d.get("id"),
            actual_id,
            d.get("field_name"),
            d.get("extracted_value"),
            d.get("confidence", 0.9),
            d.get("suggested_value"),
            d.get("suggestion_reason"),
            d.get("inspector_status", "Unreviewed"),
            d.get("confirmed_value"),
            d.get("source_view", "Front")
        ))
        
    # 4. Compliance Findings
    for f in dossier.get("findings", []):
        r_code = f.get("rule_code")
        r_row = cursor.execute("SELECT id FROM rules WHERE rule_code = ?", (r_code,)).fetchone()
        rule_id = r_row["id"] if r_row else f.get("rule_id")
        cursor.execute("""
            INSERT OR REPLACE INTO compliance_findings (id, inspection_id, rule_id, declaration_field, status, observed_value, expected_value, finding_note, severity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f.get("id"),
            actual_id,
            rule_id,
            f.get("declaration_field"),
            f.get("status", "Compliant"),
            f.get("observed_value"),
            f.get("expected_value"),
            f.get("finding_note"),
            f.get("severity", "LOW")
        ))
        
    # 5. Inspection Images
    for img in dossier.get("images", []):
        cursor.execute("""
            INSERT OR REPLACE INTO inspection_images (id, inspection_id, view_side, original_image_path, enhanced_image_path, quality_score, is_enhanced)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            img.get("id"),
            actual_id,
            img.get("view_side", "Front"),
            img.get("original_image_path"),
            img.get("enhanced_image_path"),
            img.get("quality_score", 95),
            img.get("is_enhanced", 1)
        ))
        
    conn.commit()


def get_inspection_detail(inspection_id_or_ref, version_override=None):
    """
    Fetches the complete inspection dossier with full revision history across reports,
    notices, compounding proposals, and immutable audit trails.
    If version_override is specified, loads that specific historical snapshot for the report.
    """
    conn = get_db()
    try:
        query = """
            SELECT i.*, p.name as product_name, p.barcode as product_barcode, p.category as product_category,
                   p.brand as product_brand, p.manufacturer as product_manufacturer, p.mfg_date as product_mfg_date,
                   p.expiry_date as product_expiry_date, p.country_of_origin as product_country_of_origin,
                   u.name as inspector_name, u.designation as inspector_designation, u.organization as inspector_org
            FROM inspections i
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON i.inspector_id = u.id
            WHERE i.id = ? OR i.ref_no = ?
        """
        insp = conn.execute(query, (inspection_id_or_ref, str(inspection_id_or_ref))).fetchone()
        
        if not insp:
            # Check Flask session fallback for serverless state restoration
            try:
                from flask import session
                saved_dossier = session.get(f"dossier_{inspection_id_or_ref}") or session.get("active_dossier")
                if saved_dossier and (str(saved_dossier.get("inspection", {}).get("id")) == str(inspection_id_or_ref) or str(saved_dossier.get("inspection", {}).get("ref_no")) == str(inspection_id_or_ref)):
                    _restore_dossier_to_db(saved_dossier, conn)
                    insp = conn.execute(query, (inspection_id_or_ref, str(inspection_id_or_ref))).fetchone()
            except Exception as e:
                print(f"[eSavadh DB] Notice restoring dossier from session: {e}")

        if not insp:
            return None

        actual_id = insp["id"]
        images = [dict(img) for img in conn.execute("SELECT * FROM inspection_images WHERE inspection_id = ? ORDER BY id ASC", (actual_id,)).fetchall()]
        decls = [dict(d) for d in conn.execute("SELECT * FROM declarations WHERE inspection_id = ? ORDER BY id ASC", (actual_id,)).fetchall()]
        findings = [dict(cf) for cf in conn.execute("""
            SELECT cf.*, r.rule_code, r.rule_name, r.legal_section
            FROM compliance_findings cf
            LEFT JOIN rules r ON cf.rule_id = r.id
            WHERE cf.inspection_id = ?
            ORDER BY cf.id ASC
        """, (actual_id,)).fetchall()]
        
        # Report with editor and generator details
        report_row = conn.execute("""
            SELECT r.*, 
                   u_gen.name as generator_name, u_gen.designation as generator_designation, u_gen.role as generator_role,
                   u_ed.name as editor_name, u_ed.designation as editor_designation, u_ed.role as editor_role
            FROM reports r
            LEFT JOIN users u_gen ON r.generated_by = u_gen.id
            LEFT JOIN users u_ed ON r.last_edited_by = u_ed.id
            WHERE r.inspection_id = ?
        """, (actual_id,)).fetchone()
        
        if not report_row:
            report_num = f"RPT-2026-DEL-{actual_id:04d}"
            prod_title = insp.get("product_name") or "Packaged Commodity"
            title = f"Statutory Compliance Certificate - {prod_title}"
            summary = insp.get("overall_notes") or f"Statutory surveillance dossier {insp.get('ref_no')}. Determination: {insp.get('compliance_status')}."
            status = insp.get("compliance_status") or "Needs Review"
            gen_by = insp.get("inspector_id") or 1
            
            conn.execute("""
                INSERT OR IGNORE INTO reports (inspection_id, report_number, title, summary, observations, remarks, corrective_actions, recommendations, final_status, generated_by, version_no, is_revised)
                VALUES (?, ?, ?, ?, 'Physical container and primary display panel inspected. All declarations verified against statutory criteria.', 'All declarations evaluated under Legal Metrology (Packaged Commodities) Rules, 2011.', 'Ensure full font height and contrast requirements under Rule 7 for all subsequent production batches.', 'Proceed with enforcement record archival and routine periodic surveillance.', ?, ?, 1, 0)
            """, (actual_id, report_num, title, summary, status, gen_by))
            conn.commit()
            
            report_row = conn.execute("""
                SELECT r.*, 
                       u_gen.name as generator_name, u_gen.designation as generator_designation, u_gen.role as generator_role,
                       u_ed.name as editor_name, u_ed.designation as editor_designation, u_ed.role as editor_role
                FROM reports r
                LEFT JOIN users u_gen ON r.generated_by = u_gen.id
                LEFT JOIN users u_ed ON r.last_edited_by = u_ed.id
                WHERE r.inspection_id = ?
            """, (actual_id,)).fetchone()

        report = dict(report_row) if report_row else None
        
        # Report Revisions
        report_revisions = []
        if report:
            rev_rows = conn.execute("""
                SELECT rr.*, u.name as editor_name, u.designation as editor_designation
                FROM report_revisions rr
                LEFT JOIN users u ON rr.edited_by = u.id
                WHERE rr.report_id = ?
                ORDER BY rr.version_no ASC
            """, (report["id"],)).fetchall()
            for r in rev_rows:
                r_dict = dict(r)
                try:
                    r_dict["changed_fields_list"] = json.loads(r_dict.get("changed_fields") or "[]")
                    r_dict["old_values_dict"] = json.loads(r_dict.get("old_values") or "{}")
                    r_dict["new_values_dict"] = json.loads(r_dict.get("new_values") or "{}")
                    r_dict["snapshot_dict"] = json.loads(r_dict.get("snapshot_data") or "{}")
                except Exception:
                    r_dict["changed_fields_list"] = []
                    r_dict["old_values_dict"] = {}
                    r_dict["new_values_dict"] = {}
                    r_dict["snapshot_dict"] = {}
                report_revisions.append(r_dict)

            # If version_override is requested, overlay historical snapshot onto report object
            if version_override is not None:
                try:
                    v_num = int(version_override)
                    latest_v_no = report.get("version_no", 1)
                    if v_num == 1 and report_revisions:
                        # Version 1 is the state before the first revision or snapshot in revision 1
                        v1_snap = report_revisions[0].get("old_values_dict") or {}
                        for k, v in v1_snap.items():
                            report[k] = v
                        report["version_no"] = 1
                        report["is_viewing_historical"] = (latest_v_no > 1)
                        report["viewed_version"] = 1
                    else:
                        for rev in report_revisions:
                            if rev["version_no"] == v_num:
                                snap = rev.get("snapshot_dict") or rev.get("new_values_dict") or {}
                                for k, v in snap.items():
                                    report[k] = v
                                report["version_no"] = v_num
                                report["is_viewing_historical"] = (v_num != latest_v_no)
                                report["viewed_version"] = v_num
                                break
                except (ValueError, TypeError):
                    pass

        ocr_row = conn.execute("SELECT * FROM ocr_results WHERE inspection_id = ? ORDER BY id DESC LIMIT 1", (actual_id,)).fetchone()
        ocr_res = dict(ocr_row) if ocr_row else None
        
        # Notices with editor and revision information
        notices = []
        notice_rows = conn.execute("""
            SELECT n.*, 
                   u_off.name as officer_name, u_off.designation as officer_designation,
                   u_ed.name as editor_name, u_ed.designation as editor_designation
            FROM notices n 
            LEFT JOIN users u_off ON n.officer_id = u_off.id
            LEFT JOIN users u_ed ON n.last_edited_by = u_ed.id
            WHERE n.inspection_id = ? 
            ORDER BY n.id DESC
        """, (actual_id,)).fetchall()
        for nr in notice_rows:
            n_dict = dict(nr)
            n_revs = conn.execute("""
                SELECT nr.*, u.name as editor_name 
                FROM notice_revisions nr 
                LEFT JOIN users u ON nr.edited_by = u.id 
                WHERE nr.notice_id = ? 
                ORDER BY nr.version_no ASC
            """, (n_dict["id"],)).fetchall()
            n_dict["revisions"] = [dict(r) for r in n_revs]
            notices.append(n_dict)

        # Compounding records with editor and revision information
        compounding = []
        comp_rows = conn.execute("""
            SELECT c.*, 
                   u_app.name as officer_name, u_app.designation as officer_designation,
                   u_ed.name as editor_name, u_ed.designation as editor_designation
            FROM compounding_records c 
            LEFT JOIN users u_app ON c.approved_by = u_app.id 
            LEFT JOIN users u_ed ON c.last_edited_by = u_ed.id
            WHERE c.inspection_id = ? 
            ORDER BY c.id DESC
        """, (actual_id,)).fetchall()
        for cr in comp_rows:
            c_dict = dict(cr)
            c_revs = conn.execute("""
                SELECT crv.*, u.name as editor_name 
                FROM compounding_revisions crv 
                LEFT JOIN users u ON crv.edited_by = u.id 
                WHERE crv.compounding_id = ? 
                ORDER BY crv.version_no ASC
            """, (c_dict["id"],)).fetchall()
            c_dict["revisions"] = [dict(r) for r in c_revs]
            compounding.append(c_dict)

        # Legacy report edits for backward compatibility
        edits = []
        if report:
            edits = [dict(re) for re in conn.execute("SELECT re.*, u.name as editor_name FROM report_edits re LEFT JOIN users u ON re.edited_by = u.id WHERE re.report_id = ? ORDER BY re.id DESC", (report["id"],)).fetchall()]
            
        logs = [dict(al) for al in conn.execute("""
            SELECT al.*, u.name as user_name 
            FROM audit_logs al 
            LEFT JOIN users u ON al.user_id = u.id 
            WHERE (al.entity_type = 'Inspection' AND al.entity_id = ?) 
               OR (al.entity_type = 'Declaration' AND al.entity_id IN (SELECT id FROM declarations WHERE inspection_id = ?))
               OR (al.entity_type = 'Notice' AND al.entity_id = ?)
               OR (al.entity_type = 'Compounding' AND al.entity_id = ?)
               OR (al.entity_type = 'Report' AND al.entity_id = ?)
            ORDER BY al.id DESC
        """, (actual_id, actual_id, actual_id, actual_id, actual_id)).fetchall()]

        return {
            "inspection": dict(insp),
            "images": images,
            "declarations": decls,
            "findings": findings,
            "report": report,
            "report_revisions": report_revisions,
            "ocr_result": ocr_res,
            "notices": notices,
            "compounding_records": compounding,
            "report_edits": edits,
            "audit_logs": logs
        }
    finally:
        conn.close()


def save_report_revision(inspection_id, updated_fields, edit_reason, user_id, user_role, ip_address="127.0.0.1"):
    """
    Saves an edited revision of an inspection report.
    Validates modified fields, prevents duplicate revisions on identical data,
    stores old vs new values, creates a version record in report_revisions,
    updates the reports table, and records an immutable audit event.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # 1. Fetch current report
        report_row = cursor.execute("SELECT * FROM reports WHERE inspection_id = ?", (inspection_id,)).fetchone()
        if not report_row:
            # Create base report if none exists
            insp_row = cursor.execute("SELECT * FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
            prod_row = cursor.execute("SELECT name FROM products WHERE id = ?", (insp_row["product_id"],)).fetchone() if insp_row and insp_row["product_id"] else None
            prod_name = prod_row["name"] if prod_row else "Packaged Commodity"
            
            cursor.execute(
                """
                INSERT INTO reports (inspection_id, report_number, title, summary, final_status, generated_by, version_no, is_revised)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0)
                """,
                (
                    inspection_id, f"RPT-2026-DEL-{inspection_id:04d}",
                    f"Statutory Compliance Certificate - {prod_name}",
                    f"Dossier {insp_row['ref_no']} completed. Determination: {insp_row['compliance_status']}.",
                    insp_row["compliance_status"] if insp_row else "Needs Review",
                    user_id
                )
            )
            report_id = cursor.lastrowid
            report_row = cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        
        report = dict(report_row)
        report_id = report["id"]
        current_version = report.get("version_no") or 1

        # 2. Compare editable fields
        editable_keys = ["observations", "remarks", "corrective_actions", "recommendations", "summary"]
        changed_fields = []
        old_values = {}
        new_values = {}

        for k in editable_keys:
            old_val = (report.get(k) or "").strip()
            new_val = (updated_fields.get(k) or "").strip()
            if old_val != new_val:
                changed_fields.append(k)
                old_values[k] = old_val
                new_values[k] = new_val

        # If no fields modified, avoid creating duplicate revision
        if not changed_fields:
            return {
                "success": True,
                "no_change": True,
                "version_no": current_version,
                "message": "No report fields were modified. Revision unchanged."
            }

        # 3. Increment version number
        new_version_no = current_version + 1

        # Fetch user name for audit details
        user_row = cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        user_name = user_row["name"] if user_row else f"User #{user_id}"

        # Build complete snapshot of new state
        snapshot = {
            "title": report.get("title"),
            "summary": new_values.get("summary", report.get("summary") or ""),
            "observations": new_values.get("observations", report.get("observations") or ""),
            "remarks": new_values.get("remarks", report.get("remarks") or ""),
            "corrective_actions": new_values.get("corrective_actions", report.get("corrective_actions") or ""),
            "recommendations": new_values.get("recommendations", report.get("recommendations") or ""),
            "final_status": report.get("final_status"),
            "version_no": new_version_no,
            "edited_by": user_id,
            "edited_by_name": user_name,
            "edited_role": user_role,
            "edit_reason": edit_reason
        }

        # 4. Insert into report_revisions
        cursor.execute(
            """
            INSERT INTO report_revisions (report_id, inspection_id, version_no, previous_version_id, changed_fields, old_values, new_values, edited_by, edited_role, edit_reason, snapshot_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id, inspection_id, new_version_no, current_version,
                json.dumps(changed_fields), json.dumps(old_values), json.dumps(new_values),
                user_id, user_role, edit_reason, json.dumps(snapshot)
            )
        )
        rev_id = cursor.lastrowid

        # 5. Update reports table
        cursor.execute(
            """
            UPDATE reports
            SET summary = ?, observations = ?, remarks = ?, corrective_actions = ?, recommendations = ?,
                version_no = ?, is_revised = 1, last_edited_by = ?, last_edited_at = CURRENT_TIMESTAMP, last_edit_reason = ?
            WHERE id = ?
            """,
            (
                snapshot["summary"], snapshot["observations"], snapshot["remarks"],
                snapshot["corrective_actions"], snapshot["recommendations"],
                new_version_no, user_id, edit_reason, report_id
            )
        )

        # 6. Immutable audit log entry
        changed_str = ", ".join([f.replace("_", " ").title() for f in changed_fields])
        audit_details = f"Officer {user_name} ({user_role}) published Report Version {new_version_no}. Reason: '{edit_reason}'. Modified fields: {changed_str}."
        cursor.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (?, 'REPORT_REVISION', 'Inspection', ?, ?, ?)
            """,
            (user_id, inspection_id, audit_details, ip_address)
        )

        conn.commit()
        return {
            "success": True,
            "no_change": False,
            "version_no": new_version_no,
            "revision_id": rev_id,
            "changed_fields": changed_fields,
            "message": f"Report successfully updated to Version {new_version_no}."
        }
    finally:
        conn.close()


def save_notice_revision(notice_id, inspection_id, notice_ref_no, issued_to, draft_text, edit_reason, user_id, user_role, ip_address="127.0.0.1"):
    """
    Saves an updated revision of a draft legal notice with version tracking and audit logs.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        current_row = cursor.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
        if not current_row:
            return {"success": False, "error": "Notice not found."}

        current = dict(current_row)
        current_version = current.get("version_no") or 1

        changed_fields = []
        old_values = {}
        new_values = {}

        if (current.get("issued_to") or "").strip() != issued_to.strip():
            changed_fields.append("issued_to")
            old_values["issued_to"] = current.get("issued_to")
            new_values["issued_to"] = issued_to.strip()

        if (current.get("draft_text") or "").strip() != draft_text.strip():
            changed_fields.append("draft_text")
            old_values["draft_text"] = current.get("draft_text")
            new_values["draft_text"] = draft_text.strip()

        if not changed_fields:
            return {"success": True, "no_change": True, "version_no": current_version}

        new_version_no = current_version + 1
        user_row = cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        user_name = user_row["name"] if user_row else f"User #{user_id}"

        snapshot = {
            "notice_ref_no": notice_ref_no,
            "issued_to": issued_to.strip(),
            "draft_text": draft_text.strip(),
            "version_no": new_version_no,
            "edited_by": user_id,
            "edited_by_name": user_name,
            "edit_reason": edit_reason
        }

        # Insert notice_revisions
        cursor.execute(
            """
            INSERT INTO notice_revisions (notice_id, inspection_id, version_no, changed_fields, old_values, new_values, edited_by, edited_role, edit_reason, snapshot_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notice_id, inspection_id, new_version_no,
                json.dumps(changed_fields), json.dumps(old_values), json.dumps(new_values),
                user_id, user_role, edit_reason, json.dumps(snapshot)
            )
        )

        # Update notices
        cursor.execute(
            """
            UPDATE notices
            SET notice_ref_no = ?, issued_to = ?, draft_text = ?,
                version_no = ?, is_revised = 1, last_edited_by = ?, last_edited_at = CURRENT_TIMESTAMP, last_edit_reason = ?
            WHERE id = ?
            """,
            (notice_ref_no, issued_to.strip(), draft_text.strip(), new_version_no, user_id, edit_reason, notice_id)
        )

        # Audit log
        cursor.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (?, 'NOTICE_REVISION', 'Notice', ?, ?, ?)
            """,
            (user_id, inspection_id, f"Officer {user_name} published Revised Draft Notice {notice_ref_no} (Version {new_version_no}). Reason: '{edit_reason}'.", ip_address)
        )

        conn.commit()
        return {"success": True, "no_change": False, "version_no": new_version_no}
    finally:
        conn.close()


def save_compounding_revision(comp_id, inspection_id, proposed_fee, offense_section, audit_note, edit_reason, user_id, user_role, ip_address="127.0.0.1"):
    """
    Saves an updated revision of a compounding settlement proposal with version tracking.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()
        current_row = cursor.execute("SELECT * FROM compounding_records WHERE id = ?", (comp_id,)).fetchone()
        if not current_row:
            return {"success": False, "error": "Compounding record not found."}

        current = dict(current_row)
        current_version = current.get("version_no") or 1

        changed_fields = []
        old_values = {}
        new_values = {}

        if float(current.get("proposed_fee") or 0.0) != float(proposed_fee):
            changed_fields.append("proposed_fee")
            old_values["proposed_fee"] = current.get("proposed_fee")
            new_values["proposed_fee"] = proposed_fee

        if (current.get("audit_note") or "").strip() != audit_note.strip():
            changed_fields.append("audit_note")
            old_values["audit_note"] = current.get("audit_note")
            new_values["audit_note"] = audit_note.strip()

        if not changed_fields:
            return {"success": True, "no_change": True, "version_no": current_version}

        new_version_no = current_version + 1
        user_row = cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,)).fetchone()
        user_name = user_row["name"] if user_row else f"User #{user_id}"

        snapshot = {
            "proposed_fee": proposed_fee,
            "offense_section": offense_section,
            "audit_note": audit_note.strip(),
            "version_no": new_version_no,
            "edited_by": user_id,
            "edited_by_name": user_name,
            "edit_reason": edit_reason
        }

        cursor.execute(
            """
            INSERT INTO compounding_revisions (compounding_id, inspection_id, version_no, changed_fields, old_values, new_values, edited_by, edited_role, edit_reason, snapshot_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                comp_id, inspection_id, new_version_no,
                json.dumps(changed_fields), json.dumps(old_values), json.dumps(new_values),
                user_id, user_role, edit_reason, json.dumps(snapshot)
            )
        )

        cursor.execute(
            """
            UPDATE compounding_records
            SET proposed_fee = ?, calculated_amount = ?, offense_section = ?, audit_note = ?,
                version_no = ?, is_revised = 1, last_edited_by = ?, last_edited_at = CURRENT_TIMESTAMP, last_edit_reason = ?
            WHERE id = ?
            """,
            (proposed_fee, proposed_fee, offense_section, audit_note.strip(), new_version_no, user_id, edit_reason, comp_id)
        )

        cursor.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (?, 'COMPOUNDING_REVISION', 'Compounding', ?, ?, ?)
            """,
            (user_id, inspection_id, f"Officer {user_name} updated Compounding Settlement Order (Version {new_version_no}). Fee: ₹{proposed_fee:,.2f}. Reason: '{edit_reason}'.", ip_address)
        )

        conn.commit()
        return {"success": True, "no_change": False, "version_no": new_version_no}
    finally:
        conn.close()


def get_notice_detail(notice_id):
    conn = get_db()
    try:
        query = """
            SELECT n.*, i.ref_no as inspection_ref, p.name as product_name, p.category as product_category,
                   u.name as officer_name, u.designation as officer_designation, u.organization as officer_org,
                   u_ed.name as editor_name, u_ed.designation as editor_designation
            FROM notices n
            LEFT JOIN inspections i ON n.inspection_id = i.id
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON n.officer_id = u.id
            LEFT JOIN users u_ed ON n.last_edited_by = u_ed.id
            WHERE n.id = ?
        """
        row = conn.execute(query, (notice_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        n_revs = conn.execute("""
            SELECT nr.*, u.name as editor_name 
            FROM notice_revisions nr 
            LEFT JOIN users u ON nr.edited_by = u.id 
            WHERE nr.notice_id = ? 
            ORDER BY nr.version_no ASC
        """, (notice_id,)).fetchall()
        res["revisions"] = [dict(r) for r in n_revs]
        return res
    finally:
        conn.close()


def get_compounding_detail(comp_id):
    conn = get_db()
    try:
        query = """
            SELECT c.*, i.ref_no as inspection_ref, p.name as product_name, p.category as product_category,
                   p.manufacturer as product_mfr,
                   u.name as officer_name, u.designation as officer_designation, u.organization as officer_org,
                   u_ed.name as editor_name, u_ed.designation as editor_designation
            FROM compounding_records c
            LEFT JOIN inspections i ON c.inspection_id = i.id
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON c.approved_by = u.id
            LEFT JOIN users u_ed ON c.last_edited_by = u_ed.id
            WHERE c.id = ?
        """
        row = conn.execute(query, (comp_id,)).fetchone()
        if not row:
            return None
        res = dict(row)
        c_revs = conn.execute("""
            SELECT crv.*, u.name as editor_name 
            FROM compounding_revisions crv 
            LEFT JOIN users u ON crv.edited_by = u.id 
            WHERE crv.compounding_id = ? 
            ORDER BY crv.version_no ASC
        """, (comp_id,)).fetchall()
        res["revisions"] = [dict(r) for r in c_revs]
        return res
    finally:
        conn.close()


def add_audit_log(user_id, action, entity_type, entity_id, details, ip_address="127.0.0.1", conn=None):
    """Appends an immutable audit log entry. Reuses active connection if provided."""
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
        
    try:
        conn.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, action, entity_type, entity_id, details, ip_address)
        )
        if should_close:
            conn.commit()
    finally:
        if should_close:
            conn.close()


if __name__ == "__main__":
    init_db()
