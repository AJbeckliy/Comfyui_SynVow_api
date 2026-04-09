"""
SynVow Sora2 视频生成节点
"""
import requests
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import synvow_auth
from .video_common import (
    DIRECT_API_BASE, tensor_to_jpeg_bytes, parse_task_id,
    extract_video_url, download_video,
)

SORA2_MODEL_DEFAULT = "sora-2"
SORA2_MODEL_PRO = "sora2-优质"


def _tensor_to_b64(image_tensor):
    """tensor → 纯 base64 字符串（不含 data URI 前缀）"""
    b = tensor_to_jpeg_bytes(image_tensor)
    return base64.b64encode(b).decode() if b else None


def _submit_task(api_key, model, prompt, image_tensors=None, **extra):
    headers = synvow_auth.make_api_headers(api_key)
    payload = {"model": model, "prompt": prompt, **extra}
    if image_tensors:
        b64_list = [_tensor_to_b64(t) for t in image_tensors if t is not None]
        b64_list = [b for b in b64_list if b]
        if b64_list:
            payload["images"] = b64_list
    res = requests.post(f"{DIRECT_API_BASE}/api/models/video/generate",
                        headers=headers, json=payload, verify=False, timeout=60)
    if res.status_code != 200:
        raise Exception(f"提交失败 ({res.status_code}): {res.json()}")
    resp_data = res.json()
    task_id = parse_task_id(resp_data)
    consumption_id = resp_data.get("consumption_id") or ""
    return task_id, consumption_id


def _poll_sora2_sync(api_key, model, task_id, timeout=1200, interval=5, consumption_id=""):
    """通用同步轮询（POST /api/models/tasks），适用于所有 sora2 模型"""
    import time, requests as _req
    headers = synvow_auth.make_api_headers(api_key)
    url = f"{DIRECT_API_BASE}/api/models/tasks"
    start = time.time()
    count = 0
    while True:
        count += 1
        if time.time() - start > timeout:
            raise Exception(f"任务超时 ({timeout}秒)")
        try:
            res = _req.post(url, headers=headers,
                            json={k: v for k, v in {
                                "model": model,
                                "task_id": task_id,
                                "consumption_id": consumption_id or None,
                            }.items() if v is not None},
                            verify=False, timeout=30)
            data = res.json() if res.status_code == 200 else {"_http_error": res.status_code, "_body": res.text[:200]}
            # 服务端限流，退避等待
            if res.status_code in (429, 500, 503):
                time.sleep(10)
                continue
            outer = data if isinstance(data, dict) else {}
            # status 在顶层，output 在 data.output
            raw = (outer.get("status") or outer.get("task_status") or outer.get("state") or "")
            status = str(raw).upper()
            nested = outer.get("data") or {}
            video_url = (nested.get("output") or outer.get("output")
                         or outer.get("video_url") or outer.get("url") or "")
            finish_time = outer.get("finish_time", 0)
            print(f"⏳ [Sora2][{task_id[:8]}] 轮询 {count}: {raw or '(无状态)'}")
            # finish_time > 0 说明后台已完成，强制打印完整响应
            if status in ("SUCCESS", "SUCCEED", "COMPLETED", "DONE", "FINISH", "FINISHED"):
                return outer
            if video_url and status not in ("FAILURE", "FAILED", "ERROR", "NOT_START",
                                            "PENDING", "PROCESSING", "RUNNING", "QUEUED", ""):
                return outer
            if status in ("FAILURE", "FAILED", "ERROR"):
                raise Exception(f"任务失败: {outer.get('fail_reason') or 'Unknown'}")
        except Exception as e:
            if "任务失败" in str(e) or "超时" in str(e):
                raise
            print(f"[Sora2] 轮询异常: {e}")
        time.sleep(interval)


