"""
eSavadh - Intelligent Legal Metrology Compliance & Inspection Platform
Made by Team Avyukt

Statutory Framework: Legal Metrology Act, 2009 & Legal Metrology (Packaged Commodities) Rules, 2011.
Modular Flask architecture designed for straightforward future migration to FastAPI / PostgreSQL.
"""

import os
import time
import json
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

import database
from core.ocr_engine import perform_ocr_extraction, parse_declarations_from_text
from core.image_enhancer import enhance_evidence_image, analyze_image_quality, get_upload_directories
from core.rule_engine import evaluate_product_compliance
from core.legal_notices import generate_draft_notice, calculate_compounding_fee
from core.ecommerce_engine import parse_ecommerce_listing_details, get_tier2_roadmap_spec

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = os.environ.get("SECRET_KEY", "esavadh-statutory-metrology-avyukt-2026")

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(BASE_DIR, os.W_OK))

if IS_SERVERLESS:
    UPLOAD_FOLDER = "/tmp/uploads/original"
else:
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "original")

try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception as e:
    print(f"[eSavadh Storage] Notice: {e}")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.before_request
def ensure_serverless_db_ready():
    """Ensures database tables are bootstrapped if starting cold on a serverless container."""
    if not getattr(app, "_db_bootstrapped", False):
        try:
            database.init_db()
            app._db_bootstrapped = True
        except Exception as e:
            print(f"[eSavadh DB] Serverless init notice: {e}")


@app.route("/static/uploads/<path:filename>")
@app.route("/uploads/<path:filename>")
def serve_uploaded_evidence(filename):
    """Serves uploaded original and enhanced evidence images across local and serverless /tmp directories."""
    # 1. Local static uploads directory
    local_path = os.path.join(BASE_DIR, "static", "uploads", filename)
    if os.path.exists(local_path):
        return send_from_directory(os.path.dirname(local_path), os.path.basename(local_path))
    # 2. Serverless /tmp uploads directory
    tmp_path = os.path.join("/tmp", "uploads", filename)
    if os.path.exists(tmp_path):
        return send_from_directory(os.path.dirname(tmp_path), os.path.basename(tmp_path))
    return ("Evidence image not found", 404)


