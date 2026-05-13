"""
SynVow 参考图提示词优化 节点 V1.1
"""

import base64
import hashlib
import io
import json
import pathlib
import re

import numpy as np
import requests
import urllib3
from PIL import Image

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_DIRECT_API_BASE = "https://service.synvow.com/api/v1"
_CHAT_URL = f"{_DIRECT_API_BASE}/api/models/chat/completions"

_SYSTEM_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "reference_image_optimizer_system.txt").read_text(encoding="utf-8")

_REFERENCE_MODE_MAP = {
    "自动判断": "auto",
    "综合参考": "full_reference",
    "只参考风格": "style_only",
    "只参考构图": "composition_only",
    "只参考色彩光影": "color_lighting_only",
    "只参考版式": "layout_only",
}



def _tensor_to_base64(tensor) -> str:
    i = 255.0 * tensor[0].cpu().numpy()
    img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    if img.width > 1024 or img.height > 1024:
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _build_user_message(reference_image, user_prompt: str, reference_mode: str, target_aspect_ratio: str, subject_image=None) -> list:
    content = []
    if subject_image is not None:
        b64_subject = _tensor_to_base64(subject_image)
        content.append({"type": "text", "text": "以下是 subject_image（主体图）："})
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_subject}"}})
    b64_ref = _tensor_to_base64(reference_image)
    content.append({"type": "text", "text": "以下是 reference_image（参考图）："})
    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_ref}"}})
    has_subject = "是" if subject_image is not None else "否"
    content.append({
        "type": "text",
        "text": (
            f"用户需求：{user_prompt}\n"
            f"是否提供 subject_image：{has_subject}\n"
            f"reference_mode：{reference_mode}\n"
            f"target_aspect_ratio：{target_aspect_ratio}"
        ),
    })
    return content


def _parse_output(raw: str):
    def extract(tag: str) -> str:
        pattern = rf"{tag}:\s*(.*?)(?=\n\w+_\w+:|$)"
        m = re.search(pattern, raw, re.DOTALL)
        return m.group(1).strip() if m else ""

    optimized_prompt = extract("optimized_prompt")
    reference_summary = extract("reference_summary")
    return optimized_prompt, reference_summary


class PromptOptimizeBReferenceImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_image": ("IMAGE",),
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "reference_mode": (
                    ["自动判断", "综合参考", "只参考风格", "只参考构图", "只参考色彩光影", "只参考版式"],
                    {"default": "自动判断"},
                ),
                "target_aspect_ratio": (
                    ["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "5:4", "4:5",
                     "3:2", "2:3", "3:1", "1:3", "2:1", "1:2", "21:9", "9:21"],
                    {"default": "auto"},
                ),
                "model": (
                    ["gpt-5.4-mini", "gpt-5.5", "gemini-3.1-flash", "gemini-3.1-pro"],
                    {"default": "gpt-5.4-mini"},
                ),
                "mode": (
                    ["默认"],
                    {"default": "默认"},
                ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "subject_image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("optimized_prompt", "reference_summary")
    FUNCTION = "optimize"
    CATEGORY = "💫SynVow_api/tools"
    DESCRIPTION = "图生图提示词控制器：可选主体图 + 必填参考图 + 用户需求 → 结构化生图提示词"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        key = json.dumps({k: str(v) for k, v in kwargs.items() if k not in ("reference_image", "subject_image")}, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key.encode()).hexdigest()

    def optimize(self, reference_image, user_prompt, reference_mode, target_aspect_ratio,
                 model, mode, seed=0, subject_image=None):
        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        ref_mode_en = _REFERENCE_MODE_MAP.get(reference_mode, reference_mode)
        ratio_en = target_aspect_ratio
        actual_model = f"{model}-{mode}"

        has_subject = subject_image is not None
        print(f"[图生图 RefOptimizer] model={actual_model} mode={ref_mode_en} ratio={ratio_en} has_subject={has_subject}")

        user_content = _build_user_message(reference_image, user_prompt, ref_mode_en, ratio_en, subject_image=subject_image)

        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        }
        if seed > 0:
            payload["seed"] = seed

        res = requests.post(_CHAT_URL, headers=headers, json=payload, timeout=(30, 600), verify=False)
        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            response_text = res.text[:2000] if res.text else "<empty response>"
            raise RuntimeError(f"SynVow API request failed: HTTP {res.status_code}; response={response_text}") from e

        raw = synvow_auth.parse_chat_response(res.json())
        if not raw or not raw.strip():
            raise RuntimeError(f"模型未返回有效内容: {str(res.json())[:200]}")

        raw = raw.strip()
        print(f"[图生图 RefOptimizer] raw={raw[:300]}")

        optimized_prompt, reference_summary = _parse_output(raw)

        if not optimized_prompt:
            optimized_prompt = raw

        return (optimized_prompt, reference_summary)


NODE_CLASS_MAPPINGS = {
    "PromptOptimizeBReferenceImage": PromptOptimizeBReferenceImage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptOptimizeBReferenceImage": "图生图提示词控制器",
}
