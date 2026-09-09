# -*- coding: utf-8 -*-
"""
SynVow Omni-Flash 视频生成
"""
import json
import math

from . import synvow_auth
from .model_display import combo_models, display_name, pick_model
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
    upload_media_file,
)

_EXT = "Omni-Flash-Ext"
_PREVIEW = "omni-flash-preview"
_V11 = "omni-1.1-flash"
_API_MODELS = [_PREVIEW, _V11, _EXT]
_MODELS = combo_models(_API_MODELS)
_DEFAULT_MODEL = _PREVIEW
_DEFAULT_COMBO = display_name(_DEFAULT_MODEL)
_MODES = ["single", "triple", "video"]
_DEFAULT_MODE = "single"
_ASPECTS = ["16:9", "9:16"]
_V11_RESOLUTIONS = ["360p", "720p", "1080p", "4k"]
_RESOLUTIONS = _V11_RESOLUTIONS[1:]
_DURATIONS = ["4", "6", "8", "10"]
_DEFAULT_ASPECT = "16:9"
_DEFAULT_RESOLUTION = "720p"
_DEFAULT_DURATION = "6"
_MAX_IMAGES = 3
_V11_MAX_IMAGES = 9
_MAX_REF_VIDEO_SECONDS = 10
_TAG = "OmniFlash"


def _normalize_model(raw):
    return pick_model(raw, _API_MODELS, _DEFAULT_MODEL)


def _normalize_mode(raw):
    return raw if raw in _MODES else _DEFAULT_MODE


def _normalize_aspect(ratio):
    return ratio if ratio in _ASPECTS else _DEFAULT_ASPECT


def _normalize_resolution(resolution, model=""):
    lower = (resolution or "").lower()
    allowed = _V11_RESOLUTIONS if _normalize_model(model) == _V11 else _RESOLUTIONS
    return lower if lower in allowed else _DEFAULT_RESOLUTION


def _normalize_duration(raw):
    try:
        n = int(float(raw))
    except Exception:
        return int(_DEFAULT_DURATION)
    return n if str(n) in _DURATIONS else int(_DEFAULT_DURATION)


def _duration_from_ref(seconds):
    try:
        d = int(math.ceil(float(seconds)))
    except Exception:
        d = 1
    return min(_MAX_REF_VIDEO_SECONDS, max(1, d))


def _mode_max_images(mode):
    if mode == "triple":
        return 3
    if mode == "single":
        return 1
    return 0


def _image_cap(model, mode):
    model = _normalize_model(model)
    if model == _V11:
        return _V11_MAX_IMAGES
    if model == _PREVIEW:
        return _MAX_IMAGES
    return _mode_max_images(mode)


def _pack_image_urls(urls, model, mode):
    list_urls = [u for u in (urls or []) if u][:_image_cap(model, mode)]
    if model != _V11 and len(list_urls) == 2:
        raise ValueError("OmniFlash 参考图仅支持 0、1 或 3 张，不可传 2 张")
    return list_urls


def _build_body(model, mode, prompt, aspect_ratio, duration, resolution, image_urls, video_url, video_duration_sec=None):
    model = _normalize_model(model)
    dual = model != _EXT
    v11 = model == _V11
    images = _pack_image_urls(image_urls, model, mode)
    has_video = bool(video_url)
    text = (prompt or "").strip()

    body = {
        "model": model,
        "aspect_ratio": _normalize_aspect(aspect_ratio),
        "resolution": "720p" if model == _PREVIEW else _normalize_resolution(resolution, model),
    }
    if v11:
        if text:
            body["prompt"] = text
    else:
        body["prompt"] = prompt or ""

    if dual:
        if v11 and not text and not images and not has_video:
            raise ValueError("OmniFlash 请输入提示词，或接入参考图/视频")
        if images:
            body["image_urls"] = images
        if video_url:
            body["video_urls"] = [video_url]
        return body

    mode = _normalize_mode(mode)
    if mode == "video":
        if not has_video:
            raise ValueError("OmniFlash 视频模式请传入参考视频")
        body["video_urls"] = [video_url]
    else:
        if images:
            body["image_urls"] = images
        body["generation_type"] = "reference" if mode == "triple" else "frame"

    if has_video:
        sec = video_duration_sec if video_duration_sec is not None else _normalize_duration(duration)
        body["duration"] = _duration_from_ref(sec)
    else:
        body["duration"] = _normalize_duration(duration)
    return body


def _run_once(api_key, prompt, model, mode, aspect_ratio, duration, resolution,
              image_tensors, video_path, save_path="", filename=""):
    model = _normalize_model(model)
    mode = _normalize_mode(mode)
    dual = model != _EXT
    max_images = _image_cap(model, mode)
    want_video = bool((video_path or "").strip()) if dual else (mode == "video")

    tensors = [t for t in (image_tensors or []) if t is not None]
    tensors = [] if max_images <= 0 else tensors[:max_images]
    image_urls = [upload_image(api_key, t) for t in tensors]

    video_url = ""
    video_duration_sec = None
    if want_video and (video_path or "").strip():
        video_url = upload_media_file(api_key, video_path, "video")
        video_duration_sec = _normalize_duration(duration)

    if not dual and mode == "video" and not video_url:
        raise ValueError("OmniFlash 视频模式请传入参考视频")

    body = _build_body(
        model, mode, prompt, aspect_ratio, duration, resolution,
        image_urls, video_url, video_duration_sec,
    )
    submit_model = body.get("model") or model
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(api_key, task_id, submit_model, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="omni", filename=filename) or ""
    return path, url, task_id, submit_model


class SynVowOmniFlash:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Omni-Flash"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _DEFAULT_COMBO}),
                "mode": (_MODES, {"default": _DEFAULT_MODE}),
                "aspect_ratio": (_ASPECTS, {"default": _DEFAULT_ASPECT}),
                "duration": (_DURATIONS, {"default": _DEFAULT_DURATION}),
                "resolution": (_V11_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "video_path": ("STRING", {"default": "", "multiline": False, "placeholder": "参考视频本地路径或 URL"}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, model, mode, aspect_ratio, duration, resolution, seed=0,
                       image_1=None, image_2=None, image_3=None, image_4=None, image_5=None,
                       image_6=None, image_7=None, image_8=None, image_9=None,
                       video_path="", filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4, image_5,
                               image_6, image_7, image_8, image_9] if t is not None]
        try:
            path, url, task_id, used_model = _run_once(
                api_key, prompt, model, mode, aspect_ratio, duration, resolution,
                tensors, video_path, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": used_model, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            return (path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowOmniFlash": SynVowOmniFlash,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowOmniFlash": "SynVow Omni-Flash",
}
