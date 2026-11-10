# -*- coding: utf-8 -*-
"""SynVow Muse Video。"""
import json

from . import synvow_auth
from .model_display import combo_models, display_name
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
)

_MODEL = "muse-video-wd"
_MODELS = combo_models([_MODEL])
_RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3"]
_DURATION = 10
_RESOLUTION = "720p"
_MAX_IMAGES = 9
_TAG = "MuseVideo"


def _build_body(prompt, ratio, image_urls):
    body = {
        "model": _MODEL,
        "prompt": prompt or "",
        "aspect_ratio": ratio if ratio in _RATIOS else _RATIOS[0],
        "duration": _DURATION,
        "resolution": _RESOLUTION,
    }
    urls = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    if urls:
        body["image_urls"] = urls
    return body


class SynVowMuseVideo:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Muse Video"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": display_name(_MODEL)}),
                "aspect_ratio": (_RATIOS, {"default": "16:9"}),
                "duration": ([str(_DURATION)], {"default": str(_DURATION)}),
                "resolution": ([_RESOLUTION], {"default": _RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                **{f"image_{i}": ("IMAGE",) for i in range(1, _MAX_IMAGES + 1)},
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")
    IS_CHANGED = staticmethod(is_changed_by_inputs)

    def generate_video(self, prompt, model, aspect_ratio, duration, resolution, seed=0, **kwargs):
        del model, duration, resolution
        api_key = synvow_auth.read_api_key()
        try:
            tensors = [kwargs.get(f"image_{i}") for i in range(1, _MAX_IMAGES + 1)]
            urls = [upload_image(api_key, t) for t in tensors if t is not None]
            body = _build_body(prompt, aspect_ratio, urls)
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id)
            path = download_video(
                url, task_id, kwargs.get("save_path") or "", prefix="muse",
                filename=kwargs.get("filename") or "",
            ) or ""
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id, "model": _MODEL,
                "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            return (path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {"SynVowMuseVideo": SynVowMuseVideo}
NODE_DISPLAY_NAME_MAPPINGS = {"SynVowMuseVideo": "SynVow Muse Video"}
