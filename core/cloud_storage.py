"""
eSavadh - Serverless Cloud Storage Manager
Made by Team Avyukt

Supports:
1. Vercel Blob Storage (via BLOB_READ_WRITE_TOKEN)
2. Cloudinary Storage (via CLOUDINARY_URL / CLOUDINARY_CLOUD_NAME)
3. Serverless /tmp/uploads & Local Disk Fallback
"""

import os
import time
import base64
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_storage_dirs():
    """Returns writable fallback directories on local disk or serverless /tmp."""
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(BASE_DIR, os.W_OK))
    if is_serverless:
        orig = "/tmp/uploads/original"
        enh = "/tmp/uploads/enhanced"
    else:
        orig = os.path.join(BASE_DIR, "static", "uploads", "original")
        enh = os.path.join(BASE_DIR, "static", "uploads", "enhanced")

    os.makedirs(orig, exist_ok=True)
    os.makedirs(enh, exist_ok=True)
    return orig, enh


def save_image_to_storage(file_obj, filename, folder_type="original"):
    """
    Saves an uploaded image to Vercel Blob, Cloudinary, or local/serverless disk.
    Returns (stored_path_or_url, absolute_local_path_if_any).
    """
    orig_dir, enh_dir = get_local_storage_dirs()
    target_dir = orig_dir if folder_type == "original" else enh_dir
    local_abs_path = os.path.join(target_dir, filename)

    # Read bytes
    if hasattr(file_obj, "read"):
        file_bytes = file_obj.read()
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
    elif isinstance(file_obj, bytes):
        file_bytes = file_obj
    else:
        file_bytes = b""

    # Save to local/tmp path as cache/working copy
    if file_bytes:
        try:
            with open(local_abs_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            print(f"[eSavadh Storage] Warning saving local working copy: {e}")

    # 1. Try Vercel Blob Storage
    blob_token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if blob_token and file_bytes:
        try:
            blob_url = f"https://blob.vercel-storage.com/{filename}"
            content_type = "image/png" if filename.endswith(".png") else "image/jpeg"
            headers = {
                "authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
                "content-type": content_type
            }
            resp = requests.put(blob_url, data=file_bytes, headers=headers, timeout=10)
            if resp.status_code in [200, 201]:
                data = resp.json()
                public_url = data.get("url")
                if public_url:
                    return public_url, local_abs_path
        except Exception as e:
            print(f"[eSavadh Storage] Vercel Blob upload notice: {e}")

    # 2. Try Cloudinary
    cloudinary_url = os.environ.get("CLOUDINARY_URL")
    if cloudinary_url and file_bytes:
        try:
            import cloudinary
            import cloudinary.uploader
            res = cloudinary.uploader.upload(
                file_bytes,
                public_id=os.path.splitext(filename)[0],
                folder=f"esavadh/{folder_type}"
            )
            secure_url = res.get("secure_url")
            if secure_url:
                return secure_url, local_abs_path
        except Exception as e:
            print(f"[eSavadh Storage] Cloudinary upload notice: {e}")

    # 3. Default to relative static/uploads path
    rel_path = f"uploads/{folder_type}/{filename}"
    return rel_path, local_abs_path
