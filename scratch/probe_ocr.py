import sys
import os

print("Step 1: Check imports", flush=True)
try:
    import winocr
    print("winocr is available", flush=True)
except Exception as e:
    print("winocr error:", e, flush=True)

try:
    import pytesseract
    print("pytesseract is available", flush=True)
except Exception as e:
    print("pytesseract error:", e, flush=True)

from PIL import Image

print("Step 2: Load an image", flush=True)
test_img_path = "scratch/test_images/product_2_oil.png"
if os.path.exists(test_img_path):
    im = Image.open(test_img_path).convert("RGB")
    print(f"Loaded {test_img_path}, size={im.size}", flush=True)
    if "winocr" in sys.modules:
        print("Step 3: Run winocr", flush=True)
        res = winocr.recognize_pil_sync(im, "en")
        print("winocr result text length:", len(res.get("text", "")), flush=True)
        print("winocr text sample:\n", res.get("text", "")[:400], flush=True)
else:
    print("Test image path does not exist:", test_img_path, flush=True)
