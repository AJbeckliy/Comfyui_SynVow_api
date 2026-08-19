# -*- coding: utf-8 -*-
"""SynVow Seedance 2.5 视频生成。"""
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

_MODEL = "doubao-seedance-2.5"
_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
_RESOLUTIONS = ["480p", "720p", "1080p"]
_DURATIONS = [str(i) for i in range(4, 31)]
_IMAGE_SLOTS = 12
_TAG = "Seedance25"


def _clamp_duration(raw):
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        n = 5
    return max(4, min(30, n))


def _build_body(prompt, ratio, duration, resolution, image_urls, video_url, audio_url, generate_audio):
    body = {
        "model": _MODEL,
        "prompt": prompt or "",
        "size": ratio if ratio in _RATIOS else "adaptive",
        "resolution": resolution if resolution in _RESOLUTIONS else "720p",
        "duration": _clamp_duration(duration),
        "generate_audio": bool(generate_audio),
    }
    if image_urls:
        body["image_urls"] = image_urls
    if video_url:
        body["video_urls"] = [video_url]
    if audio_url:
        body["audio_urls"] = [audio_url]
    return body


class SynVowSeedance25:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.5（doubao-seedance-2.5）"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")
    IS_CHANGED = staticmethod(is_changed_by_inputs)

    @classmethod
    def INPUT_TYPES(cls):
        optional = {f"image_{i}": ("IMAGE",) for i in range(1, _IMAGE_SLOTS + 1)}
        optional.update({
            "video_path": ("STRING", {"multiline": False, "default": ""}),
            "audio_path": ("STRING", {"multiline": False, "default": ""}),
            "filename": ("STRING", {"multiline": False, "default": ""}),
            "save_path": ("STRING", {"multiline": False, "default": ""}),
        })
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "ratio": (_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "720p"}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": optional,
        }

    def generate_video(self, prompt, ratio, duration, resolution, generate_audio=True, seed=0, **kwargs):
        api_key = synvow_auth.read_api_key()
        try:
            tensors = [kwargs.get(f"image_{i}") for i in range(1, _IMAGE_SLOTS + 1)]
            video_path = kwargs.get("video_path") or ""
            audio_path = kwargs.get("audio_path") or ""
            image_urls = [upload_image(api_key, t) for t in tensors if t is not None]
            video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
            audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
            body = _build_body(
                prompt, ratio, duration, resolution, image_urls, video_url, audio_url, generate_audio,
            )
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            url = poll_edit_task(api_key, task_id, _MODEL, _TAG, consumption_id=consumption_id)
            path = download_video(
                url, task_id, kwargs.get("save_path") or "", prefix="seedance25",
                filename=kwargs.get("filename") or "",
            ) or ""
            info = json.dumps({
                "status": "SUCCESS",
                "task_id": task_id,
                "model": _MODEL,
                "video_url": url,
                "video_path": path,
                "seed": seed,
            }, ensure_ascii=False)
            result = (path, url, info)
        except Exception as e:
            print(f"[{_TAG}] Error: {e}")
            result = ("", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        synvow_auth.refresh_balance()
        return result


NODE_CLASS_MAPPINGS = {
    "SynVowSeedance25": SynVowSeedance25,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSeedance25": "SynVow Seedance 2.5",
}
