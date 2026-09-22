import os
import sys
import unittest
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
import database

class TestRealOCRWorkflowE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        
        # Authenticate as Inspector
        with cls.client.session_transaction() as sess:
            user = database.get_user_by_email("inspector@esavadh.gov.in")
            sess["user"] = dict(user)

    def test_complete_inspection_ocr_and_hitl_workflow(self):
        print("\n=======================================================")
        print("--- RUNNING REAL OCR & 5-STEP INSPECTION E2E TEST ---")
        print("=======================================================")

        # 1. Use real test image: Himalayan Tea
        img_path = os.path.join(os.path.dirname(__file__), "test_images", "product_1_tea.png")
        self.assertTrue(os.path.exists(img_path), "Test image product_1_tea.png must exist")

        with open(img_path, "rb") as f:
            img_bytes = f.read()

        # 2. Submit new inspection with real image upload
        resp = self.client.post(
            "/inspection/create",
            data={
                "ref_no": "INSP-TEST-REAL-OCR-001",
                "location": "Central Delhi Superstore",
                "product_name": "", # Auto-detect from OCR
                "category": "Beverages / Food",
                "mfg_date": "",     # Auto-detect from OCR
                "view_side": "Back",
                "package_image": (BytesIO(img_bytes), "himalayan_green_tea.png")
            },
            follow_redirects=True
        )
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        print("[Step 1] Inspection created with real image upload & multi-pass OCR.")
        
        # Verify inspection exists in database
        conn = database.get_db()
        try:
            insp = conn.execute("SELECT * FROM inspections WHERE ref_no = 'INSP-TEST-REAL-OCR-001'").fetchone()
            self.assertIsNotNone(insp)
            insp_id = insp["id"]
            
            # Verify OCR Results in DB
            ocr_row = conn.execute("SELECT * FROM ocr_results WHERE inspection_id = ?", (insp_id,)).fetchone()
            self.assertIsNotNone(ocr_row)
            self.assertTrue(len(ocr_row["raw_text"]) > 50, "Raw OCR text must be stored in DB")
            print(f"[Step 2] Raw OCR preserved in database ({len(ocr_row['raw_text'])} chars):")
            print(ocr_row["raw_text"][:200])

            # Verify Declarations in DB
            decls = conn.execute("SELECT * FROM declarations WHERE inspection_id = ?", (insp_id,)).fetchall()
            decls_dict = {d["field_name"]: d for d in decls}
            
            self.assertIn("mrp", decls_dict)
            self.assertIn("net_quantity", decls_dict)
            self.assertIn("manufacturer", decls_dict)
            self.assertIn("mfg_date", decls_dict)

            mrp_val = decls_dict["mrp"]["extracted_value"]
            net_val = decls_dict["net_quantity"]["extracted_value"]
            mfr_val = decls_dict["manufacturer"]["extracted_value"]
            mfg_val = decls_dict["mfg_date"]["extracted_value"]

            print(f"[Step 3] Real Extracted Declarations:")
            print(f"  - MRP: {mrp_val}")
            print(f"  - Net Quantity: {net_val}")
            print(f"  - Manufacturer: {mfr_val}")
            print(f"  - Mfg Date: {mfg_val}")

            self.assertIsNotNone(mrp_val)
            self.assertIn("240", mrp_val)
            self.assertEqual(net_val, "250 g")
            self.assertIn("Uttar Pradesh", mfr_val)
            self.assertIn("A/3", mfr_val)
            self.assertEqual(mfg_val, "05/2024")

            # 3. Test HITL Review: Confirm MRP declaration
            mrp_decl_id = decls_dict["mrp"]["id"]
            rev_resp = self.client.post(
                f"/api/declarations/{mrp_decl_id}/review",
                json={"action": "confirm", "confirmed_value": "₹ 240.00"}
            )
            self.assertEqual(rev_resp.status_code, 200)
            self.assertTrue(rev_resp.get_json()["success"])
            print("[Step 4] HITL Confirm Action verified on MRP declaration.")

            # 4. Test HITL Edit: Edit remarks or values
            mfr_decl_id = decls_dict["manufacturer"]["id"]
            edit_resp = self.client.post(
                f"/api/declarations/{mfr_decl_id}/edit",
                json={"value": "Himalayan Pure Harvest Ltd., Plot No. A/3, Industrial Area, Sector 62, Noida, Uttar Pradesh - 201301"}
            )
            self.assertEqual(edit_resp.status_code, 200)
            self.assertTrue(edit_resp.get_json()["success"])
            print("[Step 5] HITL Edit Action verified.")

            # 5. Test Step 3 Re-Evaluation
            eval_resp = self.client.post(f"/api/inspection/{insp_id}/evaluate")
            self.assertEqual(eval_resp.status_code, 200)
            eval_json = eval_resp.get_json()
            self.assertTrue(eval_json["success"])
            print(f"[Step 6] Step 3 Statutory Rule Evaluation result: {eval_json['overall_status']}")

            # 6. Test Step 4 Printable Dossier
            dossier_resp = self.client.get(f"/inspection/{insp_id}/print")
            self.assertEqual(dossier_resp.status_code, 200)
            self.assertIn("Himalayan Pure Harvest Ltd.", dossier_resp.get_data(as_text=True))
            print("[Step 7] Step 4 Printable Dossier rendered with verified OCR data.")

        finally:
            conn.close()

        print("\n=======================================================")
        print("--- ALL REAL OCR & WORKFLOW TESTS PASSED 100% ---")
        print("=======================================================")

if __name__ == "__main__":
    unittest.main()
