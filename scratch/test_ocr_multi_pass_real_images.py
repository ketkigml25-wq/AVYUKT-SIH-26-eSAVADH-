"""
Comprehensive Real Image Multi-Pass OCR Test Suite
Tests 3 distinct packaging images for:
- MRP detection across formats (Rs 240, Rs 380, Rs 199)
- "Uttar Pradesh" state accuracy & "A/3" plot accuracy
- Net Quantity standardization (250 g, 1 L, 100 ml)
- Manufacturer & Address with 6-digit PIN codes
- Date of Manufacture (05/2024, 03/2024, 01/2024)
- Consumer Care helpline & emails
- Country of Origin
- Dietary Indicators
- Zero hardcoded fallback verification
"""

import os
import sys
import unittest

# Ensure UTF-8 output in Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ocr_engine import perform_ocr_extraction, extract_mrp_field, extract_net_quantity_field
import database

TEST_IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
os.makedirs(TEST_IMG_DIR, exist_ok=True)


def create_realistic_packaging_panel(filename, lines, has_veg_symbol=True):
    """Creates a high-resolution packaging panel image with text and statutory symbols."""
    img_w, img_h = 1400, 850
    # Background off-white / ivory
    img = Image.new("RGB", (img_w, img_h), color=(252, 250, 246))
    draw = ImageDraw.Draw(img)

    # Load system font if available
    try:
        header_font = ImageFont.truetype("arial.ttf", 26)
        body_font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        header_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Outer border / PDP box
    draw.rectangle([20, 20, img_w - 20, img_h - 20], outline=(60, 30, 70), width=3)
    draw.rectangle([28, 28, img_w - 28, 90], fill=(60, 30, 70))
    
    # Header title
    draw.text((45, 45), lines[0], fill=(255, 255, 255), font=header_font)

    # Dietary symbol (Green vegetarian indicator)
    if has_veg_symbol:
        sym_x, sym_y, sym_s = 1280, 38, 44
        draw.rectangle([sym_x, sym_y, sym_x + sym_s, sym_y + sym_s], outline=(0, 140, 40), width=3, fill=(255, 255, 255))
        draw.ellipse([sym_x + 11, sym_y + 11, sym_x + sym_s - 11, sym_y + sym_s - 11], fill=(0, 140, 40))

    # Body lines
    y_offset = 120
    for line in lines[1:]:
        draw.text((45, y_offset), line, fill=(20, 20, 20), font=body_font)
        y_offset += 55

    out_path = os.path.join(TEST_IMG_DIR, filename)
    img.save(out_path, quality=98)
    return out_path


class TestMultiPassOCRRealImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

        # Image 1: Himalayan Tea (Contains Uttar Pradesh and Plot No. A/3)
        cls.img1_path = create_realistic_packaging_panel(
            "product_1_tea.png",
            [
                "HIMALAYAN ORGANIC DARJEELING GREEN TEA",
                "Net Qty: 250 g",
                "MRP: ₹ 240.00 (Inclusive of all taxes)",
                "Mfd by: Himalayan Pure Harvest Ltd., Plot No. A/3, Industrial Area, Sector 62, Noida, Uttar Pradesh - 201301",
                "Date of Mfg: 05/2024",
                "Customer Care: 1800-112-4455 / care@himalayanharvest.in",
                "Country of Origin: India",
                "Best Before: 12 Months from Packing"
            ],
            has_veg_symbol=True
        )

        # Image 2: Sesame Oil
        cls.img2_path = create_realistic_packaging_panel(
            "product_2_oil.png",
            [
                "NUTRI-PURE COLD PRESSED ORGANIC SESAME OIL",
                "Net Quantity: 1 L",
                "M.R.P. ₹ 380.00 (Incl. of all taxes)",
                "Manufactured & Packed by: Vedic Agro Formulations Pvt Ltd, 45 GIDC Estate, Vadodara, Gujarat - 390010",
                "PKD: 03/2024",
                "Consumer Care: +91-9876543210 / support@vedicagro.in",
                "Country of Origin: India",
                "Best Before: 9 Months from PKD"
            ],
            has_veg_symbol=True
        )

        # Image 3: Face Cleanser (Cosmetic non-food)
        cls.img3_path = create_realistic_packaging_panel(
            "product_3_cleanser.png",
            [
                "SILKCARE HYDRATING FACIAL CLEANSER",
                "Net Content: 100 ml",
                "MRP Rs 199/- (all taxes incl.)",
                "Manufactured by: CosmoPure Herbals LLP, Plot No. B-12, MIDC, Andheri East, Mumbai, Maharashtra - 400093",
                "Date of Mfg: 01/2024",
                "Helpline: 1800-220-9988 / customercare@cosmopure.com",
                "Country of Origin: India",
                "Use by: 01/2026"
            ],
            has_veg_symbol=False
        )

    def test_image_1_tea_extraction(self):
        print("\n--- Testing Image 1: Himalayan Organic Tea (Uttar Pradesh & Plot A/3) ---")
        res = perform_ocr_extraction(self.img1_path, side_hint="Back")
        decls = res["declarations"]

        print(f"Raw OCR Text:\n{res['raw_text']}\n")
        print(f"MRP: {decls['mrp']['extracted_value']}")
        print(f"Net Quantity: {decls['net_quantity']['extracted_value']}")
        print(f"Manufacturer: {decls['manufacturer']['extracted_value']}")
        print(f"Mfg Date: {decls['mfg_date']['extracted_value']}")
        print(f"Consumer Care: {decls['consumer_care']['extracted_value']}")
        print(f"Country of Origin: {decls['country_of_origin']['extracted_value']}")
        print(f"Dietary Indicator: {decls['veg_nonveg']['extracted_value']}")

        # Assertions for Image 1
        self.assertIsNotNone(decls["mrp"]["extracted_value"])
        self.assertIn("240", decls["mrp"]["extracted_value"])
        self.assertEqual(decls["net_quantity"]["extracted_value"], "250 g")
        
        mfr_val = decls["manufacturer"]["extracted_value"]
        self.assertIsNotNone(mfr_val)
        self.assertIn("Uttar Pradesh", mfr_val, "Uttar Pradesh should be accurately recognized in address")
        self.assertIn("A/3", mfr_val, "A/3 should be accurately recognized without N3 corruption")
        self.assertIn("201301", mfr_val, "6-digit PIN code should be preserved")

        self.assertEqual(decls["mfg_date"]["extracted_value"], "05/2024")
        self.assertIn("1800", decls["consumer_care"]["extracted_value"])
        self.assertEqual(decls["country_of_origin"]["extracted_value"], "India")
        self.assertIn("Vegetarian", decls["veg_nonveg"]["extracted_value"])

    def test_image_2_oil_extraction(self):
        print("\n--- Testing Image 2: Nutri-Pure Sesame Oil (1 L & Rs 380) ---")
        res = perform_ocr_extraction(self.img2_path, side_hint="Front")
        decls = res["declarations"]

        print(f"MRP: {decls['mrp']['extracted_value']}")
        print(f"Net Quantity: {decls['net_quantity']['extracted_value']}")
        print(f"Manufacturer: {decls['manufacturer']['extracted_value']}")
        print(f"Mfg Date: {decls['mfg_date']['extracted_value']}")

        # Assertions for Image 2
        self.assertIsNotNone(decls["mrp"]["extracted_value"])
        self.assertIn("380", decls["mrp"]["extracted_value"])
        self.assertEqual(decls["net_quantity"]["extracted_value"], "1 L")
        self.assertIn("Gujarat", decls["manufacturer"]["extracted_value"])
        self.assertIn("390010", decls["manufacturer"]["extracted_value"])
        self.assertEqual(decls["mfg_date"]["extracted_value"], "03/2024")
        self.assertEqual(decls["country_of_origin"]["extracted_value"], "India")

    def test_image_3_cleanser_extraction(self):
        print("\n--- Testing Image 3: SilkCare Facial Cleanser (100 ml & Rs 199) ---")
        res = perform_ocr_extraction(self.img3_path, side_hint="Back")
        decls = res["declarations"]

        print(f"MRP: {decls['mrp']['extracted_value']}")
        print(f"Net Quantity: {decls['net_quantity']['extracted_value']}")
        print(f"Manufacturer: {decls['manufacturer']['extracted_value']}")
        print(f"Mfg Date: {decls['mfg_date']['extracted_value']}")

        # Assertions for Image 3
        self.assertIsNotNone(decls["mrp"]["extracted_value"])
        self.assertIn("199", decls["mrp"]["extracted_value"])
        self.assertEqual(decls["net_quantity"]["extracted_value"], "100 ml")
        self.assertIn("Maharashtra", decls["manufacturer"]["extracted_value"])
        self.assertIn("400093", decls["manufacturer"]["extracted_value"])
        self.assertEqual(decls["mfg_date"]["extracted_value"], "01/2024")
        self.assertEqual(decls["country_of_origin"]["extracted_value"], "India")

    def test_zero_fake_data_on_blank_image(self):
        print("\n--- Testing Blank Image for Zero Fake Fallbacks ---")
        blank_path = os.path.join(TEST_IMG_DIR, "blank_image.png")
        Image.new("RGB", (300, 300), color=(255, 255, 255)).save(blank_path)

        res = perform_ocr_extraction(blank_path, side_hint="Front")
        decls = res["declarations"]

        self.assertIsNone(decls["mrp"]["extracted_value"], "MRP must be None for blank image (no fake fallback)")
        self.assertIsNone(decls["net_quantity"]["extracted_value"], "Net Qty must be None for blank image")
        self.assertIsNone(decls["manufacturer"]["extracted_value"], "Manufacturer must be None for blank image")
        self.assertIsNone(decls["mfg_date"]["extracted_value"], "Mfg date must be None for blank image")
        self.assertEqual(decls["mrp"]["inspector_status"], "Needs Review")


if __name__ == "__main__":
    unittest.main()
