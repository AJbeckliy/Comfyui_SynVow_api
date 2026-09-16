# -*- coding: utf-8 -*-
"""SynVow MiniMax H3 视频生成。"""
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

_API_MODELS = ["MiniMax-H3", "MiniMax-H3-dj"]
_MODELS = combo_models(_API_MODELS)
_DEFAULT_MODEL = "MiniMax-H3"
_RESOLUTIONS = ["2K", "768P"]
_DURATIONS = [str(i) for i in range(4, 16)]
_ASPECT_RATIOS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"]
_R2V_ASPECT_RATIOS = ["adaptive", *_ASPECT_RATIOS]
_TAG = "MiniMax"
_OPTIONAL_SAVE = {
    "filename": ("STRING", {"multiline": False, "default": ""}),
    "save_path": ("STRING", {"multiline": False, "default": ""}),
}


def _clamp_duration(raw):
    try:
        duration = round(float(raw))
    except (TypeError, ValueError):
        duration = 5
    return max(4, min(15, duration))


def _pick_ratio(ratio, allowed, default):
    return ratio if ratio in allowed else default


def _pick_resolution(raw):
    return raw if raw in _RESOLUTIONS else "2K"


def _content(prompt, image_roles=None, video_url="", audio_url=""):
    content = [{"type": "text", "text": prompt}]
    for item in image_roles or []:
        content.append({
            "type": "image_url",
            "image_url": {"url": item["url"]},
            "role": item["role"],
        })
    if video_url:
        content.append({"type": "video_url", "video_url": {"url": video_url}, "role": "reference_video"})
    if audio_url:
        content.append({"type": "audio_url", "audio_url": {"url": audio_url}, "role": "reference_audio"})
    return content


def _base_body(model, prompt, duration, resolution, ratio=None, image_roles=None, video_url="", audio_url=""):
    body = {
        "model": model,
        "prompt": prompt,
        "content": _content(prompt, image_roles, video_url, audio_url),
        "duration": _clamp_duration(duration),
        "resolution": _pick_resolution(resolution),
    }
    if ratio is not None:
        body["ratio"] = ratio
    return body


def _generate(build_body, save_path="", filename=""):
    try:
        api_key = synvow_auth.read_api_key()
        body = build_body(api_key)
        model = body["model"]
        task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
        url = poll_edit_task(api_key, task_id, model, _TAG, consumption_id=consumption_id)
        path = download_video(url, task_id, save_path, prefix="minimax", filename=filename) or ""
        return path, url, json.dumps({
            "status": "SUCCESS",
            "task_id": task_id,
            "model": model,
            "video_url": url,
            "video_path": path,
        }, ensure_ascii=False)
    finally:
        synvow_auth.refresh_balance()


class _MiniMaxNode:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")
    IS_CHANGED = staticmethod(is_changed_by_inputs)


class SynVowMiniMaxTextToVideo(_MiniMaxNode):
    DESCRIPTION = "SynVow MiniMax H3 文生视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _MODELS[0]}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "16:9"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "2K"}),
            },
            "optional": dict(_OPTIONAL_SAVE),
        }

    def generate_video(self, prompt, model, aspect_ratio, duration, resolution="2K", filename="", save_path=""):
        model = pick_model(model, _API_MODELS, _DEFAULT_MODEL)
        return _generate(
            lambda _api_key: _base_body(
                model, prompt, duration, resolution,
                ratio=_pick_ratio(aspect_ratio, _ASPECT_RATIOS, "16:9"),
            ),
            save_path, filename,
        )


class SynVowMiniMaxFirstLastFrame(_MiniMaxNode):
    DESCRIPTION = "SynVow MiniMax H3 首尾帧视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _MODELS[0]}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "2K"}),
            },
            "optional": {
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
                **_OPTIONAL_SAVE,
            },
        }

    def generate_video(self, prompt, model, duration, resolution="2K", first_frame=None, last_frame=None,
                       filename="", save_path=""):
        model = pick_model(model, _API_MODELS, _DEFAULT_MODEL)

        def build(api_key):
            roles = []
            if first_frame is not None:
                roles.append({"url": upload_image(api_key, first_frame), "role": "first_frame"})
            if last_frame is not None:
                roles.append({"url": upload_image(api_key, last_frame), "role": "last_frame"})
            if not roles:
                raise ValueError("请至少传入首帧或末帧图像")
            return _base_body(model, prompt, duration, resolution, image_roles=roles)

        return _generate(build, save_path, filename)


class SynVowMiniMaxReferenceToVideo(_MiniMaxNode):
    DESCRIPTION = "SynVow MiniMax H3 多模态参考视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _MODELS[0]}),
                "aspect_ratio": (_R2V_ASPECT_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "2K"}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "video_path": ("STRING", {"multiline": False, "default": ""}),
                "audio_path": ("STRING", {"multiline": False, "default": ""}),
                **_OPTIONAL_SAVE,
            },
        }

    def generate_video(self, prompt, model, aspect_ratio, duration, resolution="2K", image_1=None, image_2=None,
                       video_path="", audio_path="", filename="", save_path=""):
        model = pick_model(model, _API_MODELS, _DEFAULT_MODEL)

        def build(api_key):
            image_urls = [upload_image(api_key, image) for image in (image_1, image_2) if image is not None]
            video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
            audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
            if not image_urls and not video_url and not audio_url:
                raise ValueError("请至少传入图像、视频或音频之一")
            roles = [{"url": url, "role": "reference_image"} for url in image_urls]
            return _base_body(
                model, prompt, duration, resolution,
                ratio=_pick_ratio(aspect_ratio, _R2V_ASPECT_RATIOS, "adaptive"),
                image_roles=roles,
                video_url=video_url,
                audio_url=audio_url,
            )

        return _generate(build, save_path, filename)


NODE_CLASS_MAPPINGS = {
    "SynVowMiniMaxTextToVideo": SynVowMiniMaxTextToVideo,
    "SynVowMiniMaxFirstLastFrame": SynVowMiniMaxFirstLastFrame,
    "SynVowMiniMaxReferenceToVideo": SynVowMiniMaxReferenceToVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowMiniMaxTextToVideo": "SynVow MiniMax 文生视频",
    "SynVowMiniMaxFirstLastFrame": "SynVow MiniMax 首尾帧视频",
    "SynVowMiniMaxReferenceToVideo": "SynVow MiniMax 多模态参考视频",
}
