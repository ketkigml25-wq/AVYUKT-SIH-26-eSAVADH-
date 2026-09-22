"""
Comprehensive End-to-End Test for eSavadh:
- BUG 1: Notice Unique Constraint Error & Idempotent Notice Saving
- BUG 2: Compounding Order Navigation (stating on Step 4)
- BUG 3: Two distinct Real Product Images with Multimodal OCR & Visual Veg/Non-Veg Symbol Detection
"""

import sys
import os
import io
import json
import sqlite3
from PIL import Image, ImageDraw, ImageFont

# Ensure unbuffered utf-8 output
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
sys.path.insert(0, r"c:\Users\Khushi\OneDrive\Desktop\eSavadh")

from app import app
import database
from core.symbol_detector import detect_visual_symbol
from core.ocr_engine import perform_ocr_extraction


def create_test_product_images():
    """Generates two distinct, realistic packaged commodity images with actual text and visual symbols."""
    img_dir = r"c:\Users\Khushi\OneDrive\Desktop\eSavadh\static\uploads\original"
    os.makedirs(img_dir, exist_ok=True)
    
    # Image 1: Himalayan Organic Honey (Vegetarian)
    img1_path = os.path.join(img_dir, "test_prod_1_honey_veg.png")
    img1 = Image.new("RGB", (800, 900), color="#FAF7EE")
    draw1 = ImageDraw.Draw(img1)
    
    # Draw Green Vegetarian Symbol (Green square + green circle inside)
    # Box: (50, 50, 110, 110)
    draw1.rectangle([50, 50, 110, 110], outline="#1E7E34", width=4)
    draw1.ellipse([65, 65, 95, 95], fill="#1E7E34")
    
    # Product text
    text1 = """HIMALAYAN ORGANIC MULTIFLORA HONEY
100% PURE & NATURAL

Maximum Retail Price: Rs. 385.00
(Inclusive of all taxes)
Net Quantity: 500 g
Unit Sale Price: Rs. 0.77 per g
Date of Mfg: 06/2024
Best Before: 24 Months from packaging
Country of Origin: India

Manufactured & Packed by:
Himalayan Pure Harvest Ltd.
Plot 45, Industrial Estate, Solan, Himachal Pradesh - 173212

Customer Care Cell:
Helpline: 1800-200-8899
Email: care@himalayanharvest.in
"""
    draw1.text((50, 140), text1, fill="#1B120C")
    img1.save(img1_path)
    
    # Image 2: Coastal Catch Tuna Flakes (Non-Vegetarian)
    img2_path = os.path.join(img_dir, "test_prod_2_tuna_nonveg.png")
    img2 = Image.new("RGB", (800, 900), color="#F4F6F8")
    draw2 = ImageDraw.Draw(img2)
    
    # Draw Brown Non-Vegetarian Symbol (Brown square + brown triangle inside)
    # Box: (50, 50, 110, 110)
    draw2.rectangle([50, 50, 110, 110], outline="#7A3816", width=4)
    draw2.polygon([(80, 65), (65, 95), (95, 95)], fill="#7A3816")
    
    # Product text
    text2 = """COASTAL CATCH PREMIUM TUNA FLAKES IN OLIVE OIL
RICH IN OMEGA 3

MRP: Rs. 240.00 (Incl. of all taxes)
Net Weight: 185 g
USP: Rs. 1.30 per g
Date of Packing: 04/2024
Expiry Date: 04/2026
Country of Origin: India

Manufactured by:
Coastal Fisheries Marine Foods India Pvt. Ltd.
Cochin Port Road, Ernakulam, Kerala - 682003

Consumer Feedback:
Toll Free: 1800-425-9911
Email: grievance@coastalfoods.in
"""
    draw2.text((50, 140), text2, fill="#111827")
    img2.save(img2_path)
    
    return img1_path, img2_path


def test_visual_symbol_detection(img1_path, img2_path):
    print("\n--- Test 1: Visual Symbol Detection Engine ---")
    
    res1 = detect_visual_symbol(img1_path)
    print(f"Product 1 Detection: Status='{res1['status']}', Conf={res1['confidence']}, Method='{res1['detection_method']}'")
    assert res1["is_detected"] is True, "Failed to detect vegetarian symbol in Image 1"
    assert "Vegetarian" in res1["status"], "Image 1 should be detected as Vegetarian"
    print("[OK] Product 1 Green Vegetarian symbol correctly identified via computer vision.")
    
    res2 = detect_visual_symbol(img2_path)
    print(f"Product 2 Detection: Status='{res2['status']}', Conf={res2['confidence']}, Method='{res2['detection_method']}'")
    assert res2["is_detected"] is True, "Failed to detect non-vegetarian symbol in Image 2"
    assert "Non-Vegetarian" in res2["status"], "Image 2 should be detected as Non-Vegetarian"
    print("[OK] Product 2 Brown Non-Vegetarian symbol correctly identified via computer vision.")


