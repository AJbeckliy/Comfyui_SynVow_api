# -*- coding: utf-8 -*-
"""SynVow MAI-image 2.6 图像生成。"""
import concurrent.futures
import random as _random
import time

import comfy.utils

from . import synvow_auth
from .media_common import (
    download_image_tensors,
    extract_result_urls,
    is_changed_by_inputs as _is_changed,
    poll_edit_task,
    stack_image_tensors,
    submit_edit_async,
    unpack_list_input as _unpack,
    upload_image as _upload_image,
)
from .model_display import combo_models, display_name, resolve_model

_API_MODELS = ["mai-image-2.6-wd", "mai-image-2.6-flash-wd"]
_MODEL_OPTIONS = combo_models(_API_MODELS)
_DEFAULT_MODEL = "mai-image-2.6-wd"
_DEFAULT_COMBO = display_name(_DEFAULT_MODEL)
_ASPECT_RATIOS = [
    "auto", "1:1", "4:3", "3:4", "3:2", "2:3", "16:9", "9:16",
    "2:1", "1:2", "21:9", "9:21", "4:1", "1:4",
]
_IMAGE_SIZES = ["1K", "2K"]
_MAX_IMAGES = 5
_TAG = "MAI-img"
_POLL_TIMEOUT = 1800


def _resolve_aspect(aspect_ratio):
    return aspect_ratio if aspect_ratio in _ASPECT_RATIOS else "1:1"


def _build_body(model, prompt, aspect_ratio, image_size, image_urls):
    body = {"model": model, "prompt": prompt or ""}
    if aspect_ratio and aspect_ratio != "auto":
        body["size"] = aspect_ratio
    body["resolution"] = image_size if image_size in _IMAGE_SIZES else "2K"
    urls = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    if urls:
        body["image_urls"] = urls
    return body


def _poll_urls(api_key, task_id, model, consumption_id=""):
    def pick(inner, data):
        found = extract_result_urls(inner) or extract_result_urls(data)
        return found or None

    result = poll_edit_task(
        api_key, task_id, model, _TAG,
        consumption_id=consumption_id or "", timeout=_POLL_TIMEOUT,
        fail_soft=True, pick_url=pick,
    )
    if not result:
        return []
    return result if isinstance(result, list) else [result]


def _run_tasks(tasks, model, aspect_ratio, image_size, api_key):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    submitted = []
    for i, (prompt, imgs) in enumerate(tasks):
        try:
            urls = [_upload_image(api_key, t) for t in (imgs or []) if t is not None][:_MAX_IMAGES]
            body = _build_body(model, prompt, aspect_ratio, image_size, urls)
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            submitted.append((task_id, consumption_id))
            print(f"[{_TAG}] [{i + 1}/{total}] 提交成功 task_id=...{task_id[-8:]}")
        except Exception as e:
            print(f"[{_TAG}] [{i + 1}/{total}] 提交失败: {e}")
            submitted.append(None)
        if i < total - 1:
            time.sleep(1)

    def poll_one(item):
        if item is None:
            pbar.update(1)
            return None
        task_id, consumption_id = item
        urls = _poll_urls(api_key, task_id, model, consumption_id)
        pbar.update(1)
        return urls

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        results = list(executor.map(poll_one, submitted))

    image_urls = []
    for i, urls in enumerate(results):
        if urls:
            image_urls.extend(urls)
        else:
            print(f"[{_TAG}] task[{i}] 失败，黑图占位")
            image_urls.append(None)
    return image_urls


def _images_from_slots(*tensors):
    imgs = []
    for tensor in tensors:
        item = _unpack(tensor)
        if item is not None:
            imgs.append(item)
        if len(imgs) >= _MAX_IMAGES:
            break
    return imgs


def _group_at(lists, index):
    imgs = []
    for lst in lists:
        if not lst:
            continue
        if len(lst) == 1:
            imgs.append(lst[0])
        elif index < len(lst):
            imgs.append(lst[index])
        if len(imgs) >= _MAX_IMAGES:
            break
    return imgs


class SynVowMaiImage:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow MAI-image 2.6"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_COMBO}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (_IMAGE_SIZES, {"default": "2K"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, model_type=None, aspect_ratio=None, image_size=None, seed=None,
                 prompt=None, image1=None, image2=None, image3=None, image4=None, image5=None):
        model = resolve_model(_unpack(model_type), _DEFAULT_MODEL)
        image_size = _unpack(image_size) or "2K"
        prompt = str(_unpack(prompt) or "").strip()
        imgs = _images_from_slots(image1, image2, image3, image4, image5)
        aspect = _resolve_aspect(_unpack(aspect_ratio))
        api_key = synvow_auth.read_api_key()
        try:
            urls = _run_tasks([(prompt, imgs)], model, aspect, image_size, api_key)
            ok = sum(1 for u in urls if u)
            status = f"已完成 model={model} size={aspect} resolution={image_size}" if ok else f"[ERROR] 生成失败 model={model}"
            return (stack_image_tensors(urls, tag=_TAG), status)
        finally:
            synvow_auth.refresh_balance()


