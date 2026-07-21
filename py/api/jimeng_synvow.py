# -*- coding: utf-8 -*-
"""
SynVow 即梦 图像生成节点

对齐 SynMew jimeng：
提交 /api/models/image/edit，轮询 state + result_url。
payload: { model, prompt, params: { web_search, aspect_ratio, size, images } }
"""
import concurrent.futures
import io
import random as _random
import time

import comfy.utils
import numpy as np
import requests
import torch
from PIL import Image

from . import synvow_auth
from .media_common import (
    is_changed_by_inputs as _is_changed,
    submit_edit_async,
    upload_image as _upload_image,
)

_MODELS = ["即梦5.0"]
_DEFAULT_MODEL = "即梦5.0"
_ASPECT_RATIOS = ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9"]
_RESOLUTIONS = ["2K", "3K"]
_DEFAULT_RATIO = "1:1"
_DEFAULT_RESOLUTION = "2K"
_MAX_IMAGES = 9
_TAG = "Jimeng"
_POLL_TIMEOUT = 900
_POLL_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/tasks"


def _unpack(v):
    return v[0] if isinstance(v, list) else v


def _blank_image(h=1024, w=1024):
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


def _build_body(model, prompt, aspect_ratio, resolution, image_urls):
    model = model if model in _MODELS else _DEFAULT_MODEL
    params = {"web_search": True}
    ratio = aspect_ratio if aspect_ratio in _ASPECT_RATIOS else _DEFAULT_RATIO
    size = resolution if resolution in _RESOLUTIONS else _DEFAULT_RESOLUTION
    if ratio:
        params["aspect_ratio"] = ratio
    if size:
        params["size"] = size
    urls = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    if urls:
        params["images"] = urls
    return {"model": model, "prompt": prompt or "", "params": params}


