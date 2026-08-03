# -*- coding: utf-8 -*-
"""
SynVow Suno 音乐生成（灵感模式 / 自定义模式）
"""
import json
import os
import time

import requests
import torch

from . import synvow_auth
from .media_common import EDIT_POLL_URL, EDIT_SUBMIT_URL, download_audio, is_changed_by_inputs
from comfy_extras.nodes_audio import load as load_audio_file

_MODEL_TO_MV = {"suno5.5": "chirp-v5"}
_MODELS = list(_MODEL_TO_MV.keys())
_DEFAULT_MODEL = "suno5.5"
_SUCCESS = ("success", "succeeded", "succeed", "completed", "complete", "done", "finished")
_FAILURE = ("failure", "failed", "error", "exception")


def _empty_audio():
    return {"waveform": torch.zeros((1, 1, 1), dtype=torch.float32), "sample_rate": 44100}


def _load_audio(path):
    if not path or not os.path.isfile(path):
        return _empty_audio()
    waveform, sample_rate = load_audio_file(path)
    return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sample_rate)}


def _build_inspire_body(model, instrumental, prompt):
    model = model if model in _MODEL_TO_MV else _DEFAULT_MODEL
    return {
        "gpt_description_prompt": prompt or "",
        "make_instrumental": bool(instrumental),
        "mv": _MODEL_TO_MV.get(model, "chirp-v5"),
        "model": model,
    }


def _build_custom_body(model, instrumental, prompt, title, tags):
    model = model if model in _MODEL_TO_MV else _DEFAULT_MODEL
    return {
        "model": model,
        "mv": _MODEL_TO_MV.get(model, "chirp-v5"),
        "make_instrumental": bool(instrumental),
        "prompt": prompt or "",
        "tags": tags or "",
        "title": title or "",
    }


def _parse_task_id(data):
    payload = data.get("data")
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if isinstance(payload, dict):
        return (
            payload.get("task_id")
            or payload.get("taskId")
            or data.get("task_id")
            or ""
        )
    return data.get("task_id") or ""


def _submit(api_key, body):
    headers = synvow_auth.make_api_headers(api_key)
    print(f"[Suno] 提交: model={body.get('model')} mv={body.get('mv')}")
    res = requests.post(
        EDIT_SUBMIT_URL, headers=headers, params={"async": "true"},
        json=body, verify=False, timeout=120,
    )
    data = res.json() if res.text.strip() else {}
    if res.status_code == 401:
        raise RuntimeError("API Key 无效或已过期，请重新登录")
    if res.status_code not in (200, 202):
        raise Exception(f"Suno 提交失败 ({res.status_code}): {data.get('message') or str(data)[:200]}")
    task_id = _parse_task_id(data)
    if not task_id:
        raise Exception(f"Suno 响应中无 task_id: {str(data)[:200]}")
    consumption_id = data.get("consumption_id") or ""
    if isinstance(data.get("data"), dict):
        consumption_id = consumption_id or data["data"].get("consumption_id") or ""
    print(f"[Suno] task_id=...{str(task_id)[-8:]}")
    return str(task_id), str(consumption_id), body.get("model") or _DEFAULT_MODEL


def _get_items(json_data):
    if not isinstance(json_data, dict):
        return []
    data = json_data.get("data")
    candidates = []
    if isinstance(data, dict):
        candidates.append(data.get("data"))
        inner = data.get("data")
        if isinstance(inner, dict):
            nested = inner.get("data")
            if isinstance(nested, dict):
                candidates.append(nested.get("items"))
        candidates.append(data.get("items"))
    candidates.append(json_data.get("items"))
    for c in candidates:
        if isinstance(c, list):
            return c
    return []


def _normalize_text(v):
    return v.strip() if isinstance(v, str) else ""


def _pick_lyrics(item):
    if not isinstance(item, dict):
        return ""
    original = _normalize_text(item.get("gptDescriptionPrompt"))
    meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    candidates = [
        item.get("lyrics"),
        item.get("lyric"),
        item.get("generatedLyrics"),
        meta.get("lyrics"),
        meta.get("lyric"),
        meta.get("prompt"),
        item.get("prompt"),
    ]
    for value in candidates:
        text = _normalize_text(value)
        if text and text != original:
            return text
    return ""


