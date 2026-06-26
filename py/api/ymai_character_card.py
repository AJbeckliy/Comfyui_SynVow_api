import json
import re
import urllib.error

from .ymai_character_prompts import (
    FALLBACK_PROMPT_TEMPLATE,
    FALLBACK_REQUIREMENTS,
    PROMPT_TYPE_OPTIONS,
    USER_PROMPT_TEMPLATE,
    load_system_prompt,
)
from .ymai_llm import (
    DEFAULT_MODEL,
    chat_completion,
    default_model,
    fetch_models,
    image_to_data_urls,
)


DEFAULT_TIMEOUT_SECONDS = 180


def _fetch_rh_models():
    return fetch_models()


def _default_model(models):
    return default_model(models)


def _extract_json_object(text):
    if not text:
        return {}

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def _extract_prompt(text):
    data = _extract_json_object(text)
    prompt = data.get("prompt") if isinstance(data, dict) else None
    if prompt:
        return _clean_output_prompt(str(prompt))
    return _clean_output_prompt(str(text or ""))


def _clean_output_prompt(prompt):
    text = str(prompt or "").strip()
    if not text:
        return ""

    unwanted_clauses = {
        "no text",
        "no title",
        "no label",
        "no labels",
        "no number",
        "no numbers",
        "no dividing line",
        "no dividing lines",
        "no border",
        "no borders",
        "no table line",
        "no table lines",
        "no complex background",
        "no story scene",
        "no poster style",
        "no expression thumbnail",
        "no expression thumbnails",
        "no action pose group",
        "no pose references",
        "no pose reference area",
        "no extra pose figures",
        "no repeated expressions",
        "do not repeat expressions",
    }
    unwanted_patterns = [
        r"^不要(加入|出现|使用|写)?(任何)?(标题|编号|英文标签|中文标签|说明文字|分隔线|边框|虚线|表格线|复杂背景|故事场景|海报风格|动作姿态组|姿态参考区|额外小人姿态|重复表情).*",
        r"^不要让\s*4\s*个小表情重复.*",
    ]

    sentences = re.split(r"(?<=[。.!?])\s*|\n+", text)
    cleaned_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if any(re.search(pattern, sentence, flags=re.I) for pattern in unwanted_patterns):
            continue

        clauses = re.split(r"[,，]\s*", sentence)
        cleaned_clauses = []
        for clause in clauses:
            stripped = clause.strip().strip(".。")
            if not stripped:
                continue
            if stripped.lower() in unwanted_clauses:
                continue
            cleaned_clauses.append(clause.strip())
        if cleaned_clauses:
            cleaned_sentences.append("，".join(cleaned_clauses).strip(" ，,"))

    if not cleaned_sentences:
        return text

    result = "。".join(cleaned_sentences)
    result = re.sub(r"\s+", " ", result).strip(" ，,")
    result = re.sub(r"。{2,}", "。", result)
    return result


def _post_rh_llm(model, system_prompt, user_prompt, face_image, outfit_image, timeout):
    images = [image for image in (face_image, outfit_image) if image is not None]
    image_urls = []
    for image in images:
        image_urls.extend(image_to_data_urls(image))
    return chat_completion(
        model,
        system_prompt,
        user_prompt,
        image_urls=image_urls,
        temperature=0.35,
        max_tokens=4096,
        top_p=1.0,
        reasoning_effort="none",
        timeout=timeout,
    )


def _fallback_prompt(prompt_type, character_brief, visual_style):
    subject = character_brief.strip() or "原创人物角色"
    return _clean_output_prompt(FALLBACK_PROMPT_TEMPLATE.format(
        subject=subject,
        specific_requirements=f"{FALLBACK_REQUIREMENTS[prompt_type]}。视觉风格：{visual_style}",
    ))