def _run_single(api_key, model, prompt, image_tensors, save_path, filename="", **extra):
    import time as _t
    short_prompt = (prompt or "")[:20].replace("\n", " ")
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            task_id, consumption_id = _submit_task(api_key, model, prompt, image_tensors, **extra)
        except Exception as e:
            reason = str(e)
            if attempt < max_retries and ("502" in reason or "502" in reason or "系统繁忙" in reason or "busy" in reason.lower()):
                print(f"[Sora2] 提交失败，30秒后重试 ({attempt}/{max_retries}): {reason[:80]}")
                _t.sleep(30)
                continue
            raise
        try:
            result = _poll_sora2_sync(api_key, model, task_id, consumption_id=consumption_id)
        except Exception as e:
            reason = str(e)
            if attempt < max_retries and ("系统繁忙" in reason or "busy" in reason.lower()):
                print(f"[Sora2] 系统繁忙，30秒后重试 ({attempt}/{max_retries})...")
                _t.sleep(30)
                continue
            raise
        url = extract_video_url(result)
        path = download_video(url, task_id, save_path, prefix="sora2", filename=filename) or ""
        return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


def _poll_only(api_key, model, task_id, save_path, filename="", stagger_delay=0):
    """仅轮询已提交的任务，stagger_delay 用于错开并发请求"""
    import time as _t
    if stagger_delay > 0:
        _t.sleep(stagger_delay)
    result = _poll_sora2_sync(api_key, model, task_id)
    url = extract_video_url(result)
    path = download_video(url, task_id, save_path, prefix="sora2", filename=filename) or ""
    return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


def _poll_batch_serial(api_key, model, task_list, save_path):
    """串行轮询批量任务：[(idx, task_id, filename), ...]，逐个完成，避免并发查询限流
    返回 {idx: result_dict}
    """
    import time as _t
    results = {}
    pending = list(task_list)  # [(idx, task_id, filename)]
    while pending:
        next_pending = []
        for idx, task_id, fname in pending:
            try:
                result = _poll_sora2_sync(api_key, model, task_id, timeout=1200, interval=5)
                url = extract_video_url(result)
                path = download_video(url, task_id, save_path, prefix="sora2", filename=fname) or ""
                results[idx] = {"success": True, "video_path": path, "video_url": url, "task_id": task_id}
            except Exception as e:
                print(f"[Sora2 Batch] 任务{idx} 失败: {e}")
                results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}
        pending = next_pending
    return results


def _batch_filenames(base_filename, count):
    """根据基础文件名生成批量文件名列表：base, base(1), base(2)..."""
    if not base_filename or not base_filename.strip():
        return [""] * count
    base = base_filename.strip()
    # 去掉 .mp4 后缀，download_video 会自动加
    if base.lower().endswith(".mp4"):
        base = base[:-4]
    names = [base]
    for i in range(1, count):
        names.append(f"{base}({i})")
    return names


def _collect_tensors(image_1, image_2, image_3, image_4):
    return [img for img in [image_1, image_2, image_3, image_4] if img is not None]


def _make_preview_result(path, video_url, task_info):
    """生成带内嵌预览的返回值"""
    import os, shutil, folder_paths as _fp
    gifs = []
    if path and os.path.isfile(path):
        out_dir = _fp.get_output_directory()
        fname = os.path.basename(path)
        preview_path = os.path.join(out_dir, fname)
        if os.path.normpath(path) != os.path.normpath(preview_path):
            shutil.copy2(path, preview_path)
        gifs.append({"filename": fname, "subfolder": "", "type": "output", "format": "video/mp4"})
    return {"ui": {"gifs": gifs}, "result": (path, video_url, task_info)}


# ---------------------------------------------------------------------------
# 默认模式节点（sora-2，duration: 10/15秒）
# ---------------------------------------------------------------------------

