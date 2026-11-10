# -*- coding: utf-8 -*-
"""
SynVow Omni-Flash 视频生成
"""
import json

from . import synvow_auth
from .model_display import combo_models, display_name
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
    upload_media_file,
)

_MODEL = "omni-1.2-flash"
_MODELS = combo_models([_MODEL])
_ASPECTS = ["16:9", "9:16"]
_RESOLUTIONS = ["360p", "720p", "1080p", "4k"]
_DURATIONS = [str(i) for i in range(3, 16)]
_DEFAULT_ASPECT = "16:9"
_DEFAULT_RESOLUTION = "720p"
_DEFAULT_DURATION = "6"
_MAX_IMAGES = 9
_TAG = "OmniFlash"


def _normalize_aspect(ratio):
    return ratio if ratio in _ASPECTS else _DEFAULT_ASPECT


def _normalize_resolution(resolution):
    lower = (resolution or "").lower()
    if lower == "2160p":
        lower = "4k"
    return lower if lower in _RESOLUTIONS else _DEFAULT_RESOLUTION


def _normalize_duration(raw):
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        return int(_DEFAULT_DURATION)
    return max(3, min(15, n))


def _build_body(prompt, aspect_ratio, duration, resolution, image_urls, video_url):
    images = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    text = (prompt or "").strip()
    if not text and not images and not video_url:
        raise ValueError("OmniFlash 请输入提示词，或接入参考图/视频")
    body = {
        "model": _MODEL,
        "aspect_ratio": _normalize_aspect(aspect_ratio),
        "resolution": _normalize_resolution(resolution),
        "duration": _normalize_duration(duration),
    }
    if text:
        body["prompt"] = text
    if images:
        body["image_urls"] = images
    if video_url:
        body["video_urls"] = [video_url]
    return body


def _run_once(api_key, prompt, aspect_ratio, duration, resolution,
              image_tensors, video_path, save_path="", filename=""):
    tensors = [t for t in (image_tensors or []) if t is not None][:_MAX_IMAGES]
    image_urls = [upload_image(api_key, t) for t in tensors]
    video_url = upload_media_file(api_key, video_path, "video") if (video_path or "").strip() else ""
    body = _build_body(prompt, aspect_ratio, duration, resolution, image_urls, video_url)
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="omni", filename=filename) or ""
    return path, url, task_id


class SynVowOmniFlash:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Omni-Flash"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": display_name(_MODEL)}),
                "aspect_ratio": (_ASPECTS, {"default": _DEFAULT_ASPECT}),
                "duration": (_DURATIONS, {"default": _DEFAULT_DURATION}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
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

    def generate_video(self, prompt, model, aspect_ratio, duration, resolution, seed=0,
                       image_1=None, image_2=None, image_3=None, image_4=None, image_5=None,
                       image_6=None, image_7=None, image_8=None, image_9=None,
                       video_path="", filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4, image_5,
                               image_6, image_7, image_8, image_9] if t is not None]
        try:
            del model
            path, url, task_id = _run_once(
                api_key, prompt, aspect_ratio, duration, resolution,
                tensors, video_path, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": _MODEL, "video_url": url, "video_path": path, "seed": seed,
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
