"""
视频节点公共工具：图像/视频上传、视频下载
"""
import requests
import time
import os
import io
import numpy as np
from PIL import Image
import folder_paths
from . import synvow_auth

DIRECT_API_BASE = "https://service.synvow.com/api/v1"


def upload_image(api_key, img_tensor):
    arr = (img_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    res = requests.post(
        f"{DIRECT_API_BASE}/api/upload/images",
        headers={"X-API-Key": api_key},
        files=[("files", ("image.jpg", buf, "image/jpeg"))],
        verify=False, timeout=60,
    )
    data = res.json()
    if res.status_code != 200 or data.get("code") != 200:
        raise RuntimeError(f"Image upload failed: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise RuntimeError(f"Image upload returned no URL: {data}")
    return urls[0]


def tensor_to_jpeg_bytes(image_tensor):
    if image_tensor is None:
        return None
    if len(image_tensor.shape) > 3:
        image_tensor = image_tensor[0]
    arr = (255.0 * image_tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def download_video(video_url, task_id, save_path="", prefix="video", max_retries=3, filename=""):
    output_dir = save_path.strip() if save_path and save_path.strip() else ""
    if not output_dir:
        try:
            output_dir = folder_paths.get_output_directory()
        except Exception:
            output_dir = ""
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    if filename and filename.strip():
        fname = filename.strip()
        if not fname.lower().endswith(".mp4"):
            fname += ".mp4"
    else:
        fname = f"{prefix}_{task_id[:8].replace(':', '_')}.mp4"

    base, ext = os.path.splitext(fname)
    candidate = fname
    counter = 1
    while os.path.exists(os.path.join(output_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    fname = candidate
    video_path = os.path.join(output_dir, fname)
    for attempt in range(max_retries):
        try:
            res = requests.get(video_url, verify=False, timeout=120, stream=True)
            if res.status_code == 200:
                with open(video_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                return video_path
        except Exception as e:
            print(f"[{prefix}] download failed ({attempt+1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            time.sleep(3)
    return None


def upload_video_file(api_key, video_path):
    url = f"{DIRECT_API_BASE}/api/upload/videos"
    headers = {"X-API-Key": api_key}
    fname = os.path.basename(video_path)
    print(f"[upload] 视频上传: {fname} -> {url}")
    with open(video_path, "rb") as f:
        res = requests.post(url, headers=headers, files=[("files", (fname, f, "video/mp4"))], verify=False, timeout=120)
    data = res.json()
    print(f"[upload] 视频上传响应: HTTP {res.status_code} | {str(data)[:200]}")
    if res.status_code != 200 or data.get("code") != 200:
        raise Exception(f"Video upload failed: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise Exception(f"Video upload returned no URL: {data}")
    return urls[0]


def upload_images(api_key, image_bytes_list):
    url = f"{DIRECT_API_BASE}/api/upload/images"
    headers = {"X-API-Key": api_key}
    files = [("files", (f"image_{i}.jpg", b, "image/jpeg")) for i, b in enumerate(image_bytes_list)]
    print(f"[upload] 图像上传: {len(image_bytes_list)} 张 -> {url}")
    res = requests.post(url, headers=headers, files=files, verify=False, timeout=60)
    data = res.json()
    print(f"[upload] 图像上传响应: HTTP {res.status_code} | {str(data)[:200]}")
    if res.status_code != 200 or data.get("code") != 200:
        raise Exception(f"Image upload failed: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise Exception(f"Image upload returned no URL: {data}")
    return urls


def upload_audio_file(api_key, audio_path):
    url = f"{DIRECT_API_BASE}/api/upload/audios"
    headers = {"X-API-Key": api_key}
    fname = os.path.basename(audio_path)
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else "mp3"
    mime = {"mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg",
            "flac": "audio/flac", "aac": "audio/aac", "m4a": "audio/mp4"}.get(ext, "audio/mpeg")
    print(f"[upload] 音频上传: {fname} -> {url}")
    with open(audio_path, "rb") as f:
        res = requests.post(url, headers=headers, files=[("files", (fname, f, mime))], verify=False, timeout=120)
    data = res.json()
    print(f"[upload] 音频上传响应: HTTP {res.status_code} | {str(data)[:200]}")
    if res.status_code != 200 or data.get("code") != 200:
        raise Exception(f"Audio upload failed: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise Exception(f"Audio upload returned no URL: {data}")
    return urls[0]

