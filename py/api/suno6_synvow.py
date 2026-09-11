# -*- coding: utf-8 -*-
"""SynVow Suno 6：生成 / 翻唱 / 延长 × 灵感 / 自定义"""
import json
import os

import torch
from comfy_extras.nodes_audio import load as load_audio_file

from . import synvow_auth
from .media_common import (
    download_audio,
    is_changed_by_inputs,
    poll_edit_task,
    submit_edit_async,
    upload_media_file,
)
from .model_display import display_name

_TAG = "Suno6"
_TASK_GENERATE = "生成音乐"
_TASK_COVER = "翻唱"
_TASK_EXTEND = "延长"
_TASKS = [_TASK_GENERATE, _TASK_COVER, _TASK_EXTEND]
_MODE_INSPIRE = "灵感"
_MODE_CUSTOM = "自定义"
_MODES = [_MODE_INSPIRE, _MODE_CUSTOM]
_VERSIONS = ["v6", "v6-wild", "v6-mini"]
_VOCALS = ["自动", "男", "女"]
_VOCAL_API = {"男": "Male", "女": "Female"}
_REQUEST_MODEL = {
    _TASK_GENERATE: "suno6",
    _TASK_COVER: "suno6-fc",
    _TASK_EXTEND: "suno6-yc",
}
_SUCCESS = ("SUCCESS", "SUCCEED", "SUCCEEDED", "COMPLETED", "DONE", "FINISH", "FINISHED")
_FAILURE = ("FAILURE", "FAILED", "ERROR", "EXCEPTION")
_CONTINUE_MIN, _CONTINUE_MAX = 1, 480


def _empty_audio():
    return {"waveform": torch.zeros((1, 1, 1), dtype=torch.float32), "sample_rate": 44100}


def _load_audio(path):
    if not path or not os.path.isfile(path):
        return _empty_audio()
    waveform, sample_rate = load_audio_file(path)
    return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sample_rate)}


def _stack_audio(audios):
    if not audios:
        return _empty_audio()
    if len(audios) == 1:
        return audios[0]
    sr = int(audios[0].get("sample_rate") or 44100)
    waves = []
    max_t = 1
    for a in audios:
        w = a.get("waveform")
        if w is None:
            continue
        max_t = max(max_t, int(w.shape[-1]))
        waves.append(w)
    if not waves:
        return _empty_audio()
    padded = []
    for w in waves:
        if w.shape[-1] < max_t:
            w = torch.nn.functional.pad(w, (0, max_t - w.shape[-1]))
        padded.append(w)
    return {"waveform": torch.cat(padded, dim=0), "sample_rate": sr}


def _clamp_weight(raw):
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return 0.0
    return round(min(1.0, max(0.0, n)), 2)


def _clamp_duration(raw):
    try:
        n = int(round(float(raw) or 0))
    except (TypeError, ValueError):
        return 0
    if n <= 0:
        return 0
    return max(10, min(360, n))


def _clamp_continue(raw):
    try:
        n = int(round(float(raw)))
    except (TypeError, ValueError):
        n = _CONTINUE_MIN
    return max(_CONTINUE_MIN, min(_CONTINUE_MAX, n))


def _task(raw):
    v = str(raw or "").strip()
    return v if v in _REQUEST_MODEL else _TASK_GENERATE


def _custom(raw):
    return str(raw or "").strip() == _MODE_CUSTOM


def _version(raw):
    v = str(raw or "").strip()
    return v if v in _VERSIONS else _VERSIONS[0]


def _vocal(raw):
    return _VOCAL_API.get(str(raw or "").strip(), "")


def _apply_weights(body, style_weight, weirdness, audio_weight, weirdness_key):
    body["style_weight"] = _clamp_weight(style_weight)
    body[weirdness_key] = _clamp_weight(weirdness)
    body["audio_weight"] = _clamp_weight(audio_weight)


