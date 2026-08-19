"""Shared SynVow LLM client used by integrated YMAI prompt nodes."""

from __future__ import annotations

import re
import time
import json
import hashlib
from io import BytesIO
from typing import Any, Dict, Iterable, List, Optional

import requests

from . import synvow_auth
from .gemini_synvow import DEFAULT_GEMINI_MODEL, GEMINI_MODEL_OPTIONS
from .gpt_synvow import GPT_MODEL_OPTIONS, resolve_gpt_model
from .media_common import DIRECT_API_BASE, upload_images


DEFAULT_MODEL = DEFAULT_GEMINI_MODEL
CHAT_MAX_RETRIES = 3
SEED_INPUT = ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF})


def add_seed_input(inputs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    cloned = {group: dict(values) if isinstance(values, dict) else values for group, values in inputs.items()}
    optional = dict(cloned.get("optional", {}))
    optional["seed"] = SEED_INPUT
    cloned["optional"] = optional
    return cloned


def json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    shape = getattr(value, "shape", None)
    dtype = getattr(value, "dtype", None)
    if shape is not None:
        return {"type": type(value).__name__, "shape": list(shape), "dtype": str(dtype)}
    return repr(value)


def input_hash(*args: Any, **kwargs: Any) -> str:
    payload = {"args": json_safe(args), "kwargs": json_safe(kwargs)}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def strip_seed(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    kwargs.pop("seed", None)
    return kwargs


def _dedupe_models(models: List[str]) -> List[str]:
    seen = set()
    result = []
    for model in models:
        if model and model not in seen:
            seen.add(model)
            result.append(model)
    return result


MODEL_OPTIONS = _dedupe_models(list(GEMINI_MODEL_OPTIONS) + list(GPT_MODEL_OPTIONS))


def fetch_models() -> List[str]:
    return list(MODEL_OPTIONS)


def default_model(models: List[str]) -> str:
    return DEFAULT_MODEL if DEFAULT_MODEL in models else models[0]


def remove_reasoning_tags(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\|begin_of_box\|>|<\|end_of_box\|>", "", cleaned)
    return cleaned.strip()


def image_to_data_urls(image: Any, quality: int = 90) -> List[str]:
    """Upload a ComfyUI IMAGE batch to SynVow storage and return image URLs."""
    if image is None:
        return []

    import numpy as np
    from PIL import Image

    value = image.detach().cpu().numpy() if hasattr(image, "detach") else np.asarray(image)
    if value.ndim == 3:
        value = value[np.newaxis, ...]

    image_bytes: List[bytes] = []
    for item in value:
        if item.ndim == 3 and item.shape[0] in (1, 3, 4) and item.shape[-1] not in (1, 3, 4):
            item = np.transpose(item, (1, 2, 0))
        item = np.clip(item * 255.0 if item.max() <= 1.0 else item, 0, 255).astype(np.uint8)
        if item.ndim == 2:
            pil_image = Image.fromarray(item, mode="L")
        elif item.shape[-1] == 4:
            pil_image = Image.fromarray(item, mode="RGBA")
        else:
            pil_image = Image.fromarray(item, mode="RGB")
        pil_image = pil_image.convert("RGB")
        buffer = BytesIO()
        pil_image.save(buffer, format="JPEG", quality=quality)
        image_bytes.append(buffer.getvalue())
    if not image_bytes:
        return []
    return upload_images(synvow_auth.read_api_key(), image_bytes)


def build_messages(system_prompt: str, user_prompt: str, image_urls: Optional[Iterable[str]] = None):
    urls = list(image_urls or [])
    if not urls:
        return [
            {"role": "system", "content": system_prompt or ""},
            {"role": "user", "content": user_prompt or ""},
        ]

    content: List[Dict[str, Any]] = [{"type": "text", "text": user_prompt or ""}]
    content.extend({"type": "image_url", "image_url": {"url": url}} for url in urls)
    return [
        {"role": "system", "content": system_prompt or ""},
        {"role": "user", "content": content},
    ]


def post_chat_completion(payload: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    api_key = synvow_auth.read_api_key()
    headers = synvow_auth.make_api_headers(api_key)
    url = f"{DIRECT_API_BASE}/api/models/completions"
    payload = dict(payload)
    payload.setdefault("stream", False)
    last_error: Optional[RuntimeError] = None

    for attempt in range(CHAT_MAX_RETRIES):
        if attempt:
            time.sleep(min(2 ** attempt, 5))
        response = requests.post(url, headers=headers, json=payload, timeout=timeout, verify=False)
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"SynVow LLM returned non-JSON content: {response.text[:200]}") from exc

        if response.status_code == 200:
            synvow_auth.refresh_balance()
            return _unwrap_response_data(data)

        message = _extract_error_message(data, response.text)
        last_error = RuntimeError(f"SynVow LLM request failed: HTTP {response.status_code}: {message}")
        if _is_transient_provider_error(response.status_code, message):
            continue
        raise last_error

    raise last_error or RuntimeError("SynVow LLM request failed.")


def _extract_error_message(data: Dict[str, Any], response_text: str) -> str:
    for key in ("error", "message", "msg"):
        value = data.get(key) if isinstance(data, dict) else None
        if value:
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
    return response_text[:500]


def _is_transient_provider_error(status_code: int, message: str) -> bool:
    if status_code >= 500 or status_code == 429:
        return True
    lowered = str(message or "").lower()
    transient_markers = (
        "model load is too high",
        "try again later",
        "temporarily unavailable",
        "overloaded",
        "rate limit",
        "too many requests",
        "timeout",
        "timed out",
        "upstream",
        "provider",
    )
    return any(marker in lowered for marker in transient_markers)


def _unwrap_response_data(data: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        inner = data["data"]
        if "choices" in inner or "candidates" in inner:
            return inner
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return {"choices": data["data"]}
    if isinstance(data, list):
        return {"choices": data}
    return data


def extract_content(data: Dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        choices = data["data"].get("choices", choices)
    if not choices or not isinstance(choices, list):
        parsed = synvow_auth.parse_chat_response(data)
        if parsed:
            return str(remove_reasoning_tags(parsed))
        raise RuntimeError("SynVow LLM did not return choices.")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")
    if content is None:
        content = first.get("text")
    if isinstance(content, list):
        content = "\n".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("text")
        )
    if not content:
        parsed = synvow_auth.parse_chat_response(data)
        if parsed:
            return str(remove_reasoning_tags(parsed))
        raise RuntimeError("SynVow LLM returned empty content.")
    return str(remove_reasoning_tags(str(content)))


def chat_completion(
    model: str,
    system_prompt: str,
    user_prompt: str,
    *,
    image_urls: Optional[Iterable[str]] = None,
    temperature: float = 0.6,
    max_tokens: int = 4096,
    top_p: float = 1.0,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
    reasoning_effort: Optional[str] = None,
    timeout: int = 180,
) -> str:
    payload: Dict[str, Any] = {
        "model": resolve_gpt_model(model),
        "messages": build_messages(system_prompt, user_prompt, image_urls),
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "top_p": float(top_p),
        "presence_penalty": float(presence_penalty),
        "frequency_penalty": float(frequency_penalty),
    }
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    return extract_content(post_chat_completion(payload, timeout=timeout))