# ============================================================================
# Auth Decorators
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Official authentication required to access this compliance register.", "error")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                flash("Official authentication required.", "error")
                return redirect(url_for("login"))
            user_role = session["user"].get("role")
            if user_role not in allowed_roles:
                flash(f"Access Denied: You do not have permission to view this resource. Requires {', '.join(allowed_roles)} clearance.", "error")
                return redirect(url_for("dashboard_router"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================================
# Core Navigation & Landing Routes
# ============================================================================

@app.route("/")
@app.route("/landing")
def index():
    if "user" in session:
        return redirect(url_for("dashboard_router"))
    return render_template("landing.html")


@app.route("/landing")
def landing():
    return render_template("landing.html")


@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", active_page="how_it_works")


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route("/debug-request", methods=["GET", "POST"])
def debug_request():
    return jsonify({
        "method": request.method,
        "path": request.path,
        "url": request.url,
        "path_info": request.environ.get("PATH_INFO"),
        "query_string": request.environ.get("QUERY_STRING"),
        "raw_uri": request.environ.get("RAW_URI"),
        "request_uri": request.environ.get("REQUEST_URI"),
        "x_matched_path": request.environ.get("HTTP_X_MATCHED_PATH"),
        "x_forwarded_uri": request.environ.get("HTTP_X_FORWARDED_URI"),
        "x_vercel_id": request.environ.get("HTTP_X_VERCEL_ID")
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = database.get_user_by_email(email)

        if user and check_password_hash(user["password_hash"], password):
            u_dict = dict(user)
            if u_dict.get("role") not in ["Inspector", "Admin"]:
                flash("Access Denied: User role not authorized for system enforcement access.", "error")
                return render_template("login.html")

            session["user"] = {
                "id": u_dict.get("id"),
                "name": u_dict.get("name"),
                "email": u_dict.get("email"),
                "role": u_dict.get("role"),
                "organization": u_dict.get("organization", "Enforcement Wing"),
                "designation": u_dict.get("designation", "Officer")
            }
            database.add_audit_log(u_dict["id"], "LOGIN_SUCCESS", "User", u_dict["id"], f"Authenticated as {u_dict['role']}", request.remote_addr)
            flash(f"Welcome, {u_dict['name']} ({u_dict['role']}). Verified clearance granted.", "success")
            
            if u_dict["role"] == "Inspector":
                return redirect(url_for("inspector_dashboard"))
            elif u_dict["role"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard_router"))
        else:
            flash("Invalid credentials. Please verify your official email address and password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    user = session.get("user")
    if user:
        database.add_audit_log(user["id"], "LOGOUT", "User", user["id"], "User signed out.", request.remote_addr)
    session.clear()
    flash("You have been signed out from the legal metrology portal.", "info")
    return redirect(url_for("login"))


# ============================================================================
# Dashboards by Role
# ============================================================================

@app.route("/dashboard")
@login_required
def dashboard_router():
    role = session["user"].get("role")
    if role == "Inspector":
        return redirect(url_for("inspector_dashboard"))
    elif role == "Admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("login"))


@app.route("/inspector/dashboard")
@login_required
@role_required(["Inspector", "Admin"])
def inspector_dashboard():
    inspections = database.get_inspections(role_filter="Inspector", user_id=session["user"]["id"])
    compliant_count = sum(1 for i in inspections if i["compliance_status"] == "Compliant")
    violation_count = sum(1 for i in inspections if i["compliance_status"] == "Non-Compliant")
    
    conn = database.get_db()
    try:
        tasks = conn.execute("SELECT * FROM tasks WHERE assigned_to = ? AND status != 'Completed' ORDER BY id DESC", (session["user"]["id"],)).fetchall()
    finally:
        conn.close()

    return render_template(
        "dashboard_inspector.html",
        user=session["user"],
        inspections=inspections,
        compliant_count=compliant_count,
        violation_count=violation_count,
        tasks=tasks,
        active_page="dashboard"
    )


@app.route("/admin/dashboard")
@login_required
@role_required(["Admin"])
def admin_dashboard():
    inspections = database.get_inspections(limit=50)
    total = len(inspections)
    compliant = sum(1 for i in inspections if i["compliance_status"] == "Compliant")
    violations = sum(1 for i in inspections if i["compliance_status"] == "Non-Compliant")
    compliance_rate = int((compliant / max(total, 1)) * 100)

    return render_template(
        "dashboard_admin.html",
        user=session["user"],
        inspections=inspections,
        total_inspections=total,
        compliant_count=compliant,
        violation_count=violations,
        compliance_rate=compliance_rate,
        active_page="dashboard"
    )


# ============================================================================
# Inspection Management & Guided 5-Step Flow
# ============================================================================

@app.route("/inspection/new")
@login_required
@role_required(["Inspector", "Admin"])
def new_inspection():
    auto_ref_no = f"INSP-2026-DEL-{int(time.time()) % 10000:04d}"
    return render_template("inspection_new.html", auto_ref_no=auto_ref_no, active_page="new_inspection")


@app.route("/inspection/create", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def create_inspection():
    req_ref = request.form.get("ref_no")
    conn_check = database.get_db()
    try:
        existing_ref = conn_check.execute("SELECT id FROM inspections WHERE ref_no = ?", (req_ref,)).fetchone() if req_ref else None
    finally:
        conn_check.close()
    
    if existing_ref or not req_ref:
        ref_no = f"INSP-2026-DEL-{int(time.time() * 1000) % 100000:05d}"
    else:
        ref_no = req_ref
        
    location = request.form.get("location", "").strip() or "Field Market Surveillance Node"
    user_product_name = request.form.get("product_name", "").strip()
    category = request.form.get("category", "Beverages / Food")
    user_mfg_date = request.form.get("mfg_date", "").strip()
    view_side = request.form.get("view_side", "Front")

    # 1. Handle Real Image Upload
    file = request.files.get("package_image")
    if not file or file.filename == "":
        flash("Please upload a real package image or capture one using your camera to perform inspection.", "error")
        return redirect(url_for("new_inspection"))

    fname = secure_filename(file.filename)
    timestamped_name = f"{int(time.time())}_{fname}"
    abs_orig_path = os.path.join(app.config["UPLOAD_FOLDER"], timestamped_name)
    file.save(abs_orig_path)
    image_rel_path = f"uploads/original/{timestamped_name}"
    
    # 2. Quality Enhancement (Preserving original evidence separately)
    enhanced_rel_path, enh_summary, quality_score = enhance_evidence_image(abs_orig_path, timestamped_name)

    # 3. Real OCR & Declaration Extraction
    ocr_data = perform_ocr_extraction(abs_orig_path, side_hint=view_side)
    decls = ocr_data["declarations"]
    raw_ocr_text = ocr_data.get("raw_text", "").strip()

    # Determine commodity name
    if user_product_name:
        product_name = user_product_name
    elif raw_ocr_text:
        # Infer title from first line of text
        first_line = raw_ocr_text.split("\n")[0].strip()
        product_name = first_line[:70] if len(first_line) > 3 else f"Commodity ({category})"
    else:
        product_name = f"Packaged Item ({category})"

    # Determine manufacturing date
    extracted_mfg = decls.get("mfg_date", {}).get("extracted_value")
    mfg_date = user_mfg_date if user_mfg_date else (extracted_mfg if extracted_mfg else datetime.now().strftime("%m/%Y"))

    # 4. Time-Aware Rule Evaluation
    compliance_res = evaluate_product_compliance(decls, mfg_date_str=mfg_date, category=category)

    # 5. Persist into Database
    conn = database.get_db()
    try:
        cursor = conn.cursor()

        # Product record
        cursor.execute(
            """
            INSERT INTO products (name, category, mfg_date, country_of_origin, net_quantity, mrp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product_name, category, mfg_date, 
                decls.get("country_of_origin", {}).get("extracted_value"),
                decls.get("net_quantity", {}).get("extracted_value"),
                decls.get("mrp", {}).get("extracted_value")
            )
        )
        product_id = cursor.lastrowid

        # Inspection record
        cursor.execute(
            """
            INSERT INTO inspections (ref_no, product_id, inspector_id, location, compliance_status, source, overall_notes)
            VALUES (?, ?, ?, ?, ?, 'field', ?)
            """,
            (
                ref_no, product_id, session["user"]["id"], location,
                compliance_res["overall_status"],
                f"Evaluated against Legal Metrology Rules (Packaged Commodities) 2011. Time-aware baseline: {mfg_date}."
            )
        )
        inspection_id = cursor.lastrowid

        # Inspection Image
        cursor.execute(
            """
            INSERT INTO inspection_images (inspection_id, view_side, original_image_path, enhanced_image_path, quality_score, is_enhanced)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (inspection_id, view_side, image_rel_path, enhanced_rel_path, quality_score)
        )
        image_id = cursor.lastrowid

        # OCR Results Record (Raw text extracted from image)
        cursor.execute(
            """
            INSERT INTO ocr_results (inspection_id, image_id, raw_text, detected_languages, confidence_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (inspection_id, image_id, raw_ocr_text, ocr_data.get("detected_languages", "English"), ocr_data.get("overall_confidence", 0.0))
        )

        # Declarations
        for field, d in decls.items():
            cursor.execute(
                """
                INSERT INTO declarations (inspection_id, field_name, extracted_value, confidence, suggested_value, suggestion_reason, inspector_status, confirmed_value, source_view)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id, field, d["extracted_value"], d["confidence"],
                    d["suggested_value"], d["suggestion_reason"], "Unreviewed",
                    d["suggested_value"] or d["extracted_value"], view_side
                )
            )

        # Compliance Findings
        for f in compliance_res["findings"]:
            r = cursor.execute("SELECT id FROM rules WHERE rule_code = ?", (f["rule_code"],)).fetchone()
            rule_id = r["id"] if r else None
            cursor.execute(
                """
                INSERT INTO compliance_findings (inspection_id, rule_id, declaration_field, status, observed_value, expected_value, finding_note, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id, rule_id, f["declaration_field"], f["status"],
                    f["observed_value"], f["expected_value"], f["finding_note"], f["severity"]
                )
            )

        # Report certificate record
        cursor.execute(
            """
            INSERT INTO reports (inspection_id, report_number, title, summary, final_status, generated_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inspection_id, f"RPT-2026-DEL-{inspection_id:04d}",
                f"Statutory Compliance Certificate - {product_name}",
                f"Dossier {ref_no} completed by Officer {session['user']['name']}. Determination: {compliance_res['overall_status']}.",
                compliance_res["overall_status"], session["user"]["id"]
            )
        )

        # Audit log
        cursor.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address)
            VALUES (?, 'CREATE_INSPECTION', 'Inspection', ?, ?, ?)
            """,
            (
                session["user"]["id"], inspection_id,
                f"Officer created inspection dossier {ref_no} for {product_name}. Status: {compliance_res['overall_status']}.",
                request.remote_addr
            )
        )

        conn.commit()
    finally:
        conn.close()

    flash(f"Inspection dossier {ref_no} created successfully. Real OCR extracted {len([k for k,v in decls.items() if v['extracted_value']])} declaration(s).", "success")
    return redirect(url_for("inspection_detail", inspection_id=inspection_id))


@app.route("/inspections")
@login_required
def inspections_list():
    status_filter = request.args.get("status")
    source_filter = request.args.get("source")
    
    inspections = database.get_inspections(limit=100, source_filter=source_filter)
    if status_filter:
        inspections = [i for i in inspections if i["compliance_status"] == status_filter]
        
    return render_template(
        "inspections_list.html",
        inspections=inspections,
        current_filter=status_filter,
        current_source=source_filter,
        active_page="inspections"
    )


@app.route("/inspection/<int:inspection_id>")
@login_required
def inspection_detail(inspection_id):
    dossier = database.get_inspection_detail(inspection_id)
    if not dossier:
        flash("Inspection dossier not found.", "error")
        return redirect(url_for("inspections_list"))
    return render_template("inspection_detail.html", dossier=dossier, active_page="inspections")


@app.route("/inspection/<int:inspection_id>/print")
@login_required
def printable_dossier(inspection_id):
    version_param = request.args.get("version")
    dossier = database.get_inspection_detail(inspection_id, version_override=version_param)
    if not dossier:
        flash("Dossier not found.", "error")
        return redirect(url_for("inspections_list"))
    return render_template("printable_dossier.html", dossier=dossier, viewed_version=version_param)


# ============================================================================
# Human In The Loop (HITL) API Handlers
# ============================================================================

@app.route("/api/declarations/<int:decl_id>/review", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def review_declaration(decl_id):
    data = request.get_json() or {}
    action = data.get("action", "confirm")  # 'confirm' or 'deny'
    confirmed_val = data.get("confirmed_value")

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        status_str = "Confirmed" if action == "confirm" else "Denied"
        cursor.execute(
            "UPDATE declarations SET inspector_status = ?, confirmed_value = ? WHERE id = ?",
            (status_str, confirmed_val, decl_id)
        )

        # Log to audit trail
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, 'HITL_REVIEW', 'Declaration', ?, ?, ?)",
            (session["user"]["id"], decl_id, f"Officer {session['user']['name']} set declaration #{decl_id} to {status_str} (Value: '{confirmed_val}')", request.remote_addr)
        )

        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True, "action": action, "status": status_str})


@app.route("/api/declarations/<int:decl_id>/edit", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def edit_declaration(decl_id):
    data = request.get_json() or {}
    new_value = data.get("value", "").strip()

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE declarations SET inspector_status = 'Edited', confirmed_value = ? WHERE id = ?",
            (new_value, decl_id)
        )

        # Log to audit trail
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, 'EDIT_DECLARATION', 'Declaration', ?, ?, ?)",
            (session["user"]["id"], decl_id, f"Officer {session['user']['name']} edited declaration #{decl_id} to '{new_value}'", request.remote_addr)
        )

        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True, "status": "Edited", "value": new_value})


@app.route("/api/declarations/confirm-all/<int:inspection_id>", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def confirm_all_declarations(inspection_id):
    conn = database.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE declarations 
            SET inspector_status = 'Confirmed', confirmed_value = COALESCE(suggested_value, extracted_value) 
            WHERE inspection_id = ? AND inspector_status = 'Unreviewed' AND extracted_value IS NOT NULL AND extracted_value != ''
            """,
            (inspection_id,)
        )
        updated_count = cursor.rowcount

        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, 'BULK_CONFIRM', 'Inspection', ?, ?, ?)",
            (session["user"]["id"], inspection_id, f"Officer {session['user']['name']} bulk confirmed {updated_count} declarations.", request.remote_addr)
        )

        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True, "updated_count": updated_count})


