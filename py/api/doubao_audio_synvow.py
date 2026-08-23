# -*- coding: utf-8 -*-
"""SynVow Doubao 语音合成 1.0"""
import json
import os

import torch
from comfy_extras.nodes_audio import load as load_audio_file

from . import synvow_auth
from .model_display import combo_models, resolve_model
from .media_common import (
    download_audio,
    extract_result_url,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_media_file,
)

_MODEL = "doubao-seed-audio-1.0"
_MODELS = combo_models([_MODEL])
_FORMATS = ["wav", "mp3"]
_SAMPLE_RATES_WAV = [8000, 16000, 24000, 32000, 40000, 44100, 48000]
_SAMPLE_RATES_MP3 = [8000, 16000, 24000, 32000, 44100, 48000]
_SAMPLE_RATE_CHOICES = [str(n) for n in _SAMPLE_RATES_WAV]
_TAG = "DoubaoAudio"
_MAX_REFS = 3


def _clamp_sample_rate(fmt, rate):
    allowed = _SAMPLE_RATES_MP3 if fmt == "mp3" else _SAMPLE_RATES_WAV
    try:
        n = int(float(rate))
    except (TypeError, ValueError):
        n = 24000
    return n if n in allowed else 24000


def _clamp_int(raw, lo, hi, default=0):
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        n = default
    return max(lo, min(hi, n))


def _empty_audio():
    return {"waveform": torch.zeros((1, 1, 1), dtype=torch.float32), "sample_rate": 44100}


def _load_audio(path):
    if not path or not os.path.isfile(path):
        return _empty_audio()
    waveform, sample_rate = load_audio_file(path)
    return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sample_rate)}


def _build_body(model, prompt, fmt, sample_rate, speech_rate, loudness_rate, pitch_rate, audio_urls):
    fmt = "mp3" if fmt == "mp3" else "wav"
    text = (prompt or "").strip()
    body = {
        "model": resolve_model(model, _MODEL),
        "text_prompt": text or None,
        "format": fmt,
        "sample_rate": _clamp_sample_rate(fmt, sample_rate),
        "speech_rate": _clamp_int(speech_rate, -50, 100),
        "loudness_rate": _clamp_int(loudness_rate, -50, 100),
        "pitch_rate": _clamp_int(pitch_rate, -12, 12),
    }
    if audio_urls:
        body["audio_url"] = audio_urls
    return body


def _pick_audio_url(inner, data):
    for src in (inner, data):
        if not isinstance(src, dict):
            continue
        url = (
            extract_result_url(src)
            or src.get("cld2AudioUrl")
            or src.get("audio_url")
            or src.get("audioUrl")
        )
        if isinstance(url, list):
            url = next((u for u in url if isinstance(u, str) and u.startswith("http")), "")
        if isinstance(url, str) and url.startswith("http"):
            return url
        nested = src.get("data") if isinstance(src.get("data"), dict) else {}
        for item in (nested, nested.get("data") if isinstance(nested.get("data"), dict) else {}):
            if not isinstance(item, dict):
                continue
            u = item.get("cld2AudioUrl") or item.get("audio_url") or item.get("audioUrl")
            if isinstance(u, list):
                u = next((x for x in u if isinstance(x, str) and x.startswith("http")), "")
            if isinstance(u, str) and u.startswith("http"):
                return u
            items = item.get("items")
            if isinstance(items, list):
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    u = it.get("cld2AudioUrl") or it.get("audio_url") or it.get("audioUrl")
                    if isinstance(u, str) and u.startswith("http"):
                        return u
    return ""


class SynVowDoubaoAudio:
    FUNCTION = "generate_audio"
    CATEGORY = "💫SynVow_api/api/音频"
    DESCRIPTION = "SynVow Doubao 语音合成 1.0"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (_MODELS, {"default": _MODELS[0]}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "format": (_FORMATS, {"default": "wav"}),
                "sample_rate": (_SAMPLE_RATE_CHOICES, {"default": "24000"}),
                "speech_rate": ("INT", {"default": 0, "min": -50, "max": 100}),
                "loudness_rate": ("INT", {"default": 0, "min": -50, "max": 100}),
                "pitch_rate": ("INT", {"default": 0, "min": -12, "max": 12}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "audio_path_1": ("STRING", {"multiline": False, "default": ""}),
                "audio_path_2": ("STRING", {"multiline": False, "default": ""}),
                "audio_path_3": ("STRING", {"multiline": False, "default": ""}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "audio_path", "audio_url", "task_info")
    IS_CHANGED = staticmethod(is_changed_by_inputs)

    def generate_audio(self, model, prompt, format, sample_rate, speech_rate, loudness_rate,
                       pitch_rate, seed=0, audio_path_1="", audio_path_2="", audio_path_3="",
                       filename="", save_path=""):
        del seed
        api_key = synvow_auth.read_api_key()
        try:
            refs = [p for p in (audio_path_1, audio_path_2, audio_path_3) if (p or "").strip()][:_MAX_REFS]
            if not (prompt or "").strip() and not refs:
                raise ValueError("Doubao语音：请输入提示词，或接入参考音频（最多 3 段）")
            audio_urls = [upload_media_file(api_key, p, "audio") for p in refs]
            body = _build_body(
                model, prompt, format, sample_rate, speech_rate, loudness_rate, pitch_rate, audio_urls,
            )
            used_model = body["model"]
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            url = poll_edit_task(
                api_key, task_id, used_model, _TAG,
                consumption_id=consumption_id, timeout=1800, pick_url=_pick_audio_url,
            )
            ext = ".mp3" if body["format"] == "mp3" else ".wav"
            fname = filename or ""
            if fname and not fname.lower().endswith((".mp3", ".wav")):
                fname += ext
            path = download_audio(
                url, task_id, save_path, prefix="doubao", filename=fname or f"doubao_{task_id[:8]}{ext}",
            ) or ""
            audio = _load_audio(path)
            info = json.dumps({
                "status": "SUCCESS",
                "task_id": task_id,
                "model": used_model,
                "audio_url": url,
                "audio_path": path,
            }, ensure_ascii=False)
            return (audio, path, url, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowDoubaoAudio": SynVowDoubaoAudio,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowDoubaoAudio": "SynVow Doubao 语音",
}
