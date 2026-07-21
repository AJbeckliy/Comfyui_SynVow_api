"""
SynVow 媒体公共工具：上传、下载、异步任务提交/轮询、Comfy 媒体包装
"""
import hashlib
import io
import json
import os
import time

import folder_paths
import numpy as np
import requests
from PIL import Image
from comfy_api.input_impl import VideoFromFile

from . import synvow_auth

DIRECT_API_BASE = "https://service.synvow.com/api/v1"
EDIT_SUBMIT_URL = f"{DIRECT_API_BASE}/api/models/image/edit"
EDIT_POLL_URL = f"{DIRECT_API_BASE}/api/models/tasks"

_SUCCESS = ("SUCCESS", "SUCCEED", "SUCCEEDED", "COMPLETED", "DONE", "FINISH", "FINISHED")
_FAILURE = ("FAILURE", "FAILED", "ERROR")


def is_changed_by_inputs(**kwargs):
    key = json.dumps({k: str(v) for k, v in kwargs.items()}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key.encode()).hexdigest()


def as_comfy_video(path):
    if path and os.path.isfile(path):
        return VideoFromFile(path)
    return VideoFromFile(io.BytesIO())


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


def upload_media_file(api_key, file_path, media_type="video"):
    path = (file_path or "").strip()
    if not path:
        return ""
    if path.startswith(("http://", "https://")):
        return path
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{media_type} 文件不存在: {path}")
    endpoint = "videos" if media_type == "video" else "audios"
    mime = "video/mp4" if media_type == "video" else "audio/mpeg"
    default_name = "ref.mp4" if media_type == "video" else "ref.mp3"
    fname = os.path.basename(path) or default_name
    with open(path, "rb") as f:
        content = f.read()
    res = requests.post(
        f"{DIRECT_API_BASE}/api/upload/{endpoint}",
        headers={"X-API-Key": api_key},
        files=[("files", (fname, content, mime))],
        verify=False,
        timeout=180,
    )
    data = res.json() if res.text.strip() else {}
    if res.status_code != 200 or data.get("code") != 200:
        raise RuntimeError(f"{media_type} 上传失败: {data or res.text[:200]}")
    urls = (data.get("data") or {}).get("urls") or []
    if not urls:
        raise RuntimeError(f"{media_type} 上传无 URL: {data}")
    return urls[0]


def _resolve_output_dir(save_path=""):
    output_dir = save_path.strip() if save_path and save_path.strip() else ""
    if not output_dir:
        try:
            output_dir = folder_paths.get_output_directory()
        except Exception:
            output_dir = ""
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _unique_path(output_dir, fname):
    base, ext = os.path.splitext(fname)
    candidate = fname
    counter = 1
    while os.path.exists(os.path.join(output_dir, candidate)):
        candidate = f"{base}({counter}){ext}"
        counter += 1
    return os.path.join(output_dir, candidate)