def _build_visual_style(preset, custom_style):
    preset_map = {
        "自定义": "",
        "专业动漫设定稿": "专业动漫人物设定稿，线条干净，比例准确，细节丰富，达到可用于制作的完整度",
        "写实角色设定稿": "写实人物设定稿，人体结构自然，面部结构真实，服装材质和细节清晰，采用干净的影棚参考图风格",
        "国风角色设定稿": "国风奇幻人物设定稿，轮廓优雅，服装结构精致，包含传统元素与细腻材质，画面专业整洁",
        "二次元游戏立绘设定": "二次元游戏人物设定稿，角色比例美观，服装层次清晰，立绘精致，线条干净",
        "3D建模参考设定": "3D 建模参考设定稿，采用正交视图，比例统一，正面、侧面和背面轮廓清楚，材质与配饰细节明确",
        "厚涂概念设定": "厚涂概念人物设定稿，笔触细腻，造型明确，服装和材质说明完整，版式干净",
        "简洁线稿设定": "简洁线稿人物设定，阴影克制，轮廓准确，造型易读，服装结构清晰",
    }
    base_style = preset_map.get(preset, preset)
    if preset == "自定义":
        return custom_style.strip() or preset_map["写实角色设定稿"]
    if custom_style.strip():
        return f"{base_style}, {custom_style.strip()}"
    return base_style


class CharacterCardPromptBuilder:
    @classmethod
    def INPUT_TYPES(cls):
        models = _fetch_rh_models()
        return {
            "required": {
                "prompt_type": (
                    PROMPT_TYPE_OPTIONS,
                    {"default": "人物角色卡"},
                ),
                "character_brief": (
                    "STRING",
                    {
                        "default": "一个原创人物角色。请在这里写角色简介、外貌、服装、气质，以及本次生成的额外要求。",
                        "multiline": True,
                    },
                ),
                "rh_model": (models, {"default": _default_model(models)}),
                "visual_style_preset": (
                    [
                        "自定义",
                        "专业动漫设定稿",
                        "写实角色设定稿",
                        "国风角色设定稿",
                        "二次元游戏立绘设定",
                        "3D建模参考设定",
                        "厚涂概念设定",
                        "简洁线稿设定",
                    ],
                    {"default": "专业动漫设定稿"},
                ),
                "custom_visual_style": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                    },
                ),
            },
            "optional": {
                "face_reference_image": ("IMAGE",),
                "outfit_reference_image": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("提示词",)
    FUNCTION = "build"
    CATEGORY = "💫SynVow_api/api/文本"

    def build(
        self,
        prompt_type,
        character_brief,
        rh_model,
        visual_style_preset,
        custom_visual_style,
        face_reference_image=None,
        outfit_reference_image=None,
    ):
        system_prompt = load_system_prompt(prompt_type, outfit_reference_image is not None)
        visual_style = _build_visual_style(visual_style_preset, custom_visual_style)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            prompt_type=prompt_type,
            character_brief=character_brief.strip(),
            face_reference_note=(
                "已连接面部参考图。请读取参考图中的脸型、五官、发型、发色、表情气质和头部轮廓。"
                if face_reference_image is not None
                else "未提供面部参考图。请根据角色简介/生成要求生成稳定的面部描述。"
            ),
            outfit_reference_note=(
                "已连接服装参考图。请读取参考图中的服装版型、层次、材质、颜色、纹样和配件。"
                if outfit_reference_image is not None
                else "未提供服装参考图。请根据角色简介/生成要求生成稳定的服装描述。"
            ),
            visual_style=visual_style.strip(),
            language="中文",
        )

        prompt = ""
        try:
            raw_response = _post_rh_llm(
                rh_model,
                system_prompt,
                user_prompt,
                face_reference_image,
                outfit_reference_image,
                DEFAULT_TIMEOUT_SECONDS,
            )
            prompt = _extract_prompt(raw_response)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            print(f"[YM-角色卡] SynVow LLM call failed, fallback prompt generated. Error: {exc}")

        if not prompt:
            prompt = _fallback_prompt(prompt_type, character_brief.strip(), visual_style)

        return (_clean_output_prompt(prompt),)
