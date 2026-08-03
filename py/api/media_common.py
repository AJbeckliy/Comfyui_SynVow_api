"""
SynVow 媒体公共工具：上传、下载、异步任务提交/轮询
"""
import concurrent.futures
import hashlib
import io
import json
import os
import time

import comfy.model_management as mm
import folder_paths
import numpy as np
import requests
import torch
from PIL import Image

from . import synvow_auth

DIRECT_API_BASE = "https://service.synvow.com/api/v1"
EDIT_SUBMIT_URL = f"{DIRECT_API_BASE}/api/models/image/edit"
EDIT_POLL_URL = f"{DIRECT_API_BASE}/api/models/tasks"

_SUCCESS = ("SUCCESS", "SUCCEED", "SUCCEEDED", "COMPLETED", "DONE", "FINISH", "FINISHED")
_FAILURE = ("FAILURE", "FAILED", "ERROR", "EXCEPTION")


def is_changed_by_inputs(**kwargs):
    key = json.dumps({k: str(v) for k, v in kwargs.items()}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key.encode()).hexdigest()


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


_URL_FIELD_KEYS = (
    "result_url", "url", "image_url", "imageUrl", "video_url", "video",
    "cld2VideoUrl", "result_file",
)
_NEST_FIELD_KEYS = (
    "content", "images", "results", "data", "result", "output", "outputs",
    "sourceData", "task_result", "videos", "resultImages", "items",
)


def extract_result_urls(value):
    """从任务结果里取出全部 http(s) 资源 URL（图/视通用，去重保序）。"""
    out, seen = [], set()

    def add(u):
        if isinstance(u, str) and u.startswith(("http://", "https://")) and u not in seen:
            seen.add(u)
            out.append(u)

    def walk(v):
        if not v:
            return
        if isinstance(v, str):
            add(v)
            return
        if isinstance(v, list):
            for item in v:
                walk(item)
            return
        if not isinstance(v, dict):
            return
        for key in _URL_FIELD_KEYS:
            val = v.get(key)
            if isinstance(val, str):
                add(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        add(item)
                    else:
                        walk(item)
        for key in _NEST_FIELD_KEYS:
            if v.get(key) is not None:
                walk(v.get(key))

    walk(value)
    return out


def extract_result_url(value):
    urls = extract_result_urls(value)
    return urls[0] if urls else ""


def unpack_list_input(v):
    return v[0] if isinstance(v, list) else v


def normalize_prompts(prompts_list, fallback=""):
    if isinstance(prompts_list, list):
        prompts = [str(p).strip() for p in prompts_list if p is not None and str(p).strip()]
    elif prompts_list and str(prompts_list).strip():
        prompts = [str(prompts_list).strip()]
    else:
        prompts = []
    if not prompts and fallback is not None and str(fallback).strip():
        prompts = [str(fallback).strip()]
    return prompts or [""]


def blank_image(h=1024, w=1024):
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


def download_image_tensor(img_url, tag="image", retries=3):
    short = f"...{img_url[-24:]}" if len(img_url) > 24 else img_url
    print(f"[{tag}] 开始下载: {short}")
    for attempt in range(retries):
        try:
            r = requests.get(img_url, timeout=120, verify=False)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            print(f"[{tag}] 下载成功 ({attempt + 1}/{retries}): {short} 尺寸={img.width}x{img.height}")
            return torch.from_numpy(arr).unsqueeze(0)
        except Exception as e:
            print(f"[{tag}] 下载失败 ({attempt + 1}/{retries}): {short} 错误={e}")
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    print(f"[{tag}] {retries}次重试均失败，使用黑图占位: {short}")
    return blank_image()


def download_image_tensors(image_urls, tag="image"):
    valid = [(i, u) for i, u in enumerate(image_urls) if u]
    print(f"[{tag}] 并发下载 {len(valid)}/{len(image_urls)} 张...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(image_urls), 1)) as ex:
        futures = {i: ex.submit(download_image_tensor, u, tag) for i, u in valid}
    downloaded = {i: f.result() for i, f in futures.items()}
    ref_h, ref_w = next(((t.shape[1], t.shape[2]) for t in downloaded.values()), (1024, 1024))
    return [
        downloaded[i] if i in downloaded else blank_image(ref_h, ref_w)
        for i in range(len(image_urls))
    ]


def stack_image_tensors(image_urls, tag="image"):
    tensors = download_image_tensors(image_urls, tag=tag)
    if not tensors:
        return blank_image()
    h, w = tensors[0].shape[1], tensors[0].shape[2]
    resized = []
    for t in tensors:
        if t.shape[1] != h or t.shape[2] != w:
            pil = Image.fromarray((t[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8))
            pil = pil.resize((w, h), Image.LANCZOS)
            t = torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)
        resized.append(t)
    return torch.cat(resized, dim=0)


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


def _poll_status_label(inner):
    raw = inner.get("state") or inner.get("status") or inner.get("task_status") or ""
    if raw in (1, "1"):
        return "SUCCESS"
    if raw in (2, "2", -1, "-1"):
        return "FAILURE"
    text = str(raw)
    if text in ("已完成", "成功"):
        return "SUCCESS"
    if text in ("失败",):
        return "FAILURE"
    return text.upper()


def _default_poll_success(inner):
    status = _poll_status_label(inner)
    return status in _SUCCESS, status


def _default_poll_failed(inner):
    status = _poll_status_label(inner)
    return status in _FAILURE, status


def poll_edit_task(api_key, task_id, model, tag, consumption_id="", timeout=1800, interval=5,
                   check_success=None, check_failed=None, pick_url=None, fail_soft=False,
                   extra_body=None):
    """
    check_success(inner) -> (done: bool, label: str)
    check_failed(inner) -> (failed: bool, label: str)
    pick_url(inner, data) -> url str
    fail_soft=True 时超时/失败/无 URL 返回 None，不抛异常。
    """
    check_success = check_success or _default_poll_success
    check_failed = check_failed or _default_poll_failed
    pick_url = pick_url or (lambda inner, data: extract_result_url(inner) or extract_result_url(data))
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            msg = f"[{tag}] 轮询超时 ({timeout}s)"
            if fail_soft:
                print(msg)
                return None
            raise Exception(msg)
        time.sleep(interval)
        mm.throw_exception_if_processing_interrupted()
        try:
            body = {"task_id": task_id, "model": model}
            if consumption_id:
                body["consumption_id"] = consumption_id
            if extra_body:
                body.update(extra_body)
            res = requests.post(EDIT_POLL_URL, headers=headers, json=body, verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[{tag}] ...{task_id[-8:]} HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else {})
            if not isinstance(inner, dict):
                inner = {}
            done, label = check_success(inner)
            failed, fail_label = check_failed(inner)
            print(f"[{tag}] ...{task_id[-8:]} status={label or fail_label or '(无状态)'} ({elapsed}s)")
            if done:
                url = pick_url(inner, data)
                if not url:
                    msg = f"{tag} 任务成功但无结果 URL"
                    if fail_soft:
                        print(msg)
                        return None
                    raise Exception(msg)
                return url
            if failed:
                err = inner.get("fail_reason") or inner.get("error") or fail_label
                msg = f"{tag} 任务失败: {err}"
                if fail_soft:
                    print(f"[{tag}] 失败: ...{task_id[-8:]} {err}")
                    return None
                raise Exception(msg)
        except Exception as e:
            msg = str(e)
            is_fatal = msg.startswith(f"[{tag}]") or msg.startswith(tag) or "超时" in msg
            if is_fatal:
                if fail_soft:
                    return None
                raise
            print(f"[{tag}] 轮询异常: {e}")
