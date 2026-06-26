"""YMAI prompt nodes exposed through the SynVow API text category."""

from __future__ import annotations

import hashlib
import json

from .ymai_character_card import CharacterCardPromptBuilder as _CharacterCardPromptBuilder
from .ymai_emotion_reaction import EmotionReactionVideoPromptNode as _EmotionReactionVideoPromptNode
from .ymai_storyboard import YunMengStoryboardPromptBuilder as _YunMengStoryboardPromptBuilder
from .ymai_viral_cover import ViralCoverLLMPrompt as _ViralCoverLLMPrompt


_CATEGORY = "💫SynVow_api/api/文本"
_SEED_INPUTS = {
    "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
}


def _clone_inputs(inputs):
    cloned = {}
    for group, values in inputs.items():
        cloned[group] = dict(values) if isinstance(values, dict) else values
    return cloned


def _with_seed_inputs(inputs):
    inputs = _clone_inputs(inputs)
    optional = dict(inputs.get("optional", {}))
    optional.update(_SEED_INPUTS)
    inputs["optional"] = optional
    return inputs


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    shape = getattr(value, "shape", None)
    dtype = getattr(value, "dtype", None)
    if shape is not None:
        return {"type": type(value).__name__, "shape": list(shape), "dtype": str(dtype)}
    return repr(value)


def _input_hash(*args, **kwargs):
    payload = {"args": _json_safe(args), "kwargs": _json_safe(kwargs)}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _strip_seed_kwargs(kwargs):
    kwargs.pop("seed", None)
    return kwargs


class _SeedCacheMixin:
    @classmethod
    def INPUT_TYPES(cls):
        return _with_seed_inputs(super().INPUT_TYPES())

    @classmethod
    def IS_CHANGED(cls, *args, **kwargs):
        return _input_hash(*args, **kwargs)


class ViralCoverLLMPrompt(_SeedCacheMixin, _ViralCoverLLMPrompt):
    CATEGORY = _CATEGORY
    API_NODE = False

    def generate(self, *args, **kwargs):
        return super().generate(*args, **_strip_seed_kwargs(kwargs))


class YunMengStoryboardPromptBuilder(_SeedCacheMixin, _YunMengStoryboardPromptBuilder):
    CATEGORY = _CATEGORY
    API_NODE = False

    def build_prompts(self, **kwargs):
        return super().build_prompts(**_strip_seed_kwargs(kwargs))


class EmotionReactionVideoPromptNode(_SeedCacheMixin, _EmotionReactionVideoPromptNode):
    CATEGORY = _CATEGORY
    API_NODE = False

    def generate(self, *args, **kwargs):
        return super().generate(*args, **_strip_seed_kwargs(kwargs))


class CharacterCardPromptBuilder(_SeedCacheMixin, _CharacterCardPromptBuilder):
    CATEGORY = _CATEGORY
    API_NODE = False

    def build(self, *args, **kwargs):
        return super().build(*args, **_strip_seed_kwargs(kwargs))


NODE_CLASS_MAPPINGS = {
    "ViralCoverLLMPrompt": ViralCoverLLMPrompt,
    "YunMengStoryboardPromptBuilder": YunMengStoryboardPromptBuilder,
    "EmotionReactionVideoPromptNode": EmotionReactionVideoPromptNode,
    "CharacterCardPromptBuilder": CharacterCardPromptBuilder,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ViralCoverLLMPrompt": "YM-爆款封面",
    "YunMengStoryboardPromptBuilder": "YM-故事板",
    "EmotionReactionVideoPromptNode": "YM-人物情绪",
    "CharacterCardPromptBuilder": "YM-角色卡",
}
