# -*- coding: utf-8 -*-
"""
SynVow Veo31 视频生成
"""
import json

from . import synvow_auth
from .model_display import combo_models, pick_model
from .media_common import (
    download_video,
    extract_result_url,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
)

_API_MODELS = ["veo3.1"]
_DEFAULT_MODEL = "veo3.1"
_MODELS = combo_models(_API_MODELS)
_MAX_IMAGES = 2
_ASPECTS = ["16:9", "9:16"]
_DURATIONS = ["8"]
_DEFAULT_ASPECT = "16:9"
_DEFAULT_DURATION = "8"
_QUALITY = "1080p"
_TAG = "Veo31"


def _normalize_model(model):
    return pick_model(model, _API_MODELS, _DEFAULT_MODEL)


def _build_body(prompt, model, aspect_ratio, duration, image_urls):
    model = _normalize_model(model)
    images = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    return {
        "model": model,
        "prompt": prompt or "",
        "params": {
            "aspect_ratio": aspect_ratio if aspect_ratio in _ASPECTS else _DEFAULT_ASPECT,
            "duration": str(duration) if str(duration) in _DURATIONS else _DEFAULT_DURATION,
            "enable_upsample": True,
            "enhance_prompt": True,
            "generation_mode": "fast",
            "generation_type": "TEXT",
            "images": images,
            "quality": _QUALITY,
        },
    }


def _check_success(inner):
    state = str(inner.get("state") or "").lower()
    status = str(inner.get("status") or "")
    if state == "success" or status == "已完成":
        return True, state or status
    return False, state or status


def _check_failed(inner):
    state = str(inner.get("state") or "").lower()
    if state in ("failure", "failed", "error"):
        return True, state
    status = str(inner.get("status") or inner.get("task_status") or "").upper()
    if status in ("FAILURE", "FAILED", "ERROR"):
        return True, status
    return False, status


def _pick_url(inner, data):
    return extract_result_url(inner) or extract_result_url(data)


def _run_once(api_key, prompt, model, aspect_ratio, duration, image_tensors, save_path="", filename=""):
    image_urls = [upload_image(api_key, t) for t in (image_tensors or []) if t is not None][:_MAX_IMAGES]
    body = _build_body(prompt, model, aspect_ratio, duration, image_urls)
    used_model = body.get("model") or _DEFAULT_MODEL
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(
        api_key, task_id, used_model, _TAG, consumption_id=consumption_id,
        check_success=_check_success, check_failed=_check_failed, pick_url=_pick_url,
    )
    path = download_video(url, task_id, save_path, prefix="veo31", filename=filename) or ""
    return path, url, task_id, used_model


class SynVowVeo31:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Veo31"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _MODELS[0]}),
                "aspect_ratio": (_ASPECTS, {"default": _DEFAULT_ASPECT}),
                "duration": (_DURATIONS, {"default": _DEFAULT_DURATION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, model, aspect_ratio, duration, seed=0,
                       image_1=None, image_2=None, filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2] if t is not None]
        try:
            path, url, task_id, used_model = _run_once(
                api_key, prompt, model, aspect_ratio, duration, tensors, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": used_model, "video_url": url, "video_path": path,
                "quality": _QUALITY, "seed": seed,
            }, ensure_ascii=False)
            return (path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowVeo31": SynVowVeo31,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVeo31": "SynVow Veo31",
}
