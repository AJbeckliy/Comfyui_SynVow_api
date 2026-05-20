"""
SynVow GPT-Image-2 Prompt Optimizer 节点 V1.5 — 双LLM Schema流程
"""

import json
import pathlib
import re
import requests
import urllib3

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_DIRECT_API_BASE = "https://service.synvow.com/api/v1"
_CHAT_URL = f"{_DIRECT_API_BASE}/api/models/completions"

_SCHEMA_PARSER_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "gpt-image-2_schema_parser_v1.txt").read_text(encoding="utf-8")
_RENDERER_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "gpt-image-2_prompt_renderer_v1.txt").read_text(encoding="utf-8")

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


def generate_prompt_schema(headers, model, payload: dict) -> dict:
    user_message = json.dumps(payload, ensure_ascii=False)
    raw = _chat(headers, model, _SCHEMA_PARSER_PROMPT, user_message)
    raw_clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(raw_clean)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"schema 解析失败，模型输出非 JSON: {raw[:300]}") from e


_BANNED_TEXT_PHRASES = [
    "预留标题", "标题展示", "展示标题", "显示标题",
    "预留文字", "文字展示", "展示文字", "添加文案",
    "按钮文字", "具体文案", "标题区", "卖点栏", "品牌区", "信息栏",
    "主标题", "副标题", "卖点", "文字", "文案", "标签",
]


def _remove_text_hints(schema: dict) -> dict:
    for key in ["composition", "ui_layout", "constraints", "layout_plan", "information_hierarchy"]:
        value = schema.get(key)
        if isinstance(value, str):
            for p in _BANNED_TEXT_PHRASES:
                value = value.replace(p, "")
            schema[key] = value.strip(" ，,；;。")
        elif isinstance(value, list):
            schema[key] = [item for item in value if not any(p in str(item) for p in _BANNED_TEXT_PHRASES)]
    schema["text_requirements"] = []
    schema["typography_plan"] = ""
    schema["copy_strategy"] = ""
    return schema


def normalize_schema(schema: dict, aspect_ratio: str, exact_text: str, user_prompt: str, text_policy: str, optimize_strength: str = "", layout_type: str = "") -> dict:
    schema["aspect_ratio"] = aspect_ratio
    schema["direction"] = ratio_to_direction(aspect_ratio)
    schema["text_policy"] = text_policy
    schema["optimize_strength"] = optimize_strength
    schema["layout_type"] = layout_type

    if not isinstance(schema.get("constraints"), list):
        schema["constraints"] = []
    schema["constraints"] = schema["constraints"][:3]

    if not isinstance(schema.get("named_entities"), list):
        schema["named_entities"] = []

    exact = exact_text.strip() if exact_text else ""

    if text_policy == "none":
        schema = _remove_text_hints(schema)
    elif text_policy == "preserve":
        schema["text_requirements"] = [exact] if exact else []
    elif text_policy == "enhance":
        if not schema.get("text_requirements"):
            schema["text_requirements"] = [exact] if exact else []
    elif text_policy == "generate":
        pass
    else:
        if exact:
            schema["text_requirements"] = [exact]
        elif not schema.get("text_requirements"):
            schema["text_requirements"] = []

    return schema


def render_final_prompt(headers, model, schema: dict) -> str:
    user_message = json.dumps(schema, ensure_ascii=False)
    return _chat(headers, model, _RENDERER_PROMPT, user_message)


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
                    ["gpt-5.5-2605", "gpt-5.4-2605", "gemini-3.1-pro-2605", "gemini-3.1-flash-2605", "gemini-3.5-flash-2605", "gemini-3-pro-2605"],
                    {"default": "gpt-5.5-2605"},
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
        actual_model = model or "gpt-5.5-2605"
        text_policy = self._TEXT_POLICY_MAP.get(text_policy, text_policy)

        payload = build_input_payload(layout_type, optimize_strength, aspect_ratio, user_prompt, exact_text, text_policy)
        schema = generate_prompt_schema(headers, actual_model, payload)
        schema = normalize_schema(schema, aspect_ratio, exact_text, user_prompt, text_policy, optimize_strength, layout_type)
        optimized = render_final_prompt(headers, actual_model, schema)
        if optimize_strength == "增强" and text_policy == "generate":
            optimized = optimized.replace("【限制条件】", "【创作自由】")
        if optimize_strength == "标准" and text_policy == "generate":
            texts = schema.get("text_requirements", [])
            text_list = "、".join([f"\"{t}\"" for t in texts])
            strict_text_block = (
                f"画面必须且只能显示以下文字：{text_list}。\n"
                "不得出现除此之外的任何可读文字、装饰文字、章印文字、小标签、英文补充或无意义文字。"
                "文字应清晰、准确、层级明确，排版稳定，不做创意发散。"
            )
            optimized = re.sub(
                r"【文字要求】.*?(?=【|$)",
                f"【文字要求】\n{strict_text_block}\n",
                optimized,
                flags=re.DOTALL,
            )
        direction = ratio_to_direction(aspect_ratio)
        debug_info = (
            f"layout_type={layout_type}\n"
            f"optimize_strength={optimize_strength}\n"
            f"aspect_ratio={aspect_ratio}\n"
            f"direction={direction}\n"
            f"text_policy={text_policy}\n"
            f"has_exact_text={str(bool(exact_text.strip())).lower()}\n"
            f"seed={seed}\n"
            f"resolved_layout_type={schema.get('image_type', '')}\n"
            f"resolved_text_policy={schema.get('text_policy', '')}\n"
            f"schema_result={json.dumps(schema, ensure_ascii=False)}\n"
            f"renderer_input={json.dumps(schema, ensure_ascii=False)}\n"
            f"final_prompt={optimized}"
        )
        try:
            import server
            server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
        except Exception:
            pass
        return (optimized, debug_info)


NODE_CLASS_MAPPINGS = {
    "GptImage2PromptOptimizer": GptImage2PromptOptimizer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GptImage2PromptOptimizer": "GPT-Image-2 文生图提示词控制器",
}
