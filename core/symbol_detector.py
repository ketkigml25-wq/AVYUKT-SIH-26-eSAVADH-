"""
eSavadh - Visual Packaging Symbol & Indicator Detection Engine
Made by Team Avyukt

Detects statutory visual packaging symbols (Green Vegetarian, Brown Non-Vegetarian)
using computer vision (OpenCV contour, hierarchy, aspect ratio, and HSV color analysis)
independent of textual OCR.
"""

import os
import cv2
import numpy as np
from PIL import Image


def detect_visual_symbol(image_path, ocr_text=None):
    """
    Analyzes an image for statutory Vegetarian (Green dot in square) or
    Non-Vegetarian (Brown triangle/circle in square) visual packaging symbols.

    Returns dict with:
      - status: 'Vegetarian (Green Symbol Detected)', 'Non-Vegetarian (Brown Symbol Detected)', 'Unclear / Needs Review', 'Not Detected on Scanned Panel'
      - symbol_type: 'Veg' | 'Non-Veg' | 'Unclear' | 'Not Detected'
      - confidence: float (0.0 to 1.0)
      - is_detected: bool
      - detection_method: 'Visual Contour Analysis' | 'Multimodal Vision + OCR'
      - rationale: str
      - bounding_box: [x, y, w, h] or None
    """
    if not os.path.exists(image_path):
        return {
            "status": "Not Detected on Scanned Panel",
            "symbol_type": "Not Detected",
            "confidence": 0.0,
            "is_detected": False,
            "detection_method": "None",
            "rationale": "Image file not found on disk.",
            "bounding_box": None
        }

    try:
        # Load image via OpenCV
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            # Fallback to PIL
            pil_img = Image.open(image_path).convert("RGB")
            img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        h, w, _ = img_bgr.shape
        img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

        # ---------------------------------------------------------------------
        # 1. Green Symbol Detection (Vegetarian)
        # Indian Standard: Green outlined square with filled green concentric circle.
        # HSV Green range: Hue ~ 35 to 85
        # ---------------------------------------------------------------------
        lower_green = np.array([35, 45, 40], dtype=np.uint8)
        upper_green = np.array([85, 255, 255], dtype=np.uint8)
        green_mask = cv2.inRange(img_hsv, lower_green, upper_green)

        # Morphology to remove tiny noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        green_clean = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_clean = cv2.morphologyEx(green_clean, cv2.MORPH_CLOSE, kernel)

        green_candidates = _find_symbol_candidates(green_clean, img_bgr, h, w, target_color="green")

        # ---------------------------------------------------------------------
        # 2. Brown / Dark Red Symbol Detection (Non-Vegetarian)
        # Indian Standard: Brown outlined square with filled brown triangle/dot.
        # HSV Brown range: Hue 0 to 20 or 165 to 180, moderate S and V
        # ---------------------------------------------------------------------
        lower_brown1 = np.array([0, 50, 30], dtype=np.uint8)
        upper_brown1 = np.array([20, 255, 180], dtype=np.uint8)
        mask_brown1 = cv2.inRange(img_hsv, lower_brown1, upper_brown1)

        lower_brown2 = np.array([165, 50, 30], dtype=np.uint8)
        upper_brown2 = np.array([180, 255, 180], dtype=np.uint8)
        mask_brown2 = cv2.inRange(img_hsv, lower_brown2, upper_brown2)
        brown_mask = cv2.bitwise_or(mask_brown1, mask_brown2)

        brown_clean = cv2.morphologyEx(brown_mask, cv2.MORPH_OPEN, kernel)
        brown_clean = cv2.morphologyEx(brown_clean, cv2.MORPH_CLOSE, kernel)

        brown_candidates = _find_symbol_candidates(brown_clean, img_bgr, h, w, target_color="brown")

        # ---------------------------------------------------------------------
        # 3. Decision Logic & Multimodal Corroboration with OCR text
        # ---------------------------------------------------------------------
        has_text_veg = bool(ocr_text and any(k in ocr_text.upper() for k in ["100% VEG", "VEGETARIAN", "GREEN DOT", "PURE VEG", "शाकाहारी"]))
        has_text_nonveg = bool(ocr_text and any(k in ocr_text.upper() for k in ["NON-VEG", "NON VEG", "BROWN DOT", "NON VEGETARIAN", "CONTAINS EGG", "मांसाहारी"]))

        # Check Green findings
        if green_candidates:
            best_green = max(green_candidates, key=lambda c: c["score"])
            if best_green["score"] >= 0.70 or (best_green["score"] >= 0.50 and has_text_veg):
                confidence = min(0.98, round(best_green["score"] + (0.10 if has_text_veg else 0.05), 2))
                return {
                    "status": "Vegetarian (Green Symbol Detected)",
                    "symbol_type": "Veg",
                    "confidence": confidence,
                    "is_detected": True,
                    "detection_method": "Visual Contour & Color Analysis" + (" + Text Corroboration" if has_text_veg else ""),
                    "rationale": f"Green square/circle indicator detected (aspect ratio: {best_green['aspect_ratio']:.2f}, solidity: {best_green['solidity']:.2f}).",
                    "bounding_box": best_green["box"]
                }

        # Check Brown findings
        if brown_candidates:
            best_brown = max(brown_candidates, key=lambda c: c["score"])
            if best_brown["score"] >= 0.70 or (best_brown["score"] >= 0.50 and has_text_nonveg):
                confidence = min(0.98, round(best_brown["score"] + (0.10 if has_text_nonveg else 0.05), 2))
                return {
                    "status": "Non-Vegetarian (Brown Symbol Detected)",
                    "symbol_type": "Non-Veg",
                    "confidence": confidence,
                    "is_detected": True,
                    "detection_method": "Visual Contour & Color Analysis" + (" + Text Corroboration" if has_text_nonveg else ""),
                    "rationale": f"Brown non-veg symbol indicator detected (aspect ratio: {best_brown['aspect_ratio']:.2f}, solidity: {best_brown['solidity']:.2f}).",
                    "bounding_box": best_brown["box"]
                }

        # Text-only fallback if visual detection had poor lighting
        if has_text_veg:
            return {
                "status": "Vegetarian (Green Symbol Declared)",
                "symbol_type": "Veg",
                "confidence": 0.85,
                "is_detected": True,
                "detection_method": "OCR Text Corroboration",
                "rationale": "Explicit vegetarian declaration detected in packaging text transcript.",
                "bounding_box": None
            }

        if has_text_nonveg:
            return {
                "status": "Non-Vegetarian (Brown Symbol Declared)",
                "symbol_type": "Non-Veg",
                "confidence": 0.85,
                "is_detected": True,
                "detection_method": "OCR Text Corroboration",
                "rationale": "Explicit non-vegetarian declaration detected in packaging text transcript.",
                "bounding_box": None
            }

        # Borderline candidates -> Unclear / Needs Review
        all_candidates = green_candidates + brown_candidates
        if all_candidates:
            top_cand = max(all_candidates, key=lambda c: c["score"])
            if top_cand["score"] >= 0.40:
                return {
                    "status": "Unclear / Needs Review",
                    "symbol_type": "Unclear",
                    "confidence": 0.50,
                    "is_detected": False,
                    "detection_method": "Visual Contour Analysis (Low Confidence)",
                    "rationale": f"Low-contrast or partially occluded candidate region detected ({top_cand['color']}). Officer review recommended.",
                    "bounding_box": top_cand["box"]
                }

        # Definitively not detected
        return {
            "status": "Not Detected on Scanned Panel",
            "symbol_type": "Not Detected",
            "confidence": 0.0,
            "is_detected": False,
            "detection_method": "Visual Contour Analysis",
            "rationale": "No statutory vegetarian or non-vegetarian visual symbol detected on this package panel.",
            "bounding_box": None
        }

    except Exception as e:
        print(f"[eSavadh Symbol Detector] Analysis exception: {e}")
        return {
            "status": "Not Detected on Scanned Panel",
            "symbol_type": "Not Detected",
            "confidence": 0.0,
            "is_detected": False,
            "detection_method": "Fallback",
            "rationale": f"Visual detection analysis encountered: {str(e)}",
            "bounding_box": None
        }


