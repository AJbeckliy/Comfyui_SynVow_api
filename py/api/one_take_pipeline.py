from pathlib import Path
from hashlib import sha256
import re

from .ymai_llm import chat_completion, default_model, fetch_models, image_to_data_urls


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
CATEGORY = "💫SynVow_api/api/文本"
LLM_MODELS = fetch_models()
DEFAULT_LLM_MODEL = (
    "gemini-3.5-flash-稳定"
    if "gemini-3.5-flash-稳定" in LLM_MODELS
    else default_model(LLM_MODELS)
)


def _load_prompt(filename):
    return (PROMPT_DIR / filename).read_text(encoding="utf-8").strip()


def _prompt_digest(*filenames):
    digest = sha256()
    for filename in filenames:
        digest.update((PROMPT_DIR / filename).read_bytes())
    return digest.hexdigest()


def _render(filename, values):
    prompt = _load_prompt(filename)
    for key, value in values.items():
        prompt = prompt.replace("{{" + key + "}}", str(value))
    return prompt


def _append_requirements(prompt, requirements):
    requirements = str(requirements or "").strip()
    if not requirements:
        return prompt
    return f"{prompt}\n\n【用户补充要求】\n{requirements}"


def _image_digest(image):
    if image is None:
        return ""
    try:
        value = image.detach().cpu().numpy() if hasattr(image, "detach") else image
        digest = sha256()
        digest.update(str(getattr(value, "shape", "")).encode("utf-8"))
        digest.update(str(getattr(value, "dtype", "")).encode("utf-8"))
        digest.update(value.tobytes())
        return digest.hexdigest()
    except Exception:
        return sha256(repr(image).encode("utf-8")).hexdigest()


def _clean_compiled_prompt(text):
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"^```(?:text|markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = re.sub(r"^(?:Seedance\s*2\.0\s*)?(?:视频)?提示词[：:]\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _compiled_prompt_is_complete(prompt):
    text = str(prompt or "").strip()
    return len(text) >= 180 and text[-1] in "。！？.!?"


def _secondary_subject_rule(subject_count):
    if subject_count == "0":
        return "画面中不新增动态次要主体，未被动作引导指定运动的背景元素保持原状态。"
    if subject_count == "1":
        return "画面中只有一个动态次要主体，并从开始到结束保持同一身份、外形和功能。"
    if subject_count == "2":
        return "画面中最多只有两个动态次要主体，二者身份、外形和功能保持稳定，不复制或增殖。"
    return "动态次要主体的数量和身份严格遵循动作引导，不新增未指定的角色、物体或活动元素。"


def _guardrail_suffix(subject_count):
    if subject_count == "0":
        count_rule = "始终只有同一个核心主体，不新增动态次要主体"
    elif subject_count == "1":
        count_rule = "始终只有同一个核心主体和一个指定的动态次要主体"
    elif subject_count == "2":
        count_rule = "始终只有同一个核心主体和最多两个指定的动态次要主体"
    else:
        count_rule = "核心主体保持唯一，动态次要主体数量严格遵循动作引导"
    return (
        f"稳定约束：{count_rule}；未被动作引导指定运动的背景人物、物体和装饰保持原状态；"
        "禁止复制、分裂、增殖、瞬移、无依据跳位、折返和新增事件；"
        "不生成编号、箭头、路线、小地图、时间轴或文字；无背景音乐和人声。"
    )


def _fallback_video_prompt(action, duration, scene_type, subject_count, camera, requirements):
    parts = [
        f"根据干净视频首帧生成{duration}连续视频。",
        "画面从始至终只有同一个核心主体，其身份、外观、比例、材质、服装和随身物件保持一致。",
        _secondary_subject_rule(subject_count),
        f"核心主体严格按顺序完成以下行动：{action}",
        "动作沿同一条连续路线推进，主体与地面、轨道或支撑面的空间关系稳定，不瞬移、不无依据跳位、不折返，不跳过起点或终点。",
        f"全程采用{camera if camera != '自动' else '稳定跟随'}运镜，一镜到底，无剪辑、无转场、无跳切、无突然变焦。",
        "不要生成分镜图中的编号、箭头、路线、小地图、时间轴或文字。不要增加动作、事件、特效、动态主体或场景结构。",
        "结束时核心主体稳定到达动作引导规定的最终位置。不要生成背景音乐和人声，只保留环境音与动作音效。",
    ]
    if requirements:
        parts.append(str(requirements).strip())
    return "\n".join(parts)


