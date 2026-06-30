from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, List, Optional
from xml.etree import ElementTree

from .ymai_llm import (
    DEFAULT_MODEL,
    add_seed_input,
    chat_completion,
    fetch_models as shared_fetch_models,
    image_to_data_urls,
    input_hash,
    strip_seed,
)


EMOTION_DIRECTIONS = [
    "开心 / 喜悦 / 惊喜",
    "害羞 / 尴尬 / 不自在",
    "紧张 / 害怕 / 慌乱",
    "惊讶 / 疑惑 / 愣住",
    "心虚 / 被看穿 / 想隐藏",
    "委屈 / 失落 / 难过",
    "生气 / 不满 / 压着火",
    "自定义情绪",
]

EMOTION_CATEGORIES = {
    "开心 / 喜悦 / 惊喜": "positive_outward",
    "害羞 / 尴尬 / 不自在": "social_awkward",
    "紧张 / 害怕 / 慌乱": "tense_defensive",
    "惊讶 / 疑惑 / 愣住": "surprise_confusion",
    "心虚 / 被看穿 / 想隐藏": "hidden_avoidant",
    "委屈 / 失落 / 难过": "sad_downward",
    "生气 / 不满 / 压着火": "restrained_anger",
    "自定义情绪": "custom",
}

PROMPT_DIRECTORY = Path(__file__).resolve().parents[1] / "prompts"
SYSTEM_PROMPT_DOCUMENT = PROMPT_DIRECTORY / "ymai_emotion_人物情绪反应视频提示词生成系统.docx"
INPUT_RULES_DOCUMENT = PROMPT_DIRECTORY / "ymai_emotion_节点输入理解规则.docx"


def read_docx_text(path: Path) -> str:
    """Read paragraph text from a bundled DOCX without third-party dependencies."""
    try:
        with zipfile.ZipFile(path) as archive:
            xml_data = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_data)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(
                node.text or "" for node in paragraph.findall(".//w:t", namespace)
            ).strip()
            if text:
                paragraphs.append(text)
        if not paragraphs:
            raise RuntimeError("文档中没有可读取的文字。")
        return "\n".join(paragraphs)
    except Exception as exc:
        raise RuntimeError(f"无法读取内置提示词文档 {path.name}: {exc}") from exc


def load_system_prompt() -> str:
    system_prompt = read_docx_text(SYSTEM_PROMPT_DOCUMENT)
    input_rules = read_docx_text(INPUT_RULES_DOCUMENT)
    return (
        f"{system_prompt}\n\n"
        "以下是追加的节点输入理解规则，必须与上方系统规则共同遵守；"
        "若发生冲突，以上方系统规则为准：\n"
        f"{input_rules}"
    )


SYSTEM_PROMPT = load_system_prompt()

def fetch_models() -> List[str]:
    return shared_fetch_models()


def image_to_data_url(image: Any) -> Optional[str]:
    urls = image_to_data_urls(image)
    return urls[0] if urls else None


def build_user_prompt(
    emotion_direction: str,
    emotion_intensity: str,
    video_duration: int,
    extra_requirements: str,
    has_image: bool,
) -> str:
    extra = extra_requirements.strip() or "无"
    if emotion_direction == "自定义情绪" and extra == "无":
        extra = "用户选择了自定义情绪但未填写具体情绪，请生成自然、明显、真实的人物情绪反应。"
    return f"""用户输入信息：
图片：{'已上传' if has_image else '未上传'}
情绪方向：{emotion_direction}
内部情绪分类：{EMOTION_CATEGORIES[emotion_direction]}
情绪强度：{emotion_intensity}
视频时长：{video_duration}秒
补充要求：{extra}

生成任务：
请根据以上信息生成一份人物情绪反应视频提示词。有图时优先理解并保持参考图；没有明确触发点时自动生成简单自然的触发原因；补充要求中的具体情绪、触发原因、动作和禁忌优先级最高。严格只输出【基础镜头设定】和【分段视频提示词】。"""


def clean_output(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"</?think>", "", cleaned, flags=re.IGNORECASE).strip()
    start = cleaned.find("【基础镜头设定】")
    if start >= 0:
        cleaned = cleaned[start:]
    return cleaned.strip()


class EmotionReactionVideoPromptNode:
    @classmethod
    def INPUT_TYPES(cls):
        models = fetch_models()
        default_model = DEFAULT_MODEL if DEFAULT_MODEL in models else models[0]
        return add_seed_input({
            "required": {
                "模型": (models, {"default": default_model}),
                "情绪方向": (EMOTION_DIRECTIONS, {"default": EMOTION_DIRECTIONS[0]}),
                "情绪强度": (
                    ["轻微隐藏", "自然明显", "明显外露", "强烈但真实"],
                    {"default": "自然明显"},
                ),
                "视频时长": (
                    "INT",
                    {"default": 5, "min": 1, "max": 15, "step": 1, "display": "slider"},
                ),
                "自定义、补充要求": (
                    "STRING",
                    {"default": "", "multiline": True, "placeholder": "具体情绪、场景、动作、禁忌或台词要求"},
                ),
            },
            "optional": {
                "图像": ("IMAGE",),
            },
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("提示词",)
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/文本"
    OUTPUT_NODE = True
    API_NODE = False
    IS_CHANGED = staticmethod(input_hash)

    def generate(
        self,
        模型: str,
        情绪方向: str,
        情绪强度: str,
        视频时长: int,
        图像: Any = None,
        **kwargs: Any,
    ):
        strip_seed(kwargs)
        补充要求 = str(kwargs.get("自定义、补充要求", ""))
        user_prompt = build_user_prompt(
            情绪方向,
            情绪强度,
            int(视频时长),
            补充要求,
            图像 is not None,
        )
        image_url = image_to_data_url(图像)
        result = chat_completion(
            模型,
            SYSTEM_PROMPT,
            user_prompt,
            image_urls=[image_url] if image_url else None,
            temperature=0.6,
            max_tokens=4096,
            timeout=180,
        )
        prompt = clean_output(result)
        if not prompt:
            raise RuntimeError("SynVow LLM 返回了空提示词。")
        return {"ui": {"text": [prompt]}, "result": (prompt,)}


NODE_CLASS_MAPPINGS = {
    "EmotionReactionVideoPromptNode": EmotionReactionVideoPromptNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmotionReactionVideoPromptNode": "YM-人物情绪",
}