def _apply_tagged(body, prompt, title, style, negative, duration, style_weight, weirdness, audio_weight):
    body["prompt"] = prompt
    body["title"] = title
    body["tags"] = style
    body["negative_tags"] = negative
    if duration >= 10:
        body["duration_s"] = duration
    _apply_weights(body, style_weight, weirdness, audio_weight, "weirdness")


def _build_body(
    task_kind, mode, version, instrumental, vocal_gender, prompt, title, style, negative,
    duration, style_weight, weirdness, audio_weight, continue_at, audio_url,
):
    kind = _task(task_kind)
    custom = _custom(mode)
    instrumental = bool(instrumental)
    prompt = str(prompt or "").strip()
    title = str(title or "").strip()
    style = str(style or "").strip()
    negative = str(negative or "").strip()
    duration = _clamp_duration(duration)
    allow_empty = kind == _TASK_EXTEND or (kind == _TASK_GENERATE and custom and instrumental)
    if not prompt and not allow_empty:
        raise ValueError("suno 翻唱灵感方式请填写灵感提示词" if kind == _TASK_COVER and not custom else "suno 请输入提示词")
    if kind == _TASK_GENERATE and custom and (not title or not style):
        raise ValueError("suno 自定义方式请填写标题" if not title else "suno 自定义方式请填写风格")
    body = {"model": _REQUEST_MODEL[kind], "version": _version(version)}
    if kind != _TASK_GENERATE:
        if not audio_url:
            raise ValueError("suno 翻唱/延长请连接参考音频")
        body["audio_url"] = audio_url
    if kind == _TASK_EXTEND:
        body["continue_at"] = _clamp_continue(continue_at)
        _apply_tagged(body, prompt, title, style, negative, duration, style_weight, weirdness, audio_weight)
    elif kind == _TASK_COVER:
        body["custom"] = custom
        body["instrumental"] = instrumental
        if custom:
            _apply_tagged(body, prompt, title, style, negative, duration, style_weight, weirdness, audio_weight)
            body["max_mode"] = False
        else:
            body["gpt_description"] = prompt
    else:
        if instrumental:
            body["instrumental"] = True
        if custom:
            body["custom"] = True
            body["prompt"] = prompt
            body["title"] = title
            body["style"] = style
            if negative:
                body["negative_tags"] = negative
            if duration >= 10:
                body["duration"] = duration
        else:
            body["prompt"] = prompt
        _apply_weights(body, style_weight, weirdness, audio_weight, "weirdness_constraint")
    vocal = _vocal(vocal_gender)
    if (kind == _TASK_EXTEND or not instrumental) and vocal:
        body["vocal_gender"] = vocal
    return body, instrumental


def _item_url(it):
    if not isinstance(it, dict):
        return ""
    for key in ("audio_url", "cld2AudioUrl"):
        u = it.get(key)
        if isinstance(u, str) and u.startswith(("http://", "https://")):
            return u
    return ""


def _norm_text(v):
    return v.strip() if isinstance(v, str) else ""


def _pick_lyrics(it):
    lyrics = _norm_text(it.get("lyrics") or it.get("lyric"))
    prompt = _norm_text(it.get("prompt"))
    return lyrics if lyrics and lyrics != prompt else ""


def _collect_tracks(node):
    if not node:
        return []
    if isinstance(node, list):
        tracks = [it for it in node if _item_url(it)]
        return tracks or [t for it in node for t in _collect_tracks(it)]
    if not isinstance(node, dict):
        return []
    if _item_url(node):
        return [node]
    for key in ("music", "result", "data", "items"):
        found = _collect_tracks(node.get(key))
        if found:
            return found
    return []


def _walk_status(inner):
    nested = inner.get("data") if isinstance(inner.get("data"), dict) else {}
    deeper = nested.get("data") if isinstance(nested.get("data"), dict) else {}
    for src in (inner, nested, deeper):
        if not isinstance(src, dict):
            continue
        st = str(src.get("status") or src.get("taskStatus") or src.get("state") or "").strip().upper()
        if st:
            return st
    return ""


def _poll_flag(inner, names):
    st = _walk_status(inner)
    return st in names, st


