# -*- coding: utf-8 -*-
"""
SynVow Seedance 2.0 视频生成 (720P)

POST /api/models/image/edit?async=true
payload: model/resolution/duration/ratio + content[]（text / image_url / video_url / audio_url）
"""
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

_MODEL_UI = "seedance2.0"
_API_MODEL = "seedance_2_720p"
_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
_DURATIONS = [str(i) for i in range(4, 16)]
_RESOLUTIONS = ["720p"]
_TAG = "Seedance720P"
_MAX_IMAGES = 8


def _clamp_duration(raw):
    try:
        n = int(float(raw))
    except Exception:
        n = 5
    return max(4, min(15, n))


def _build_content(prompt, image_urls=None, video_url="", audio_url=""):
    content = [{"type": "text", "text": prompt or ""}]
    for url in image_urls or []:
        if not url:
            continue
        content.append({
            "type": "image_url",
            "image_url": {"url": url},
            "role": "reference_image",
        })
    if video_url:
        content.append({
            "type": "video_url",
            "video_url": {"url": video_url},
            "role": "reference_video",
        })
    if audio_url:
        content.append({
            "type": "audio_url",
            "audio_url": {"url": audio_url},
            "role": "reference_audio",
        })
    return content


def _build_body(prompt, ratio, duration, resolution,
                image_urls=None, video_url="", audio_url="",
                generate_audio=True, watermark=False):
    duration_n = _clamp_duration(duration)
    return {
        "model": _API_MODEL,
        "resolution": resolution if resolution in _RESOLUTIONS else "720p",
        "duration": duration_n,
        "ratio": ratio or "adaptive",
        "generate_audio": bool(generate_audio),
        "watermark": bool(watermark),
        "content": _build_content(prompt, image_urls, video_url, audio_url),
    }


def _submit(api_key, prompt, ratio, duration, resolution,
            image_urls=None, video_url="", audio_url="",
            generate_audio=True, watermark=False):
    body = _build_body(
        prompt, ratio, duration, resolution, image_urls, video_url, audio_url,
        generate_audio=generate_audio, watermark=watermark,
    )
    n_img = sum(1 for c in body["content"] if c.get("type") == "image_url")
    has_video = any(c.get("type") == "video_url" for c in body["content"])
    has_audio = any(c.get("type") == "audio_url" for c in body["content"])
    print(
        f"[{_TAG}] 提交: model={_API_MODEL} ratio={body['ratio']} "
        f"duration={body['duration']} resolution={body['resolution']} "
        f"generate_audio={body['generate_audio']} watermark={body['watermark']} "
        f"images={n_img} video={int(has_video)} audio={int(has_audio)}"
    )
    return submit_edit_async(api_key, body, _TAG)


def _collect_refs(api_key, tensors, video_path="", audio_path=""):
    image_urls = [
        upload_image(api_key, t)
        for t in (tensors or []) if t is not None
    ][:_MAX_IMAGES]
    video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
    audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
    return image_urls, video_url, audio_url


def _run_once(api_key, prompt, ratio, duration, resolution, tensors,
              video_path="", audio_path="", save_path="", filename="",
              generate_audio=True, watermark=False):
    image_urls, video_url, audio_url = _collect_refs(api_key, tensors, video_path, audio_path)
    task_id, consumption_id = _submit(
        api_key, prompt, ratio, duration, resolution, image_urls, video_url, audio_url,
        generate_audio=generate_audio, watermark=watermark,
    )
    url = poll_edit_task(api_key, task_id, _API_MODEL, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="seedance2", filename=filename) or ""
    return path, url, task_id


_OPTIONAL_MEDIA = {
    "image_1": ("IMAGE",), "image_2": ("IMAGE",),
    "image_3": ("IMAGE",), "image_4": ("IMAGE",),
    "image_5": ("IMAGE",), "image_6": ("IMAGE",),
    "image_7": ("IMAGE",), "image_8": ("IMAGE",),
    "video_path": ("STRING", {"multiline": False, "default": ""}),
    "audio_path": ("STRING", {"multiline": False, "default": ""}),
    "filename": ("STRING", {"multiline": False, "default": ""}),
    "save_path": ("STRING", {"multiline": False, "default": ""}),
}


class SynVowSeedance2Video:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance 2.0 视频生成 (720P，content 协议)"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "模型": ([_MODEL_UI], {"default": _MODEL_UI}),
                "ratio": (_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "720p"}),
                "generate_audio": ("BOOLEAN", {"default": True}),
                "watermark": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": dict(_OPTIONAL_MEDIA),
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, 模型, ratio, duration, resolution, seed=0,
                       generate_audio=True, watermark=False,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None, image_8=None,
                       video_path="", audio_path="", filename="", save_path=""):
        del 模型
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4,
                               image_5, image_6, image_7, image_8] if t is not None]
        try:
            path, url, task_id = _run_once(
                api_key, prompt, ratio, duration, resolution, tensors,
                video_path=video_path or "", audio_path=audio_path or "",
                save_path=save_path, filename=filename,
                generate_audio=generate_audio, watermark=watermark,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": _API_MODEL, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            synvow_auth.refresh_balance()
            return (path, url, info)
        except Exception as e:
            print(f"[{_TAG}] Error: {e}")
            synvow_auth.refresh_balance()
            return (
                "", "",
                json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
            )


NODE_CLASS_MAPPINGS = {
    "SynVowSeedance2Video": SynVowSeedance2Video,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSeedance2Video": "SynVow Seedance2.0 视频生成 (720P)",
}
