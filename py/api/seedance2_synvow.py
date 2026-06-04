# -*- coding: utf-8 -*-
"""
SynVow Seedance 2.0 视频生成节点
"""
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import synvow_auth
from .media_common import (
    DIRECT_API_BASE, tensor_to_jpeg_bytes, download_video,
    upload_images,
)

SEEDANCE2_SUBMIT_URL = f"{DIRECT_API_BASE}/api/models/video/generate"
SEEDANCE2_POLL_URL = f"{DIRECT_API_BASE}/api/models/tasks"

MODEL_OPTIONS = ["seedance2.0"]
RATIO_OPTIONS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
DURATION_OPTIONS = ["5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"]
RESOLUTION_OPTIONS = ["720p"]

_RESOLUTION_TO_MODEL = {
    "720p": "seedance_2_720p",
}


def _build_files(api_key, image_urls=None):
    files = []
    if image_urls:
        for u in image_urls:
            files.append({"url": u, "type": "image"})
    return files or None


def _submit_task(api_key, prompt, model, ratio, duration, resolution, files=None):
    headers = synvow_auth.make_api_headers(api_key)
    payload = {
        "prompt": prompt,
        "model": model,
        "ratio": ratio,
        "duration": str(duration),
        "resolution": resolution,
    }
    if files:
        payload["files"] = files
    print(f"[Seedance2] 提交: model={payload.get('model')} ratio={payload.get('ratio')} duration={payload.get('duration')} resolution={payload.get('resolution')}")
    res = requests.post(SEEDANCE2_SUBMIT_URL + "?async=true", headers=headers, json=payload, verify=False, timeout=120)
    if not res.text.strip():
        raise Exception(f"提交返回为空 ({res.status_code})")
    resp = res.json()
    if res.status_code == 401:
        raise RuntimeError("API Key 无效或已过期，请重新登录")
    if res.status_code not in (200, 202):
        raise Exception(f"提交失败 ({res.status_code}): {resp.get('message', res.text[:200])}")
    task_id = (resp.get("task_id") or resp.get("data", {}).get("task_id") or
               resp.get("data", {}).get("data", {}).get("task_id") or
               resp.get("data", {}).get("sourceData", {}).get("task_id") or "")
    if not task_id:
        raise Exception(f"响应中无 task_id: {str(resp)[:200]}")
    consumption_id = resp.get("consumption_id") or resp.get("data", {}).get("consumption_id") or ""
    print(f"[Seedance2] task_id=...{task_id[-8:]}")
    return task_id, consumption_id


def _poll_seedance2(api_key, task_id, model, timeout=1800, interval=5, consumption_id=""):
    import comfy.model_management as mm
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            raise Exception(f"[Seedance2] 轮询超时 ({timeout}s)")
        time.sleep(interval)
        mm.throw_exception_if_processing_interrupted()
        try:
            body = {"task_id": task_id, "model": model}
            if consumption_id:
                body["consumption_id"] = consumption_id
            res = requests.post(SEEDANCE2_POLL_URL, headers=headers, json=body, verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[Seedance2] ...{task_id[-8:]} HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            inner = data.get("data") or data
            status = str(inner.get("status") or inner.get("task_status") or "").upper()
            elapsed = int(time.time() - start)
            print(f"[Seedance2] ...{task_id[-8:]} status={status or '(无状态)'} ({elapsed}s)")
            if status in ("SUCCESS", "SUCCEED", "SUCCEEDED", "COMPLETED", "DONE", "FINISH", "FINISHED"):
                return inner
            if status in ("FAILURE", "FAILED", "ERROR"):
                err = inner.get("fail_reason") or str(inner.get("error", "Unknown"))
                print(f"[Seedance2] 失败: ...{task_id[-8:]} {err}")
                raise Exception(f"任务失败: {err}")
        except Exception as e:
            if "任务失败" in str(e) or "超时" in str(e):
                raise
            print(f"[Seedance2] 轮询异常: {e}")


def _extract_video_url(result):
    if isinstance(result, dict):
        for key in ["url", "video_url", "video"]:
            if isinstance(result.get(key), str) and result[key].startswith("http"):
                return result[key]
        for key in ["data", "result", "output", "sourceData", "task_result", "videos"]:
            found = _extract_video_url(result.get(key)) if isinstance(result.get(key), (dict, list)) else ""
            if found:
                return found
    if isinstance(result, list):
        for item in result:
            found = _extract_video_url(item)
            if found:
                return found
    return ""


def _download_video_with_retry(url, task_id, save_path, filename="", retries=3):
    short = f"...{url[-24:]}" if len(url) > 24 else url
    print(f"[Seedance2] 开始下载视频: {short}")
    for attempt in range(retries):
        try:
            path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename)
            if path:
                print(f"[Seedance2] 下载成功 ({attempt+1}/{retries}): {short} -> {path}")
                return path
            raise Exception("download_video 返回空路径")
        except Exception as e:
            print(f"[Seedance2] 下载失败 ({attempt+1}/{retries}): {short} 错误={e}")
            if attempt < retries - 1:
                wait = 3 * (attempt + 1)
                print(f"[Seedance2] {wait}s 后重试...")
                time.sleep(wait)
    print(f"[Seedance2] {retries}次重试均失败，返回空路径: {short}")
    return ""


