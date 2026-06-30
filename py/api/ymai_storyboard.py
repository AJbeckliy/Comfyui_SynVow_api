"""YunMeng storyboard prompt builder backed by SynVow LLM."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ymai_llm import (
    DEFAULT_MODEL,
    add_seed_input,
    default_model,
    fetch_models,
    image_to_data_urls,
    input_hash,
    post_chat_completion as shared_post_chat_completion,
    strip_seed,
)
from . import synvow_auth


DEFAULT_MAX_TOKENS = 8192

SHOT_COUNTS = ["4", "6", "8", "10", "12"]

REFERENCE_INPUTS = {
    "角色卡参考图1": ("character_card_reference_image_1", "第 1 张角色卡参考图，用于保持角色身份、服装、发型、表情和整体造型一致"),
    "角色卡参考图2": ("character_card_reference_image_2", "第 2 张角色卡参考图，用于多角色或补充角色设定参考"),
    "角色卡参考图3": ("character_card_reference_image_3", "第 3 张角色卡参考图，用于多角色或补充角色设定参考"),
    "角色卡参考图4": ("character_card_reference_image_4", "第 4 张角色卡参考图，用于多角色或补充角色设定参考"),
    "场景参考图": ("scene_reference_image", "场景参考图，用于参考空间、背景、舞台、房间、街道等环境"),
    "画风参考图": ("style_reference_image", "画风参考图，用于参考整体风格、光影、色调、质感、设计风格"),
}

SENSITIVE_WORD_REPLACEMENTS = [
    ("性感", "优雅时尚"),
    ("妩媚", "柔和自信"),
    ("撩人", "有吸引力"),
    ("挑逗", "自然互动"),
    ("诱惑", "精致氛围"),
    ("诱人", "有魅力"),
    ("火辣", "活力时尚"),
    ("大胆暴露", "设计感服装"),
    ("暴露", "服装完整"),
    ("裸露", "服装完整"),
    ("半裸", "轻便穿搭"),
    ("裸体", "完整着装"),
    ("全裸", "完整着装"),
    ("赤裸", "完整着装"),
    ("露点", "细节得体"),
    ("透视", "轻薄质感"),
    ("低胸", "修身领口"),
    ("深V", "简洁领口"),
    ("乳沟", "上身线条自然"),
    ("胸部特写", "上半身构图"),
    ("臀部特写", "人物姿态构图"),
    ("大腿根", "腿部姿态自然"),
    ("内衣", "贴身服装"),
    ("泳衣", "运动风服装"),
    ("比基尼", "夏日服装"),
    ("情趣", "精致"),
    ("sex appeal", "elegant fashion style"),
    ("sexy", "elegant and stylish"),
    ("seductive", "confident and refined"),
    ("nude", "fully clothed"),
    ("naked", "fully clothed"),
    ("topless", "fully clothed"),
    ("bottomless", "fully clothed"),
    ("cleavage", "natural upper-body silhouette"),
    ("underwear", "fitted outfit"),
    ("lingerie", "fitted outfit"),
    ("bikini", "summer outfit"),
]

SENSITIVE_REGEX_REPLACEMENTS = [
    (r"(?i)\b(NSFW|18\+|adult content|erotic|pornographic)\b", "clean fashion style"),
    (r"(?i)\bsee[-\s]?through\b", "lightweight textured"),
]


def _plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _prompt_dir() -> Path:
    return _plugin_root() / "prompts"


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        print(f"[YunMengStoryboardPromptBuilder] failed to read prompt file {path.name}: {exc}")
        return ""


def _system_prompt() -> str:
    files = [
        "ymai_storyboard_01_基础身份.txt",
        "ymai_storyboard_03_分镜表规则.txt",
        "ymai_storyboard_04_分镜视频提示词规则.txt",
        "ymai_storyboard_07_安全词规则.txt",
        "ymai_storyboard_08_输出格式规则.txt",
    ]
    prompt = "\n\n".join(text for text in (_read_text_file(_prompt_dir() / name) for name in files) if text)
    if prompt:
        return prompt
    return "你是一名专业 AIGC 故事版提示词导演。只返回 JSON 对象，字段为 storyboard_prompt、video_prompt_list。"


def fetch_llm_models() -> List[str]:
    return fetch_models()


def _default_model(models: List[str]) -> str:
    return default_model(models)


def _collect_reference_images(kwargs: Dict[str, Any]) -> List[Dict[str, str]]:
    references: List[Dict[str, str]] = []
    for ui_name, (api_name, description) in REFERENCE_INPUTS.items():
        image = kwargs.get(ui_name)
        if image is None:
            continue
        for data_url in image_to_data_urls(image):
            references.append({"name": api_name, "description": description, "url": data_url})
    return references


def _post_chat_completion(payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    return shared_post_chat_completion(payload, timeout=timeout)


def _remove_think_tags(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\|begin_of_box\|>|<\|end_of_box\|>", "", text)
    return text.strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json|JSON|markdown|md)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = _strip_code_fences(_remove_think_tags(text))
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(_normalize_text(item) for item in value if _normalize_text(item)).strip()
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value).strip()


def _sanitize_for_downstream_image_nodes(text: str) -> str:
    if not text:
        return ""
    for source, target in SENSITIVE_WORD_REPLACEMENTS:
        text = re.sub(re.escape(source), target, text, flags=re.IGNORECASE)
    for pattern, target in SENSITIVE_REGEX_REPLACEMENTS:
        text = re.sub(pattern, target, text)
    text = re.sub(r"(?im)^\s*.*(?:未成年|儿童|幼女|幼齿|child|minor|teen).*(?:性感|裸|露|诱惑|sexy|nude|naked).*$", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _clean_output(text: str, kind: str) -> str:
    text = _strip_code_fences(_remove_think_tags(text))
    text = re.sub(r"^\s*(好的|当然可以|下面是|以下是|我理解为)[:：,，。\s]*", "", text)
    text = re.sub(r"(?im)^\s*(项目蓝图|摘要|分析过程|debug|raw_response|blueprint_json|summary)\s*[:：].*$", "", text)
    text = text.replace("```json", "").replace("```markdown", "").replace("```", "")

    if kind == "video_prompt_list":
        banned = [
            "蓝色箭头", "橙色箭头", "绿色箭头", "紫色箭头", "箭头图例",
            "分镜表", "分镜格", "P01 面板栏", "页面排版", "纸张底色",
            "灰度手绘分镜表", "角色卡三视图",
        ]
        for word in banned:
            text = text.replace(word, "")
    elif kind == "storyboard_prompt" and "蓝色箭头" not in text:
        text = text.rstrip() + (
            "\n\n箭头标注规则：蓝色箭头表示镜头运动，橙色箭头表示人物运动，"
            "绿色箭头表示道具或环境运动，紫色箭头表示视线或注意力方向；"
            "箭头简洁清晰，不遮挡人物脸部，可在角落加入小型图例。"
        )

    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line.strip()).strip()
    return _sanitize_for_downstream_image_nodes(text)


def _layout_for_shot_count(shot_count: int) -> str:
    return {
        4: "4列 x 1行，或 2列 x 2行",
        6: "3列 x 2行",
        8: "4列 x 2行",
        10: "5列 x 2行",
        12: "4列 x 3行",
    }.get(shot_count, f"{shot_count}格，排版清晰")


def _messages(system_prompt: str, user_prompt: str, uploaded_references: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    if not uploaded_references:
        return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

    content: List[Dict[str, Any]] = [{"type": "text", "text": user_prompt}]
    for item in uploaded_references:
        content.append({"type": "image_url", "image_url": {"url": item["url"]}})
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": content}]


def _user_prompt(
    script: str,
    shot_count: int,
    extra_requirements: str,
    uploaded_references: List[Dict[str, str]],
) -> str:
    reference_lines = [
        f"- {item['name']}: {item['description']}，已作为图片输入发送给 LLM"
        for item in uploaded_references
    ]
    references_text = "\n".join(reference_lines) if reference_lines else "无参考图。"
    return f"""请根据以下节点参数生成结果。

