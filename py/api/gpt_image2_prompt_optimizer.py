"""
SynVow GPT-Image-2 Prompt Optimizer 节点 — 通过 LLM 优化图像生成提示词
"""

import pathlib
import random
import requests
import urllib3

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_DIRECT_API_BASE = "https://service.synvow.com/api/v1"
_CHAT_URL = f"{_DIRECT_API_BASE}/api/models/chat/completions"

_TASK_TYPE_PROMPTS = [
    "通用图像",
    "产品广告图",
    "人像摄影",
    "海报封面",
    "电商主图",
    "电商详情图",
    "插画/插图",
]

_STRENGTH_INSTRUCTION = {
    "light":    "在保持原始提示词意图的前提下，做少量润色和补充，输出长度与原文相近。",
    "standard": "在原始提示词基础上，补充场景细节、光线、构图、风格等描述，使提示词更完整。",
    "strong":   "充分发挥创意，在原始提示词的核心主题上，生成一段专业、详尽、富有表现力的英文 prompt，可大幅扩展细节。",
}

_PROMPT_FILE = pathlib.Path(__file__).parent.parent / "prompts" / "gpt-image-2_prompt_optimizer_general.txt"
_SYSTEM_PROMPT_TEMPLATE = _PROMPT_FILE.read_text(encoding="utf-8")


def _build_user_message(user_prompt: str, exact_text: str = "") -> str:
    if exact_text.strip():
        return f"{user_prompt}\n\n画面中必须出现的文字：{exact_text.strip()}"
    return user_prompt


class GptImage2PromptOptimizer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "user_prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
                "task_type": (
                    ["通用图像", "产品广告图", "人像摄影", "海报封面",
                     "电商主图", "电商详情图", "插画/插图"],
                    {"default": "通用图像"},
                ),
                "model": (
                    ["gpt-5.4-mini", "gpt-5.5"],
                    {"default": "gpt-5.4-mini"},
                ),
                "optimize_strength": (
                    ["light", "standard", "strong"],
                    {"default": "standard"},
                ),
                "mode": (
                    ["默认", "优质"],
                    {"default": "默认"},
                ),
                "aspect_ratio": (
                    ["auto", "1:1", "16:9", "9:16", "4:3", "3:4", "5:4", "4:5",
                     "3:2", "2:3", "3:1", "1:3", "2:1", "1:2", "21:9", "9:21"],
                    {"default": "16:9"},
                ),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "exact_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("optimized_prompt", "debug_info")
    FUNCTION = "optimize"
    CATEGORY = "💫SynVow_api/tools"
    DESCRIPTION = "使用 LLM 优化 GPT-Image-2 图像生成提示词"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def optimize(self, user_prompt, task_type, model, optimize_strength, mode, aspect_ratio="16:9", seed=0, exact_text=""):
        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        exact_text = exact_text or ""
        actual_model = f"{model}-{mode}"
        print(f"[SynVow Prompt Optimizer] exact_text={repr(exact_text)}")
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            task_type=task_type,
            optimize_strength=optimize_strength,
            exact_text=exact_text.strip() if exact_text.strip() else "（无）",
            user_prompt=user_prompt,
            aspect_ratio=aspect_ratio,
        )
        user_message = _build_user_message(user_prompt, exact_text)

        payload = {
            "model": actual_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            "stream": False,
        }

        print(f"[SynVow Prompt Optimizer] 请求模型={actual_model} task_type={task_type} strength={optimize_strength}")

        res = requests.post(_CHAT_URL, headers=headers, json=payload, timeout=300, verify=False)
        res.raise_for_status()
        data = res.json()

        raw = synvow_auth.parse_chat_response(data)
        if raw is None:
            raise RuntimeError(f"[SynVow Prompt Optimizer] 模型未返回有效内容: {str(data)[:200]}")
        optimized = raw.strip()
        if not optimized:
            raise RuntimeError(f"[SynVow Prompt Optimizer] 模型未返回有效内容: {str(data)[:200]}")

        debug_info = (
            f"task_type={task_type}\n"
            f"optimize_strength={optimize_strength}\n"
            f"aspect_ratio={aspect_ratio}\n"
            f"has_exact_text={str(bool(exact_text.strip())).lower()}\n"
            f"seed={seed}"
        )
        print(f"[SynVow Prompt Optimizer] 优化结果: {optimized[:200]}")
        return (optimized, debug_info)


NODE_CLASS_MAPPINGS = {
    "GptImage2PromptOptimizer": GptImage2PromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GptImage2PromptOptimizer": "GPT-Image-2 Prompt Optimizer",
}
