"""
Role-Based Access Control (RBAC) & Authentication Test Suite (Inspector & Admin Roles Only)
Platform: eSavadh - Intelligent Legal Metrology Compliance Platform
Made by Team Avyukt
"""

import os
import sys
import unittest

# Ensure root directory is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
import database

class TestRBACInspectorAdminOnly(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

    def setUp(self):
        self.client = app.test_client()

    def login(self, email, password):
        return self.client.post("/login", data={
            "email": email,
            "password": password
        }, follow_redirects=False)

    def logout(self):
        return self.client.get("/logout", follow_redirects=True)

    # ------------------------------------------------------------------------
    # 1. Unauthenticated Security Tests
    # ------------------------------------------------------------------------
    def test_unauthenticated_protected_routes_redirect_to_login(self):
        protected_routes = [
            "/dashboard",
            "/inspector/dashboard",
            "/admin/dashboard",
            "/inspection/new",
            "/inspections",
            "/inspection/1",
            "/ecommerce",
            "/teams",
            "/audit",
            "/reports",
            "/rules",
            "/inspection/1/notice",
            "/inspection/1/compounding"
        ]
        for route in protected_routes:
            resp = self.client.get(route, follow_redirects=False)
            self.assertEqual(resp.status_code, 302, f"Unauthenticated route {route} should return 302 redirect")
            self.assertIn("/login", resp.headers["Location"], f"Route {route} should redirect to /login")

    # ------------------------------------------------------------------------
    # 2. Inspector Role Tests
    # ------------------------------------------------------------------------
    def test_inspector_workflow_and_rbac(self):
        # 1. Login
        resp = self.login("inspector@esavadh.gov.in", "inspector123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/inspector/dashboard", resp.headers["Location"])

        # 2. Permitted Enforcement Routes
        permitted_routes = [
            "/inspector/dashboard",
            "/inspection/new",
            "/inspections",
            "/inspection/1",
            "/ecommerce",
            "/reports",
            "/rules",
            "/inspection/1/notice",
            "/inspection/1/compounding"
        ]
        for route in permitted_routes:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200, f"Inspector should have 200 access to {route}")

        # 3. Denied Admin-Only Routes
        admin_only_routes = ["/admin/dashboard", "/teams", "/audit"]
        for route in admin_only_routes:
            r = self.client.get(route, follow_redirects=False)
            self.assertEqual(r.status_code, 302, f"Inspector accessing {route} should be redirected (302)")
            followed = self.client.get(route, follow_redirects=True)
            self.assertIn(b"Access Denied", followed.data)

        self.logout()

    # ------------------------------------------------------------------------
    # 3. Admin Role Tests
    # ------------------------------------------------------------------------
    def test_admin_workflow_and_rbac(self):
        # 1. Login
        resp = self.login("admin@esavadh.gov.in", "admin123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/dashboard", resp.headers["Location"])

        # 2. Permitted Admin & Supervisory Routes
        admin_permitted_routes = [
            "/admin/dashboard",
            "/inspector/dashboard",
            "/inspection/new",
            "/inspections",
            "/inspection/1",
            "/ecommerce",
            "/teams",
            "/audit",
            "/reports",
            "/rules",
            "/inspection/1/notice",
            "/inspection/1/compounding"
        ]
        for route in admin_permitted_routes:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200, f"Admin should have 200 access to {route}")

        self.logout()

    # ------------------------------------------------------------------------
    # 4. Verification that Legacy Retailer/Manufacturer Roles are Denied Login
    # ------------------------------------------------------------------------
    def test_removed_roles_cannot_authenticate(self):
        removed_accounts = [
            ("retailer@esavadh.gov.in", "retailer123"),
            ("manufacturer@esavadh.gov.in", "manufacturer123"),
        ]
        for email, password in removed_accounts:
            resp = self.login(email, password)
            self.assertEqual(resp.status_code, 200) # Renders login with error flash
            self.assertIn(b"Invalid credentials", resp.data)


if __name__ == "__main__":
    unittest.main()
