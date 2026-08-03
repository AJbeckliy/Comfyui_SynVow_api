# -*- coding: utf-8 -*-
"""SynVow 悠船 (Midjourney) 图像生成"""
import concurrent.futures
import time

import comfy.utils

from . import synvow_auth
from .media_common import (
    extract_result_urls,
    is_changed_by_inputs as _is_changed,
    poll_edit_task,
    stack_image_tensors,
    submit_edit_async,
    unpack_list_input as _unpack,
    upload_image as _upload_image,
)

_MODEL_TEXT = "Midjourney_文生图"
_MODEL_BLEND = "Midjourney_多图融合"
_MODEL_EDIT = "Midjourney_图像编辑"
_VERSIONS = ["8.2", "8.1"]
_QUALITIES = ["0.25", "0.5", "1", "2"]
_SPEEDS = ["relax", "fast", "turbo"]
_SIZES = [
    "1:1", "16:9", "9:16", "4:3", "3:4", "5:4", "4:5",
    "3:2", "2:3", "3:1", "1:3", "2:1", "1:2", "21:9", "9:21",
]
_BLEND_MAX = 4
_TAG = "悠船"
_POLL_TIMEOUT = 900


def _image_limit(model):
    if model == _MODEL_TEXT:
        return 0
    if model == _MODEL_BLEND:
        return _BLEND_MAX
    return 1


def _build_body(model, prompt, size, version, quality, stylize, chaos, weird, speed,
                tile, raw, draft, hd, iw, ow, sw, dw,
                image_urls, oref_url="", sref_url="", dref_url=""):
    size = size if size in _SIZES else "1:1"
    speed = speed if speed in _SPEEDS else "relax"
    urls = [u for u in (image_urls or []) if u]

    if model == _MODEL_BLEND:
        return {
            "model": model,
            "image_urls": urls,
            "size": size,
            "speed": speed,
        }

    body = {
        "model": model,
        "prompt": prompt or "",
        "version": version if version in _VERSIONS else "8.2",
        "size": size,
        "quality": str(quality if quality is not None else "1"),
        "stylize": int(stylize),
        "chaos": int(chaos),
        "weird": int(weird),
        "speed": speed,
    }
    if urls:
        body["image_urls"] = urls
        body["iw"] = float(iw)
    if oref_url:
        body["oref"] = [oref_url]
        body["ow"] = int(ow)
    if sref_url:
        body["sref"] = sref_url
        body["sw"] = int(sw)
    if dref_url:
        body["dref"] = [dref_url]
        body["dw"] = int(dw)
    if tile:
        body["tile"] = True
    if raw:
        body["raw"] = True
    if draft:
        body["draft"] = True
    if hd:
        body["hd"] = True
    return body


def _poll_task(api_key, task_id, model, consumption_id=""):
    def pick_urls(inner, data):
        found = extract_result_urls(inner) or extract_result_urls(data)
        return found or None

    result = poll_edit_task(
        api_key, task_id, model, _TAG,
        consumption_id=consumption_id, timeout=_POLL_TIMEOUT, fail_soft=True,
        extra_body={"response": "url"},
        pick_url=pick_urls,
    )
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _validate(model, prompt, image_urls):
    n = len(image_urls)
    if model == _MODEL_BLEND:
        if n < 2 or n > _BLEND_MAX:
            raise ValueError(f"悠船_多图融合：需要提供 2–{_BLEND_MAX} 张图像")
        return
    if model == _MODEL_EDIT and n < 1:
        raise ValueError("悠船_图像编辑：需要提供输入图像")
    if model != _MODEL_BLEND and not str(prompt or "").strip():
        raise ValueError("悠船：请输入提示词")