class OneTakeCharacterPrompt:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return _prompt_digest(
            "one_take_character_setting.txt",
            "one_take_character_text_setting.txt",
        )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "生成模式": (["图生图", "文生图"], {"default": "图生图"}),
                "人物描述": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "仅文生图模式必填：描述成年角色的外貌、体型、服装、配饰与视觉风格。",
                }),
                "保留标志性道具": (
                    ["自动判断", "保留", "移除"],
                    {"default": "自动判断"},
                ),
                "持握方式": (
                    ["自动判断", "单手", "双手", "双持", "不适用"],
                    {"default": "自动判断"},
                ),
                "武器比例": (
                    ["保持参考图", "常规", "加长", "自定义描述"],
                    {"default": "保持参考图"},
                ),
            },
            "optional": {
                "人物参考图": ("IMAGE",),
                "补充要求": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "IMAGE")
    RETURN_NAMES = ("人物设定提示词", "人物参考图")
    FUNCTION = "build"
    CATEGORY = CATEGORY
    API_NODE = False

    def build(self, 生成模式, 人物描述, 保留标志性道具,
              持握方式="自动判断", 武器比例="保持参考图",
              人物参考图=None, 补充要求="", **_legacy_inputs):
        if 生成模式 == "文生图":
            description = str(人物描述 or "").strip()
            if not description:
                raise ValueError("文生图模式下请填写“人物描述”。")
            prompt = _render("one_take_character_text_setting.txt", {
                "人物描述": description,
                "保留标志性道具": 保留标志性道具,
                "持握方式": 持握方式,
                "武器比例": 武器比例,
            })
        else:
            prompt = _render("one_take_character_setting.txt", {
                "保留标志性道具": 保留标志性道具,
                "持握方式": 持握方式,
                "武器比例": 武器比例,
            })

        return (_append_requirements(prompt, 补充要求), 人物参考图)


class OneTakeScenePrompt:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return _prompt_digest(
            "one_take_scene_setting.txt",
            "one_take_scene_text_setting.txt",
        )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "生成模式": (["图生图", "文生图"], {"default": "图生图"}),
                "场景描述": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "仅文生图模式必填：描述场景类型、空间结构、时间、天气、光线与关键元素。",
                }),
                "空间扩展程度": (
                    ["保守", "适度", "自由"],
                    {"default": "保守"},
                ),
                "关键区域数量": (
                    ["自动", "3", "4", "5", "6"],
                    {"default": "自动"},
                ),
            },
            "optional": {
                "补充要求": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("场景设定提示词",)
    FUNCTION = "build"
    CATEGORY = CATEGORY
    API_NODE = False

    def build(self, 生成模式, 场景描述, 空间扩展程度, 关键区域数量, 补充要求="", **_legacy_inputs):
        values = {
            "空间扩展程度": 空间扩展程度,
            "关键区域数量": 关键区域数量,
        }

        if 生成模式 == "文生图":
            description = str(场景描述 or "").strip()
            if not description:
                raise ValueError("文生图模式下请填写“场景描述”。")
            values["场景描述"] = description
            prompt = _render("one_take_scene_text_setting.txt", values)
        else:
            prompt = _render("one_take_scene_setting.txt", values)

        return (_append_requirements(prompt, 补充要求),)


class OneTakeStoryboardPrompt:
    @classmethod
    def IS_CHANGED(cls, **_kwargs):
        return _prompt_digest("one_take_storyboard.txt")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "人物设定图": ("IMAGE",),
                "场景设定图": ("IMAGE",),
                "动作引导": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "描述人物从哪里开始、经过哪里、完成什么动作以及如何结束。",
                }),
                "目标时长": (
                    ["15秒", "30秒", "45秒", "60秒"],
                    {"default": "15秒"},
                ),
                "节点数量": (
                    ["自动", "4", "5", "6", "7", "8", "9", "10"],
                    {"default": "自动"},
                ),
                "动作节奏": (
                    ["自动", "舒缓", "自然", "紧凑", "强烈"],
                    {"default": "自动"},
                ),
                "运镜偏好": (
                    ["自动", "跟随", "推进", "侧移", "环绕", "混合"],
                    {"default": "自动"},
                ),
            },
            "optional": {
                "补充要求": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "IMAGE", "IMAGE")
    RETURN_NAMES = ("路线分镜提示词", "人物设定图", "场景设定图")
    FUNCTION = "build"
    CATEGORY = CATEGORY
    API_NODE = False

    def build(self, 人物设定图, 场景设定图, 动作引导, 目标时长, 节点数量,
              动作节奏, 运镜偏好, 补充要求="", **_legacy_inputs):
        action = str(动作引导 or "").strip()
        if not action:
            raise ValueError("请填写“动作引导”，明确人物的起点、行动和结束状态。")

        prompt = _render("one_take_storyboard.txt", {
            "动作引导": action,
            "目标时长": 目标时长,
            "节点数量": 节点数量,
            "动作节奏": 动作节奏,
            "运镜偏好": 运镜偏好,
        })
        return (_append_requirements(prompt, 补充要求), 人物设定图, 场景设定图)