class SynVowSora2Video:
    FUNCTION = "generate_video"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Sora2 默认模式图生视频（duration: 10/15秒）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_1": ("IMAGE",),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "duration": (["10", "15"], {"default": "10"}),
                "hd": ("BOOLEAN", {"default": False}),
                "prompt": ("STRING", {"multiline": True, "default": "make animate"}),
            },
            "optional": {
                "image_2": ("IMAGE",), "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "private": ("BOOLEAN", {"default": True}),
                "watermark": ("BOOLEAN", {"default": False}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, image_1, aspect_ratio, duration, hd, prompt,
                       image_2=None, image_3=None, image_4=None,
                       private=True, watermark=False, filename="", save_path=""):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        images = _collect_tensors(image_1, image_2, image_3, image_4)
        try:
            r = _run_single(api_key, SORA2_MODEL_DEFAULT, prompt, images, save_path, filename=filename,
                            aspect_ratio=aspect_ratio, duration=duration,
                            hd=hd, private=private, watermark=watermark)
            info = json.dumps({"status": "SUCCESS", **r}, ensure_ascii=False)
            return _make_preview_result(r["video_path"], r["video_url"], info)
        except Exception as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 优质模式节点（sora2-优质，duration: 4/8/12秒）
# ---------------------------------------------------------------------------

class SynVowSora2Video_Pro:
    FUNCTION = "generate_video"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Sora2 优质模式图生视频（duration: 4/8/12秒）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_1": ("IMAGE",),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "duration": (["4", "8", "12"], {"default": "4"}),
                "hd": ("BOOLEAN", {"default": False}),
                "prompt": ("STRING", {"multiline": True, "default": "make animate"}),
            },
            "optional": {
                "image_2": ("IMAGE",), "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "private": ("BOOLEAN", {"default": True}),
                "watermark": ("BOOLEAN", {"default": False}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, image_1, aspect_ratio, duration, hd, prompt,
                       image_2=None, image_3=None, image_4=None,
                       private=True, watermark=False, filename="", save_path=""):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        images = _collect_tensors(image_1, image_2, image_3, image_4)
        try:
            r = _run_single(api_key, SORA2_MODEL_PRO, prompt, images, save_path, filename=filename,
                            aspect_ratio=aspect_ratio, duration=duration,
                            hd=hd, private=private, watermark=watermark)
            info = json.dumps({"status": "SUCCESS", **r}, ensure_ascii=False)
            return _make_preview_result(r["video_path"], r["video_url"], info)
        except Exception as e:
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 批量节点（默认模式）
# ---------------------------------------------------------------------------

class SynVowSora2Video_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Sora2 默认模式批量图生视频（duration: 10/15秒）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "duration": (["10", "15"], {"default": "10"}),
                "hd": ("BOOLEAN", {"default": False}),
                "批次数量": ("INT", {"default": 3, "min": 1, "max": 10}),
            },
            "optional": {
                "images_list1": ("IMAGE",), "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",), "images_list4": ("IMAGE",),
                "private": ("BOOLEAN", {"default": True}),
                "watermark": ("BOOLEAN", {"default": False}),
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

    def process_batch(self, prompts_list, aspect_ratio, duration, hd, 批次数量,
                      images_list1=None, images_list2=None, images_list3=None, images_list4=None,
                      private=None, watermark=None, filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ([""], [""], json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        aspect_ratio, duration = _u(aspect_ratio, "16:9"), _u(duration, "10")
        hd, max_concurrent = _u(hd, False), _u(批次数量, 3)
        private, watermark = _u(private, True), _u(watermark, False)
        filename, save_path = _u(filename, ""), _u(save_path, "")
        # 展平 prompts_list：INPUT_IS_LIST 可能把列表包一层，也可能是单字符串
        raw = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts = []
        for item in raw:
            if isinstance(item, list):
                prompts.extend([p for p in item if p and str(p).strip()])
            elif item and str(item).strip():
                prompts.append(str(item).strip())
        if not prompts:
            prompts = [""]
        all_lists = [images_list1 or [], images_list2 or [], images_list3 or [], images_list4 or []]
        results = [None] * len(prompts)
        filenames = _batch_filenames(filename, len(prompts))

        # 第一步：串行提交所有任务，避免 API 池并发限制
        import time as _time
        task_ids = []
        for i, prompt in enumerate(prompts):
            imgs = []
            for lst in all_lists:
                if not lst: continue
                img = lst[0] if len(lst) == 1 else (lst[i] if i < len(lst) else None)
                if img is not None:
                    imgs.append(img)
            try:
                task_id = _submit_task(api_key, SORA2_MODEL_DEFAULT, prompt, imgs,
                                       aspect_ratio=aspect_ratio, duration=duration,
                                       hd=hd, private=private, watermark=watermark)
                task_ids.append((i, task_id, filenames[i]))
                if i < len(prompts) - 1:
                    _time.sleep(2)  # 提交间隔2秒，避免限流
            except Exception as e:
                print(f"[Sora2 Batch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        # 第二步：并发轮询，每个任务错开10秒启动，避免同时打爆API
        with ThreadPoolExecutor(max_workers=min(max_concurrent, len(task_ids))) as pool:
            futures = {}
            for seq, (i, task_id, fname) in enumerate(task_ids):
                futures[pool.submit(_poll_only, api_key, SORA2_MODEL_DEFAULT, task_id, save_path, fname, seq * 10)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Sora2 Batch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"]); urls.append(r["video_url"])
            if r.get("success"): ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok, "failed": len(prompts) - ok}, ensure_ascii=False)

        # 批量预览
        import os, shutil, folder_paths as _fp
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
# 批量节点（优质模式）
# ---------------------------------------------------------------------------

class SynVowSora2Video_ProBatch:
    FUNCTION = "process_batch"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "SynVow Sora2 优质模式批量图生视频（duration: 4/8/12秒）"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "aspect_ratio": (["16:9", "9:16"], {"default": "16:9"}),
                "duration": (["4", "8", "12"], {"default": "4"}),
                "hd": ("BOOLEAN", {"default": False}),
                "批次数量": ("INT", {"default": 3, "min": 1, "max": 10}),
            },
            "optional": {
                "images_list1": ("IMAGE",), "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",), "images_list4": ("IMAGE",),
                "private": ("BOOLEAN", {"default": True}),
                "watermark": ("BOOLEAN", {"default": False}),
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

    def process_batch(self, prompts_list, aspect_ratio, duration, hd, 批次数量,
                      images_list1=None, images_list2=None, images_list3=None, images_list4=None,
                      private=None, watermark=None, filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return ([""], [""], json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        aspect_ratio, duration = _u(aspect_ratio, "16:9"), _u(duration, "4")
        hd, max_concurrent = _u(hd, False), _u(批次数量, 3)
        private, watermark = _u(private, True), _u(watermark, False)
        filename, save_path = _u(filename, ""), _u(save_path, "")
        raw = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts = []
        for item in raw:
            if isinstance(item, list):
                prompts.extend([p for p in item if p and str(p).strip()])
            elif item and str(item).strip():
                prompts.append(str(item).strip())
        if not prompts:
            prompts = [""]
        all_lists = [images_list1 or [], images_list2 or [], images_list3 or [], images_list4 or []]
        results = [None] * len(prompts)
        filenames = _batch_filenames(filename, len(prompts))

        # 第一步：串行提交所有任务，避免 API 池并发限制
        import time as _time
        task_ids = []
        for i, prompt in enumerate(prompts):
            imgs = []
            for lst in all_lists:
                if not lst: continue
                img = lst[0] if len(lst) == 1 else (lst[i] if i < len(lst) else None)
                if img is not None:
                    imgs.append(img)
            try:
                task_id = _submit_task(api_key, SORA2_MODEL_PRO, prompt, imgs,
                                       aspect_ratio=aspect_ratio, duration=duration,
                                       hd=hd, private=private, watermark=watermark)
                task_ids.append((i, task_id, filenames[i]))
                if i < len(prompts) - 1:
                    _time.sleep(2)
            except Exception as e:
                print(f"[Sora2 ProBatch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        # 第二步：并发轮询，每个任务错开10秒启动，避免同时打爆API
        with ThreadPoolExecutor(max_workers=min(max_concurrent, len(task_ids))) as pool:
            futures = {}
            for seq, (i, task_id, fname) in enumerate(task_ids):
                futures[pool.submit(_poll_only, api_key, SORA2_MODEL_PRO, task_id, save_path, fname, seq * 10)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Sora2 ProBatch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": "", "error": str(e)}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"]); urls.append(r["video_url"])
            if r.get("success"): ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok, "failed": len(prompts) - ok}, ensure_ascii=False)

        # 批量预览
        import os, shutil, folder_paths as _fp
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


NODE_CLASS_MAPPINGS = {
    "SynVowSora2Video": SynVowSora2Video,
    "SynVowSora2Video_Pro": SynVowSora2Video_Pro,
    "SynVowSora2Video_TBatch": SynVowSora2Video_TBatch,
    "SynVowSora2Video_ProBatch": SynVowSora2Video_ProBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSora2Video": "SynVow Sora2 视频生成",
    "SynVowSora2Video_Pro": "SynVow Sora2 优质视频生成",
    "SynVowSora2Video_TBatch": "SynVow Sora2 批量视频生成",
    "SynVowSora2Video_ProBatch": "SynVow Sora2 优质批量视频生成",
}
