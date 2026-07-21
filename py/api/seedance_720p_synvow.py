# -*- coding: utf-8 -*-
"""
SynVow Seedance 2.0 视频生成 (720P)

旧接口：POST /api/models/video/generate ，实际模型 seedance_2_720p。
与 SynVow Seedance（image/edit 全能/mini/face 等）不是同一条链路。
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from . import synvow_auth
from .media_common import (
    DIRECT_API_BASE,
    as_comfy_video,
    download_video,
    is_changed_by_inputs,
    parse_task_id,
    poll_edit_task,
    upload_image,
)

_SUBMIT_URL = f"{DIRECT_API_BASE}/api/models/video/generate"
_MODEL_UI = "seedance2.0"
_API_MODEL = "seedance_2_720p"
_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
_DURATIONS = [str(i) for i in range(5, 16)]
_RESOLUTIONS = ["720p"]
_TAG = "Seedance720P"


def _build_files(image_urls):
    if not image_urls:
        return None
    return [{"url": u, "type": "image"} for u in image_urls]


def _submit(api_key, prompt, ratio, duration, resolution, files=None):
    headers = synvow_auth.make_api_headers(api_key)
    payload = {
        "prompt": prompt,
        "model": _API_MODEL,
        "ratio": ratio,
        "duration": str(duration),
        "resolution": resolution if resolution in _RESOLUTIONS else "720p",
    }
    if files:
        payload["files"] = files
    print(
        f"[{_TAG}] 提交: model={_API_MODEL} ratio={payload['ratio']} "
        f"duration={payload['duration']} resolution={payload['resolution']} "
        f"url={_SUBMIT_URL}"
    )
    res = requests.post(
        _SUBMIT_URL, headers=headers, params={"async": "true"},
        json=payload, verify=False, timeout=120,
    )
    if not res.text.strip():
        raise Exception(f"提交返回为空 ({res.status_code})")
    data = res.json()
    if res.status_code == 401:
        raise RuntimeError("API Key 无效或已过期，请重新登录")
    if res.status_code not in (200, 202):
        raise Exception(f"提交失败 ({res.status_code}): {data.get('message') or str(data)[:200]}")
    task_id = parse_task_id(data)
    if not task_id:
        # 兼容旧响应字段
        payload_data = data.get("data") if isinstance(data.get("data"), dict) else {}
        task_id = (
            data.get("task_id")
            or payload_data.get("task_id")
            or (payload_data.get("data") or {}).get("task_id")
            or (payload_data.get("sourceData") or {}).get("task_id")
            or ""
        )
    if not task_id:
        raise Exception(f"{_TAG} 响应中无 task_id: {str(data)[:200]}")
    consumption_id = data.get("consumption_id") or (data.get("data") or {}).get("consumption_id") or ""
    print(f"[{_TAG}] task_id=...{str(task_id)[-8:]}")
    return str(task_id), str(consumption_id)


def _collect_image_urls(api_key, tensors):
    return [upload_image(api_key, t) for t in (tensors or []) if t is not None]


def _run_once(api_key, prompt, ratio, duration, resolution, tensors, save_path="", filename=""):
    image_urls = _collect_image_urls(api_key, tensors)
    files = _build_files(image_urls)
    task_id, consumption_id = _submit(api_key, prompt, ratio, duration, resolution, files)
    url = poll_edit_task(api_key, task_id, _API_MODEL, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename) or ""
    return path, url, task_id


def _poll_and_download(api_key, task_id, save_path, filename="", stagger_delay=0, consumption_id=""):
    if stagger_delay > 0:
        time.sleep(stagger_delay)
    url = poll_edit_task(api_key, task_id, _API_MODEL, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename) or ""
    return {"success": True, "video_path": path, "video_url": url, "task_id": task_id}


class SynVowSeedance2Video:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.0 视频生成 (720P，旧 video/generate 接口)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "模型": ([_MODEL_UI], {"default": _MODEL_UI}),
                "ratio": (_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "10"}),
                "resolution": (_RESOLUTIONS, {"default": "720p"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
                "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video", "video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, 模型, ratio, duration, resolution, seed=0,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None, image_8=None,
                       filename="", save_path=""):
        del 模型  # UI 展示用；实际提交固定 seedance_2_720p
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4,
                               image_5, image_6, image_7, image_8] if t is not None]
        try:
            path, url, task_id = _run_once(
                api_key, prompt, ratio, duration, resolution, tensors, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": _API_MODEL, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            synvow_auth.refresh_balance()
            return (as_comfy_video(path), path, url, info)
        except Exception as e:
            print(f"[{_TAG}] Error: {e}")
            synvow_auth.refresh_balance()
            return (
                as_comfy_video(""), "", "",
                json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            )


class SynVowSeedance2VideoBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.0 批量视频生成 (720P，旧 video/generate 接口)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "模型": ([_MODEL_UI], {"default": _MODEL_UI}),
                "ratio": (_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "10"}),
                "resolution": (_RESOLUTIONS, {"default": "720p"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",),
                "image_3": ("IMAGE",), "image_4": ("IMAGE",),
                "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_paths", "video_urls", "batch_info")
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, True, False)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def process_batch(self, prompts_list, 模型, ratio, duration, resolution, seed=0,
                      image_1=None, image_2=None, image_3=None, image_4=None,
                      image_5=None, image_6=None, image_7=None, image_8=None,
                      filename=None, save_path=None):
        del 模型, seed
        _u = lambda v, d=None: v[0] if isinstance(v, list) and v else (v if v is not None else d)
        ratio = _u(ratio, "adaptive")
        duration = _u(duration, "10")
        resolution = _u(resolution, "720p")
        filename, save_path = _u(filename, ""), _u(save_path, "")

        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [
            _u(image_1), _u(image_2), _u(image_3), _u(image_4),
            _u(image_5), _u(image_6), _u(image_7), _u(image_8),
        ] if t is not None]
        files = _build_files(_collect_image_urls(api_key, tensors))

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
                task_id, consumption_id = _submit(api_key, prompt, ratio, duration, resolution, files)
                task_ids.append((i, task_id, consumption_id))
                if i < len(prompts) - 1:
                    time.sleep(1)
            except Exception as e:
                print(f"[{_TAG} Batch] 任务{i} 提交失败: {e}")
                results[i] = {"success": False, "video_path": "", "video_url": ""}

        with ThreadPoolExecutor(max_workers=max(len(task_ids), 1)) as pool:
            futures = {}
            for seq, (i, task_id, consumption_id) in enumerate(task_ids):
                fname = filename if not filename else (
                    filename if len(prompts) == 1 else f"{filename}_{i + 1:03d}"
                )
                futures[pool.submit(
                    _poll_and_download, api_key, task_id, save_path, fname,
                    seq * 5, consumption_id,
                )] = i
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    results[idx] = fut.result()
                except Exception as e:
                    print(f"[{_TAG} Batch] 任务{idx} 失败: {e}")
                    results[idx] = {"success": False, "video_path": "", "video_url": ""}

        paths, urls, ok = [], [], 0
        for r in results:
            r = r or {"video_path": "", "video_url": "", "success": False}
            paths.append(r.get("video_path") or "")
            urls.append(r.get("video_url") or "")
            if r.get("success"):
                ok += 1
        info = json.dumps(
            {"total": len(prompts), "successful": ok, "failed": len(prompts) - ok, "model": _API_MODEL},
            ensure_ascii=False,
        )
        print(f"[{_TAG} Batch] 完成: {ok}/{len(prompts)} 成功")
        synvow_auth.refresh_balance()
        return (paths, urls, info)


NODE_CLASS_MAPPINGS = {
    "SynVowSeedance2Video": SynVowSeedance2Video,
    "SynVowSeedance2VideoBatch": SynVowSeedance2VideoBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSeedance2Video": "SynVow Seedance2.0 视频生成 (720P)",
    "SynVowSeedance2VideoBatch": "SynVow Seedance2.0 批量视频生成 (720P)",
}