def _poll_task(api_key, task_id, model, consumption_id=""):
    import comfy.model_management as mm
    headers = synvow_auth.make_api_headers(api_key)
    body = {"task_id": task_id, "model": model}
    if consumption_id:
        body["consumption_id"] = consumption_id
    start = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start)
        if elapsed >= _POLL_TIMEOUT:
            print(f"[{_TAG}] 超时: ...{task_id[-8:]} ({elapsed}s)")
            return None
        time.sleep(5)
        mm.throw_exception_if_processing_interrupted()
        try:
            res = requests.post(_POLL_URL, headers=headers, json=body, timeout=30, verify=False)
            if res.status_code in (429, 500, 503):
                print(f"[{_TAG}] ...{task_id[-8:]} HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            data = res.json() if res.status_code == 200 else {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else {})
            state = str(inner.get("state") or "").lower()
            print(f"[{_TAG}] ...{task_id[-8:]} state={state or '(无)'} ({elapsed}s)")
            if state in ("success", "succeeded", "completed", "done", "finished"):
                url = inner.get("result_url") or ""
                return url or None
            if state in ("failed", "failure", "error"):
                msg = inner.get("error") or "任务失败"
                print(f"[{_TAG}] 失败: ...{task_id[-8:]} {msg}")
                return None
        except Exception as e:
            print(f"[{_TAG}] 轮询异常: ...{task_id[-8:]} {e}")
            return None


def _download_image(img_url):
    short = f"...{img_url[-24:]}" if len(img_url) > 24 else img_url
    print(f"[{_TAG}] 开始下载: {short}")
    for attempt in range(3):
        try:
            r = requests.get(img_url, timeout=120, verify=False)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            print(f"[{_TAG}] 下载成功 ({attempt + 1}/3): {short} 尺寸={img.width}x{img.height}")
            return torch.from_numpy(arr).unsqueeze(0)
        except Exception as e:
            print(f"[{_TAG}] 下载失败 ({attempt + 1}/3): {short} 错误={e}")
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
    print(f"[{_TAG}] 3次重试均失败，使用黑图占位: {short}")
    return _blank_image()


def _download_with_placeholder(image_urls):
    valid = [(i, u) for i, u in enumerate(image_urls) if u]
    print(f"[{_TAG}] 并发下载 {len(valid)}/{len(image_urls)} 张...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(image_urls), 1)) as ex:
        futures = {i: ex.submit(_download_image, u) for i, u in valid}
    downloaded = {i: f.result() for i, f in futures.items()}
    ref_h, ref_w = next(((t.shape[1], t.shape[2]) for t in downloaded.values()), (1024, 1024))
    return [downloaded.get(i, _blank_image(ref_h, ref_w)) for i in range(len(image_urls))]


def _collect_tensors(image_urls):
    tensors = _download_with_placeholder(image_urls)
    if not tensors:
        return _blank_image()
    h, w = tensors[0].shape[1], tensors[0].shape[2]
    resized = []
    for t in tensors:
        if t.shape[1] != h or t.shape[2] != w:
            pil = Image.fromarray((t[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8))
            pil = pil.resize((w, h), Image.LANCZOS)
            t = torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)
        resized.append(t)
    return torch.cat(resized, dim=0)


def _upload_tensors(api_key, tensors):
    return [_upload_image(api_key, t) for t in (tensors or []) if t is not None][:_MAX_IMAGES]


def _run_tasks(tasks, model, aspect_ratio, resolution, api_key):
    """tasks: list[(prompt, image_tensors)] -> list[url|None]"""
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    submitted = []
    for i, (prompt, imgs) in enumerate(tasks):
        try:
            urls = _upload_tensors(api_key, imgs)
            body = _build_body(model, prompt, aspect_ratio, resolution, urls)
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            submitted.append((task_id, consumption_id, body.get("model") or model))
            print(f"[{_TAG}] [{i + 1}/{total}] 提交成功 task_id=...{task_id[-8:]}")
        except Exception as e:
            print(f"[{_TAG}] [{i + 1}/{total}] 提交失败: {e}")
            submitted.append(None)
        if i < total - 1:
            time.sleep(1)

    def _poll_one(item):
        if item is None:
            pbar.update(1)
            return None
        task_id, consumption_id, used_model = item
        url = _poll_task(api_key, task_id, used_model, consumption_id)
        pbar.update(1)
        return url

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        return list(executor.map(_poll_one, submitted))


def _pick_group_images(all_lists, index):
    imgs = []
    for lst in all_lists:
        if not lst:
            continue
        if len(lst) == 1:
            imgs.append(lst[0])
        elif index < len(lst):
            imgs.append(lst[index])
    return imgs


def _normalize_prompts(prompts_list, fallback=""):
    if isinstance(prompts_list, list):
        prompts = [str(p).strip() for p in prompts_list if p is not None and str(p).strip()]
    elif prompts_list and str(prompts_list).strip():
        prompts = [str(prompts_list).strip()]
    else:
        prompts = []
    if not prompts and fallback is not None and str(fallback).strip():
        prompts = [str(fallback).strip()]
    return prompts or [""]


class SynVowJimeng:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow 即梦 文生图/图生图"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODELS, {"default": _DEFAULT_MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",), "image6": ("IMAGE",),
                "image7": ("IMAGE",), "image8": ("IMAGE",), "image9": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, model_type=None, aspect_ratio=None, resolution=None, seed=None,
                 prompt=None, image1=None, image2=None, image3=None, image4=None,
                 image5=None, image6=None, image7=None, image8=None, image9=None):
        del seed
        model = _unpack(model_type) or _DEFAULT_MODEL
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        resolution = _unpack(resolution) or _DEFAULT_RESOLUTION
        prompt = _unpack(prompt)
        imgs = [
            _unpack(t) for t in [image1, image2, image3, image4, image5, image6, image7, image8, image9]
            if _unpack(t) is not None
        ]
        api_key = synvow_auth.read_api_key()
        p = str(prompt).strip() if prompt else ""
        image_urls = _run_tasks([(p, imgs)], model, aspect_ratio, resolution, api_key)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 生成失败 model={model}"
        )
        out = _collect_tensors(image_urls)
        synvow_auth.refresh_balance()
        return (out, status)


class SynVowJimeng_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow 即梦 提示词批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODELS, {"default": _DEFAULT_MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",), "image6": ("IMAGE",),
                "image7": ("IMAGE",), "image8": ("IMAGE",), "image9": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, model_type=None, aspect_ratio=None, resolution=None, seed=None,
                      prompts_list=None, image1=None, image2=None, image3=None, image4=None,
                      image5=None, image6=None, image7=None, image8=None, image9=None):
        del seed
        model = _unpack(model_type) or _DEFAULT_MODEL
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        resolution = _unpack(resolution) or _DEFAULT_RESOLUTION
        imgs = [
            _unpack(t) for t in [image1, image2, image3, image4, image5, image6, image7, image8, image9]
            if _unpack(t) is not None
        ]
        api_key = synvow_auth.read_api_key()
        prompts = _normalize_prompts(prompts_list)
        tasks = [(p, imgs) for p in prompts]
        print(f"[{_TAG} TBatch] {len(tasks)} 条 prompt, model={model}")
        image_urls = _run_tasks(tasks, model, aspect_ratio, resolution, api_key)
        image_list = _download_with_placeholder(image_urls)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 {ok}/{len(tasks)} model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 所有任务失败 model={model} total={len(tasks)}"
        )
        synvow_auth.refresh_balance()
        return (image_list, status)


