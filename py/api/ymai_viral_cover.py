"""YMAI viral-cover prompt node backed by the shared SynVow LLM client."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .ymai_llm import add_seed_input, chat_completion, default_model, fetch_models, image_to_data_urls, input_hash, strip_seed


AUTO_STYLE = "不指定（根据标题自动设计）"
STYLES = [
    AUTO_STYLE,
    "小红书干净高级风",
    "强冲击爆款标题风",
    "科技感教程封面风",
    "商业海报风",
    "杂志大片风",
    "可爱手账风",
    "电商产品种草风",
    "真实生活方式风",
    "自定义",
]
STYLE_PROFILES = {
    "小红书干净高级风": "自然、清爽、有生活方式审美和编辑感",
    "强冲击爆款标题风": "第一眼有吸引力，主体与标题关系有力量，整体像成熟内容海报",
    "科技感教程封面风": "专业、清晰、有科技与教程气质，视觉信息有秩序",
    "商业海报风": "完整的品牌主视觉和广告级画面，成熟、有传播感",
    "杂志大片风": "强调摄影、人物气场和编辑式排版，像真实杂志封面",
    "可爱手账风": "轻松、有亲和力、带手作或拼贴趣味，但保持完整设计感",
    "电商产品种草风": "突出产品价值、使用场景和购买吸引力，产品准确可信",
    "真实生活方式风": "自然、真实、有生活气息，像被捕捉到的优质内容瞬间",
}

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "ymai_viral_cover_system_prompt.txt"


def load_system_prompt():
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def text_fingerprint(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:12]


def build_user_prompt(封面风格, 主题关键词, 封面标题, 自定义要求, has_image=False):
    image_notice = (
        "已上传参考图片，请先理解图片，再让图片服务于封面标题。"
        if has_image
        else "没有参考图片，请围绕封面标题自主创造合适的主体、场景和设计形式。"
    )
    封面风格 = (封面风格 or AUTO_STYLE).strip()
    自定义要求 = (自定义要求 or "").strip()
    主题关键词 = (主题关键词 or "").strip()
    封面标题 = (封面标题 or "").strip()

    if 封面风格 == AUTO_STYLE:
        style_profile = "不预设风格，请根据标题、可选主题和参考图自行选择最合适的完整封面设计"
    elif 封面风格 == "自定义":
        style_profile = (
            "按补充要求中的自定义审美方向执行，但不要套用固定模板"
            if 自定义要求
            else "不预设风格，请根据标题和参考图自行设计"
        )
    else:
        profile = STYLE_PROFILES.get(封面风格, 封面风格)
        style_profile = f"可参考{封面风格}的审美气质（{profile}），但不要套用固定模板"

    return f"""请像商业封面视觉导演一样理解本次需求，并输出一段完整、具体、可执行的中文生图指令。
封面标题：{封面标题}
可选主题信息：{主题关键词 or "未提供，请从标题和参考图判断"}
审美方向：{style_profile}
补充要求：{自定义要求 or "无"}
{image_notice}
不要复述这些字段，不要写分析过程；要给出完整封面方案，包括主视觉、标题版式、辅助信息区、场景光影和成品质感。"""


class ViralCoverLLMPrompt:
    @classmethod
    def INPUT_TYPES(cls):
        models = fetch_models()
        return add_seed_input({
            "required": {
                "model": (models, {"default": default_model(models)}),
                "封面标题": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "加载图像": ("IMAGE",),
                "封面风格": (STYLES, {"default": AUTO_STYLE}),
                "主题关键词": ("STRING", {"default": "", "multiline": False}),
                "自定义要求": ("STRING", {"default": "", "multiline": True}),
                "temperature": ("FLOAT", {"default": 0.4, "min": 0.0, "max": 2.0, "step": 0.1}),
                "max_tokens": ("INT", {"default": 2048, "min": 256, "max": 8192, "step": 1}),
            },
        })

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("封面提示词",)
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/文本"
    OUTPUT_NODE = True
    API_NODE = False
    IS_CHANGED = staticmethod(input_hash)

    def generate(
        self,
        model,
        封面标题,
        加载图像=None,
        封面风格=AUTO_STYLE,
        主题关键词="",
        自定义要求="",
        temperature=0.4,
        max_tokens=2048,
        **kwargs,
    ):
        strip_seed(kwargs)
        if not str(封面标题 or "").strip():
            raise RuntimeError("请填写封面标题。")

        role = load_system_prompt()
        prompt = build_user_prompt(
            封面风格,
            主题关键词,
            封面标题,
            自定义要求,
            has_image=加载图像 is not None,
        )
        image_urls = image_to_data_urls(加载图像, quality=92)
        result = chat_completion(
            model,
            role,
            prompt,
            image_urls=image_urls,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=180,
        ).strip()
        print(
            json.dumps(
                {
                    "node": "ViralCoverLLMPrompt",
                    "model": model,
                    "system_prompt_hash": text_fingerprint(role),
                    "has_image": bool(image_urls),
                    "output_length": len(result),
                },
                ensure_ascii=False,
            )
        )
        return (result,)


NODE_CLASS_MAPPINGS = {
    "ViralCoverLLMPrompt": ViralCoverLLMPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ViralCoverLLMPrompt": "YM-爆款封面",
}