def download_media(url, task_id, save_path="", prefix="file", default_ext=".mp4",
                   max_retries=3, filename="", audio_exts=False):
    output_dir = _resolve_output_dir(save_path)
    if filename and filename.strip():
        fname = filename.strip()
        lower = fname.lower()
        if audio_exts:
            if not lower.endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
                fname += ".mp3"
        elif not lower.endswith(default_ext):
            fname += default_ext
    else:
        fname = f"{prefix}_{str(task_id)[:8].replace(':', '_')}{default_ext}"
    media_path = _unique_path(output_dir, fname)
    for attempt in range(max_retries):
        try:
            res = requests.get(url, verify=False, timeout=120, stream=True)
            if res.status_code == 200:
                with open(media_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                return media_path
        except Exception as e:
            print(f"[{prefix}] download failed ({attempt+1}/{max_retries}): {e}")
        if attempt < max_retries - 1:
            time.sleep(3)
    return None


def download_video(video_url, task_id, save_path="", prefix="video", max_retries=3, filename=""):
    return download_media(
        video_url, task_id, save_path=save_path, prefix=prefix,
        default_ext=".mp4", max_retries=max_retries, filename=filename,
    )


def download_audio(audio_url, task_id, save_path="", prefix="audio", max_retries=3, filename=""):
    return download_media(
        audio_url, task_id, save_path=save_path, prefix=prefix,
        default_ext=".mp3", max_retries=max_retries, filename=filename, audio_exts=True,
    )


def parse_task_id(data):
    payload = data.get("data") if isinstance(data.get("data"), dict) else {}
    source = payload.get("sourceData") if isinstance(payload.get("sourceData"), dict) else {}
    source_inner = source.get("data")
    source_item = source_inner[0] if isinstance(source_inner, list) and source_inner else {}
    task_ids = payload.get("task_ids") if isinstance(payload.get("task_ids"), list) else []
    return (
        (source_item.get("task_id") if isinstance(source_item, dict) else None)
        or payload.get("task_id")
        or (task_ids[0] if task_ids else None)
        or data.get("task_id")
        or ""
    )


def extract_video_url(value):
    if not value:
        return ""
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    if isinstance(value, list):
        for item in value:
            found = extract_video_url(item)
            if found:
                return found
        return ""
    if isinstance(value, dict):
        for key in ("result_url", "url", "video_url", "video"):
            val = value.get(key)
            if isinstance(val, str) and val.startswith(("http://", "https://")):
                return val
            if isinstance(val, list):
                found = extract_video_url(val)
                if found:
                    return found
        for key in ("data", "result", "output", "sourceData", "task_result", "videos"):
            if key in value:
                found = extract_video_url(value.get(key))
                if found:
                    return found
    return ""


def submit_edit_async(api_key, body, tag):
    headers = synvow_auth.make_api_headers(api_key)
    print(f"[{tag}] 提交: model={body.get('model')}")
    res = requests.post(
        EDIT_SUBMIT_URL, headers=headers, params={"async": "true"},
        json=body, verify=False, timeout=120,
    )
    data = res.json() if res.text.strip() else {}
    if res.status_code == 401:
        raise RuntimeError("API Key 无效或已过期，请重新登录")
    if res.status_code not in (200, 202):
        raise Exception(f"提交失败 ({res.status_code}): {data.get('message') or str(data)[:200]}")
    task_id = parse_task_id(data)
    if not task_id:
        raise Exception(f"{tag} 响应中无 task_id: {str(data)[:200]}")
    consumption_id = data.get("consumption_id") or (data.get("data") or {}).get("consumption_id") or ""
    print(f"[{tag}] task_id=...{str(task_id)[-8:]}")
    return str(task_id), str(consumption_id)


def _default_poll_success(inner):
    status = str(inner.get("state") or inner.get("status") or inner.get("task_status") or "").upper()
    return status in _SUCCESS, status


def _default_poll_failed(inner):
    status = str(inner.get("state") or inner.get("status") or inner.get("task_status") or "").upper()
    return status in _FAILURE, status


def poll_edit_task(api_key, task_id, model, tag, consumption_id="", timeout=1800, interval=5,
                   check_success=None, check_failed=None, pick_url=None):
    """
    check_success(inner) -> (done: bool, label: str)
    check_failed(inner) -> (failed: bool, label: str)
    pick_url(inner, data) -> url str
    """
    import comfy.model_management as mm
    check_success = check_success or _default_poll_success
    check_failed = check_failed or _default_poll_failed
    pick_url = pick_url or (lambda inner, data: extract_video_url(inner) or extract_video_url(data))
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            raise Exception(f"[{tag}] 轮询超时 ({timeout}s)")
        time.sleep(interval)
        mm.throw_exception_if_processing_interrupted()
        try:
            body = {"task_id": task_id, "model": model}
            if consumption_id:
                body["consumption_id"] = consumption_id
            res = requests.post(EDIT_POLL_URL, headers=headers, json=body, verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[{tag}] ...{task_id[-8:]} HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else {})
            done, label = check_success(inner)
            failed, fail_label = check_failed(inner)
            print(f"[{tag}] ...{task_id[-8:]} status={label or fail_label or '(无状态)'} ({elapsed}s)")
            if done:
                url = pick_url(inner, data)
                if not url:
                    raise Exception(f"{tag} 任务成功但无视频 URL")
                return url
            if failed:
                err = inner.get("fail_reason") or inner.get("error") or fail_label
                raise Exception(f"{tag} 任务失败: {err}")
        except Exception as e:
            msg = str(e)
            if msg.startswith(tag) or "超时" in msg:
                raise
            print(f"[{tag}] 轮询异常: {e}")
