import os
import glob
from PIL import Image

print("--- OCR Library Detection ---")
try:
    import winocr
    print("winocr: AVAILABLE")
except Exception as e:
    print("winocr: NOT AVAILABLE -", e)

try:
    import pytesseract
    print("pytesseract: AVAILABLE")
except Exception as e:
    print("pytesseract: NOT AVAILABLE -", e)

try:
    import easyocr
    print("easyocr: AVAILABLE")
except Exception as e:
    print("easyocr: NOT AVAILABLE -", e)

images = glob.glob("static/uploads/original/*") + glob.glob("scratch/test_images/*")
print(f"\nFound {len(images)} sample images.")

from core.ocr_engine import perform_ocr_extraction, _run_single_ocr_pass
from core.image_enhancer import generate_ocr_preprocessing_variants

for img_path in images[:4]:
    print("\n=======================================================")
    print("TESTING FILE:", img_path)
    print("=======================================================")
    try:
        im = Image.open(img_path).convert("RGB")
        print(f"Image Resolution: {im.size}")
        
        # Test direct winocr
        if "winocr" in globals():
            try:
                res = winocr.recognize_pil_sync(im, "en")
                print("winocr direct raw length:", len(res.get("text", "")))
                print("winocr sample text:\n", res.get("text", "")[:300])
            except Exception as we:
                print("winocr direct error:", we)
                
        # Test full perform_ocr_extraction
        result = perform_ocr_extraction(img_path)
        print("\nperform_ocr_extraction result:")
        print("Raw text length:", len(result.get("raw_text", "")))
        print("Passes executed:", result.get("pass_results_count", 0))
        print("Declarations extracted:")
        for k, v in result.get("declarations", {}).items():
            print(f"  - {k}: {v.get('extracted_value')} (conf: {v.get('confidence')})")
    except Exception as e:
        print("Exception testing image:", e)