class SynVowSuno6:
    FUNCTION = "generate_audio"
    CATEGORY = "💫SynVow_api/api/音频"
    DESCRIPTION = "SynVow Suno 音乐生成 / 翻唱 / 延长"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "task_kind": (_TASKS, {"default": _TASK_GENERATE}),
                "mode": (_MODES, {"default": _MODE_INSPIRE}),
                "version": (_VERSIONS, {"default": "v6"}),
                "instrumental": ("BOOLEAN", {"default": False}),
                "vocal_gender": (_VOCALS, {"default": "自动"}),
                "style_weight": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "weirdness": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "audio_weight": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "continue_at": ("INT", {"default": 1, "min": _CONTINUE_MIN, "max": _CONTINUE_MAX}),
                "duration": ("INT", {"default": 0, "min": 0, "max": 360, "step": 1}),
                "title": ("STRING", {"multiline": False, "default": ""}),
                "tags": ("STRING", {"multiline": True, "default": ""}),
                "negative_tags": ("STRING", {"multiline": True, "default": ""}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "audio_path": ("STRING", {"forceInput": True}),
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "audio_path", "audio_url", "lyrics", "title", "task_info")
    OUTPUT_IS_LIST = (False, True, True, True, True, False)
    IS_CHANGED = staticmethod(is_changed_by_inputs)

    def generate_audio(
        self, task_kind, mode, version, instrumental, vocal_gender,
        style_weight, weirdness, audio_weight, continue_at, duration,
        title, tags, negative_tags, prompt, seed=0, audio_path="", filename="", save_path="",
    ):
        del seed
        api_key = synvow_auth.read_api_key()
        try:
            kind = _task(task_kind)
            path_in = (audio_path or "").strip()
            audio_url = upload_media_file(api_key, path_in, "audio") if kind != _TASK_GENERATE and path_in else ""
            body, instrumental = _build_body(
                task_kind, mode, version, instrumental, vocal_gender, prompt, title, tags,
                negative_tags, duration, style_weight, weirdness, audio_weight, continue_at, audio_url,
            )
            used_model = body["model"]
            task_id, consumption_id = submit_edit_async(api_key, body, _TAG)
            tracks_box = []

            def pick(inner, data):
                found = _collect_tracks(inner) or _collect_tracks(data)
                tracks_box[:] = found
                return _item_url(found[0]) if found else ""

            poll_edit_task(
                api_key, task_id, used_model, _TAG,
                consumption_id=consumption_id, timeout=1800,
                check_success=lambda inner: _poll_flag(inner, _SUCCESS),
                check_failed=lambda inner: _poll_flag(inner, _FAILURE),
                pick_url=pick,
            )
            items = [it for it in tracks_box if _item_url(it)]
            audios, paths, urls, lyrics, titles, tracks = [], [], [], [], [], []
            for i, it in enumerate(items):
                u = _item_url(it)
                title_i = "" if instrumental else (it.get("title") or "")
                lyrics_i = "" if instrumental else _pick_lyrics(it)
                fn = filename
                if fn and len(items) > 1:
                    base, ext = os.path.splitext(fn)
                    fn = f"{base}_{i + 1}{ext}"
                path = download_audio(u, f"{task_id}-{i}", save_path, prefix="suno6", filename=fn) or ""
                audios.append(_load_audio(path))
                paths.append(path)
                urls.append(u)
                lyrics.append(lyrics_i)
                titles.append(title_i)
                tracks.append({
                    "audio_url": u,
                    "title": title_i,
                    "clipId": it.get("audio_id") or it.get("clipId") or "",
                    "lyrics": lyrics_i,
                    "audio_path": path,
                })
            info = json.dumps({
                "status": "SUCCESS",
                "task_id": task_id,
                "model": used_model,
                "display": display_name(used_model),
                "tracks": tracks,
            }, ensure_ascii=False)
            return (_stack_audio(audios), paths, urls, lyrics, titles, info)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowSuno6": SynVowSuno6,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSuno6": "SynVow Suno",
}
