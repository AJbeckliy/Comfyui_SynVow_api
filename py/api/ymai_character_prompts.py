from pathlib import Path


PROMPT_TYPE_TO_KEY = {
    "人物三视图": "character_turnaround",
    "人物面部三视图": "face_turnaround",
    "人物面部增强三视图": "face_plus_turnaround",
    "人物面部+三视图": "face_plus_turnaround",
    "人物角色卡": "character_card",
}


PROMPT_TYPE_TO_FILE = {
    "人物三视图": "ymai_character_card_人物三视图系统提示词.txt",
    "人物面部三视图": "ymai_character_card_人物面部三视图系统提示词.txt",
    "人物面部增强三视图": "ymai_character_card_人物面部增强三视图系统提示词.txt",
    "人物面部+三视图": "ymai_character_card_人物面部增强三视图系统提示词.txt",
    "人物角色卡": "ymai_character_card_人物角色卡系统提示词.txt",
}


PROMPT_TYPE_OPTIONS = [
    "人物三视图",
    "人物面部三视图",
    "人物面部增强三视图",
    "人物角色卡",
]


FALLBACK_REQUIREMENTS = {
    "人物三视图": "标准全身人物三视图，包含正面、侧面和背面，统一 A-pose 站姿，所有视图保持相同服装",
    "人物面部三视图": "胸部以上人物面部三视图，包含正面、侧面和后脑视图，五官与发型保持一致",
    "人物面部增强三视图": "面部细节视图与全身正面、侧面、背面三视图组合，版式清晰整洁",
    "人物面部+三视图": "面部细节视图与全身正面、侧面、背面三视图组合，版式清晰整洁",
    "人物角色卡": "完整人物角色卡，包含主要全身视图、面部特写、服装细节、配饰细节、颜色与材质说明",
}


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
CLOTHING_REFERENCE_PROMPT_FILE = PROMPT_DIR / "ymai_character_card_服装参考图系统提示词.txt"

CHINESE_OUTPUT_REQUIREMENT = """输出语言强制规则：
1. 最终 JSON 中的 prompt 字段值必须全部使用简体中文。
2. 除无法翻译的专有名词、模型名称或用户明确要求保留的原文外，不得输出英文句子，不得中英文混排。
3. 如果输入中包含英文风格词、英文描述或英文参考信息，必须先理解其含义，再转换成自然、完整的简体中文写入 prompt。
4. JSON 键名保持为 prompt，但 prompt 的内容必须是可直接交给下游生图节点使用的中文提示词。
5. 不要解释语言转换过程，不要在 JSON 外输出任何内容。"""


def load_system_prompt(prompt_type, include_clothing_reference=False):
    prompt_file = PROMPT_DIR / PROMPT_TYPE_TO_FILE[prompt_type]
    prompt = prompt_file.read_text(encoding="utf-8").strip()
    if include_clothing_reference:
        clothing_prompt = CLOTHING_REFERENCE_PROMPT_FILE.read_text(encoding="utf-8").strip()
        prompt = f"{prompt}\n\n{clothing_prompt}"
    return f"{prompt}\n\n{CHINESE_OUTPUT_REQUIREMENT}"


USER_PROMPT_TEMPLATE = """请根据以下信息生成「{prompt_type}」提示词。

角色简介/生成要求：
{character_brief}

面部参考图：
{face_reference_note}

服装参考图：
{outfit_reference_note}

统一风格要求：
{visual_style}

输出语言：
{language}（强制）

输出要求：
只生成当前选择的「{prompt_type}」这一种提示词，不要生成其他类型提示词。最终提示词必须使用简体中文。"""


FALLBACK_PROMPT_TEMPLATE = """{subject}。根据已提供的面部参考图和服装参考图，保持同一人物身份、发型、面部结构、服装设计、颜色、材质和标志性配饰。{specific_requirements}。生成干净专业的人物设定图，纯白背景，柔和影棚光线，细节清晰，各视图比例一致，不要复杂场景，不要戏剧化动作。"""