class OneTakeSeedancePromptCompiler:
    @classmethod
    def IS_CHANGED(cls, 路线分镜图, 动作引导, 目标时长, 场景类型,
                   动态次要主体数量, 运镜偏好, LLM模型, 人物设定图=None,
                   干净场景图=None, 补充要求="", **_kwargs):
        digest = sha256()
        digest.update(_prompt_digest("one_take_seedance_compiler.txt").encode("utf-8"))
        for value in (动作引导, 目标时长, 场景类型, 动态次要主体数量,
                      运镜偏好, LLM模型, 补充要求):
            digest.update(str(value).encode("utf-8"))
        for image in (路线分镜图, 人物设定图, 干净场景图):
            digest.update(_image_digest(image).encode("utf-8"))
        return digest.hexdigest()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "路线分镜图": ("IMAGE",),
                "动作引导": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "粘贴生成分镜时使用的原始动作引导，作为角色数量、动作和终点的事实来源。",
                }),
                "目标时长": (
                    [f"{seconds}秒" for seconds in range(5, 16)],
                    {"default": "15秒"},
                ),
                "场景类型": (
                    ["自动判断", "路径移动", "人物互动", "物体互动", "轻量动作"],
                    {"default": "自动判断"},
                ),
                "动态次要主体数量": (
                    ["自动", "0", "1", "2"],
                    {"default": "自动"},
                ),
                "运镜偏好": (
                    ["自动", "跟随", "推进", "侧移", "环绕"],
                    {"default": "跟随"},
                ),
                "LLM模型": (LLM_MODELS, {"default": DEFAULT_LLM_MODEL}),
            },
            "optional": {
                "人物设定图": ("IMAGE",),
                "干净场景图": ("IMAGE",),
                "补充要求": ("STRING", {"multiline": True, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("Seedance提示词", "编译信息")
    FUNCTION = "compile"
    CATEGORY = CATEGORY
    API_NODE = False

    def compile(self, 路线分镜图, 动作引导, 目标时长, 场景类型,
                动态次要主体数量, 运镜偏好, LLM模型, 人物设定图=None,
                干净场景图=None, 补充要求=""):
        action = str(动作引导 or "").strip()
        if not action:
            raise ValueError("请填写生成路线分镜时使用的原始“动作引导”。")

        system_prompt = _load_prompt("one_take_seedance_compiler.txt")
        user_prompt = f"""请把参考图中的路线分镜编译为可直接提交给 Seedance 2.0 的中文视频提示词。

输入约束：
- 动作引导：{action}
- 目标时长：{目标时长}
- 场景类型：{场景类型}
- 动态次要主体数量：{动态次要主体数量}
- 运镜偏好：{运镜偏好}
- 补充要求：{str(补充要求 or '').strip() or '无'}

参考图顺序：
1. 路线分镜图：只用于读取空间路线、动作顺序与结束位置。
2. 人物设定图（如有）：只用于识别同一主角与固定武器。
3. 干净场景图（如有）：只用于识别真实场景结构和必须保持静止的背景物体。

只输出最终视频提示词，不要解释。"""

        image_urls = []
        for image in (路线分镜图, 人物设定图, 干净场景图):
            if image is not None:
                image_urls.extend(image_to_data_urls(image))

        try:
            model = LLM模型 or DEFAULT_LLM_MODEL
            compiled = ""
            for attempt, max_tokens in enumerate((4096, 8192), start=1):
                retry_note = "" if attempt == 1 else "\n上一次输出被截断。请重新完整输出，禁止省略结尾。"
                result = chat_completion(
                    model,
                    system_prompt,
                    user_prompt + retry_note,
                    image_urls=image_urls,
                    temperature=0.1,
                    max_tokens=max_tokens,
                    timeout=300,
                )
                compiled = _clean_compiled_prompt(result)
                if _compiled_prompt_is_complete(compiled):
                    break
            if not _compiled_prompt_is_complete(compiled):
                raise RuntimeError(f"LLM 提示词不完整，当前长度 {len(compiled)} 字。")
            compiled = f"{compiled.rstrip()}\n{_guardrail_suffix(动态次要主体数量)}"
            info = f"LLM编译成功 | model={model} | attempts={attempt}"
        except Exception as exc:
            compiled = _fallback_video_prompt(
                action, 目标时长, 场景类型, 动态次要主体数量,
                运镜偏好, 补充要求,
            )
            info = f"LLM编译失败，已使用规则兜底 | {exc}"

        return (compiled, info)


NODE_CLASS_MAPPINGS = {
    "SynVowOneTakeCharacterSetting": OneTakeCharacterPrompt,
    "SynVowOneTakeSceneSetting": OneTakeScenePrompt,
    "SynVowOneTakeStoryboard": OneTakeStoryboardPrompt,
    "SynVowOneTakeSeedanceCompiler": OneTakeSeedancePromptCompiler,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowOneTakeCharacterSetting": "一镜到底-人物设定提示词",
    "SynVowOneTakeSceneSetting": "一镜到底-场景设定提示词",
    "SynVowOneTakeStoryboard": "一镜到底-路线分镜提示词",
    "SynVowOneTakeSeedanceCompiler": "一镜到底-Seedance提示词编译器（LLM）",
}