def _run_tasks(tasks, model, size, version, quality, stylize, chaos, weird, speed,
               tile, raw, draft, hd, iw, ow, sw, dw, oref_url, sref_url, dref_url, api_key):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    submitted = []
    for i, (prompt, imgs) in enumerate(tasks):
        try:
            limit = _image_limit(model)
            urls = [_upload_image(api_key, t) for t in (imgs or []) if t is not None][:limit]
            _validate(model, prompt, urls)
            body = _build_body(
                model, prompt, size, version, quality, stylize, chaos, weird, speed,
                tile, raw, draft, hd, iw, ow, sw, dw, urls, oref_url, sref_url, dref_url,
            )
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
            return []
        task_id, consumption_id, used_model = item
        urls = _poll_task(api_key, task_id, used_model, consumption_id)
        pbar.update(1)
        return urls

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        results = list(executor.map(_poll_one, submitted))
    image_urls = []
    for urls in results:
        if urls:
            image_urls.extend(urls)
        else:
            image_urls.append(None)
    return image_urls


def _upload_optional(api_key, tensor):
    t = _unpack(tensor)
    return _upload_image(api_key, t) if t is not None else ""


def _pick_params(version, size, quality, speed, stylize, chaos, weird, iw, ow, sw, dw,
                 tile, raw, draft, hd):
    return {
        "version": _unpack(version) or "8.2",
        "size": _unpack(size) or "1:1",
        "quality": _unpack(quality) or "1",
        "speed": _unpack(speed) or "relax",
        "stylize": int(_unpack(stylize) if stylize is not None else 100),
        "chaos": int(_unpack(chaos) if chaos is not None else 0),
        "weird": int(_unpack(weird) if weird is not None else 0),
        "iw": float(_unpack(iw) if iw is not None else 1),
        "ow": int(_unpack(ow) if ow is not None else 100),
        "sw": int(_unpack(sw) if sw is not None else 100),
        "dw": int(_unpack(dw) if dw is not None else 0),
        "tile": bool(_unpack(tile)),
        "raw": bool(_unpack(raw)),
        "draft": bool(_unpack(draft)),
        "hd": bool(_unpack(hd)),
    }


_FULL_REQUIRED = {
    "版本": (_VERSIONS, {"default": "8.2"}),
    "比例": (_SIZES, {"default": "1:1"}),
    "质量": (_QUALITIES, {"default": "1"}),
    "速度": (_SPEEDS, {"default": "relax"}),
    "风格化": ("INT", {"default": 100, "min": 0, "max": 1000, "step": 10}),
    "混乱": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
    "怪异": ("INT", {"default": 0, "min": 0, "max": 3000, "step": 10}),
    "角色权重": ("INT", {"default": 100, "min": 0, "max": 100, "step": 1}),
    "风格权重": ("INT", {"default": 100, "min": 0, "max": 1000, "step": 10}),
    "深度权重": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
    "平铺": ("BOOLEAN", {"default": False}),
    "Raw": ("BOOLEAN", {"default": False}),
    "草图": ("BOOLEAN", {"default": False}),
    "HD": ("BOOLEAN", {"default": False}),
    "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
}

_REF_OPTIONAL = {
    "角色参考": ("IMAGE",),
    "风格参考": ("IMAGE",),
    "深度参考": ("IMAGE",),
}


def _run_full(model, prompt_tasks, images, params, api_key, oref, sref, dref):
    oref_url = _upload_optional(api_key, oref)
    sref_url = _upload_optional(api_key, sref)
    dref_url = _upload_optional(api_key, dref)
    return _run_tasks(
        [(p, images) for p in prompt_tasks],
        model, params["size"], params["version"], params["quality"],
        params["stylize"], params["chaos"], params["weird"], params["speed"],
        params["tile"], params["raw"], params["draft"], params["hd"],
        params["iw"], params["ow"], params["sw"], params["dw"],
        oref_url, sref_url, dref_url, api_key,
    )