class SynVowMaiImage_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_COMBO}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (_IMAGE_SIZES, {"default": "2K"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, model_type=None, aspect_ratio=None, image_size=None, seed=None,
                      prompts_list=None, image1=None, image2=None, image3=None, image4=None, image5=None):
        model = resolve_model(_unpack(model_type), _DEFAULT_MODEL)
        image_size = _unpack(image_size) or "2K"
        imgs = _images_from_slots(image1, image2, image3, image4, image5)
        aspect = _resolve_aspect(_unpack(aspect_ratio))
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [p for p in prompts if p is not None] or [""]
        api_key = synvow_auth.read_api_key()
        try:
            urls = _run_tasks([(p, imgs) for p in prompts], model, aspect, image_size, api_key)
            ok = sum(1 for u in urls if u)
            status = f"已完成 {ok}/{len(prompts)} model={model}" if ok else f"[ERROR] 所有任务失败 model={model}"
            return (download_image_tensors(urls, tag=_TAG), status)
        finally:
            synvow_auth.refresh_balance()


class SynVowMaiImage_IBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_COMBO}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (_IMAGE_SIZES, {"default": "2K"}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",), "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",), "images_list5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, image_size=None,
                      prompt=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None):
        model = resolve_model(_unpack(model_type), _DEFAULT_MODEL)
        image_size = _unpack(image_size) or "2K"
        prompt = str(_unpack(prompt) or "").strip()
        lists = [images_list1, images_list2 or [], images_list3 or [], images_list4 or [], images_list5 or []]
        batch_size = max(len(lst) for lst in lists)
        aspect = _resolve_aspect(_unpack(aspect_ratio))
        api_key = synvow_auth.read_api_key()
        try:
            urls = _run_tasks([(prompt, _group_at(lists, i)) for i in range(batch_size)], model, aspect, image_size, api_key)
            ok = sum(1 for u in urls if u)
            status = f"已完成 {ok}/{batch_size} model={model}" if ok else f"[ERROR] 所有任务失败 model={model}"
            return (download_image_tensors(urls, tag=_TAG), status)
        finally:
            synvow_auth.refresh_balance()


class SynVowMaiImage_TIBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_COMBO}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (_IMAGE_SIZES, {"default": "2K"}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",), "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",), "images_list5": ("IMAGE",),
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, image_size=None,
                      prompt_order=None, seed=None, prompts_list=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None):
        model = resolve_model(_unpack(model_type), _DEFAULT_MODEL)
        image_size = _unpack(image_size) or "2K"
        order = _unpack(prompt_order) or "sequential"
        lists = [images_list1, images_list2 or [], images_list3 or [], images_list4 or [], images_list5 or []]
        batch_size = max(len(lst) for lst in lists)
        aspect = _resolve_aspect(_unpack(aspect_ratio))
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [])
        prompts = [p for p in prompts if p is not None] or [""]
        if order == "reverse":
            prompts = prompts[::-1]
        assigned = [
            _random.choice(prompts) if order == "random" else prompts[i % len(prompts)]
            for i in range(batch_size)
        ]
        api_key = synvow_auth.read_api_key()
        try:
            urls = _run_tasks([(assigned[i], _group_at(lists, i)) for i in range(batch_size)], model, aspect, image_size, api_key)
            ok = sum(1 for u in urls if u)
            status = f"已完成 {ok}/{batch_size} model={model}" if ok else f"[ERROR] 所有任务失败 model={model}"
            return (download_image_tensors(urls, tag=_TAG), status)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowMaiImage": SynVowMaiImage,
    "SynVowMaiImage_TBatch": SynVowMaiImage_TBatch,
    "SynVowMaiImage_IBatch": SynVowMaiImage_IBatch,
    "SynVowMaiImage_TIBatch": SynVowMaiImage_TIBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowMaiImage": "SynVow MAI-image",
    "SynVowMaiImage_TBatch": "SynVow MAI-image (T_batch)",
    "SynVowMaiImage_IBatch": "SynVow MAI-image (I_batch)",
    "SynVowMaiImage_TIBatch": "SynVow MAI-image (T_I_batch)",
}
