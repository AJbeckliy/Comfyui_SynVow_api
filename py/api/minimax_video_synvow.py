# -*- coding: utf-8 -*-
"""SynVow MiniMax H3 视频生成。"""
import json

from . import synvow_auth
from .media_common import (
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
    upload_media_file,
)

_MODEL = "MiniMax-H3"
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


def _base_body(prompt, duration, resolution, **extra):
    body = {
        "model": _MODEL,
        "prompt": prompt,
        "duration": _clamp_duration(duration),
        "resolution": _pick_resolution(resolution),
    }
    body.update(extra)
    return body


def _generate(build_body, save_path="", filename=""):
    try:
        api_key = synvow_auth.read_api_key()
        body = build_body(api_key)
        task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
        url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id)
        path = download_video(url, task_id, save_path, prefix="minimax", filename=filename) or ""
        result = path, url, json.dumps({
            "status": "SUCCESS",
            "task_id": task_id,
            "model": _MODEL,
            "video_url": url,
            "video_path": path,
        }, ensure_ascii=False)
    except Exception as e:
        print(f"[{_TAG}] Error: {e}")
        result = "", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
    synvow_auth.refresh_balance()
    return result


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
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "16:9"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "2K"}),
            },
            "optional": dict(_OPTIONAL_SAVE),
        }

    def generate_video(self, prompt, aspect_ratio, duration, resolution="2K", filename="", save_path=""):
        return _generate(
            lambda _api_key: _base_body(
                prompt, duration, resolution,
                aspect_ratio=_pick_ratio(aspect_ratio, _ASPECT_RATIOS, "16:9"),
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
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "2K"}),
            },
            "optional": {
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
                **_OPTIONAL_SAVE,
            },
        }

    def generate_video(self, prompt, duration, resolution="2K", first_frame=None, last_frame=None,
                       filename="", save_path=""):
        def build(api_key):
            roles = []
            if first_frame is not None:
                roles.append({"url": upload_image(api_key, first_frame), "role": "first_frame"})
            if last_frame is not None:
                roles.append({"url": upload_image(api_key, last_frame), "role": "last_frame"})
            if not roles:
                raise ValueError("请至少传入首帧或末帧图像")
            return _base_body(prompt, duration, resolution, image_with_roles=roles)

        return _generate(build, save_path, filename)


class SynVowMiniMaxReferenceToVideo(_MiniMaxNode):
    DESCRIPTION = "SynVow MiniMax H3 多模态参考视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
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

    def generate_video(self, prompt, aspect_ratio, duration, resolution="2K", image_1=None, image_2=None,
                       video_path="", audio_path="", filename="", save_path=""):
        def build(api_key):
            image_urls = [upload_image(api_key, image) for image in (image_1, image_2) if image is not None]
            video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
            audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
            if not image_urls and not video_url and not audio_url:
                raise ValueError("请至少传入图像、视频或音频之一")
            extra = {"aspect_ratio": _pick_ratio(aspect_ratio, _R2V_ASPECT_RATIOS, "adaptive")}
            if image_urls:
                extra["image_urls"] = image_urls
            if video_url:
                extra["video_urls"] = [video_url]
            if audio_url:
                extra["audio_urls"] = [audio_url]
            return _base_body(prompt, duration, resolution, **extra)

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
