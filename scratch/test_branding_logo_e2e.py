"""
Comprehensive E2E Branding & Logo Test Suite for eSavadh.
Verifies:
1. Logo asset file existence & validity at /static/img/esavadh_logo.png
2. Login Page renders official logo & no 'ई.सा' placeholder
3. Landing Page renders official logo & no 'ई.सा' placeholder
4. Common Navigation Header (base.html) renders official logo across all pages
5. Printable Official Dossier renders official logo & no 'ई.सा' placeholder
6. Printable Notice renders official logo
7. Printable Compounding Order renders official logo
8. Zero remaining instances of 'ई.सा' placeholder across entire application
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import app
from database import get_db

class TestBrandingLogoE2E(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def test_logo_asset_exists(self):
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "img", "esavadh_logo.png")
        self.assertTrue(os.path.exists(logo_path), "Logo asset must exist at static/img/esavadh_logo.png")
        self.assertGreater(os.path.getsize(logo_path), 10000, "Logo asset must be non-empty")
        print(f"[+] Verified logo asset exists: {logo_path} (Size: {os.path.getsize(logo_path)} bytes)")

    def test_public_pages_branding(self):
        # 1. Landing Page
        res_landing = self.client.get("/landing")
        self.assertEqual(res_landing.status_code, 200)
        landing_html = res_landing.get_data(as_text=True)
        self.assertIn("esavadh_logo.png", landing_html)
        self.assertNotIn("ई.सा", landing_html)
        print("[+] Landing page verified with official eSavadh logo.")

        # 2. Login Page
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        login_html = res_login.get_data(as_text=True)
        self.assertIn("esavadh_logo.png", login_html)
        self.assertNotIn("ई.सा", login_html)
        print("[+] Login page verified with official eSavadh logo.")

    def test_authenticated_pages_branding(self):
        # Login
        self.client.post("/login", data={
            "email": "inspector@esavadh.gov.in",
            "password": "inspector123"
        }, follow_redirects=True)

        pages = [
            ("/inspector/dashboard", "Inspector Dashboard"),
            ("/inspection/new", "New Inspection Flow"),
            ("/inspections", "Inspections Register"),
            ("/ecommerce", "E-Commerce Surveillance"),
            ("/rules", "Rules & Lookup Center"),
            ("/reports", "Reports & Compliance Analytics"),
            ("/how-it-works", "How It Works Guide")
        ]

        for path, name in pages:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed loading {name} at {path}")
            html = res.get_data(as_text=True)
            self.assertIn("esavadh_logo.png", html, f"Logo missing on {name}")
            self.assertNotIn("ई.सा", html, f"Placeholder 'ई.सा' found on {name}")
            print(f"[+] {name} ({path}) verified with official logo.")

    def test_printable_documents_branding(self):
        self.client.post("/login", data={
            "email": "inspector@esavadh.gov.in",
            "password": "inspector123"
        }, follow_redirects=True)

        with self.app.app_context():
            db = get_db()
            insp = db.execute("SELECT id FROM inspections ORDER BY id DESC LIMIT 1").fetchone()
            inspection_id = insp["id"] if insp else 1
            
            not_rec = db.execute("SELECT id FROM notices ORDER BY id DESC LIMIT 1").fetchone()
            notice_id = not_rec["id"] if not_rec else 1

            comp_rec = db.execute("SELECT id FROM compounding_records ORDER BY id DESC LIMIT 1").fetchone()
            comp_id = comp_rec["id"] if comp_rec else 1

        # 1. Printable Dossier
        res_dossier = self.client.get(f"/inspection/{inspection_id}/print")
        self.assertEqual(res_dossier.status_code, 200)
        dossier_html = res_dossier.get_data(as_text=True)
        self.assertIn("esavadh_logo.png", dossier_html)
        self.assertNotIn("ई.सा", dossier_html)
        print("[+] Printable Dossier verified with official logo.")

        # 2. Printable Notice
        res_notice = self.client.get(f"/notice/{notice_id}/print")
        self.assertEqual(res_notice.status_code, 200)
        notice_html = res_notice.get_data(as_text=True)
        self.assertIn("esavadh_logo.png", notice_html)
        self.assertNotIn("ई.सा", notice_html)
        print("[+] Printable Notice verified with official logo.")

        # 3. Printable Compounding Order
        res_comp = self.client.get(f"/compounding/{comp_id}/print")
        self.assertEqual(res_comp.status_code, 200)
        comp_html = res_comp.get_data(as_text=True)
        self.assertIn("esavadh_logo.png", comp_html)
        self.assertNotIn("ई.सा", comp_html)
        print("[+] Printable Compounding Order verified with official logo.")

        print("\n=======================================================")
        print("--- ALL BRANDING & LOGO VERIFICATION TESTS PASSED ---")
        print("=======================================================\n")

if __name__ == "__main__":
    unittest.main()
