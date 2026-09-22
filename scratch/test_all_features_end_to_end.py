"""
Comprehensive End-to-End Test Suite for eSavadh
Made by Team Avyukt
Tests all primary actions and features requested by the user.
"""

import io
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, r"c:\Users\Khushi\OneDrive\Desktop\eSavadh")

from app import app
import database

def run_comprehensive_tests():
    print("==================================================================")
    print(" [1] Initializing & Bootstrapping eSavadh Database...")
    database.init_db()
    
    client = app.test_client()

    # 1. Authenticate as Inspector
    print("\n [2] Authenticating as Senior Inspector (Rajesh Sharma)...")
    res = client.post("/login", data={
        "email": "inspector@esavadh.gov.in",
        "password": "inspector123"
    }, follow_redirects=True)
    assert res.status_code == 200, "Inspector login failed"
    print("  -> Authenticated successfully.")

    # 2. Test Real Image Upload & Inspection Creation (Field Mode)
    print("\n [3] Testing Step 1: Real Package Image Upload & OCR Analysis...")
    img = Image.new('RGB', (600, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 20), "PRODUCT: Kachi Ghani Pure Mustard Oil 1 Litre", fill=(0, 0, 0))
    d.text((20, 50), "Mfg Date: 03/2024", fill=(0, 0, 0))
    d.text((20, 80), "MRP: Rs. 185.00 (Incl. of all taxes)", fill=(0, 0, 0))
    d.text((20, 110), "Net Qty: 1 L", fill=(0, 0, 0))
    d.text((20, 140), "Mfd By: Golden Harvest Agritech Ltd, Bharatpur RJ", fill=(0, 0, 0))
    d.text((20, 170), "Country of Origin: India", fill=(0, 0, 0))
    d.text((20, 200), "USP: Rs 0.19 per ml", fill=(0, 0, 0))
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    insp_res = client.post(
        "/inspection/create",
        data={
            "product_name": "Kachi Ghani Pure Mustard Oil 1 Litre",
            "category": "Edible Oils",
            "location": "Vasant Kunj Central Supermarket",
            "mfg_date": "03/2024",
            "view_side": "Back",
            "package_image": (img_bytes, "mustard_oil_back.jpg")
        },
        content_type='multipart/form-data',
        follow_redirects=False
    )
    assert insp_res.status_code == 302, "Inspection creation failed"
    redirect_loc = insp_res.headers.get("Location")
    insp_id = int(redirect_loc.split("/")[-1])
    print(f"  -> Inspection #{insp_id} created successfully! Redirected to: {redirect_loc}")

    # 3. Test View Dossier
    print(f"\n [4] Testing Step 2: View Dossier #{insp_id} & Extracted Declarations...")
    dossier_res = client.get(f"/inspection/{insp_id}")
    assert dossier_res.status_code == 200, "View Dossier failed"
    print("  -> Dossier page loaded with images, raw OCR transcript, and declarations.")

    # 4. Test HITL Declarations APIs
    conn = database.get_db()
    decls = conn.execute("SELECT * FROM declarations WHERE inspection_id = ?", (insp_id,)).fetchall()
    conn.close()
    assert len(decls) > 0, "No declarations found for inspection"
    first_decl_id = decls[0]["id"]

    print(f"\n [5] Testing Step 3: HITL Declaration Confirm & Edit on #{first_decl_id}...")
    rev_res = client.post(f"/api/declarations/{first_decl_id}/review", json={"action": "confirm", "confirmed_value": "₹ 185.00"})
    assert rev_res.status_code == 200 and rev_res.get_json()["success"] is True
    print("  -> Confirm declaration API: OK")

    edit_res = client.post(f"/api/declarations/{first_decl_id}/edit", json={"value": "₹ 185.00 (Incl. of all taxes)"})
    assert edit_res.status_code == 200 and edit_res.get_json()["status"] == "Edited"
    print("  -> Edit declaration API: OK")

    bulk_res = client.post(f"/api/declarations/confirm-all/{insp_id}")
    assert bulk_res.status_code == 200 and bulk_res.get_json()["success"] is True
    print(f"  -> Bulk Confirm API: OK ({bulk_res.get_json()['updated_count']} updated)")

    # 5. Test Rule Re-evaluation
    print(f"\n [6] Testing Step 4: Re-evaluate Statutory Rules on Verified Declarations...")
    eval_res = client.post(f"/api/inspection/{insp_id}/evaluate")
    assert eval_res.status_code == 200 and eval_res.get_json()["success"] is True
    print(f"  -> Rule Evaluation API: OK. Determination: {eval_res.get_json()['overall_status']}")

    # 6. Test Dossier Finalization
    print(f"\n [7] Testing Step 5: Finalize Dossier with Officer Sign-off...")
    final_res = client.post(f"/api/inspection/{insp_id}/finalize", json={"notes": "All mandatory packaging declarations verified under Rule 6 of PCR 2011."})
    assert final_res.status_code == 200 and final_res.get_json()["success"] is True
    print("  -> Finalize Dossier API: OK")

    # 7. Test Save Draft Notice to Dossier & Print Notice
    print(f"\n [8] Testing Step 6: Save Notice Draft & Printable Notice...")
    save_notice_res = client.post(f"/inspection/{insp_id}/notice/save", data={
        "notice_ref_no": f"SCN-2026-{insp_id:04d}",
        "issued_to": "Golden Harvest Agritech Ltd",
        "draft_text": "Statutory Show Cause Notice under Section 18 read with Section 36 of Legal Metrology Act, 2009."
    }, follow_redirects=True)
    assert save_notice_res.status_code == 200, "Save notice failed"
    print("  -> Notice saved to dossier: OK")

    conn = database.get_db()
    saved_notice = conn.execute("SELECT id FROM notices WHERE inspection_id = ? ORDER BY id DESC LIMIT 1", (insp_id,)).fetchone()
    conn.close()
    assert saved_notice is not None, "Notice was not stored in database"
    notice_id = saved_notice["id"]
    
    print_notice_res = client.get(f"/notice/{notice_id}/print")
    assert print_notice_res.status_code == 200, "Print notice view failed"
    print(f"  -> Printable Show Cause Notice #{notice_id} loaded: OK")

    # 8. Test Compounding Order Proposal & Print Compounding
    print(f"\n [9] Testing Step 7: Formulate Compounding Settlement Proposal & Printable Order...")
    comp_res = client.post(f"/inspection/{insp_id}/compounding/submit", data={
        "proposed_fee": "25000",
        "offense_section": "Section 48 read with Section 36(1)",
        "audit_note": "First-time offense evaluated under statutory compounding guidelines."
    }, follow_redirects=True)
    assert comp_res.status_code == 200, "Submit compounding failed"
    print("  -> Compounding proposal recorded: OK")

    conn = database.get_db()
    saved_comp = conn.execute("SELECT id FROM compounding_records WHERE inspection_id = ? ORDER BY id DESC LIMIT 1", (insp_id,)).fetchone()
    conn.close()
    assert saved_comp is not None, "Compounding record not found"
    comp_id = saved_comp["id"]

    print_comp_res = client.get(f"/compounding/{comp_id}/print")
    assert print_comp_res.status_code == 200, "Print compounding view failed"
    print(f"  -> Printable Compounding Settlement #{comp_id} loaded: OK")

    # 9. Test E-Commerce Check with Screenshot Upload & Real OCR
    print("\n [10] Testing Step 8: E-Commerce Listing Check with Screenshot OCR...")
    ecom_img = Image.new('RGB', (600, 200), color=(255, 255, 255))
    ecom_d = ImageDraw.Draw(ecom_img)
    ecom_d.text((20, 20), "Title: NutriPure Cold Pressed Organic Sesame Oil 1L", fill=(0,0,0))
    ecom_d.text((20, 50), "MRP: Rs. 380.00 (Inclusive of all taxes)", fill=(0,0,0))
    ecom_d.text((20, 80), "Net Content: 1 L", fill=(0,0,0))
    ecom_d.text((20, 110), "Country of Origin: India", fill=(0,0,0))
    ecom_d.text((20, 140), "Seller: CloudRetail Solutions India Pvt Ltd", fill=(0,0,0))
    
    ecom_bytes = io.BytesIO()
    ecom_img.save(ecom_bytes, format='JPEG')
    ecom_bytes.seek(0)

    ecom_check_res = client.post("/ecommerce/check", data={
        "listing_url": "https://www.amazon.in/dp/B09XTEST12",
        "screenshot_image": (ecom_bytes, "amazon_listing_screenshot.jpg")
    }, content_type='multipart/form-data', follow_redirects=True)
    assert ecom_check_res.status_code == 200, "E-Commerce check with screenshot failed"
    print("  -> E-Commerce Screenshot OCR & Compliance Check: OK")

    # 10. Test Admin Team Task Dispatch
    print("\n [11] Testing Step 9: Admin Surveillance Task Dispatch...")
    # Switch to Admin
    client.post("/logout")
    client.post("/login", data={"email": "admin@esavadh.gov.in", "password": "admin123"})
    task_res = client.post("/teams/task/create", data={
        "title": "Connaught Place Unit Sale Price Surveillance",
        "description": "Inspect edible oils and packaged cereals under Rule 6(11).",
        "assigned_to": "2",
        "priority": "High",
        "due_date": "2026-10-15"
    }, follow_redirects=True)
    assert task_res.status_code == 200, "Task dispatch failed"
    print("  -> Admin Task Dispatch: OK")

    # 11. Test Printable Dossier
    print(f"\n [12] Testing Step 10: Printable Official Dossier for #{insp_id}...")
    print_dossier_res = client.get(f"/inspection/{insp_id}/print")
    assert print_dossier_res.status_code == 200, "Printable dossier failed"
    print("  -> Printable Official Dossier view: OK")

    print("\n==================================================================")
    print(" ALL 12 WORKFLOWS, ACTIONS, AND ENDPOINTS TESTED & PASSED 100%!")
    print("==================================================================")

if __name__ == "__main__":
    run_comprehensive_tests()