def _poll_only(api_key, task_id, model, save_path, filename="", stagger_delay=0, consumption_id=""):
    if stagger_delay > 0:
        time.sleep(stagger_delay)
    result = _poll_seedance2(api_key, task_id, model, consumption_id=consumption_id)
    url = _extract_video_url(result)
    if not url:
        raise Exception(f"[Seedance2] 任务成功但无视频 URL: {result}")
    path = _download_video_with_retry(url, task_id, save_path, filename=filename)
    return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


class SynVowSeedance2Video:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.0 视频生成"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "模型": (MODEL_OPTIONS, {"default": "seedance2.0"}),
                "ratio": (RATIO_OPTIONS, {"default": "adaptive"}),
                "duration": (DURATION_OPTIONS, {"default": "10"}),
                "resolution": (RESOLUTION_OPTIONS, {"default": "720p"}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
                "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def generate_video(self, prompt, 模型, ratio, duration, resolution,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None, image_8=None,
                       filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        model = _RESOLUTION_TO_MODEL.get(resolution, "seedance_2_720p")

        tensors = [t for t in [image_1, image_2, image_3, image_4,
                               image_5, image_6, image_7, image_8] if t is not None]
        image_urls = upload_images(api_key, [tensor_to_jpeg_bytes(t) for t in tensors]) if tensors else None

        files = _build_files(api_key, image_urls=image_urls)

        try:
            task_id, consumption_id = _submit_task(api_key, prompt, model, ratio, duration, resolution, files)
            result = _poll_seedance2(api_key, task_id, model, consumption_id=consumption_id)
            url = _extract_video_url(result)
            if not url:
                raise Exception(f"任务成功但无视频 URL: {result}")
            path = _download_video_with_retry(url, task_id, save_path, filename=filename)
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": model, "video_url": url, "video_path": path,
            }, ensure_ascii=False)
            try:
                import server
                server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
            except Exception:
                pass
            return (path, url, info)
        except Exception as e:
            print(f"[Seedance2] Error: {e}")
            try:
                import server
                server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
            except Exception:
                pass
            return ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


class SynVowSeedance2VideoBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.0 批量视频生成"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "模型": (MODEL_OPTIONS, {"default": "seedance2.0"}),
                "ratio": (RATIO_OPTIONS, {"default": "adaptive"}),
                "duration": (DURATION_OPTIONS, {"default": "10"}),
                "resolution": (RESOLUTION_OPTIONS, {"default": "720p"}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
                "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",),
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

    def process_batch(self, prompts_list, 模型, ratio, duration, resolution,
                      image_1=None, image_2=None, image_3=None, image_4=None,
                      image_5=None, image_6=None, image_7=None, image_8=None,
                      filename=None, save_path=None):
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        ratio, duration, resolution = _u(ratio, "adaptive"), _u(duration, "5"), _u(resolution, "720p")
        model = _RESOLUTION_TO_MODEL.get(resolution, "seedance_2_720p")
        filename, save_path = _u(filename, ""), _u(save_path, "")

        api_key = synvow_auth.read_api_key()

        tensors = [t for t in [_u(image_1), _u(image_2), _u(image_3), _u(image_4),
                               _u(image_5), _u(image_6), _u(image_7), _u(image_8)] if t is not None]
        image_urls = upload_images(api_key, [tensor_to_jpeg_bytes(t) for t in tensors]) if tensors else None

        files = _build_files(api_key, image_urls=image_urls)

        raw = prompts_list if isinstance(prompts_list, list) else [prompts_list]
        prompts = []
        for item in raw:
            if isinstance(item, list):
                prompts.extend([str(p).strip() for p in item if p and str(p).strip()])
            elif item and str(item).strip():
                prompts.append(str(item).strip())
        if not prompts:
            prompts = [""]

        results = [None] * len(prompts)
        task_ids = []
        for i, prompt in enumerate(prompts):
            try:
                task_id, consumption_id = _submit_task(api_key, prompt, model, ratio, duration, resolution, files)
                task_ids.append((i, task_id, consumption_id))
                if i < len(prompts) - 1:
                    time.sleep(1)
            except Exception as e:
                print(f"[Seedance2 Batch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": ""}

        with ThreadPoolExecutor(max_workers=max(len(task_ids), 1)) as pool:
            futures = {}
            for seq, (i, task_id, consumption_id) in enumerate(task_ids):
                fname = filename if not filename else (filename if len(prompts) == 1 else f"{filename}_{i+1:03d}")
                futures[pool.submit(_poll_only, api_key, task_id, model, save_path, fname,
                                    seq * 5, consumption_id)] = i
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    results[idx] = f.result()
                except Exception as e:
                    print(f"[Seedance2 Batch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": ""}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r["video_path"])
            urls.append(r["video_url"])
            if r.get("success"):
                ok += 1
        info = json.dumps({"total": len(prompts), "successful": ok, "failed": len(prompts) - ok}, ensure_ascii=False)
        print(f"[Seedance2 Batch] 完成: {ok}/{len(prompts)} 成功")
        try:
            import server
            server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
        except Exception:
            pass
        return (paths, urls, info)


NODE_CLASS_MAPPINGS = {
    "SynVowSeedance2Video": SynVowSeedance2Video,
    "SynVowSeedance2VideoBatch": SynVowSeedance2VideoBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSeedance2Video": "SynVow Seedance2.0 视频生成 (720P)",
    "SynVowSeedance2VideoBatch": "SynVow Seedance2.0 批量视频生成 (720P)",
}
