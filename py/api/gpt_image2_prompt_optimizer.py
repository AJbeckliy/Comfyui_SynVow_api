"""
SynVow GPT-Image-2 Prompt Optimizer 节点 V1.5 — 双LLM Schema流程
"""

import json
import pathlib
import requests
import urllib3

from . import synvow_auth
from .gemini_synvow import GEMINI_MODEL_OPTIONS
from .gpt_synvow import DEFAULT_GPT_MODEL, GPT_MODEL_OPTIONS, resolve_gpt_model

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_CHAT_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/completions"

_SINGLE_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "gpt-image-2_text2image_single_v1.txt").read_text(encoding="utf-8")

_LANDSCAPE = {"16:9", "4:3", "3:2", "2:1", "21:9", "3:1"}
_PORTRAIT = {"9:16", "3:4", "2:3", "1:2", "9:21", "1:3"}
_SQUARE = {"1:1"}


def ratio_to_direction(aspect_ratio: str) -> str:
    if aspect_ratio in _LANDSCAPE:
        return "横版构图"
    if aspect_ratio in _PORTRAIT:
        return "竖版构图"
    if aspect_ratio in _SQUARE:
        return "方形构图"
    return "由画面内容决定"


def build_input_payload(layout_type, optimize_strength, aspect_ratio, user_prompt, exact_text, text_policy):
    return {
        "layout_type": layout_type,
        "optimize_strength": optimize_strength,
        "aspect_ratio": aspect_ratio,
        "direction": ratio_to_direction(aspect_ratio),
        "user_prompt": user_prompt or "",
        "exact_text": exact_text or "",
        "text_policy": text_policy,
    }


def _chat(headers, model, system_prompt, user_message):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "stream": False,
    }
    print(f"[GPTImage2Optimizer] {model} 模型正在生成...")
    res = requests.post(_CHAT_URL, headers=headers, json=payload, timeout=(30, 600), verify=False)
    try:
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        response_text = res.text[:2000] if res.text else "<empty response>"
        raise RuntimeError(
            f"SynVow API request failed: HTTP {res.status_code}; response={response_text}"
        ) from e
    raw = synvow_auth.parse_chat_response(res.json())
    if not raw or not raw.strip():
        raise RuntimeError(f"模型未返回有效内容: {str(res.json())[:200]}")
    print(f"[GPTImage2Optimizer] {model} 模型生成完毕。")
    return raw.strip()




class GptImage2PromptOptimizer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "layout_type": (
                    ["自动判断", "纯画面", "图文混排海报", "电商主图", "社媒封面"],
                    {"default": "自动判断"},
                ),
                "text_policy": (
                    ["不加文字", "保留原文", "优化原文", "自动生成"],
                    {"default": "保留原文"},
                ),
                "model": (
                    list(GPT_MODEL_OPTIONS) + list(GEMINI_MODEL_OPTIONS),
                    {"default": DEFAULT_GPT_MODEL},
                ),
                "optimize_strength": (
                    ["标准", "增强"],
                    {"default": "标准"},
                ),
                "aspect_ratio": (
                    ["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "5:4", "4:5",
                     "3:2", "2:3", "3:1", "1:3", "2:1", "1:2", "21:9", "9:21"],
                    {"default": "16:9"},
                ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
                "exact_text": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("optimized_prompt", "debug_info")
    FUNCTION = "optimize"
    CATEGORY = "💫SynVow_api/api/文本"
    DESCRIPTION = "使用 LLM 优化 GPT-Image-2 图像生成提示词（V1.5 Schema 流程）"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import hashlib
        key = json.dumps(kwargs, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.md5(key.encode()).hexdigest()

    _TEXT_POLICY_MAP = {"不加文字": "none", "保留原文": "preserve", "优化原文": "enhance", "自动生成": "generate"}

    _STRENGTH_MAP = {"light": "标准", "standard": "标准", "strong": "增强"}

    def optimize(self, user_prompt, layout_type, model, optimize_strength,
                 aspect_ratio="16:9", seed=0, text_policy="保留原文", exact_text=""):
        optimize_strength = self._STRENGTH_MAP.get(optimize_strength, optimize_strength)
        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)
        exact_text = exact_text or ""
        actual_model = resolve_gpt_model(model)
        text_policy_en = self._TEXT_POLICY_MAP.get(text_policy, text_policy)

        payload = build_input_payload(layout_type, optimize_strength, aspect_ratio, user_prompt, exact_text, text_policy_en)
        payload["has_exact_text"] = str(bool(exact_text.strip())).lower()
        user_message = json.dumps(payload, ensure_ascii=False)

        optimized = _chat(headers, actual_model, _SINGLE_PROMPT, user_message)

        if optimize_strength == "增强" and text_policy_en == "generate":
            optimized = optimized.replace("【限制条件】", "【创作自由】")

        direction = ratio_to_direction(aspect_ratio)
        debug_info = (
            f"layout_type={layout_type}\n"
            f"optimize_strength={optimize_strength}\n"
            f"aspect_ratio={aspect_ratio}\n"
            f"direction={direction}\n"
            f"text_policy={text_policy_en}\n"
            f"has_exact_text={str(bool(exact_text.strip())).lower()}\n"
            f"seed={seed}\n"
            f"payload={user_message}\n"
            f"final_prompt={optimized}"
        )
        synvow_auth.refresh_balance()
        return (optimized, debug_info)


NODE_CLASS_MAPPINGS = {
    "GptImage2PromptOptimizer": GptImage2PromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GptImage2PromptOptimizer": "GPT-Image-2 文生图提示词控制器",
}