@app.route("/api/inspection/<int:inspection_id>/evaluate", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def reevaluate_inspection_compliance(inspection_id):
    dossier = database.get_inspection_detail(inspection_id)
    if not dossier:
        return jsonify({"success": False, "error": "Dossier not found"}), 404

    # Build declarations map from verified database state
    decls_map = {}
    for d in dossier["declarations"]:
        val = d["confirmed_value"] if d["confirmed_value"] is not None else d["extracted_value"]
        decls_map[d["field_name"]] = {
            "extracted_value": val,
            "confidence": d["confidence"]
        }

    mfg_date = dossier["inspection"].get("product_mfg_date") or decls_map.get("mfg_date", {}).get("extracted_value") or "05/2024"
    category = dossier["inspection"].get("product_category") or "Beverages / Food"

    eval_result = evaluate_product_compliance(decls_map, mfg_date_str=mfg_date, category=category)

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        # Delete old findings
        cursor.execute("DELETE FROM compliance_findings WHERE inspection_id = ?", (inspection_id,))

        # Insert new findings
        for f in eval_result["findings"]:
            r = cursor.execute("SELECT id FROM rules WHERE rule_code = ?", (f["rule_code"],)).fetchone()
            rule_id = r["id"] if r else None
            cursor.execute(
                """
                INSERT INTO compliance_findings (inspection_id, rule_id, declaration_field, status, observed_value, expected_value, finding_note, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inspection_id, rule_id, f["declaration_field"], f["status"],
                    f["observed_value"], f["expected_value"], f["finding_note"], f["severity"]
                )
            )

        # Update inspection overall status
        cursor.execute(
            "UPDATE inspections SET compliance_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (eval_result["overall_status"], inspection_id)
        )

        # Update report status
        cursor.execute(
            "UPDATE reports SET final_status = ?, summary = ? WHERE inspection_id = ?",
            (
                eval_result["overall_status"],
                f"Statutory compliance evaluation updated by Officer {session['user']['name']}. Determination: {eval_result['overall_status']}.",
                inspection_id
            )
        )

        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, 'REEVALUATE_RULES', 'Inspection', ?, ?, ?)",
            (session["user"]["id"], inspection_id, f"Officer re-evaluated statutory rules. New status: {eval_result['overall_status']}.", request.remote_addr)
        )

        conn.commit()
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "overall_status": eval_result["overall_status"],
        "findings_count": len(eval_result["findings"]),
        "findings": eval_result["findings"],
        "summary": f"Statutory compliance evaluation updated by Officer {session['user']['name']}. Determination: {eval_result['overall_status']}."
    })


@app.route("/api/inspection/<int:inspection_id>/finalize", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def finalize_inspection(inspection_id):
    data = request.get_json() or {}
    notes = data.get("notes", "").strip()

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE inspections SET status = 'Completed', overall_notes = COALESCE(?, overall_notes), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (notes if notes else None, inspection_id)
        )

        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?, 'FINALIZE_DOSSIER', 'Inspection', ?, ?, ?)",
            (session["user"]["id"], inspection_id, f"Officer {session['user']['name']} finalized & signed off on dossier.", request.remote_addr)
        )

        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True, "status": "Completed"})


# ============================================================================
# Offline Storage & Synchronization API
# ============================================================================

@app.route("/api/sync", methods=["POST"])
def sync_offline_inspections():
    payload = request.get_json() or {}
    items = payload.get("items", [])
    
    conn = database.get_db()
    try:
        cursor = conn.cursor()
        processed_count = 0

        for item in items:
            sync_id = item.get("sync_id")
            data = item.get("data", {})

            # Prevent duplicates
            existing = cursor.execute("SELECT id FROM inspections WHERE sync_id = ?", (sync_id,)).fetchone()
            if existing:
                continue

            ref_no = data.get("ref_no") or f"INSP-OFFLINE-{int(time.time() * 1000) % 100000:05d}"
            location = data.get("location", "Offline Field Node")
            product_name = data.get("product_name", "Packaged Commodity")
            category = data.get("category", "Beverages / Food")
            mfg_date = data.get("mfg_date", "05/2024")

            # Create product
            cursor.execute(
                "INSERT INTO products (name, category, mfg_date) VALUES (?, ?, ?)",
                (product_name, category, mfg_date)
            )
            product_id = cursor.lastrowid

            # Create inspection
            cursor.execute(
                """
                INSERT INTO inspections (ref_no, product_id, inspector_id, location, compliance_status, source, overall_notes, sync_id)
                VALUES (?, ?, 2, ?, 'Needs Review', 'field', 'Created in offline field mode and synchronized upon network restoration.', ?)
                """,
                (ref_no, product_id, location, sync_id)
            )
            inspection_id = cursor.lastrowid

            # Add audit log
            cursor.execute(
                "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address) VALUES (2, 'OFFLINE_SYNC', 'Inspection', ?, ?, ?)",
                (inspection_id, f"Synchronized offline dossier {ref_no} with sync_id: {sync_id}", request.remote_addr)
            )
            processed_count += 1

        conn.commit()
    finally:
        conn.close()

    return jsonify({"success": True, "processed_count": processed_count})


# ============================================================================
# Section 46: E-Commerce Listing Monitoring
# ============================================================================

@app.route("/ecommerce")
@login_required
@role_required(["Inspector", "Admin"])
def ecommerce_monitor():
    conn = database.get_db()
    try:
        listings = conn.execute("SELECT * FROM ecommerce_listings ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    tier2_specs = get_tier2_roadmap_spec()
    return render_template("ecommerce_monitor.html", listings=listings, tier2_specs=tier2_specs, active_page="ecommerce")


@app.route("/ecommerce/check", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def check_ecommerce_listing():
    listing_url = request.form.get("listing_url", "").strip()
    raw_text = request.form.get("raw_text", "").strip()
    
    # Check if a screenshot image was uploaded
    screenshot_file = request.files.get("screenshot_image")
    screenshot_rel_path = None
    
    if screenshot_file and screenshot_file.filename != "":
        fname = secure_filename(screenshot_file.filename)
        timestamped_name = f"ecom_{int(time.time())}_{fname}"
        abs_orig_path = os.path.join(app.config["UPLOAD_FOLDER"], timestamped_name)
        screenshot_file.save(abs_orig_path)
        screenshot_rel_path = f"uploads/original/{timestamped_name}"
        
        # Run real OCR on the uploaded screenshot
        ocr_res = perform_ocr_extraction(abs_orig_path, side_hint="Listing Screenshot")
        if ocr_res.get("raw_text"):
            raw_text = ocr_res["raw_text"] + "\n" + raw_text

    if not listing_url and not raw_text:
        flash("Please provide a product listing URL, paste specifications text, or upload a listing screenshot to analyze.", "error")
        return redirect(url_for("ecommerce_monitor"))

    effective_url = listing_url or "https://digital-marketplace.in/item/listing-check"
    result = parse_ecommerce_listing_details(effective_url, raw_text=raw_text)

    # Save to database
    conn = database.get_db()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO ecommerce_listings (platform, seller_name, listing_url, product_title, product_category, declared_mrp, declared_net_qty, declared_country, declared_mfr, content_hash, compliance_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["platform"], result["seller_name"], effective_url, result["product_title"],
                result["product_category"], result["declarations"].get("mrp", {}).get("extracted_value"),
                result["declarations"].get("net_quantity", {}).get("extracted_value"),
                result["declarations"].get("country_of_origin", {}).get("extracted_value"),
                result["declarations"].get("manufacturer", {}).get("extracted_value"),
                result["content_hash"], result["overall_status"]
            )
        )

        # Also log as an inspection equivalent
        ref_no = f"INSP-2026-ECOM-{int(time.time() * 1000) % 100000:05d}"
        cursor.execute(
            "INSERT INTO products (name, category, country_of_origin) VALUES (?, ?, ?)",
            (result["product_title"], result["product_category"], result["declarations"].get("country_of_origin", {}).get("extracted_value") or "India")
        )
        product_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO inspections (ref_no, product_id, inspector_id, location, compliance_status, source, overall_notes)
            VALUES (?, ?, ?, ?, ?, 'e-commerce', ?)
            """,
            (
                ref_no, product_id, session["user"]["id"], f"{result['platform']} Online Storefront",
                result["overall_status"],
                f"Digital listing verified under Rule 6(10) & 6(11) of PCR 2011. Seller: {result['seller_name']}."
            )
        )
        inspection_id = cursor.lastrowid

        # If screenshot uploaded, attach as evidence
        if screenshot_rel_path:
            cursor.execute(
                """
                INSERT INTO inspection_images (inspection_id, view_side, original_image_path, quality_score, is_enhanced)
                VALUES (?, 'Listing Screenshot', ?, 90, 0)
                """,
                (inspection_id, screenshot_rel_path)
            )

        # Add Declarations
        for field, d in result["declarations"].items():
            cursor.execute(
                """
                INSERT INTO declarations (inspection_id, field_name, extracted_value, confidence, suggested_value, suggestion_reason, inspector_status, confirmed_value, source_view)
                VALUES (?, ?, ?, ?, ?, ?, 'Unreviewed', ?, 'Listing Screenshot')
                """,
                (
                    inspection_id, field, d["extracted_value"], d["confidence"],
                    d["suggested_value"], d["suggestion_reason"], d["suggested_value"] or d["extracted_value"]
                )
            )

        # Add findings
        for f in result["compliance_result"]["findings"]:
            r = cursor.execute("SELECT id FROM rules WHERE rule_code = ?", (f["rule_code"],)).fetchone()
            rule_id = r["id"] if r else None
            cursor.execute(
                """
                INSERT INTO compliance_findings (inspection_id, rule_id, declaration_field, status, observed_value, expected_value, finding_note, severity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (inspection_id, rule_id, f["declaration_field"], f["status"], f["observed_value"], f["expected_value"], f["finding_note"], f["severity"])
            )

        # Report
        cursor.execute(
            """
            INSERT INTO reports (inspection_id, report_number, title, summary, final_status, generated_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (inspection_id, f"RPT-ECOM-{inspection_id:04d}", f"E-Commerce Compliance Audit - {result['product_title']}", f"Surveillance audit of {result['platform']} listing. Determination: {result['overall_status']}.", result["overall_status"], session["user"]["id"])
        )

        database.add_audit_log(session["user"]["id"], "ECOM_AUDIT", "Inspection", inspection_id, f"E-Commerce Listing compliance checked for {result['product_title']}", request.remote_addr, conn=conn)

        conn.commit()
    finally:
        conn.close()

    flash(f"E-Commerce listing evaluated: Status: {result['overall_status']} (Tier 1 Verified).", "success")
    return redirect(url_for("inspection_detail", inspection_id=inspection_id))


# ============================================================================
# Legal Notices & Compounding Routes
# ============================================================================

@app.route("/inspection/<int:inspection_id>/notice")
@login_required
@role_required(["Inspector", "Admin"])
def draft_notice_view(inspection_id):
    dossier = database.get_inspection_detail(inspection_id)
    if not dossier:
        flash("Inspection not found.", "error")
        return redirect(url_for("inspections_list"))

    violations = [f for f in dossier["findings"] if f["status"] == "Non-Compliant"]
    notice_data = generate_draft_notice(
        dossier["inspection"]["ref_no"],
        dossier["inspection"]["product_manufacturer"] or "Himalayan Pure Harvest Ltd.",
        "Plot 14, Industrial Area, Solan, Himachal Pradesh - 173212",
        violations,
        session["user"]["name"],
        session["user"].get("designation") or "Senior Legal Metrology Officer"
    )

    return render_template("draft_notice.html", inspection=dossier["inspection"], notice_data=notice_data, active_page="inspections")


# ============================================================================
# Report Revision & Editing API
# ============================================================================

@app.route("/api/inspection/<int:inspection_id>/report/edit", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def edit_inspection_report(inspection_id):
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    observations = data.get("observations", "").strip()
    remarks = data.get("remarks", "").strip()
    corrective_actions = data.get("corrective_actions", "").strip()
    recommendations = data.get("recommendations", "").strip()
    summary = data.get("summary", "").strip()
    edit_reason = data.get("edit_reason", "").strip()

    if not edit_reason:
        edit_reason = "Officer revised statutory observations and remarks."

    updated_fields = {
        "observations": observations,
        "remarks": remarks,
        "corrective_actions": corrective_actions,
        "recommendations": recommendations,
        "summary": summary
    }

    res = database.save_report_revision(
        inspection_id,
        updated_fields,
        edit_reason,
        session["user"]["id"],
        session["user"]["role"],
        request.remote_addr
    )

    if not request.is_json:
        flash(res["message"], "success")
        return redirect(url_for("inspection_detail", inspection_id=inspection_id, step=4))

    return jsonify(res)


@app.route("/api/inspection/<int:inspection_id>/report/revisions")
@login_required
def get_report_revisions_api(inspection_id):
    dossier = database.get_inspection_detail(inspection_id)
    if not dossier:
        return jsonify({"success": False, "error": "Inspection not found"}), 404
    rep = dossier.get("report") or {}
    return jsonify({
        "success": True,
        "current_version": rep.get("version_no", 1),
        "report": rep,
        "revisions": dossier.get("report_revisions", []),
        "audit_logs": [l for l in dossier.get("audit_logs", []) if l.get("action") in ["REPORT_EDITED", "REPORT_REVISION"]]
    })


@app.route("/inspection/<int:inspection_id>/notice/save", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def save_draft_notice(inspection_id):
    notice_ref = request.form.get("notice_ref_no", "").strip()
    issued_to = request.form.get("issued_to", "").strip()
    draft_text = request.form.get("draft_text", "").strip()
    edit_reason = request.form.get("edit_reason", "Statutory notice draft updated by officer.").strip()

    if not notice_ref:
        notice_ref = f"LM/ENF/{datetime.now().strftime('%Y')}/INSP-{inspection_id}-{int(time.time()) % 10000}"

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        existing = cursor.execute(
            "SELECT id, notice_ref_no FROM notices WHERE notice_ref_no = ?",
            (notice_ref,)
        ).fetchone()
        if not existing:
            existing = cursor.execute(
                "SELECT id, notice_ref_no FROM notices WHERE inspection_id = ?",
                (inspection_id,)
            ).fetchone()

        if existing:
            # Notice exists -> Create revision
            conn.close()
            res = database.save_notice_revision(
                existing["id"], inspection_id, notice_ref, issued_to, draft_text,
                edit_reason, session["user"]["id"], session["user"]["role"], request.remote_addr
            )
            v_no = res.get("version_no", 2)
            flash(f"Revised Draft Notice {notice_ref} (Version {v_no}) saved to inspection dossier.", "success")
            return redirect(url_for("inspection_detail", inspection_id=inspection_id, step=4))
        else:
            clash = cursor.execute("SELECT id FROM notices WHERE notice_ref_no = ?", (notice_ref,)).fetchone()
            if clash:
                notice_ref = f"{notice_ref}-{int(time.time()) % 1000}"

            cursor.execute(
                """
                INSERT INTO notices (inspection_id, notice_ref_no, issued_to, violation_summary, legal_provisions, draft_text, officer_id, version_no, is_revised)
                VALUES (?, ?, ?, 'Mandatory packaging declaration violations observed under Rule 6 of PCR 2011', 'Section 18 read with Section 36 & 49, LM Act 2009', ?, ?, 1, 0)
                """,
                (inspection_id, notice_ref, issued_to, draft_text, session["user"]["id"])
            )
            database.add_audit_log(session["user"]["id"], "CREATE_DRAFT_NOTICE", "Notice", inspection_id, f"Officer created original draft notice {notice_ref} (Version 1)", request.remote_addr, conn=conn)
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    flash(f"Draft Legal Notice {notice_ref} (Version 1) saved to inspection dossier.", "success")
    return redirect(url_for("inspection_detail", inspection_id=inspection_id, step=4))


@app.route("/notice/<int:notice_id>/print")
@login_required
def print_notice(notice_id):
    notice = database.get_notice_detail(notice_id)
    if not notice:
        flash("Draft Legal Notice not found.", "error")
        return redirect(url_for("inspections_list"))
    return render_template("printable_notice.html", notice=notice)


@app.route("/inspection/<int:inspection_id>/compounding")
@login_required
@role_required(["Inspector", "Admin"])
def compounding_view(inspection_id):
    dossier = database.get_inspection_detail(inspection_id)
    if not dossier:
        flash("Dossier not found.", "error")
        return redirect(url_for("inspections_list"))

    violations = [f for f in dossier["findings"] if f["status"] == "Non-Compliant"]
    fee_calc = calculate_compounding_fee(len(violations), recipient_role="Manufacturer")

    return render_template("compounding.html", inspection=dossier["inspection"], fee_calc=fee_calc, active_page="inspections")


@app.route("/inspection/<int:inspection_id>/compounding/submit", methods=["POST"])
@login_required
@role_required(["Inspector", "Admin"])
def submit_compounding_order(inspection_id):
    proposed_fee = float(request.form.get("proposed_fee", 25000.0))
    offense_section = request.form.get("offense_section", "Section 48 read with Section 36(1)")
    audit_note = request.form.get("audit_note", "")
    edit_reason = request.form.get("edit_reason", "Statutory compounding settlement proposal formulated.").strip()

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        existing = cursor.execute("SELECT id FROM compounding_records WHERE inspection_id = ?", (inspection_id,)).fetchone()
        if existing:
            conn.close()
            res = database.save_compounding_revision(
                existing["id"], inspection_id, proposed_fee, offense_section, audit_note,
                edit_reason, session["user"]["id"], session["user"]["role"], request.remote_addr
            )
            v_no = res.get("version_no", 2)
            flash(f"Revised Compounding Settlement Proposal (Version {v_no}) saved to dossier.", "success")
            return redirect(url_for("inspection_detail", inspection_id=inspection_id, step=4))
        else:
            cursor.execute(
                """
                INSERT INTO compounding_records (inspection_id, offense_section, proposed_fee, calculated_amount, status, approved_by, audit_note, version_no, is_revised)
                VALUES (?, ?, ?, ?, 'Proposed', ?, ?, 1, 0)
                """,
                (inspection_id, offense_section, proposed_fee, proposed_fee, session["user"]["id"], audit_note)
            )
            database.add_audit_log(session["user"]["id"], "PROPOSE_COMPOUNDING", "Compounding", inspection_id, f"Proposed composition sum of ₹{proposed_fee:,.2f} (Version 1)", request.remote_addr, conn=conn)
            conn.commit()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    flash("Compounding settlement proposal formulated and recorded in dossier (Version 1).", "success")
    return redirect(url_for("inspection_detail", inspection_id=inspection_id, step=4))


@app.route("/compounding/<int:comp_id>/print")
@login_required
def print_compounding(comp_id):
    compounding = database.get_compounding_detail(comp_id)
    if not compounding:
        flash("Compounding settlement proposal not found.", "error")
        return redirect(url_for("inspections_list"))
    return render_template("printable_compounding.html", compounding=compounding)


# ============================================================================
# Auxiliary Statutory Centers & Teams
# ============================================================================

@app.route("/rules")
@login_required
def rules_center():
    rules = database.get_all_rules()
    return render_template("rules_center.html", rules=rules, active_page="rules")


@app.route("/reports")
@login_required
def reports_center():
    inspections = database.get_inspections(limit=100)
    total = len(inspections)
    compliant = sum(1 for i in inspections if i["compliance_status"] == "Compliant")
    violations = sum(1 for i in inspections if i["compliance_status"] == "Non-Compliant")
    
    return render_template(
        "reports_center.html",
        inspections=inspections,
        total_inspections=total,
        compliant_count=compliant,
        violation_count=violations,
        active_page="reports"
    )


@app.route("/teams")
@login_required
@role_required(["Admin"])
def team_management():
    conn = database.get_db()
    try:
        teams = conn.execute("SELECT * FROM teams").fetchall()
        tasks = conn.execute("SELECT t.*, u.name as assigned_to_name FROM tasks t LEFT JOIN users u ON t.assigned_to = u.id").fetchall()
        inspectors = conn.execute("SELECT id, name, organization FROM users WHERE role = 'Inspector'").fetchall()
    finally:
        conn.close()
    return render_template("team_management.html", teams=teams, tasks=tasks, inspectors=inspectors, active_page="teams")


@app.route("/teams/task/create", methods=["POST"])
@login_required
@role_required(["Admin"])
def create_team_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    assigned_to = request.form.get("assigned_to")
    priority = request.form.get("priority", "Medium")
    due_date = request.form.get("due_date")

    if not title or not assigned_to:
        flash("Task title and assigned officer are required.", "error")
        return redirect(url_for("team_management"))

    conn = database.get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (title, description, assigned_to, assigned_by, priority, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, 'Assigned')
            """,
            (title, description, assigned_to, session["user"]["id"], priority, due_date or None)
        )
        task_id = cursor.lastrowid

        # Notification for inspector
        cursor.execute(
            """
            INSERT INTO notifications (user_id, title, message, type, link)
            VALUES (?, 'New Task Assigned', ?, 'info', '/dashboard')
            """,
            (assigned_to, f"New task assigned: {title}")
        )

        database.add_audit_log(session["user"]["id"], "CREATE_TASK", "Task", task_id, f"Admin assigned task '{title}' to User #{assigned_to}", request.remote_addr, conn=conn)
        conn.commit()
    finally:
        conn.close()

    flash(f"Surveillance task '{title}' successfully assigned.", "success")
    return redirect(url_for("team_management"))


@app.route("/audit")
@login_required
@role_required(["Admin"])
def audit_integrity():
    conn = database.get_db()
    try:
        logs = conn.execute("SELECT al.*, u.name as user_name FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id ORDER BY al.id DESC LIMIT 100").fetchall()
    finally:
        conn.close()
    return render_template("audit_integrity.html", logs=logs, active_page="audit")


@app.errorhandler(404)
def page_not_found(e):
    if "user" in session:
        flash("The requested compliance resource was not found. Redirected to dashboard.", "info")
        return redirect(url_for("dashboard_router"))
    return render_template("landing.html"), 200


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == "__main__":
    database.init_db()
    print("==================================================================")
    print(" eSavadh — Intelligent Legal Metrology Compliance Platform")
    print(" Made by Team Avyukt")
    print(" Running at: http://127.0.0.1:5000")
    print("==================================================================")
    app.run(debug=True, port=5000)