class SynVowJimeng_IBatch:
    """提示词列表 × 多组图（对齐 SynMew：每个 prompt 对每组图各跑一次）。"""
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow 即梦 图像批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODELS, {"default": _DEFAULT_MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",),
                "images_list5": ("IMAGE",),
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, resolution=None,
                      prompt=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None,
                      prompts_list=None):
        del seed
        model = _unpack(model_type) or _DEFAULT_MODEL
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        resolution = _unpack(resolution) or _DEFAULT_RESOLUTION
        prompt = _unpack(prompt)
        api_key = synvow_auth.read_api_key()
        all_lists = [
            images_list1,
            images_list2 if images_list2 is not None else [],
            images_list3 if images_list3 is not None else [],
            images_list4 if images_list4 is not None else [],
            images_list5 if images_list5 is not None else [],
        ]
        batch_size = max(len(lst) for lst in all_lists)
        prompts = _normalize_prompts(prompts_list, fallback=prompt or "")
        tasks = []
        for p in prompts:
            for i in range(batch_size):
                tasks.append((p, _pick_group_images(all_lists, i)))
        print(f"[{_TAG} IBatch] {len(prompts)} prompt × {batch_size} 组图 = {len(tasks)} 任务, model={model}")
        image_urls = _run_tasks(tasks, model, aspect_ratio, resolution, api_key)
        image_list = _download_with_placeholder(image_urls)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 {ok}/{len(tasks)} model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 所有任务失败 model={model} total={len(tasks)}"
        )
        synvow_auth.refresh_balance()
        return (image_list, status)


class SynVowJimeng_TIBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow 即梦 双批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODELS, {"default": _DEFAULT_MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",),
                "images_list5": ("IMAGE",),
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, resolution=None,
                      prompt_order=None, seed=None,
                      prompts_list=None, images_list2=None, images_list3=None,
                      images_list4=None, images_list5=None):
        del seed
        model = _unpack(model_type) or _DEFAULT_MODEL
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        resolution = _unpack(resolution) or _DEFAULT_RESOLUTION
        prompt_order = _unpack(prompt_order) or "sequential"
        api_key = synvow_auth.read_api_key()
        all_lists = [
            images_list1,
            images_list2 if images_list2 is not None else [],
            images_list3 if images_list3 is not None else [],
            images_list4 if images_list4 is not None else [],
            images_list5 if images_list5 is not None else [],
        ]
        batch_size = max(len(lst) for lst in all_lists)
        prompts = _normalize_prompts(prompts_list)
        if prompt_order == "reverse":
            prompts = prompts[::-1]
        count = len(prompts)
        assigned = [
            _random.choice(prompts) if prompt_order == "random" else prompts[i % count]
            for i in range(batch_size)
        ]
        print(f"[{_TAG} TIBatch] {batch_size} 组图, {count} 条 prompt, order={prompt_order}, model={model}")
        tasks = [(assigned[i], _pick_group_images(all_lists, i)) for i in range(batch_size)]
        image_urls = _run_tasks(tasks, model, aspect_ratio, resolution, api_key)
        image_list = _download_with_placeholder(image_urls)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 {ok}/{batch_size} model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
        )
        synvow_auth.refresh_balance()
        return (image_list, status)


NODE_CLASS_MAPPINGS = {
    "SynVowJimeng": SynVowJimeng,
    "SynVowJimeng_TBatch": SynVowJimeng_TBatch,
    "SynVowJimeng_IBatch": SynVowJimeng_IBatch,
    "SynVowJimeng_TIBatch": SynVowJimeng_TIBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowJimeng": "SynVow 即梦",
    "SynVowJimeng_TBatch": "SynVow 即梦 (T_batch)",
    "SynVowJimeng_IBatch": "SynVow 即梦 (I_batch)",
    "SynVowJimeng_TIBatch": "SynVow 即梦 (T_I_batch)",
}