shot_count: {shot_count}
language: 简体中文（强制）
storyboard_layout: {_layout_for_shot_count(shot_count)}
需要生成 storyboard_prompt: True
需要生成 video_prompt_list: True

分镜脚本：
{script}

其他需求：
{extra_requirements or "无。"}

参考图：
{references_text}

请只返回 JSON 对象，不要输出 JSON 外的任何文字。storyboard_prompt 和 video_prompt_list 的内容必须全部使用简体中文。"""


def _parse_response(content: str) -> Tuple[str, str]:
    data = _extract_json_object(content) or {}
    storyboard = _normalize_text(data.get("storyboard_prompt"))
    video = _normalize_text(data.get("video_prompt_list"))

    if not data:
        storyboard = _clean_output(content, "storyboard_prompt")
        video = ""

    storyboard = _clean_output(storyboard, "storyboard_prompt")
    video = _clean_output(video, "video_prompt_list")
    return storyboard, video


def _format_runtime_error(exc: Exception, model: str) -> str:
    message = str(exc)
    lowered = message.lower()
    if "model load is too high" in lowered or "try again later" in lowered or "overloaded" in lowered:
        return (
            f"[ERROR] YM-故事板：模型 `{model}` 当前上游负载过高，SynVow 已收到请求，"
            "但第三方模型没有返回可用内容。请稍后重试，或临时切换到其它 chat/multimodal 模型。"
        )
    if "http 400" in lowered and "第三方" in message:
        return (
            f"[ERROR] YM-故事板：模型 `{model}` 的第三方服务返回错误，"
            f"本次没有可解析内容。原始错误：{message}"
        )
    return f"[ERROR] YM-故事板：{message}"


def _extract_llm_content(data: Any) -> str:
    if isinstance(data, dict):
        try:
            parsed = synvow_auth.parse_chat_response(data)
            if parsed:
                return str(parsed).strip()
        except Exception:
            pass

    if isinstance(data, str):
        text = data.strip()
        if not text:
            return ""
        try:
            parsed = _extract_llm_content(json.loads(text))
            return parsed or text
        except Exception:
            return text

    if isinstance(data, dict) and isinstance(data.get("data"), (dict, list, str)):
        content = _extract_llm_content(data.get("data"))
        if content:
            return content

    choices = None
    if isinstance(data, dict):
        choices = data.get("choices") or data.get("candidates")
    elif isinstance(data, list):
        choices = data

    if isinstance(choices, list) and choices:
        first = choices[0] if isinstance(choices[0], dict) else {}
        message = first.get("message") if isinstance(first.get("message"), dict) else {}
        content = message.get("content") or first.get("content") or first.get("text")
        if isinstance(content, list):
            content = "\n".join(
                str(item.get("text", ""))
                for item in content
                if isinstance(item, dict) and item.get("text")
            )
        return str(content or "").strip()

    if isinstance(data, dict):
        message = data.get("message") if isinstance(data.get("message"), dict) else {}
        content = message.get("content") or data.get("content") or data.get("text")
        if content:
            return _content_to_text(content)
        for key in ("sourceData", "source_data", "response", "result", "raw", "output"):
            if key in data:
                content = _extract_llm_content(data[key])
                if content:
                    return content
        for value in data.values():
            if isinstance(value, (dict, list)):
                content = _extract_llm_content(value)
                if content:
                    return content

    return ""


def _content_to_text(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and item.get("text")
        ).strip()
    if isinstance(content, dict):
        for key in ("text", "content", "message"):
            if content.get(key):
                return _content_to_text(content[key])
        return json.dumps(content, ensure_ascii=False)
    return str(content or "").strip()


class YunMengStoryboardPromptBuilder:
    """Build storyboard and video prompts from one ComfyUI node."""

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("分镜表提示词", "分镜视频提示词")
    FUNCTION = "build_prompts"
    CATEGORY = "💫SynVow_api/api/文本"
    OUTPUT_NODE = True
    API_NODE = False
    IS_CHANGED = staticmethod(input_hash)

    @classmethod
    def INPUT_TYPES(cls):
        models = fetch_llm_models()
        return add_seed_input({
            "required": {
                "LLM模型": (models, {"default": _default_model(models)}),
                "脚本": ("STRING", {"multiline": True, "default": ""}),
                "镜头数量": (SHOT_COUNTS, {"default": "8"}),
                "其他需求": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "角色卡参考图1": ("IMAGE",),
                "角色卡参考图2": ("IMAGE",),
                "角色卡参考图3": ("IMAGE",),
                "角色卡参考图4": ("IMAGE",),
                "场景参考图": ("IMAGE",),
                "画风参考图": ("IMAGE",),
            },
        })

    def _error_result(self, message: str) -> Tuple[str, str]:
        return message, ""

    def build_prompts(self, **kwargs):
        strip_seed(kwargs)
        script = str(kwargs.get("脚本") or "").strip()
        if not script:
            message = "[ERROR] 故事版节点需要填写脚本。"
            print(f"[YunMengStoryboardPromptBuilder] {message}")
            return self._error_result(message)

        model = str(kwargs.get("LLM模型") or DEFAULT_MODEL)
        try:
            shot_count = int(kwargs.get("镜头数量") or 8)
            extra_requirements = str(kwargs.get("其他需求") or "").strip()

            uploaded_references = _collect_reference_images(kwargs)
            user_prompt = _user_prompt(
                script,
                shot_count,
                extra_requirements,
                uploaded_references,
            )
            payload = {
                "model": model,
                "messages": _messages(_system_prompt(), user_prompt, uploaded_references),
                "max_tokens": DEFAULT_MAX_TOKENS,
                "temperature": 0.35,
                "top_p": 0.9,
                "presence_penalty": 0.0,
                "frequency_penalty": 0.0,
                "reasoning_effort": "none",
            }
            data = _post_chat_completion(payload, min(360, 120 + len(uploaded_references) * 30))
            content = _extract_llm_content(data)
            if not content:
                raise RuntimeError(f"LLM API 返回内容为空。响应结构：{type(data).__name__}")
            return _parse_response(str(content))
        except Exception as exc:
            error = _format_runtime_error(exc, model)
            print(error)
            return self._error_result(error)


NODE_CLASS_MAPPINGS = {
    "YunMengStoryboardPromptBuilder": YunMengStoryboardPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YunMengStoryboardPromptBuilder": "YM-故事板",
}
