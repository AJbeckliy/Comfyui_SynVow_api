# -*- coding: utf-8 -*-
"""
SynVow Veo3.1 视频生成节点 — 单节点，模式下拉切换默认/优质
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

# 模型 + 模式 → 实际 API 模型名
VEO31_MODEL_OPTIONS = ["veo3.1", "veo3.1-pro", "veo3.1-fast"]
VEO31_MODE_OPTIONS = ["默认", "优质"]
VEO31_MODEL_MAP = {
    ("veo3.1",      "默认"): "veo3.1-默认",
    ("veo3.1",      "优质"): "veo3.1-优质",
    ("veo3.1-pro",  "默认"): "veo3.1-pro-默认",
    ("veo3.1-pro",  "优质"): "veo3.1-pro-优质",
    ("veo3.1-fast", "默认"): "veo3.1-fast-默认",
    ("veo3.1-fast", "优质"): "veo3.1-fast-优质",
}


# ---------------------------------------------------------------------------
#  公共函数
# ---------------------------------------------------------------------------

def _submit_task(api_key, model, prompt, image_urls=None,
                 aspect_ratio="16:9", enhance_prompt=False):
    headers = synvow_auth.make_api_headers(api_key)
    payload = {"model": model, "prompt": prompt, "enhance_prompt": enhance_prompt}
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if image_urls:
        payload["images"] = image_urls
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = requests.post(f"{DIRECT_API_BASE}/api/models/video/generate",
                                headers=headers, json=payload, verify=False, timeout=120)
            if res.status_code != 200:
                raise Exception(f"提交失败 ({res.status_code}): {res.text[:200]}")
            resp_data = res.json()
            task_id = parse_task_id(resp_data)
            consumption_id = resp_data.get("consumption_id") or ""
            return task_id, consumption_id
        except Exception as e:
            print(f"[Veo3.1] 提交重试 {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise


def _poll_veo31(api_key, model, task_id, timeout=600, interval=5, consumption_id=""):
    headers = synvow_auth.make_api_headers(api_key)
    url = f"{DIRECT_API_BASE}/api/models/tasks"
    start = time.time()
    count = 0
    while True:
        count += 1
        if time.time() - start > timeout:
            raise Exception(f"Veo3.1 超时 ({timeout}秒)")
        try:
            res = requests.post(url, headers=headers,
                                json={k: v for k, v in {
                                    "model": model,
                                    "task_id": task_id,
                                    "consumption_id": consumption_id or None,
                                }.items() if v is not None},
                                verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[Veo3.1] 轮询 {count}: HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            outer = data if isinstance(data, dict) else {}
            raw = outer.get("status") or outer.get("task_status") or ""
            status = str(raw).upper()
            print(f"⏳ [Veo3.1][{task_id[:8]}] 轮询 {count}: {raw or '(无状态)'}")
            if status in ("SUCCESS", "SUCCEED", "COMPLETED", "DONE", "FINISH", "FINISHED"):
                return outer
            if status in ("FAILURE", "FAILED", "ERROR"):
                raise Exception(f"任务失败: {outer.get('fail_reason') or 'Unknown'}")
        except Exception as e:
            if "任务失败" in str(e) or "超时" in str(e):
                raise
            print(f"[Veo3.1] 轮询异常: {e}")
        time.sleep(interval)


def _collect_images(api_key, image_1, image_2):
    tensors = [t for t in [image_1, image_2] if t is not None]
    if not tensors:
        return None
    img_bytes = [tensor_to_jpeg_bytes(t) for t in tensors]
    urls = upload_images(api_key, img_bytes)
    return urls


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


def _poll_only(api_key, model, task_id, save_path, filename="", stagger_delay=0):
    if stagger_delay > 0:
        time.sleep(stagger_delay)
    result = _poll_veo31(api_key, model, task_id)
    url = extract_video_url(result)
    path = download_video(url, task_id, save_path, prefix="veo31", filename=filename) or ""
    return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


def _batch_filenames(base, count):
    if not base or not base.strip():
        return [""] * count
    base = base.strip()
    if base.lower().endswith(".mp4"):
        base = base[:-4]
    return [base] + [f"{base}({i})" for i in range(1, count)]


# ---------------------------------------------------------------------------
#  单节点：模型 + 模式 下拉切换
# ---------------------------------------------------------------------------

class SynVowVeo31Video:
    FUNCTION = "generate_video"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Veo3.1 视频生成（模型+模式下拉切换默认/优质）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (VEO31_MODEL_OPTIONS, {"default": "veo3.1"}),
                "模式": (VEO31_MODE_OPTIONS, {"default": "默认"}),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "enhance_prompt": ("BOOLEAN", {"default": False,
                    "tooltip": "自动优化提示词"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, 模型, 模式, system_prompt, user_prompt, aspect_ratio, enhance_prompt, seed,
                       image_1=None, image_2=None, filename="", save_path=""):
        model_name = VEO31_MODEL_MAP.get((模型, 模式), "veo3.1-默认")
        prompt = user_prompt.strip() if user_prompt and user_prompt.strip() else system_prompt.strip()
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        try:
            image_urls = _collect_images(api_key, image_1, image_2)
            task_id, consumption_id = _submit_task(api_key, model_name, prompt, image_urls, aspect_ratio, enhance_prompt)
            result = _poll_veo31(api_key, model_name, task_id, consumption_id=consumption_id)
            url = extract_video_url(result)
            path = download_video(url, task_id, save_path, prefix="veo31", filename=filename) or ""
            info = json.dumps({"status": "SUCCESS", "task_id": task_id, "model": model_name,
                               "video_url": url, "video_path": path}, ensure_ascii=False)
            return _make_preview(path, url, info)
        except Exception as e:
            print(f"[Veo3.1] Error: {e}")
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
#  批量节点：模型 + 模式 下拉切换，串行提交 + 并发轮询
# ---------------------------------------------------------------------------

class SynVowVeo31VideoBatch:
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Veo3.1 批量视频生成（模型+模式下拉切换默认/优质）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "模型": (VEO31_MODEL_OPTIONS, {"default": "veo3.1"}),
                "模式": (VEO31_MODE_OPTIONS, {"default": "默认"}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "enhance_prompt": ("BOOLEAN", {"default": False}),
                "批次数量": ("INT", {"default": 3, "min": 1, "max": 10}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
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

    def process_batch(self, prompts_list, 模型, 模式, aspect_ratio, enhance_prompt, 批次数量,
                      image_1=None, image_2=None, filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ([""], [""], json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        model_key = _u(模型, "veo3.1")
        mode_key = _u(模式, "默认")
        model_name = VEO31_MODEL_MAP.get((model_key, mode_key), "veo3.1-默认")
        aspect_ratio = _u(aspect_ratio, "16:9")
        enhance_prompt = _u(enhance_prompt, False)
        max_concurrent = _u(批次数量, 3)
        filename = _u(filename, "")
        save_path = _u(save_path, "")

        # 收集图片（所有批次共用）
        image_urls = None
        img1, img2 = _u(image_1), _u(image_2)
        if img1 is not None or img2 is not None:
            image_urls = _collect_images(api_key, img1, img2)

        # 展平提示词
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

        # 串行提交
        task_ids = []
        for i, prompt in enumerate(prompts):
            try:
                task_id, _ = _submit_task(api_key, model_name, prompt, image_urls, aspect_ratio, enhance_prompt)
                task_ids.append((i, task_id, filenames[i]))
                if i < len(prompts) - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"[Veo3.1 Batch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        # 并发轮询，错开10秒
        with ThreadPoolExecutor(max_workers=min(max_concurrent, max(len(task_ids), 1))) as pool:
            futures = {}
            for seq, (i, task_id, fname) in enumerate(task_ids):
                futures[pool.submit(_poll_only, api_key, model_name, task_id, save_path, fname, seq * 10)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Veo3.1 Batch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"])
            urls.append(r["video_url"])
            if r.get("success"):
                ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok, "failed": len(prompts) - ok}, ensure_ascii=False)

        # 批量预览
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

NODE_CLASS_MAPPINGS = {
    "SynVowVeo31Video": SynVowVeo31Video,
    "SynVowVeo31VideoBatch": SynVowVeo31VideoBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVeo31Video": "SynVow Veo3.1 视频生成",
    "SynVowVeo31VideoBatch": "SynVow Veo3.1 \u6279\u91cf视频生成",
}