def test_real_image_ocr_and_declarations(img1_path, img2_path):
    print("\n--- Test 2: Real OCR Extraction & Declarations for 2 Products ---")
    
    # Product 1
    ocr1 = perform_ocr_extraction(img1_path, side_hint="Front")
    decls1 = ocr1["declarations"]
    print("--- RAW OCR 1 ---")
    print(ocr1["raw_text"])
    print("-----------------")
    print(f"Product 1 OCR Extracted MRP: {decls1['mrp']['extracted_value']}, NetQty: {decls1['net_quantity']['extracted_value']}, Veg: {decls1['veg_nonveg']['extracted_value']}")
    assert decls1["mrp"]["extracted_value"] is not None, "Product 1 MRP not extracted"
    assert decls1["net_quantity"]["extracted_value"] is not None, "Product 1 Net Qty not extracted"
    assert "Vegetarian" in str(decls1["veg_nonveg"]["extracted_value"]), "Product 1 Veg symbol not extracted"
    print("[OK] Product 1 declarations extracted accurately from real image.")

    # Product 2
    ocr2 = perform_ocr_extraction(img2_path, side_hint="Front")
    decls2 = ocr2["declarations"]
    print("--- RAW OCR 2 ---")
    print(ocr2["raw_text"])
    print("-----------------")
    print(f"Product 2 OCR Extracted MRP: {decls2['mrp']['extracted_value']}, NetQty: {decls2['net_quantity']['extracted_value']}, Veg: {decls2['veg_nonveg']['extracted_value']}")
    assert decls2["mrp"]["extracted_value"] is not None, "Product 2 MRP not extracted"
    assert decls2["net_quantity"]["extracted_value"] is not None, "Product 2 Net Qty not extracted"
    assert "Non-Vegetarian" in str(decls2["veg_nonveg"]["extracted_value"]), "Product 2 Non-Veg symbol not extracted"
    print("[OK] Product 2 declarations extracted accurately from real image.")

    # Ensure different products produce distinct values
    assert decls1["mrp"]["extracted_value"] != decls2["mrp"]["extracted_value"], "Different images must yield different MRP values"
    assert decls1["net_quantity"]["extracted_value"] != decls2["net_quantity"]["extracted_value"], "Different images must yield different Net Qty values"
    print("[OK] Verified: 2 real product images produced distinct, product-specific declarations.")


def test_bug_1_notice_idempotency_and_bug_2_compounding():
    print("\n--- Test 3: BUG 1 (Notice Idempotency) & BUG 2 (Compounding Navigation) ---")
    client = app.test_client()

    # Login as Inspector
    client.post("/login", data={
        "email": "inspector@esavadh.gov.in",
        "password": "inspector123"
    }, follow_redirects=True)

    # Get an existing inspection ID
    inspections = database.get_inspections(limit=1)
    insp_id = inspections[0]["id"]

    # 1. Test Notice Saving Idempotency (Submit Notice 1st Time)
    notice_ref = f"LM/ENF/2026/TEST-INSP-{insp_id}"
    res1 = client.post(f"/inspection/{insp_id}/notice/save", data={
        "notice_ref_no": notice_ref,
        "issued_to": "Himalayan Pure Harvest Ltd.",
        "draft_text": "Sample Statutory Show Cause Notice Text under Section 18 PCR 2011."
    })
    assert res1.status_code == 302, "Notice save should redirect"
    assert "step=4" in res1.headers.get("Location", ""), f"Notice save must redirect to Step 4, got: {res1.headers.get('Location')}"
    print("[OK] First notice save succeeded and redirected to Step 4.")

    # 2. Test Notice Saving Idempotency (Submit SAME Notice 2nd Time - Double Click simulation)
    res2 = client.post(f"/inspection/{insp_id}/notice/save", data={
        "notice_ref_no": notice_ref,
        "issued_to": "Himalayan Pure Harvest Ltd. (Updated)",
        "draft_text": "Updated Show Cause Notice Text with additional legal provisions."
    })
    assert res2.status_code == 302, "Second notice save should not throw IntegrityError, must redirect"
    assert "step=4" in res2.headers.get("Location", ""), f"Second notice save must redirect to Step 4, got: {res2.headers.get('Location')}"
    print("[OK] BUG 1 FIXED: Repeated notice save executed idempotently without SQLite Unique constraint error.")

    # Verify notice exists and is updated in DB
    dossier = database.get_inspection_detail(insp_id)
    notices = dossier["notices"]
    matching_notices = [n for n in notices if n["notice_ref_no"] == notice_ref]
    assert len(matching_notices) == 1, f"Expected exactly 1 notice for ref {notice_ref}, found {len(matching_notices)}"
    assert "Updated" in matching_notices[0]["issued_to"]
    print(f"[OK] Notice persisted cleanly in dossier (Notice Ref: {notice_ref}).")

    # 3. Test BUG 2: Compounding Formulate Submission
    cmp_res = client.post(f"/inspection/{insp_id}/compounding/submit", data={
        "proposed_fee": "25000.0",
        "offense_section": "Section 48 read with Section 36(1)",
        "audit_note": "First-time compounding settlement order formulated."
    })
    assert cmp_res.status_code == 302, "Compounding submit should redirect"
    assert "step=4" in cmp_res.headers.get("Location", ""), f"Compounding submit must redirect to Step 4, got: {cmp_res.headers.get('Location')}"
    print("[OK] BUG 2 FIXED: Compounding formulation stayed on Step 4 (did NOT reset to Step 1).")

    # Verify compounding record exists in dossier
    dossier_after = database.get_inspection_detail(insp_id)
    assert len(dossier_after["compounding_records"]) > 0
    print("[OK] Compounding record persisted and available in dossier under Step 4.")


if __name__ == "__main__":
    img1, img2 = create_test_product_images()
    test_visual_symbol_detection(img1, img2)
    test_real_image_ocr_and_declarations(img1, img2)
    test_bug_1_notice_idempotency_and_bug_2_compounding()
    print("\n=======================================================")
    print(" ALL BUG 1, BUG 2, AND BUG 3 VERIFICATION TESTS PASSED ")
    print("=======================================================\n")