def _poll(api_key, task_id, model, timeout=1800, interval=5, consumption_id=""):
    import comfy.model_management as mm
    headers = synvow_auth.make_api_headers(api_key)
    start = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            raise Exception(f"[Suno] 轮询超时 ({timeout}s)")
        time.sleep(interval)
        mm.throw_exception_if_processing_interrupted()
        try:
            body = {"task_id": task_id, "model": model}
            if consumption_id:
                body["consumption_id"] = consumption_id
            res = requests.post(EDIT_POLL_URL, headers=headers, json=body, verify=False, timeout=30)
            if res.status_code in (429, 500, 503):
                print(f"[Suno] ...{task_id[-8:]} HTTP {res.status_code}, 退避10秒")
                time.sleep(10)
                continue
            if res.status_code != 200:
                continue
            data = res.json() if res.text.strip() else {}
            inner = data.get("data") if isinstance(data.get("data"), dict) else (data if isinstance(data, dict) else {})
            status = str(inner.get("status") or "").strip().lower()
            nested = inner.get("data") if isinstance(inner.get("data"), dict) else {}
            deeper = nested.get("data") if isinstance(nested.get("data"), dict) else {}
            task_status = str(
                deeper.get("taskStatus")
                or nested.get("taskStatus")
                or inner.get("taskStatus")
                or ""
            ).strip().lower()
            print(f"[Suno] ...{task_id[-8:]} status={status or task_status or '(无)'} ({elapsed}s)")
            if status in _FAILURE or task_status in _FAILURE:
                err = inner.get("fail_reason") or "任务失败"
                raise Exception(f"Suno 任务失败: {err}")
            done = status in _SUCCESS or task_status in _SUCCESS
            if done:
                items = _get_items(data)
                if not items or not any(isinstance(it, dict) and it.get("cld2AudioUrl") for it in items):
                    raise Exception("Suno 任务完成但未解析到音频 URL")
                return items
        except Exception as e:
            msg = str(e)
            if msg.startswith("Suno") or "超时" in msg:
                raise
            print(f"[Suno] 轮询异常: {e}")


def _run_once(api_key, body, save_path="", filename=""):
    task_id, consumption_id, used_model = _submit(api_key, body)
    items = _poll(api_key, task_id, used_model, consumption_id=consumption_id)
    first = next((it for it in items if isinstance(it, dict) and it.get("cld2AudioUrl")), None)
    audio_url = first.get("cld2AudioUrl") if first else ""
    path = ""
    if audio_url:
        path = download_audio(audio_url, task_id, save_path, prefix="suno", filename=filename) or ""
    tracks = []
    for it in items:
        if not isinstance(it, dict) or not it.get("cld2AudioUrl"):
            continue
        tracks.append({
            "audio_url": it.get("cld2AudioUrl"),
            "title": it.get("title") or "",
            "clipId": it.get("clipId") or "",
            "lyrics": _pick_lyrics(it),
        })
    lyrics = tracks[0]["lyrics"] if tracks else ""
    title_out = tracks[0]["title"] if tracks else ""
    return path, audio_url, task_id, used_model, lyrics, title_out, tracks


def _execute(body, save_path="", filename=""):
    api_key = synvow_auth.read_api_key()
    try:
        path, url, task_id, used_model, lyrics, title_out, tracks = _run_once(
            api_key, body, save_path, filename,
        )
        audio = _load_audio(path)
        info = json.dumps({
            "status": "SUCCESS",
            "task_id": task_id,
            "model": used_model,
            "audio_url": url,
            "audio_path": path,
            "tracks": tracks,
        }, ensure_ascii=False)
        synvow_auth.refresh_balance()
        return (audio, path, url, lyrics, title_out, info)
    except Exception as e:
        print(f"[Suno] Error: {e}")
        synvow_auth.refresh_balance()
        return (
            _empty_audio(), "", "", "", "",
            json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False),
        )


class SynVowSunoInspire:
    FUNCTION = "generate_audio"
    CATEGORY = "💫SynVow_api/api/音频"
    DESCRIPTION = "SynVow Suno 灵感模式"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _DEFAULT_MODEL}),
                "instrumental": ("BOOLEAN", {"default": False}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "audio_path", "audio_url", "lyrics", "title", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_audio(self, prompt, model, instrumental, seed=0, filename="", save_path=""):
        body = _build_inspire_body(model, instrumental, prompt)
        return _execute(body, save_path, filename)


class SynVowSunoCustom:
    FUNCTION = "generate_audio"
    CATEGORY = "💫SynVow_api/api/音频"
    DESCRIPTION = "SynVow Suno 自定义模式"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": (_MODELS, {"default": _DEFAULT_MODEL}),
                "instrumental": ("BOOLEAN", {"default": False}),
                "title": ("STRING", {"multiline": False, "default": ""}),
                "tags": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "filename": ("STRING", {"multiline": False, "default": ""}),
                "save_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio", "audio_path", "audio_url", "lyrics", "title", "task_info")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return is_changed_by_inputs(**kwargs)

    def generate_audio(self, prompt, model, instrumental, title, tags, seed=0, filename="", save_path=""):
        body = _build_custom_body(model, instrumental, prompt, title, tags)
        return _execute(body, save_path, filename)


NODE_CLASS_MAPPINGS = {
    "SynVowSunoInspire": SynVowSunoInspire,
    "SynVowSunoCustom": SynVowSunoCustom,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowSunoInspire": "SynVow Suno 灵感模式",
    "SynVowSunoCustom": "SynVow Suno 自定义模式",
}
