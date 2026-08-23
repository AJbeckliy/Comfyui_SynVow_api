# -*- coding: utf-8 -*-
"""
SynVow Grok 1.5 Video 生成
"""
import json

from . import synvow_auth
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
)

_MODEL = "grok-1.5-video"
_MAX_IMAGES = 6
_SIZES = ["16:9", "9:16", "1:1", "3:2", "2:3"]
_QUALITIES = ["480p", "720p"]
_DURATIONS = [str(i) for i in range(6, 31)]
_DEFAULT_SIZE = "16:9"
_DEFAULT_QUALITY = "480p"
_DEFAULT_DURATION = "6"
_TAG = "GrokVideo"


def _clamp_duration(raw):
    try:
        n = int(float(raw))
    except Exception:
        n = 6
    return max(6, min(30, n))


def _build_body(prompt, size, duration, quality, image_urls):
    body = {
        "model": _MODEL,
        "prompt": prompt,
        "size": size if size in _SIZES else _DEFAULT_SIZE,
        "duration": _clamp_duration(duration),
        "quality": quality if quality in _QUALITIES else _DEFAULT_QUALITY,
    }
    urls = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    if urls:
        body["image_urls"] = urls
    return body


def _run_once(api_key, prompt, size, duration, quality, image_tensors, save_path="", filename=""):
    image_urls = [upload_image(api_key, t) for t in (image_tensors or []) if t is not None][:_MAX_IMAGES]
    body = _build_body(prompt, size, duration, quality, image_urls)
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="grok", filename=filename) or ""
    return path, url, task_id


class SynVowGrokVideo:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Grok 1.5 Video"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "size": (_SIZES, {"default": _DEFAULT_SIZE}),
                "duration": (_DURATIONS, {"default": _DEFAULT_DURATION}),
                "quality": (_QUALITIES, {"default": _DEFAULT_QUALITY}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, size, duration, quality, seed=0,
                       image_1=None, image_2=None, image_3=None,
                       image_4=None, image_5=None, image_6=None,
                       filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4, image_5, image_6] if t is not None]
        try:
            path, url, task_id = _run_once(
                api_key, prompt, size, duration, quality, tensors, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": _MODEL, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            return (path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowGrokVideo": SynVowGrokVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGrokVideo": "SynVow Grok Video",
}
