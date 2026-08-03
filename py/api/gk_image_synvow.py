# -*- coding: utf-8 -*-
"""SynVow GK1.5 图像生成"""
import concurrent.futures
import random as _random
import time

import comfy.utils

from . import synvow_auth
from .media_common import (
    download_image_tensors,
    is_changed_by_inputs as _is_changed,
    normalize_prompts as _normalize_prompts,
    poll_edit_task,
    stack_image_tensors,
    submit_edit_async,
    unpack_list_input as _unpack,
    upload_image as _upload_image,
)

_MODEL = "grok-image-1.5-稳定"
_MODELS = [_MODEL]
_ASPECT_RATIOS = ["1:1", "16:9", "9:16", "3:2", "2:3"]
_DEFAULT_RATIO = "1:1"
_MAX_IMAGES = 1
_TAG = "GK1.5"
_POLL_TIMEOUT = 1800


def _build_body(prompt, aspect_ratio, image_urls):
    body = {
        "model": _MODEL,
        "prompt": prompt or "",
        "n": 1,
    }
    urls = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    if urls:
        body["image_urls"] = urls
    else:
        body["size"] = aspect_ratio if aspect_ratio in _ASPECT_RATIOS else _DEFAULT_RATIO
    return body


def _run_tasks(tasks, aspect_ratio, api_key):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    submitted = []
    for i, (prompt, imgs) in enumerate(tasks):
        try:
            urls = [_upload_image(api_key, t) for t in (imgs or []) if t is not None][:_MAX_IMAGES]
            body = _build_body(prompt, aspect_ratio, urls)
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            submitted.append((task_id, consumption_id))
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
        task_id, consumption_id = item
        url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id, timeout=_POLL_TIMEOUT, fail_soft=True)
        pbar.update(1)
        return url

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        return list(executor.map(_poll_one, submitted))


def _list_tensors(images_list):
    if images_list is None:
        return []
    if isinstance(images_list, list):
        return [t for t in images_list if t is not None]
    return [images_list]


class SynVowGkImage:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow GK1.5 文生图/图生图"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODELS, {"default": _MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "image1": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, model_type=None, aspect_ratio=None, seed=None, prompt=None, image1=None):
        del model_type, seed
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        prompt = _unpack(prompt)
        img = _unpack(image1)
        imgs = [img] if img is not None else []
        api_key = synvow_auth.read_api_key()
        p = str(prompt).strip() if prompt else ""
        image_urls = _run_tasks([(p, imgs)], aspect_ratio, api_key)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 model={_MODEL}" if ok else f"[ERROR] 生成失败 model={_MODEL}"
        out = stack_image_tensors(image_urls, tag=_TAG)
        synvow_auth.refresh_balance()
        return (out, status)


class SynVowGkImage_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow GK1.5 提示词批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODELS, {"default": _MODEL}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": _DEFAULT_RATIO}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image1": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, model_type=None, aspect_ratio=None, seed=None,
                      prompts_list=None, image1=None):
        del model_type, seed
        aspect_ratio = _unpack(aspect_ratio) or _DEFAULT_RATIO
        img = _unpack(image1)
        imgs = [img] if img is not None else []
        api_key = synvow_auth.read_api_key()
        prompts = _normalize_prompts(prompts_list)
        tasks = [(p, imgs) for p in prompts]
        print(f"[{_TAG} TBatch] {len(tasks)} 条 prompt")
        image_urls = _run_tasks(tasks, aspect_ratio, api_key)
        image_list = download_image_tensors(image_urls, tag=_TAG)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 {ok}/{len(tasks)} model={_MODEL}" if ok else f"[ERROR] 所有任务失败 total={len(tasks)}"
        synvow_auth.refresh_balance()
        return (image_list, status)


class SynVowGkImage_IBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow GK1.5 图像批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODELS, {"default": _MODEL}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, prompt=None, seed=None, prompts_list=None):
        del model_type, seed
        prompt = _unpack(prompt)
        api_key = synvow_auth.read_api_key()
        images = _list_tensors(images_list1)
        if not images:
            raise ValueError("GK1.5 图像批量：需要接入图像组1")
        prompts = _normalize_prompts(prompts_list, fallback=prompt or "")
        tasks = [(p, [img]) for p in prompts for img in images]
        print(f"[{_TAG} IBatch] {len(prompts)} prompt × {len(images)} 图 = {len(tasks)} 任务")
        image_urls = _run_tasks(tasks, "", api_key)
        image_list = download_image_tensors(image_urls, tag=_TAG)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 {ok}/{len(tasks)} model={_MODEL}" if ok else f"[ERROR] 所有任务失败 total={len(tasks)}"
        synvow_auth.refresh_balance()
        return (image_list, status)


class SynVowGkImage_TIBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)
    DESCRIPTION = "SynVow GK1.5 双批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODELS, {"default": _MODEL}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, prompt_order=None, seed=None, prompts_list=None):
        del model_type, seed
        prompt_order = _unpack(prompt_order) or "sequential"
        api_key = synvow_auth.read_api_key()
        images = _list_tensors(images_list1)
        if not images:
            raise ValueError("GK1.5 双批量：需要接入图像组1")
        prompts = _normalize_prompts(prompts_list)
        if prompt_order == "reverse":
            prompts = prompts[::-1]
        count = len(prompts)
        assigned = [
            _random.choice(prompts) if prompt_order == "random" else prompts[i % count]
            for i in range(len(images))
        ]
        print(f"[{_TAG} TIBatch] {len(images)} 图, {count} 条 prompt, order={prompt_order}")
        tasks = [(assigned[i], [images[i]]) for i in range(len(images))]
        image_urls = _run_tasks(tasks, "", api_key)
        image_list = download_image_tensors(image_urls, tag=_TAG)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 {ok}/{len(images)} model={_MODEL}" if ok else f"[ERROR] 所有任务失败 total={len(images)}"
        synvow_auth.refresh_balance()
        return (image_list, status)


NODE_CLASS_MAPPINGS = {
    "SynVowGkImage": SynVowGkImage,
    "SynVowGkImage_TBatch": SynVowGkImage_TBatch,
    "SynVowGkImage_IBatch": SynVowGkImage_IBatch,
    "SynVowGkImage_TIBatch": SynVowGkImage_TIBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGkImage": "SynVow GK1.5",
    "SynVowGkImage_TBatch": "SynVow GK1.5 (T_batch)",
    "SynVowGkImage_IBatch": "SynVow GK1.5 (I_batch)",
    "SynVowGkImage_TIBatch": "SynVow GK1.5 (T_I_batch)",
}
