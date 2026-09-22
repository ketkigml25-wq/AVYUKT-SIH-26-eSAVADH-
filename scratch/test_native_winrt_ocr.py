import asyncio
import os
from PIL import Image
import winrt.windows.media.ocr as ocr
import winrt.windows.globalization as glob
import winrt.windows.graphics.imaging as imaging
import winrt.windows.storage.streams as streams

async def run_windows_ocr(pil_img, lang_tag="en-US"):
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    
    width, height = pil_img.size
    img_bytes = pil_img.tobytes()
    
    writer = streams.DataWriter()
    writer.write_bytes(img_bytes)
    buffer = writer.detach_buffer()
    
    sb = imaging.SoftwareBitmap.create_copy_from_buffer(
        buffer, imaging.BitmapPixelFormat.RGBA8, width, height
    )
    
    try:
        lang = glob.Language(lang_tag)
        engine = ocr.OcrEngine.try_create_from_language(lang)
    except Exception:
        engine = None
        
    if not engine:
        engine = ocr.OcrEngine.try_create_from_user_profile_languages()
        
    if not engine:
        return {"text": "", "lines": [], "words": []}
        
    ocr_result = await engine.recognize_async(sb)
    
    lines_data = []
    all_words = []
    text_lines = []
    
    for line in ocr_result.lines:
        line_words = []
        for word in line.words:
            rect = word.bounding_rect
            w_info = {
                "text": word.text,
                "bbox": {
                    "x": round(rect.x, 1),
                    "y": round(rect.y, 1),
                    "w": round(rect.width, 1),
                    "h": round(rect.height, 1)
                }
            }
            line_words.append(w_info)
            all_words.append(w_info)
        lines_data.append({"text": line.text, "words": line_words})
        text_lines.append(line.text)
        
    return {
        "text": "\n".join(text_lines),
        "lines": lines_data,
        "words": all_words
    }

def recognize_sync(pil_img, lang_tag="en-US"):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(run_windows_ocr(pil_img, lang_tag))).result()
    else:
        return loop.run_until_complete(run_windows_ocr(pil_img, lang_tag))

# Test on test images
img_path = "scratch/test_images/product_1_tea.png"
if os.path.exists(img_path):
    im = Image.open(img_path)
    res = recognize_sync(im)
    print("SUCCESS! Recognized text from tea image:")
    print(res["text"])
    print("Words count:", len(res["words"]))
