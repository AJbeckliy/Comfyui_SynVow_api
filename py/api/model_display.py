"""
model display.
"""

MODEL_DISPLAY_NAMES = {
    # 文本 Gemini
    "gemini-3.1-pro-稳定": "GM3.1-pro-稳定",
    "gemini-3.5-flash-稳定": "GM3.5-flash-稳定",
    "gemini-3.5-flash-lite-稳定": "GM3.5-flash-lite-稳定",
    "gemini-3.6-flash-稳定": "GM3.6-flash-稳定",
    "gemini-3.7-flash-wd": "GM3.7-flash-稳定",
    "gemini-3.8-flash-wd": "GM3.8-flash-稳定",
    "gemini-3-pro-2606": "GM3-pro-2606",
    "gemini-3.1-pro-2606": "GM3.1-pro-2606",
    "gemini-3.1-flash-2606": "GM3.1-flash-2606",
    "gemini-3.5-flash-2606": "GM3.5-flash-2606",
    # 文本 Qwen
    "qwen3.6-flash-wd": "qwen3.6-flash-稳定",
    "qwen3.6-plus-wd": "qwen3.6-plus-稳定",
    "qwen3.7-plus-wd": "qwen3.7-plus-稳定",
    "qwen3.7-max-wd": "qwen3.7-max-稳定",
    "qwen3.8-max-wd": "qwen3.8-max-稳定",
    # 文本 GPT / PT
    "gpt-5.5-稳定": "PT5.5-稳定",
    "gpt-5.6-sol-稳定": "PT5.6-sol-稳定",
    "gpt-5.4-qy": "PT5.4-企业",
    "gpt-5.5-qy": "PT5.5-企业",
    "gpt-5.6-sol-qy": "PT5.6-sol-企业",
    "gpt-5.5-2606": "PT5.5-2606",
    "gpt-5.4-2606": "PT5.4-2606",
    # 图像 NanoBanana
    "nano-banana-2-2605": "全能N2-2605",
    "nano-banana-2-lite-2607": "全能N2-lite-2607",
    "nano-banana-2-稳定": "全能N2-稳定",
    "nanobanana2-qy": "全能N2-企业",
    "nano-banana-2-官方": "全能N2-官方",
    "nano-banana-pro-2605": "全能Npro-2605",
    "nano-banana-pro-稳定": "全能Npro-稳定",
    "nano-banana-pro-官方": "全能Npro-官方",
    "nanobananapro-qy": "全能Npro-企业",
    # 图像 GPT-Image
    "gpt-image-2.5-wd": "PT2.5-稳定",
    "gpt-image-2.5-qy": "PT2.5-企业",
    "gpt-image-2.5-1k-qy": "PT2.5-1k-企业",
    "gpt-image-2.5-gf": "PT2.5-官方",
    "gpt-image-2.5-2609": "PT2.5-2609",
    "gpt-image-2.5-1k-2609": "PT2.5-1k-2609",
    "gpt-image-2-1k-2605": "全能G2-1k-2605",
    "gpt-image-2-稳定": "全能G2-稳定",
    "gpt-image-2-官方": "全能G2-官方",
    "gpt-image-2-1k-qy": "全能G2-1k-企业",
    "gpt-image-2-4k-qy": "全能G2-4k-企业",
    # 图像 Grok
    "grok-image-1.5-稳定": "GK1.5-稳定",
    "grok-image-2.0-wd": "GK2.0-稳定",
    # 视频
    "doubao-seedance-2.5": "seedance-2.5",
    "sd2.0-dj": "sd2.0-特惠版",
    "MiniMax-H3": "MiniMax-H3-稳定",
    "MiniMax-H3-dj": "MiniMax-H3-低价",
    "veo3.1": "Veo 3.1",
    "grok-1.5-video": "GK视频",
    "Omni-Flash-Ext": "O-Flash-Ext",
    "omni-flash-preview": "O-flash-preview",
    "omni-1.1-flash": "O-1.1-flash",
    "wan3.0-video-wd": "wan3.0-video-稳定",
    # 音频
    "suno5.5": "Suno 5.5",
    "suno6": "Suno 6",
    "suno6-fc": "Suno 6 翻唱",
    "suno6-yc": "Suno 6 延长",
    "doubao-seed-audio-1.0": "豆包语音1.0",
}

_DISPLAY_TO_API = {label: model for model, label in MODEL_DISPLAY_NAMES.items()}


def display_name(model):
    return MODEL_DISPLAY_NAMES.get(model, model)


def combo_models(api_ids):
    return [display_name(m) for m in api_ids]


def resolve_model(name, default=""):
    name = name or default
    if name in MODEL_DISPLAY_NAMES:
        return name
    return _DISPLAY_TO_API.get(name, name)


def pick_model(name, allowed, default=""):
    model = resolve_model(name, default)
    return model if model in allowed else default
