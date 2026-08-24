# -*- coding: utf-8 -*-
"""
SynVow wan-video 视频生成
"""
import json

from . import synvow_auth
from .model_display import combo_models, pick_model
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
    upload_media_file,
)

_API_MODELS = ["wan3.0-video-wd"]
_DEFAULT_MODEL = "wan3.0-video-wd"
_MODELS = combo_models(_API_MODELS)
_MAX_IMAGES = 9
_RESOLUTIONS = ["480P", "720P", "1080P"]
_SIZES = ["adaptive", "16:9", "4:3", "1:1", "3:4", "9:16"]
_DURATIONS = [str(i) for i in range(2, 31)]
_DEFAULT_RESOLUTION = "720P"
_DEFAULT_SIZE = "16:9"
_DEFAULT_DURATION = 5
_TAG = "WanVideo"


def _normalize_model(model):
    return pick_model(model, _API_MODELS, _DEFAULT_MODEL)


def _normalize_resolution(raw):
    v = str(raw or "").upper()
    return v if v in _RESOLUTIONS else _DEFAULT_RESOLUTION


def _normalize_size(raw):
    return raw if raw in _SIZES else _DEFAULT_SIZE


def _clamp_duration(raw):
    try:
        n = int(float(raw))
    except Exception:
        n = _DEFAULT_DURATION
    return max(2, min(30, n))


def _build_body(prompt, model, resolution, size, duration, image_urls, video_urls, audio_urls):
    body = {
        "model": _normalize_model(model),
        "prompt": prompt or "",
        "resolution": _normalize_resolution(resolution),
        "size": _normalize_size(size),
        "duration": _clamp_duration(duration),
    }
    images = [u for u in (image_urls or []) if u][:_MAX_IMAGES]
    videos = [u for u in (video_urls or []) if u][:1]
    audios = [u for u in (audio_urls or []) if u][:1]
    if images:
        body["image_urls"] = images
    if videos:
        body["video_urls"] = videos
    if audios:
        body["audio_urls"] = audios
    return body


def _run_once(api_key, prompt, model, resolution, size, duration,
              image_tensors, video_path, audio_path, save_path="", filename=""):
    if not (prompt or "").strip():
        raise ValueError("wan-video 请输入提示词")
    image_urls = [upload_image(api_key, t) for t in (image_tensors or []) if t is not None][:_MAX_IMAGES]
    video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
    audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
    body = _build_body(
        prompt.strip(), model, resolution, size, duration,
        image_urls, [video_url] if video_url else [], [audio_url] if audio_url else [],
    )
    used_model = body.get("model") or _DEFAULT_MODEL
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(api_key, task_id, used_model, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="wan", filename=filename) or ""
    return path, url, task_id, used_model


class SynVowWanVideo:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow wan-video"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _MODELS[0]}),
                "size": (_SIZES, {"default": _DEFAULT_SIZE}),
                "duration": (_DURATIONS, {"default": str(_DEFAULT_DURATION)}),
                "resolution": (_RESOLUTIONS, {"default": _DEFAULT_RESOLUTION}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "video_path": ("STRING", {"default": "", "multiline": False, "placeholder": "参考视频本地路径或 URL"}),
                "audio_path": ("STRING", {"default": "", "multiline": False, "placeholder": "参考音频本地路径或 URL"}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, model, size, duration, resolution, seed=0,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None, image_8=None, image_9=None,
                       video_path="", audio_path="", filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4, image_5,
                               image_6, image_7, image_8, image_9] if t is not None]
        try:
            path, url, task_id, used_model = _run_once(
                api_key, prompt, model, resolution, size, duration,
                tensors, video_path, audio_path, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": used_model, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            return (path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowWanVideo": SynVowWanVideo,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowWanVideo": "SynVow wan-video",
}
