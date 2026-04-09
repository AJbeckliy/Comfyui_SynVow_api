# -*- coding: utf-8 -*-
"""
SynVow Seedance 2.0 视频生成节点
"""
import json
import time
import os
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import synvow_auth
from .video_common import (
    DIRECT_API_BASE, tensor_to_jpeg_bytes, parse_task_id,
    extract_video_url, download_video, upload_images,
)

SEEDANCE2_MODEL = "即梦2"

SEEDANCE2_ASPECT_OPTIONS = ["16:9", "9:16", "1:1"]
SEEDANCE2_DURATION_OPTIONS = ["5", "10"]
SEEDANCE2_RESOLUTION_OPTIONS = ["720p", "1080p"]


# ---------------------------------------------------------------------------
#  公共函数
# ---------------------------------------------------------------------------

def _submit_task(api_key, prompt, image_urls=None, aspect_ratio="16:9",
                 duration="5", resolution="720p"):
    headers = synvow_auth.make_api_headers(api_key)
    content = [{"type": "text", "text": prompt}]
    if image_urls:
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})
    payload = {
        "model": SEEDANCE2_MODEL,
        "content": content,
        "aspect_ratio": aspect_ratio,
        "duration": int(duration),
        "resolution": resolution,
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.post(f"{DIRECT_API_BASE}/api/models/video/generate",
                                headers=headers, json=payload, verify=False, timeout=120)
            if res.status_code != 200:
                raise Exception(f"提交失败 ({res.status_code}): {res.text[:200]}")
            resp_data = res.json()
            task_id = (
                resp_data.get("task_id")
                or (resp_data.get("data") or {}).get("task_id")
                or resp_data.get("id")
                or (resp_data.get("data") or {}).get("id")
            )
            if not task_id:
                raise Exception(f"响应中无 task_id: {resp_data}")
            consumption_id = resp_data.get("consumption_id") or ""
            return task_id, consumption_id
        except Exception as e:
            print(f"[Seedance2] 提交重试 {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise


def _poll_seedance2(api_key, task_id, timeout=600, interval=5, consumption_id=""):
    headers = synvow_auth.make_api_headers(api_key)
    url = f"{DIRECT_API_BASE}/api/models/tasks"
    start = time.time()
    count = 0
    while True:
        count += 1
        if time.time() - start > timeout:
            raise Exception(f"Seedance2 超时 ({timeout}秒)")
        try:
            res = requests.post(url, headers=headers,
                                json={k: v for k, v in {
                                    "model": SEEDANCE2_MODEL,
                                    "id": task_id,
                                    "consumption_id": consumption_id or None,
                                }.items() if v is not None},
                                verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[Seedance2] 轮询 {count}: HTTP {res.status_code}, 退避3秒")
                time.sleep(3)
                continue
            data = res.json() if res.status_code == 200 else {}
            outer = data if isinstance(data, dict) else {}
            raw = outer.get("status") or outer.get("task_status") or ""
            status = str(raw).upper()
            print(f"⏳ [Seedance2][{task_id[:8]}] 轮询 {count}: {raw or '(无状态)'}")
            if status in ("SUCCESS", "SUCCEED", "COMPLETED", "DONE", "FINISH", "FINISHED", "SUCCEEDED"):
                return outer
            if status in ("FAILURE", "FAILED", "ERROR"):
                err = outer.get("fail_reason") or outer.get("error", {}).get("message") or "Unknown"
                raise Exception(f"任务失败: {err}")
        except Exception as e:
            if "任务失败" in str(e) or "超时" in str(e):
                raise
            print(f"[Seedance2] 轮询异常: {e}")
        time.sleep(interval)


def _extract_seedance2_url(result_data):
    """从即梦2轮询结果中提取视频 URL（content.video_url）"""
    if isinstance(result_data, dict):
        content = result_data.get("content")
        if isinstance(content, dict) and content.get("video_url"):
            return content["video_url"]
        if result_data.get("video_url"):
            return result_data["video_url"]
        if result_data.get("output"):
            return result_data["output"]
    raise Exception(f"响应中无视频 URL: {result_data}")


def _make_preview(path, video_url, task_info):
    import folder_paths as _fp
    gifs = []
    if path and os.path.isfile(path):
        out_dir = _fp.get_output_directory()
        fname = os.path.basename(path)
        preview_path = os.path.join(out_dir, fname)
        if os.path.normpath(path) != os.path.normpath(preview_path):
            shutil.copy2(path, preview_path)
        gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
    return {"ui": {"gifs": gifs}, "result": (path, video_url, task_info)}


def _poll_only(api_key, task_id, save_path, filename="", stagger_delay=0):
    if stagger_delay > 0:
        time.sleep(stagger_delay)
    result = _poll_seedance2(api_key, task_id)
    url = _extract_seedance2_url(result)
    path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename) or ""
    return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


def _batch_filenames(base, count):
    if not base or not base.strip():
        return [""] * count
    base = base.strip()
    if base.lower().endswith(".mp4"):
        base = base[:-4]
    return [f"{base}_{i+1:03d}.mp4" for i in range(count)]


# ---------------------------------------------------------------------------
#  单任务节点
# ---------------------------------------------------------------------------

class SynVowSeedance2Video:
    FUNCTION = "generate_video"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Seedance 2.0 视频生成"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "a beautiful landscape"}),
                "aspect_ratio": (SEEDANCE2_ASPECT_OPTIONS, {"default": "16:9"}),
                "duration": (SEEDANCE2_DURATION_OPTIONS, {"default": "5"}),
                "resolution": (SEEDANCE2_RESOLUTION_OPTIONS, {"default": "720p"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, prompt, aspect_ratio, duration, resolution, seed,
                       image_1=None, image_2=None, filename="", save_path=""):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        image_urls = None
        tensors = [t for t in [image_1, image_2] if t is not None]
        if tensors:
            img_bytes = [tensor_to_jpeg_bytes(t) for t in tensors]
            image_urls = upload_images(api_key, img_bytes)

        try:
            task_id, consumption_id = _submit_task(api_key, prompt, image_urls,
                                                   aspect_ratio, duration, resolution)
            result = _poll_seedance2(api_key, task_id, consumption_id=consumption_id)
            url = _extract_seedance2_url(result)
            path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename) or ""
            info = json.dumps({"status": "SUCCESS", "task_id": task_id,
                               "model": SEEDANCE2_MODEL, "video_url": url,
                               "video_path": path}, ensure_ascii=False)
            return _make_preview(path, url, info)
        except Exception as e:
            print(f"[Seedance2] Error: {e}")
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
#  批量节点
# ---------------------------------------------------------------------------

class SynVowSeedance2VideoBatch:
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Seedance 2.0 批量视频生成"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "aspect_ratio": (SEEDANCE2_ASPECT_OPTIONS, {"default": "16:9"}),
                "duration": (SEEDANCE2_DURATION_OPTIONS, {"default": "5"}),
                "resolution": (SEEDANCE2_RESOLUTION_OPTIONS, {"default": "720p"}),
                "批次数量": ("INT", {"default": 3, "min": 1, "max": 10}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_paths", "video_urls", "batch_info")
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, True, False)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def process_batch(self, prompts_list, aspect_ratio, duration, resolution, 批次数量,
                      image_1=None, image_2=None, filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ([""], [""], json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        aspect_ratio = _u(aspect_ratio, "16:9")
        duration = _u(duration, "5")
        resolution = _u(resolution, "720p")
        max_concurrent = _u(批次数量, 3)
        filename = _u(filename, "")
        save_path = _u(save_path, "")

        image_urls = None
        img1, img2 = _u(image_1), _u(image_2)
        tensors = [t for t in [img1, img2] if t is not None]
        if tensors:
            img_bytes = [tensor_to_jpeg_bytes(t) for t in tensors]
            image_urls = upload_images(api_key, img_bytes)

        raw = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts = []
        for item in raw:
            if isinstance(item, list):
                prompts.extend([p for p in item if p and str(p).strip()])
            elif item and str(item).strip():
                prompts.append(str(item).strip())
        if not prompts:
            prompts = [""]
        filenames = _batch_filenames(filename, len(prompts))
        results = [None] * len(prompts)

        task_ids = []
        for i, prompt in enumerate(prompts):
            try:
                task_id, _ = _submit_task(api_key, prompt, image_urls,
                                          aspect_ratio, duration, resolution)
                task_ids.append((i, task_id, filenames[i]))
                if i < len(prompts) - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"[Seedance2 Batch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        with ThreadPoolExecutor(max_workers=min(max_concurrent, max(len(task_ids), 1))) as pool:
            futures = {}
            for seq, (i, task_id, fname) in enumerate(task_ids):
                futures[pool.submit(_poll_only, api_key, task_id, save_path, fname, seq * 10)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Seedance2 Batch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"])
            urls.append(r["video_url"])
            if r.get("success"):
                ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok,
                           "failed": len(prompts) - ok}, ensure_ascii=False)

        import folder_paths as _fp
        gifs = []
        out_dir = _fp.get_output_directory()
        for p in paths:
            if p and os.path.isfile(p):
                fname = os.path.basename(p)
                preview_path = os.path.join(out_dir, fname)
                if os.path.normpath(p) != os.path.normpath(preview_path):
                    shutil.copy2(p, preview_path)
                gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
        return {"ui": {"gifs": gifs}, "result": (paths, urls, info)}


# ---------------------------------------------------------------------------
#  节点注册
# ---------------------------------------------------------------------------

# 暂时禁用，待优化后重新启用
# NODE_CLASS_MAPPINGS = {
#     "SynVowSeedance2Video": SynVowSeedance2Video,
#     "SynVowSeedance2VideoBatch": SynVowSeedance2VideoBatch,
# }
# NODE_DISPLAY_NAME_MAPPINGS = {
#     "SynVowSeedance2Video": "SynVow Seedance2.0 视频生成",
#     "SynVowSeedance2VideoBatch": "SynVow Seedance2.0 批量视频生成",
# }
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
