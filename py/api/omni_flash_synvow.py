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
_API_MODELS = [_EXT, _PREVIEW]
_MODELS = combo_models(_API_MODELS)
_DEFAULT_MODEL = _PREVIEW
_DEFAULT_COMBO = display_name(_DEFAULT_MODEL)
_MODES = ["single", "triple", "video"]
_DEFAULT_MODE = "single"
_ASPECTS = ["16:9", "9:16"]
_RESOLUTIONS = ["720p", "1080p", "4k"]
_DURATIONS = ["4", "6", "8", "10"]
_DEFAULT_ASPECT = "16:9"
_DEFAULT_RESOLUTION = "720p"
_DEFAULT_DURATION = "6"
_MAX_IMAGES = 3
_MAX_REF_VIDEO_SECONDS = 10
_TAG = "OmniFlash"


def _normalize_model(raw):
    return pick_model(raw, _API_MODELS, _DEFAULT_MODEL)


def _normalize_mode(raw):
    return raw if raw in _MODES else _DEFAULT_MODE


def _normalize_aspect(ratio):
    return ratio if ratio in _ASPECTS else _DEFAULT_ASPECT


def _normalize_resolution(resolution):
    lower = (resolution or "").lower()
    return lower if lower in _RESOLUTIONS else _DEFAULT_RESOLUTION


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


def _pack_image_urls(urls):
    list_urls = [u for u in (urls or []) if u][:_MAX_IMAGES]
    if len(list_urls) == 2:
        raise ValueError("OmniFlash 参考图仅支持 0、1 或 3 张，不可传 2 张")
    return list_urls


def _build_body(model, mode, prompt, aspect_ratio, duration, resolution, image_urls, video_url, video_duration_sec=None):
    model = _normalize_model(model)
    preview = model == _PREVIEW
    images = _pack_image_urls(image_urls)
    has_video = bool(video_url)

    body = {
        "model": model,
        "prompt": prompt or "",
        "aspect_ratio": _normalize_aspect(aspect_ratio),
        "resolution": "720p" if preview else _normalize_resolution(resolution),
    }

    if preview:
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
    preview = model == _PREVIEW

    want_video = bool((video_path or "").strip()) if preview else (mode == "video")
    max_images = _MAX_IMAGES if preview else _mode_max_images(mode)

    tensors = [t for t in (image_tensors or []) if t is not None]
    tensors = [] if max_images <= 0 else tensors[:max_images]
    image_urls = [upload_image(api_key, t) for t in tensors]

    video_url = ""
    video_duration_sec = None
    if want_video and (video_path or "").strip():
        video_url = upload_media_file(api_key, video_path, "video")
        video_duration_sec = _normalize_duration(duration)

    if not preview and mode == "video" and not video_url:
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
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
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
                       image_1=None, image_2=None, image_3=None,
                       video_path="", filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3] if t is not None]
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
