# -*- coding: utf-8 -*-
"""
SynVow Seedance 视频生成
"""
import json

from . import synvow_auth
from .media_common import (
    as_comfy_video,
    download_video,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_image,
    upload_media_file,
)

_QUAN_NENG = "seedance2.0-全能"
_MODELS = [
    _QUAN_NENG,
    "seedance-2.0-mini",
    "seedance-2.0",
    "seedance-2.0-fast",
    "seedance-2.0-face",
    "seedance-2.0-fast-face",
]
_DEFAULT_MODEL = _QUAN_NENG
_RATIOS = ["adaptive", "16:9", "9:16", "4:3", "3:4", "1:1", "21:9"]
_DURATIONS = [str(i) for i in range(4, 16)]
_RESOLUTIONS = ["480p", "720p", "1080p", "4K"]
_MODES = ["quan_neng", "edit", "extend"]
_VERSIONS = ["标准", "快速", "Mini"]
_DEFAULT_MODE = "quan_neng"
_DEFAULT_VERSION = "标准"
_SUPPORT_1080 = {"seedance-2.0", "seedance-2.0-face"}
_TAG = "Seedance"


def _clamp_duration(raw):
    try:
        n = int(float(raw))
    except Exception:
        n = 5
    return max(4, min(15, n))


def _coerce_quan_neng(version, resolution):
    version = version or _DEFAULT_VERSION
    resolution = resolution if resolution in _RESOLUTIONS else "720p"
    if resolution in ("1080p", "4K") and version != "标准":
        return "标准", resolution
    if version != "标准" and resolution not in ("480p", "720p"):
        return version, "720p"
    return version, resolution


def _coerce_model_for_1080(model):
    if model in _SUPPORT_1080:
        return model
    if model == "seedance-2.0-fast":
        return "seedance-2.0"
    if model == "seedance-2.0-fast-face":
        return "seedance-2.0-face"
    return _DEFAULT_MODEL


def _normalize_resolution(model, resolution):
    res = resolution if resolution in ("480p", "720p", "1080p") else "720p"
    if res == "1080p" and model not in _SUPPORT_1080:
        return "720p"
    return res


def _collect_refs(api_key, image_tensors, video_path, audio_path):
    image_urls = [upload_image(api_key, t) for t in (image_tensors or []) if t is not None]
    video_url = upload_media_file(api_key, video_path, "video") if video_path else ""
    audio_url = upload_media_file(api_key, audio_path, "audio") if audio_path else ""
    return image_urls, video_url, audio_url


def _validate_quan_neng(mode, image_urls, video_url):
    mode = mode or _DEFAULT_MODE
    if mode in ("edit", "extend"):
        if not video_url:
            label = "编辑视频" if mode == "edit" else "延长视频"
            raise ValueError(f"seedance2.0-全能「{label}」模式：请传入一个视频")
        return
    if not image_urls and not video_url:
        raise ValueError("seedance2.0-全能「全能参考」模式：请至少传入一张图像或一个视频")


def _build_body(model, prompt, ratio, duration, resolution, with_audio,
                mode, version, image_urls, video_url, audio_url):
    duration_n = _clamp_duration(duration)
    if model == _QUAN_NENG:
        version, resolution = _coerce_quan_neng(version, resolution)
        mode = mode or _DEFAULT_MODE
        params = {
            "_quan_neng_mode": mode,
            "version": version,
            "duration": str(duration_n),
            "aspect_ratio": ratio or "adaptive",
            "resolution": resolution,
        }
        use_img_audio = mode not in ("edit", "extend")
        if use_img_audio and image_urls:
            params["image_url"] = ",".join(image_urls[:9])
        if video_url:
            params["video_url"] = video_url
        if use_img_audio and audio_url:
            params["audio_url"] = audio_url
        return {"model": model, "prompt": prompt, "params": params}

    if resolution == "1080p":
        model = _coerce_model_for_1080(model)
    body = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": ratio or "adaptive",
        "duration": duration_n,
        "resolution": _normalize_resolution(model, resolution),
        "with_audio": bool(with_audio),
    }
    if image_urls:
        body["image_urls"] = image_urls[:9]
    if video_url:
        body["video_url"] = video_url
    if audio_url:
        body["audio_url"] = audio_url
    return body


def _run_once(api_key, prompt, model, ratio, duration, resolution, with_audio,
              mode, version, image_tensors, video_path, audio_path,
              save_path="", filename=""):
    model = model if model in _MODELS else _DEFAULT_MODEL
    image_urls, video_url, audio_url = _collect_refs(api_key, image_tensors, video_path, audio_path)
    if model == _QUAN_NENG:
        _validate_quan_neng(mode, image_urls, video_url)
    body = _build_body(
        model, prompt, ratio, duration, resolution, with_audio,
        mode, version, image_urls, video_url, audio_url,
    )
    submit_model = body.get("model") or model
    task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
    url = poll_edit_task(api_key, task_id, submit_model, _TAG, consumption_id=consumption_id)
    path = download_video(url, task_id, save_path, prefix="seedance", filename=filename) or ""
    return path, url, task_id, submit_model


class SynVowSeedance:
    FUNCTION = "generate_video"
    CATEGORY = "💫SynVow_api/api/视频"
    DESCRIPTION = "SynVow Seedance"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _DEFAULT_MODEL}),
                "ratio": (_RATIOS, {"default": "adaptive"}),
                "duration": (_DURATIONS, {"default": "5"}),
                "resolution": (_RESOLUTIONS, {"default": "720p"}),
                "with_audio": ("BOOLEAN", {"default": True}),
                "mode": (_MODES, {"default": _DEFAULT_MODE}),
                "version": (_VERSIONS, {"default": _DEFAULT_VERSION}),
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

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video", "video_path", "video_url", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_video(self, prompt, model, ratio, duration, resolution, with_audio, mode, version, seed=0,
                       image_1=None, image_2=None, image_3=None, image_4=None,
                       image_5=None, image_6=None, image_7=None, image_8=None, image_9=None,
                       video_path="", audio_path="", filename="", save_path=""):
        api_key = synvow_auth.read_api_key()
        tensors = [t for t in [image_1, image_2, image_3, image_4, image_5,
                               image_6, image_7, image_8, image_9] if t is not None]
        try:
            path, url, task_id, used_model = _run_once(
                api_key, prompt, model, ratio, duration, resolution, with_audio,
                mode, version, tensors, video_path, audio_path, save_path, filename,
            )
            info = json.dumps({
                "status": "SUCCESS", "task_id": task_id,
                "model": used_model, "video_url": url, "video_path": path, "seed": seed,
            }, ensure_ascii=False)
            synvow_auth.refresh_balance()
            return (as_comfy_video(path), path, url, info)
        except Exception as e:
            print(f"[Seedance] Error: {e}")
            synvow_auth.refresh_balance()
            return (as_comfy_video(""), "", "", json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))


NODE_CLASS_MAPPINGS = {
    "SynVowSeedance": SynVowSeedance,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSeedance": "SynVow Seedance",
}
