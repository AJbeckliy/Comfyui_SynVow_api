# -*- coding: utf-8 -*-
"""SynVow 即梦 图像生成"""
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

_MODEL_STD = "即梦5.0"
_MODEL_PRO = "即梦5.0-pro"
_MODELS = [_MODEL_STD, _MODEL_PRO]
_DEFAULT_MODEL = _MODEL_STD
_ASPECT_RATIOS = ["1:1", "4:3", "3:4", "16:9", "9:16", "3:2", "2:3", "21:9"]
_RESOLUTIONS = ["1K", "2K", "3K", "4K"]
_RESOLUTIONS_BY_MODEL = {
    _MODEL_STD: ["2K", "3K", "4K"],
    _MODEL_PRO: ["1K", "2K"],
}
_DEFAULT_RATIO = "1:1"
_DEFAULT_RESOLUTION = "2K"
_MAX_IMAGES_BY_MODEL = {
    _MODEL_STD: 4,
    _MODEL_PRO: 9,
}
_TAG = "Jimeng"
_POLL_TIMEOUT = 900


def _normalize_model(model):
    return model if model in _MODELS else _DEFAULT_MODEL


def _normalize_resolution(model, resolution):
    allowed = _RESOLUTIONS_BY_MODEL.get(model) or _RESOLUTIONS_BY_MODEL[_DEFAULT_MODEL]
    if resolution and resolution in allowed:
        return resolution
    return "2K" if "2K" in allowed else allowed[0]


def _max_images(model):
    return _MAX_IMAGES_BY_MODEL.get(_normalize_model(model), 4)


def _build_body(model, prompt, aspect_ratio, resolution, image_urls):
    model = _normalize_model(model)
    ratio = aspect_ratio if aspect_ratio in _ASPECT_RATIOS else _DEFAULT_RATIO
    res = _normalize_resolution(model, resolution)
    urls = [u for u in (image_urls or []) if u][:_max_images(model)]
    body = {
        "model": model,
        "prompt": prompt or "",
        "size": ratio,
        "resolution": res,
    }
    if urls:
        body["image_urls"] = urls
    return body


def _upload_tensors(api_key, tensors, model):
    return [_upload_image(api_key, t) for t in (tensors or []) if t is not None][:_max_images(model)]


def _run_tasks(tasks, model, aspect_ratio, resolution, api_key):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    submitted = []
    for i, (prompt, imgs) in enumerate(tasks):
        try:
            urls = _upload_tensors(api_key, imgs, model)
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
        url = poll_edit_task(api_key, task_id, used_model, _TAG, consumption_id=consumption_id, timeout=_POLL_TIMEOUT, fail_soft=True)
        pbar.update(1)
        return url

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        return list(executor.map(_poll_one, submitted))


def _pick_group_images(all_lists, index, model=None):
    imgs = []
    for lst in all_lists:
        if not lst:
            continue
        if len(lst) == 1:
            imgs.append(lst[0])
        elif index < len(lst):
            imgs.append(lst[index])
    return imgs[:_max_images(model)] if model else imgs


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
        out = stack_image_tensors(image_urls, tag=_TAG)
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
        image_list = download_image_tensors(image_urls, tag=_TAG)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 {ok}/{len(tasks)} model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 所有任务失败 model={model} total={len(tasks)}"
        )
        synvow_auth.refresh_balance()
        return (image_list, status)


class SynVowJimeng_IBatch:
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
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, resolution=None,
                      prompt=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None):
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
        p = str(prompt).strip() if prompt else ""
        tasks = [(p, _pick_group_images(all_lists, i, model)) for i in range(batch_size)]
        print(f"[{_TAG} IBatch] {batch_size} 组图, model={model}")
        image_urls = _run_tasks(tasks, model, aspect_ratio, resolution, api_key)
        image_list = download_image_tensors(image_urls, tag=_TAG)
        ok = sum(1 for u in image_urls if u)
        status = (
            f"已完成 {ok}/{batch_size} model={model} aspect_ratio={aspect_ratio} size={resolution}"
            if ok else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
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
        tasks = [(assigned[i], _pick_group_images(all_lists, i, model)) for i in range(batch_size)]
        image_urls = _run_tasks(tasks, model, aspect_ratio, resolution, api_key)
        image_list = download_image_tensors(image_urls, tag=_TAG)
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
