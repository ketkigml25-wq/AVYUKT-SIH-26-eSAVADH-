import os
import sys
import glob
from PIL import Image

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.ocr_engine import perform_ocr_extraction
import database

database.init_db()

images = [
    "scratch/test_images/product_1_tea.png",
    "scratch/test_images/product_2_oil.png",
    "scratch/test_images/product_3_cleanser.png",
    "static/uploads/original/1790076655_WhatsApp_Image_2026-09-22_at_4.55.37_PM.jpeg",
    "static/uploads/original/1790083907_goldleaf_oil.jpg",
    "static/uploads/original/1790088398_darjeeling_tea.png",
    "static/uploads/original/1790088398_mustard_oil.png",
    "static/uploads/original/1790089769_test_tea.jpg",
    "static/uploads/original/1790092265_mustard_oil_back.jpg",
    "static/uploads/original/test_prod_1_honey_veg.png",
    "static/uploads/original/test_prod_2_tuna_nonveg.png"
]

print("=================================================================")
print("RUNNING COMPREHENSIVE MULTI-PASS OCR EXTRACTION TEST")
print("=================================================================")

for p in images:
    if not os.path.exists(p):
        print(f"Skipping (not found): {p}")
        continue
        
    print(f"\n[+] Testing Image: {os.path.basename(p)}")
    res = perform_ocr_extraction(p, side_hint="Back")
    raw_len = len(res.get("raw_text", ""))
    decls = res.get("declarations", {})
    
    print(f"    Raw Text Length: {raw_len} chars | Overall Conf: {res.get('overall_confidence')}")
    print(f"    MRP:            {decls.get('mrp', {}).get('extracted_value')} (conf: {decls.get('mrp', {}).get('confidence')})")
    print(f"    Net Qty:        {decls.get('net_quantity', {}).get('extracted_value')} (conf: {decls.get('net_quantity', {}).get('confidence')})")
    print(f"    Manufacturer:   {decls.get('manufacturer', {}).get('extracted_value')[:60] if decls.get('manufacturer', {}).get('extracted_value') else 'None'}")
    print(f"    Mfg Date:       {decls.get('mfg_date', {}).get('extracted_value')}")
    print(f"    Consumer Care:  {decls.get('consumer_care', {}).get('extracted_value')}")
    print(f"    Country Origin: {decls.get('country_of_origin', {}).get('extracted_value')}")
    print(f"    Dietary Symbol: {decls.get('veg_nonveg', {}).get('extracted_value')}")

print("\n=================================================================")
print("ALL TESTS EXECUTED SUCCESSFULLY")
print("=================================================================")
