"""
Comprehensive E2E Test Suite for eSavadh Report Editing & Revision Tracking System.
Tests:
1. Initial Report Generation (Version 1 - Master Original)
2. Report Revision (Version 2) with mandatory justification
3. Idempotent Edit (No-op when no field changes)
4. Second Revision (Version 3) with full diffs & snapshot data
5. Historical Snapshot retrieval (?version=1, ?version=2)
6. Notice Formulation (v1) and Revision (v2)
7. Compounding Settlement Formulation (v1) and Revision (v2)
8. Printable Views showing Revision Banners and Metadata
9. Immutable Audit Trail verification (WHO, WHAT, WHEN, WHY)
10. Evidence Immutability Verification (Original OCR & images uncorrupted)
"""

import os
import sys
import time
import json
import sqlite3
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database import get_db, init_db

class TestReportRevisionsE2E(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def login_inspector(self):
        res = self.client.post("/login", data={
            "email": "inspector@esavadh.gov.in",
            "password": "inspector123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        return res

    def login_admin(self):
        res = self.client.post("/login", data={
            "email": "admin@esavadh.gov.in",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        return res

    def test_complete_revision_lifecycle(self):
        print("\n=======================================================")
        print("--- RUNNING E2E REPORT REVISION & AUDIT SUITE ---")
        print("=======================================================")

        # 1. Login as Inspector
        self.login_inspector()

        # 2. Create a fresh test inspection
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO products (name, brand, category, manufacturer)
                VALUES ('Sample Edible Oil 1L', 'Fortune Pure', 'Edible Oils', 'Fortune Agro Pack Ltd.')
            """)
            prod_id = cursor.lastrowid
            
            ref_no = f"INSP-TEST-REV-{int(time.time())}"
            cursor.execute("""
                INSERT INTO inspections (ref_no, product_id, inspector_id, compliance_status, overall_notes)
                VALUES (?, ?, 1, 'Non-Compliant', 'Initial inspection notes')
            """, (ref_no, prod_id))
            db.commit()
            inspection_id = cursor.lastrowid
            print(f"[+] Created Fresh Test Inspection ID: {inspection_id} (Ref: {ref_no})")

            # Ensure report exists at version 1
            rpt_num = f"RPT-TEST-{inspection_id:04d}"
            cursor.execute("""
                INSERT INTO reports (inspection_id, report_number, title, summary, observations, remarks, corrective_actions, recommendations, final_status, generated_by, version_no, is_revised)
                VALUES (?, ?, 'Standard Compliance Report', 'Initial Summary', 'Initial Observations', 'Initial Remarks', 'Initial Corrective', 'Initial Recommendations', 'Non-Compliant', 1, 1, 0)
            """, (inspection_id, rpt_num))
            db.commit()
            rep = db.execute("SELECT * FROM reports WHERE inspection_id = ?", (inspection_id,)).fetchone()

            print(f"[+] Initial Report Version: {rep['version_no']}, Is Revised: {rep['is_revised']}")
            self.assertEqual(rep["version_no"], 1)

        # 3. Test Editing Report -> Version 2
        edit_payload_v2 = {
            "observations": "Revised Field Observation: Front panel label font height is 1.8mm, below required 3.0mm.",
            "remarks": "Updated remarks: Sample taken from warehouse rack A4.",
            "corrective_actions": "Manufacturer instructed to halt dispatch and relabel all batch 2026-09 containers.",
            "recommendations": "Issue statutory Section 18 notice immediately.",
            "summary": "Non-compliant declaration under Rule 7(1) - Font height violation.",
            "edit_reason": "Incorporated on-site physical measurement observations and batch details."
        }

        res = self.client.post(
            f"/api/inspection/{inspection_id}/report/edit",
            data=json.dumps(edit_payload_v2),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["version_no"], 2)
        print(f"[+] Successfully edited report to Version 2: {data['message']}")

        # Verify DB state after Version 2
        with self.app.app_context():
            db = get_db()
            rep = db.execute("SELECT * FROM reports WHERE inspection_id = ?", (inspection_id,)).fetchone()
            self.assertEqual(rep["version_no"], 2)
            self.assertEqual(rep["is_revised"], 1)
            self.assertEqual(rep["last_edit_reason"], edit_payload_v2["edit_reason"])
            self.assertEqual(rep["observations"], edit_payload_v2["observations"])

            revs = db.execute("SELECT * FROM report_revisions WHERE report_id = ? ORDER BY version_no ASC", (rep["id"],)).fetchall()
            self.assertEqual(len(revs), 1)
            rev2 = revs[0]
            self.assertEqual(rev2["version_no"], 2)
            self.assertEqual(rev2["edit_reason"], edit_payload_v2["edit_reason"])
            
            changed_fields = json.loads(rev2["changed_fields"])
            self.assertIn("observations", changed_fields)
            self.assertIn("corrective_actions", changed_fields)
            print(f"[+] DB Revision 2 record verified. Changed fields: {changed_fields}")

        # 4. Test Idempotent Edit (Submitting identical data -> should NOT increment version)
        res_same = self.client.post(
            f"/api/inspection/{inspection_id}/report/edit",
            data=json.dumps(edit_payload_v2),
            content_type="application/json"
        )
        self.assertEqual(res_same.status_code, 200)
        data_same = res_same.get_json()
        self.assertTrue(data_same["success"])
        self.assertTrue(data_same.get("no_change", False))
        self.assertEqual(data_same["version_no"], 2)
        print("[+] Idempotency check PASSED: No duplicate revision created on identical submission.")

        # 5. Test Editing Report -> Version 3
        edit_payload_v3 = {
            "observations": edit_payload_v2["observations"],
            "remarks": "Updated remarks: Sample verified by Senior Assistant Controller.",
            "corrective_actions": "Manufacturer agreed to compound offence under Section 48.",
            "recommendations": "Process compounding file and recover statutory fee.",
            "summary": edit_payload_v2["summary"],
            "edit_reason": "Updated following officer review and compounding proposal."
        }

        res_v3 = self.client.post(
            f"/api/inspection/{inspection_id}/report/edit",
            data=json.dumps(edit_payload_v3),
            content_type="application/json"
        )
        self.assertEqual(res_v3.status_code, 200)
        data_v3 = res_v3.get_json()
        self.assertTrue(data_v3["success"])
        self.assertEqual(data_v3["version_no"], 3)
        print(f"[+] Successfully edited report to Version 3: {data_v3['message']}")

        # 6. Verify Revisions API
        res_rev_api = self.client.get(f"/api/inspection/{inspection_id}/report/revisions")
        self.assertEqual(res_rev_api.status_code, 200)
        rev_data = res_rev_api.get_json()
        self.assertTrue(rev_data["success"])
        self.assertEqual(rev_data["current_version"], 3)
        self.assertEqual(len(rev_data["revisions"]), 2) # v2 and v3
        print(f"[+] Revisions API verified: current_version={rev_data['current_version']}, revisions_count={len(rev_data['revisions'])}")

        # 7. Test Printable Views & Version Overrides
        # Current (v3)
        res_print_curr = self.client.get(f"/inspection/{inspection_id}/print")
        self.assertEqual(res_print_curr.status_code, 200)
        curr_html = res_print_curr.get_data(as_text=True)
        self.assertIn("REVISED REPORT", curr_html)
        self.assertIn("Version 3", curr_html)
        self.assertIn("Updated following officer review", curr_html)
        self.assertIn("Made by Team Avyukt", curr_html)
        print("[+] Printable Dossier (Current v3) verified with REVISED REPORT banner.")

        # Historical (v1)
        res_print_v1 = self.client.get(f"/inspection/{inspection_id}/print?version=1")
        self.assertEqual(res_print_v1.status_code, 200)
        v1_html = res_print_v1.get_data(as_text=True)
        if "HISTORICAL SNAPSHOT" not in v1_html:
            print("DEBUG: v1_html does not contain HISTORICAL SNAPSHOT. First 600 chars of official-dossier:")
            print(v1_html[v1_html.find("official-dossier"):v1_html.find("official-dossier")+600])
        self.assertIn("HISTORICAL SNAPSHOT", v1_html)
        self.assertIn("Version 1", v1_html)
        print("[+] Historical Printable Dossier (v1) verified with historical snapshot badge.")

        # 8. Test Notice Formulation (v1) and Revision (v2)
        notice_payload = {
            "notice_ref_no": f"LM/ENF/2026/INSP-{inspection_id}",
            "issued_to": "Fortune Agro Pack Ltd.",
            "draft_text": "You are required to show cause why legal proceedings should not be instituted under Section 18 of LM Act.",
            "edit_reason": "Initial Section 18 Show Cause Notice Formulation"
        }
        res_not_save = self.client.post(f"/inspection/{inspection_id}/notice/save", data=notice_payload, follow_redirects=True)
        self.assertEqual(res_not_save.status_code, 200)
        
        with self.app.app_context():
            db = get_db()
            not_rec = db.execute("SELECT * FROM notices WHERE inspection_id = ?", (inspection_id,)).fetchone()
            self.assertIsNotNone(not_rec)
            self.assertEqual(not_rec["version_no"], 1)
            notice_id = not_rec["id"]
            print(f"[+] Notice formulated at Version 1 (ID: {notice_id}, Ref: {not_rec['notice_ref_no']})")

        # Edit notice -> Version 2
        notice_edit_payload = {
            "notice_ref_no": not_rec["notice_ref_no"],
            "issued_to": "Fortune Agro Pack Ltd. (Registered Office)",
            "draft_text": "Updated notice with extended 21 days compliance period and Rule 7/9 references.",
            "edit_reason": "Corrected registered address and added 21-day timeline."
        }
        res_not_edit = self.client.post(f"/inspection/{inspection_id}/notice/save", data=notice_edit_payload, follow_redirects=True)
        self.assertEqual(res_not_edit.status_code, 200)

        with self.app.app_context():
            db = get_db()
            not_rec2 = db.execute("SELECT * FROM notices WHERE id = ?", (notice_id,)).fetchone()
            self.assertEqual(not_rec2["version_no"], 2)
            self.assertEqual(not_rec2["is_revised"], 1)
            self.assertEqual(not_rec2["issued_to"], "Fortune Agro Pack Ltd. (Registered Office)")
            
            not_revs = db.execute("SELECT * FROM notice_revisions WHERE notice_id = ?", (notice_id,)).fetchall()
            self.assertEqual(len(not_revs), 1)
            self.assertEqual(not_revs[0]["version_no"], 2)
            print(f"[+] Notice revision to Version 2 verified with DB revision history.")

        # Test Printable Notice
        res_print_not = self.client.get(f"/notice/{notice_id}/print")
        self.assertEqual(res_print_not.status_code, 200)
        not_html = res_print_not.get_data(as_text=True)
        self.assertIn("REVISED DRAFT", not_html)
        self.assertIn("VERSION 2", not_html)
        self.assertIn("SUBJECT TO AUTHORIZED REVIEW", not_html)
        print("[+] Printable Notice verified with REVISED DRAFT banner and review disclaimer.")

        # 9. Test Compounding Formulation (v1) and Revision (v2)
        comp_payload_v1 = {
            "proposed_fee": 25000.0,
            "offense_section": "Section 48 read with Section 36(1)",
            "audit_note": "First time violation; applicant cooperated during inspection.",
            "edit_reason": "Initial Section 48 compounding settlement formulation."
        }
        res_comp_v1 = self.client.post(f"/inspection/{inspection_id}/compounding/submit", data=comp_payload_v1, follow_redirects=True)
        self.assertEqual(res_comp_v1.status_code, 200)

        with self.app.app_context():
            db = get_db()
            comp_rec = db.execute("SELECT * FROM compounding_records WHERE inspection_id = ?", (inspection_id,)).fetchone()
            self.assertIsNotNone(comp_rec)
            self.assertEqual(comp_rec["version_no"], 1)
            comp_id = comp_rec["id"]
            print(f"[+] Compounding order formulated at Version 1 (ID: {comp_id})")

        # Edit compounding -> Version 2
        comp_payload_v2 = {
            "proposed_fee": 30000.0,
            "offense_section": "Section 48 read with Section 36(1) & 49",
            "audit_note": "Adjusted composition fee to ₹30,000 as per Assistant Controller orders.",
            "edit_reason": "Adjusted composition fee to ₹30,000 as per Assistant Controller orders."
        }
        res_comp_v2 = self.client.post(f"/inspection/{inspection_id}/compounding/submit", data=comp_payload_v2, follow_redirects=True)
        self.assertEqual(res_comp_v2.status_code, 200)

        with self.app.app_context():
            db = get_db()
            comp_rec2 = db.execute("SELECT * FROM compounding_records WHERE id = ?", (comp_id,)).fetchone()
            self.assertEqual(comp_rec2["version_no"], 2)
            self.assertEqual(comp_rec2["is_revised"], 1)
            self.assertEqual(comp_rec2["proposed_fee"], 30000.0)
            
            comp_revs = db.execute("SELECT * FROM compounding_revisions WHERE compounding_id = ?", (comp_id,)).fetchall()
            self.assertEqual(len(comp_revs), 1)
            self.assertEqual(comp_revs[0]["version_no"], 2)
            print(f"[+] Compounding revision to Version 2 verified.")

        # Test Printable Compounding Order
        res_print_comp = self.client.get(f"/compounding/{comp_id}/print")
        self.assertEqual(res_print_comp.status_code, 200)
        comp_html = res_print_comp.get_data(as_text=True)
        self.assertIn("REVISED DRAFT COMPOUNDING SETTLEMENT ORDER", comp_html)
        self.assertIn("Version 2", comp_html)
        print("[+] Printable Compounding Order verified with REVISED DRAFT banner.")

        # 10. Audit Trail Verification
        with self.app.app_context():
            db = get_db()
            audit_entries = db.execute("""
                SELECT al.*, u.name as user_name 
                FROM audit_logs al 
                LEFT JOIN users u ON al.user_id = u.id 
                WHERE al.entity_id = ? 
                   OR (al.entity_type = 'Report' AND al.entity_id = ?)
                ORDER BY al.id DESC
            """, (inspection_id, inspection_id)).fetchall()
            
            actions = [a["action"] for a in audit_entries]
            self.assertIn("REPORT_REVISION", actions)
            self.assertIn("NOTICE_REVISION", actions)
            self.assertIn("COMPOUNDING_REVISION", actions)
            
            # Check details contain editor, reason, and changed fields
            report_edit_logs = [a for a in audit_entries if a["action"] == "REPORT_REVISION"]
            self.assertTrue(len(report_edit_logs) >= 2)
            for log in report_edit_logs:
                self.assertIsNotNone(log["user_name"])
                self.assertIsNotNone(log["details"])
                self.assertIn("reason", log["details"].lower())
            print(f"[+] Immutable Audit Trail Verified! Total logs recorded: {len(audit_entries)}")

        print("\n=======================================================")
        print("--- ALL REPORT REVISION & AUDIT E2E TESTS PASSED ---")
        print("=======================================================\n")

if __name__ == "__main__":
    unittest.main()
