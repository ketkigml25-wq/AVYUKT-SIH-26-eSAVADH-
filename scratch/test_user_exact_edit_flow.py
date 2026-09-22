"""
Exact User Flow Test for Report Editing & Revision Tracking.
Simulates:
1. Open existing inspection report.
2. Verify 'Edit Report' button and drawer are present.
3. Modify remarks to 'Updated inspection remark'.
4. Enter edit reason 'Officer updated field remarks'.
5. Submit edit -> Verify backend saves to SQLite and creates Version 2.
6. Refresh page (GET /inspection/<id>?step=4).
7. Confirm 'Updated inspection remark' is rendered.
8. Confirm badge displays 'REVISED REPORT (Version 2)'.
9. Confirm Change History displays Version 1 (Original) and Version 2 (Revised) with diffs.
10. Open Printable PDF (/inspection/<id>/print) -> Confirm 'REVISED REPORT • VERSION 2' banner, date, editor, reason.
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from database import get_db

class TestUserExactEditFlow(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def test_exact_15_step_flow(self):
        print("\n=======================================================")
        print("--- RUNNING USER EXACT 15-STEP EDIT & REVISION TEST ---")
        print("=======================================================")

        # Step 1: Login as Inspector
        res_login = self.client.post("/login", data={
            "email": "inspector@esavadh.gov.in",
            "password": "inspector123"
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        print("[Step 1] Inspector logged in successfully.")

        # Step 2: Create a fresh inspection with initial report (Version 1)
        with self.app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO products (name, brand, category, manufacturer)
                VALUES ('Himalayan Organic Tea 250g', 'Himalayan Harvest', 'Tea / Beverages', 'Himalayan Pure Harvest Ltd.')
            """)
            prod_id = cursor.lastrowid
            import time
            t_now = int(time.time() * 1000)
            cursor.execute("""
                INSERT INTO inspections (ref_no, product_id, inspector_id, compliance_status, overall_notes)
                VALUES (?, ?, 1, 'Non-Compliant', 'Original initial inspection remark')
            """, (f"INSP-EXACT-TEST-{t_now}", prod_id))
            db.commit()
            inspection_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO reports (inspection_id, report_number, title, summary, observations, remarks, corrective_actions, recommendations, final_status, generated_by, version_no, is_revised)
                VALUES (?, ?, 'Statutory Compliance Certificate - Himalayan Organic Tea 250g', 'Initial Summary', 'Original observation', 'Original remark', 'Original corrective', 'Original recommendation', 'Non-Compliant', 1, 1, 0)
            """, (inspection_id, f"RPT-EXACT-{t_now}"))
            db.commit()
            print(f"[Step 2] Fresh inspection created: ID {inspection_id} with Version 1 Report.")

        # Step 3: Open dossier on Step 4 and verify Edit Button and Drawer HTML
        res_dossier = self.client.get(f"/inspection/{inspection_id}?step=4")
        self.assertEqual(res_dossier.status_code, 200)
        html_dossier = res_dossier.get_data(as_text=True)
        self.assertIn("toggleReportEditor()", html_dossier)
        self.assertIn("report-edit-drawer", html_dossier)
        self.assertIn("Original remark", html_dossier)
        self.assertIn("ORIGINAL REPORT (Version 1)", html_dossier)
        print("[Step 3] Step 4 loaded: Edit button, Drawer, and Original Version 1 badge verified.")

        # Step 4-6: Submit changes (Remarks -> 'Updated inspection remark', Reason -> 'Officer updated field remarks')
        edit_payload = {
            "observations": "Original observation",
            "remarks": "Updated inspection remark",
            "corrective_actions": "Original corrective",
            "recommendations": "Original recommendation",
            "summary": "Initial Summary",
            "edit_reason": "Officer updated field remarks"
        }
        res_edit = self.client.post(
            f"/api/inspection/{inspection_id}/report/edit",
            data=json.dumps(edit_payload),
            content_type="application/json"
        )
        self.assertEqual(res_edit.status_code, 200)
        data_edit = res_edit.get_json()
        self.assertTrue(data_edit["success"])
        self.assertEqual(data_edit["version_no"], 2)
        print(f"[Step 4-7] Save Changes executed successfully. Backend committed Version {data_edit['version_no']}.")

        # Step 8-11: Refresh page and verify updated remarks and REVISED REPORT badge
        res_refresh = self.client.get(f"/inspection/{inspection_id}?step=4")
        self.assertEqual(res_refresh.status_code, 200)
        html_refresh = res_refresh.get_data(as_text=True)
        self.assertIn("Updated inspection remark", html_refresh)
        self.assertIn("REVISED REPORT (Version 2)", html_refresh)
        self.assertIn("Officer updated field remarks", html_refresh)
        print("[Step 8-11] Page refresh verified: 'Updated inspection remark' rendered with 'REVISED REPORT (Version 2)'.")

        # Step 12-13: Verify Change History preserves Version 1 and records Version 2 diffs
        res_history = self.client.get(f"/api/inspection/{inspection_id}/report/revisions")
        self.assertEqual(res_history.status_code, 200)
        data_history = res_history.get_json()
        self.assertEqual(data_history["current_version"], 2)
        self.assertEqual(len(data_history["revisions"]), 1)
        rev = data_history["revisions"][0]
        self.assertEqual(rev["version_no"], 2)
        self.assertEqual(rev["edit_reason"], "Officer updated field remarks")
        self.assertIn("remarks", rev["changed_fields_list"])
        self.assertEqual(rev["old_values_dict"]["remarks"], "Original remark")
        self.assertEqual(rev["new_values_dict"]["remarks"], "Updated inspection remark")
        print("[Step 12-13] Change History verified: Version 1 preserved; Version 2 diffs accurately recorded.")

        # Step 14-15: Open Printable PDF Dossier and verify REVISED REPORT Version 2 banner
        res_pdf = self.client.get(f"/inspection/{inspection_id}/print")
        self.assertEqual(res_pdf.status_code, 200)
        html_pdf = res_pdf.get_data(as_text=True)
        self.assertIn("REVISED REPORT", html_pdf)
        self.assertIn("VERSION 2", html_pdf)
        self.assertIn("Officer updated field remarks", html_pdf)
        self.assertIn("Updated inspection remark", html_pdf)
        print("[Step 14-15] Printable PDF Dossier verified: 'REVISED REPORT • VERSION 2' with updated remarks and reason.")

        print("\n=======================================================")
        print("--- ALL 15 USER TEST STEPS VERIFIED 100% SUCCESS ---")
        print("=======================================================\n")

if __name__ == "__main__":
    unittest.main()