def _find_symbol_candidates(mask, img_bgr, img_h, img_w, target_color="green"):
    """
    Identifies candidate geometric symbols matching square frames with concentric dots or triangles.
    """
    candidates = []
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = max(40, int(img_h * img_w * 0.00008))
    max_area = int(img_h * img_w * 0.15)

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        if w == 0 or h == 0:
            continue

        aspect_ratio = float(w) / h
        # Symbols are square / concentric (aspect ratio between 0.70 and 1.40)
        if 0.70 <= aspect_ratio <= 1.40:
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = float(area) / hull_area if hull_area > 0 else 0.0

            # Calculate score based on squareness and solid fill / circularity
            score = 0.50
            if 0.85 <= aspect_ratio <= 1.15:
                score += 0.25
            if solidity >= 0.60:
                score += 0.15

            # Sample the crop to verify color intensity
            crop_bgr = img_bgr[y:y+h, x:x+w]
            if crop_bgr.size > 0:
                mean_b = np.mean(crop_bgr[:, :, 0])
                mean_g = np.mean(crop_bgr[:, :, 1])
                mean_r = np.mean(crop_bgr[:, :, 2])

                if target_color == "green" and mean_g > mean_r * 1.10 and mean_g > mean_b * 1.10:
                    score += 0.10
                elif target_color == "brown" and mean_r > mean_g + 10 and mean_r > mean_b + 15:
                    score += 0.10

            candidates.append({
                "box": [x, y, w, h],
                "area": area,
                "aspect_ratio": aspect_ratio,
                "solidity": solidity,
                "score": min(0.95, score),
                "color": target_color
            })

    return candidates