class SynVowMidjourneyText:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow 悠船 文生图"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": dict(_FULL_REQUIRED),
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                **_REF_OPTIONAL,
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, 版本=None, 比例=None, 质量=None, 速度=None,
                 风格化=None, 混乱=None, 怪异=None, 角色权重=None, 风格权重=None, 深度权重=None,
                 平铺=None, Raw=None, 草图=None, HD=None, seed=None, prompt=None,
                 角色参考=None, 风格参考=None, 深度参考=None):
        del seed
        params = _pick_params(版本, 比例, 质量, 速度, 风格化, 混乱, 怪异,
                              1.0, 角色权重, 风格权重, 深度权重, 平铺, Raw, 草图, HD)
        p = str(_unpack(prompt) or "").strip()
        api_key = synvow_auth.read_api_key()
        image_urls = _run_full(_MODEL_TEXT, [p], [], params, api_key, 角色参考, 风格参考, 深度参考)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 model={_MODEL_TEXT} {ok} 张" if ok else f"[ERROR] 生成失败 model={_MODEL_TEXT}"
        synvow_auth.refresh_balance()
        return (stack_image_tensors(image_urls, tag=_TAG), status)


class SynVowMidjourneyBlend:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow 悠船 多图融合"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "比例": (_SIZES, {"default": "1:1"}),
                "速度": (_SPEEDS, {"default": "relax"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, 比例=None, 速度=None, seed=None,
                 image1=None, image2=None, image3=None, image4=None):
        del seed
        size = _unpack(比例) or "1:1"
        speed = _unpack(速度) or "relax"
        imgs = [t for t in [
            _unpack(image1), _unpack(image2), _unpack(image3), _unpack(image4),
        ] if t is not None]
        api_key = synvow_auth.read_api_key()
        image_urls = _run_tasks(
            [("", imgs)], _MODEL_BLEND, size, "8.2", "1", 100, 0, 0, speed,
            False, False, False, False, 1.0, 100, 100, 0, "", "", "", api_key,
        )
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 model={_MODEL_BLEND} {ok} 张" if ok else f"[ERROR] 生成失败 model={_MODEL_BLEND}"
        synvow_auth.refresh_balance()
        return (stack_image_tensors(image_urls, tag=_TAG), status)


class SynVowMidjourneyEdit:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    DESCRIPTION = "SynVow 悠船 图像编辑"

    @classmethod
    def INPUT_TYPES(cls):
        req = dict(_FULL_REQUIRED)
        req["图片权重"] = ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.1})
        return {
            "required": req,
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "image1": ("IMAGE",),
                **_REF_OPTIONAL,
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, 版本=None, 比例=None, 质量=None, 速度=None,
                 风格化=None, 混乱=None, 怪异=None, 图片权重=None,
                 角色权重=None, 风格权重=None, 深度权重=None,
                 平铺=None, Raw=None, 草图=None, HD=None, seed=None, prompt=None,
                 image1=None, 角色参考=None, 风格参考=None, 深度参考=None):
        del seed
        params = _pick_params(版本, 比例, 质量, 速度, 风格化, 混乱, 怪异,
                              图片权重, 角色权重, 风格权重, 深度权重, 平铺, Raw, 草图, HD)
        p = str(_unpack(prompt) or "").strip()
        img = _unpack(image1)
        imgs = [img] if img is not None else []
        api_key = synvow_auth.read_api_key()
        image_urls = _run_full(_MODEL_EDIT, [p], imgs, params, api_key, 角色参考, 风格参考, 深度参考)
        ok = sum(1 for u in image_urls if u)
        status = f"已完成 model={_MODEL_EDIT} {ok} 张" if ok else f"[ERROR] 生成失败 model={_MODEL_EDIT}"
        synvow_auth.refresh_balance()
        return (stack_image_tensors(image_urls, tag=_TAG), status)


NODE_CLASS_MAPPINGS = {
    "SynVowMidjourneyText": SynVowMidjourneyText,
    "SynVowMidjourneyBlend": SynVowMidjourneyBlend,
    "SynVowMidjourneyEdit": SynVowMidjourneyEdit,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowMidjourneyText": "SynVow 悠船 文生图",
    "SynVowMidjourneyBlend": "SynVow 悠船 多图融合",
    "SynVowMidjourneyEdit": "SynVow 悠船 图像编辑",
}
