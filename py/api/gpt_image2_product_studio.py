"""SynVow GPT-Image-2 six-in-one product image studio node."""

import math
import time
from pathlib import Path

import numpy as np
import requests
import torch.nn.functional as F

from . import synvow_auth
from .gpt_image_2_synvow import (
    _API_URL,
    _MODEL_TYPE_OPTIONS,
    _POLL_URL,
    _RATIO_TO_SIZE_1K,
    _collect_image_tensors,
    _is_changed,
    _resolve_size_params,
    _run_tasks,
    _unpack,
)
from .gemini_synvow import GEMINI_MODEL_OPTIONS
from .gpt_synvow import GPT_MODEL_OPTIONS
from .media_common import DIRECT_API_BASE, upload_image as _upload_image


CATEGORY = "💫SynVow_api/api/图像"

MODE_PRODUCT_REFINE = "产品精修"
MODE_SCENE_COMPOSITE = "产品融入场景"
MODE_CLARITY_RESTORE = "模糊图片高清"
MODE_OBJECT_REMOVE = "移除物品"
MODE_ADD_LIGHT_EFFECT = "增加光效"
MODE_OUTPAINT = "扩图"
LEGACY_MODE_CYBER_LIGHT = "赛博科技光效"

MODES = [
    MODE_PRODUCT_REFINE,
    MODE_SCENE_COMPOSITE,
    MODE_CLARITY_RESTORE,
    MODE_OBJECT_REMOVE,
    MODE_ADD_LIGHT_EFFECT,
    MODE_OUTPAINT,
]


_PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"
_PROMPT_FILES = {
    MODE_PRODUCT_REFINE: "gpt_image2_product_refine.txt",
    MODE_SCENE_COMPOSITE: "gpt_image2_scene_composite.txt",
    MODE_CLARITY_RESTORE: "gpt_image2_clarity_restore.txt",
    MODE_OBJECT_REMOVE: "gpt_image2_object_remove.txt",
    MODE_ADD_LIGHT_EFFECT: "gpt_image2_add_light_effect.txt",
    MODE_OUTPAINT: "gpt_image2_outpaint.txt",
}

_LLM_PROMPT_FILE = "gpt_image2_product_studio_llm_enhancer.txt"
_DEFAULT_LLM_MODEL = "gpt-5.5-2606"
_LLM_OFF = "关闭"
_LEGACY_LLM_AUTO = "自动增强"
_LLM_URL = f"{DIRECT_API_BASE}/api/models/completions"
_MODEL_LIST_URL = f"{DIRECT_API_BASE}/models/public-list"
_LLM_MODEL_CACHE_SECONDS = 300
_llm_model_cache = (0.0, [])


def _dedupe_models(models):
    return list(dict.fromkeys(str(model).strip() for model in models if str(model).strip()))


def _is_llm_model_name(name):
    return (
        name.startswith("gemini-")
        or (name.startswith("gpt-") and not name.startswith("gpt-image"))
    )


def _fetch_llm_model_options():
    """Fetch current SynVow GPT/Gemini models, with the plugin's local list as fallback."""
    global _llm_model_cache
    now = time.time()
    if _llm_model_cache[1] and now - _llm_model_cache[0] < _LLM_MODEL_CACHE_SECONDS:
        return list(_llm_model_cache[1])

    local_models = _dedupe_models(list(GPT_MODEL_OPTIONS) + list(GEMINI_MODEL_OPTIONS))
    remote_models = []
    try:
        response = requests.get(
            _MODEL_LIST_URL,
            params={
                "page": 1,
                "page_size": 100,
                "sort_by": "sort",
                "sort_order": "ASC",
            },
            timeout=5,
        )
        response.raise_for_status()
        items = response.json().get("data", {}).get("list", [])
        remote_models = _dedupe_models(
            item.get("name")
            for item in items
            if item.get("status") == 1
            and _is_llm_model_name(str(item.get("name") or "").strip())
        )
    except Exception as exc:
        print(f"[ProductStudio] 获取 LLM 模型失败，使用本地列表：{exc}")

    models = _dedupe_models(remote_models + local_models)
    if _DEFAULT_LLM_MODEL in models:
        models.remove(_DEFAULT_LLM_MODEL)
        models.insert(0, _DEFAULT_LLM_MODEL)
    models.append(_LLM_OFF)
    _llm_model_cache = (now, models)
    return list(models)


def _llm_model_input():
    models = _fetch_llm_model_options()
    default = _DEFAULT_LLM_MODEL if _DEFAULT_LLM_MODEL in models else models[0]
    return models, {"default": default}


def _normalize_mode(mode):
    mode = str(mode or MODE_PRODUCT_REFINE).strip()
    if mode == LEGACY_MODE_CYBER_LIGHT:
        return MODE_ADD_LIGHT_EFFECT
    return mode


def _load_mode_prompt(mode):
    prompt_path = _PROMPT_DIR / _PROMPT_FILES[mode]
    try:
        prompt = prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise FileNotFoundError(f"提示词文件读取失败：{prompt_path}") from exc
    if not prompt:
        raise ValueError(f"提示词文件为空：{prompt_path}")
    return prompt


def _load_llm_prompt():
    prompt_path = _PROMPT_DIR / _LLM_PROMPT_FILE
    try:
        prompt = prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise FileNotFoundError(f"LLM 提示词文件读取失败：{prompt_path}") from exc
    if not prompt:
        raise ValueError(f"LLM 提示词文件为空：{prompt_path}")
    return prompt


def build_product_studio_prompt(
    mode,
    extra_instructions="",
    has_reference=False,
    has_mask=False,
):
    """Build the base English edit prompt for one of the six product workflows."""
    mode = _normalize_mode(mode)
    if mode not in _PROMPT_FILES:
        raise ValueError(f"不支持的场景模式：{mode}")

    extra = str(extra_instructions or "").strip()
    if mode == MODE_SCENE_COMPOSITE and not has_reference:
        raise ValueError("“产品融入场景”必须连接 reference_image 作为目标场景图。")
    if mode == MODE_OBJECT_REMOVE and not extra and not has_mask:
        raise ValueError("“移除物品”请连接 mask，或在补充要求中描述要移除的对象、位置或明显特征。")
    if mode == MODE_ADD_LIGHT_EFFECT and not has_mask:
        raise ValueError("“增加光效”请连接 mask，并在原图中涂抹需要增加光效的区域。")

    prompt = _load_mode_prompt(mode)
    if extra:
        prompt += (
            "\n\nAdditional request:\n"
            + extra
            + "\nFollow this request only where it does not conflict with the preservation constraints above."
        )
    return prompt


def _strip_prompt_wrapper(text):
    """Remove common Markdown wrappers without altering the generated prompt body."""
    prompt = str(text or "").strip()
    if prompt.startswith("```"):
        first_line_end = prompt.find("\n")
        prompt = prompt[first_line_end + 1:] if first_line_end >= 0 else ""
        if prompt.rstrip().endswith("```"):
            prompt = prompt.rstrip()[:-3]
    for prefix in ("Final prompt:", "Final Prompt:", "Enhanced prompt:", "Enhanced Prompt:"):
        if prompt.startswith(prefix):
            prompt = prompt[len(prefix):].lstrip()
            break
    return prompt.strip()


def _llm_image_roles(mode, has_mask, has_reference):
    roles = ["Image 1: the original source image that must be preserved."]
    if has_mask:
        if mode == MODE_OUTPAINT:
            roles.append(
                "Image 2: an automatically detected black-and-white outpainting guide; "
                "white is the boundary-connected blank canvas to fill and black is protected."
            )
        else:
            roles.append(
                "Image 2: a spatially aligned black-and-white selection guide; "
                "white is selected and black is protected."
            )
    if has_reference:
        roles.append(
            f"Image {len(roles) + 1}: an optional reference image; use it only for the role "
            "allowed by the base prompt."
        )
    return roles


def _enhance_prompt_with_llm(
    api_key,
    llm_model,
    mode,
    base_prompt,
    extra_instructions,
    image,
    mask_guide=None,
    reference_image=None,
    seed=0,
):
    """Use the plugin's existing SynVow multimodal endpoint as a visual prompt planner."""
    analysis_images = [image]
    if mask_guide is not None:
        analysis_images.append(mask_guide)
    if reference_image is not None and mode != MODE_OBJECT_REMOVE:
        analysis_images.append(reference_image)

    image_urls = [_upload_image(api_key, item) for item in analysis_images]
    roles = _llm_image_roles(
        mode,
        has_mask=mask_guide is not None,
        has_reference=reference_image is not None and mode != MODE_OBJECT_REMOVE,
    )
    user_text = (
        f"Mode: {mode}\n"
        f"Additional request: {str(extra_instructions or '').strip() or '(none; infer the best edit from the images)'}\n\n"
        "Image roles:\n- "
        + "\n- ".join(roles)
        + "\n\nBase GPT-Image-2 prompt to preserve and improve:\n"
        + base_prompt
    )
    user_content = [{"type": "text", "text": user_text}]
    for index, image_url in enumerate(image_urls, start=1):
        user_content.append({"type": "text", "text": f"Image {index}:"})
        user_content.append({"type": "image_url", "image_url": {"url": image_url}})

    payload = {
        "model": llm_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": _load_llm_prompt()},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 2600,
        "temperature": 0.2,
        "seed": int(seed) % 2147483647,
    }
    print(f"[ProductStudio] LLM 正在分析图片与选区，mode={mode} model={llm_model}")
    response = requests.post(
        _LLM_URL,
        headers=synvow_auth.make_api_headers(api_key),
        json=payload,
        timeout=(30, 600),
        verify=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:500]}")
    enhanced = _strip_prompt_wrapper(synvow_auth.parse_chat_response(response.json()))
    if len(enhanced) < 80:
        raise RuntimeError(f"LLM 返回内容无效或过短：{enhanced[:160]}")
    print(f"[ProductStudio] LLM 分析完成，mode={mode}")
    return enhanced


def _mask_to_guide_image(mask, target_image=None):
    """Convert a non-empty ComfyUI MASK into a three-channel image guide."""
    mask = _unpack(mask)
    if mask is None:
        return None

    if mask.ndim == 2:
        mask = mask.unsqueeze(0)
    elif mask.ndim == 4 and mask.shape[-1] == 1:
        mask = mask[..., 0]
    elif mask.ndim == 4 and mask.shape[1] == 1:
        mask = mask[:, 0]

    if mask.ndim != 3:
        raise ValueError(f"mask 格式不正确，期望 [B,H,W]，实际为 {tuple(mask.shape)}")

    mask = mask.detach().float().clamp(0.0, 1.0)
    if float(mask.max().item()) <= 0.001:
        return None
    target_image = _unpack(target_image)
    if target_image is not None:
        if target_image.ndim == 4:
            target_size = (int(target_image.shape[1]), int(target_image.shape[2]))
        elif target_image.ndim == 3:
            target_size = (int(target_image.shape[0]), int(target_image.shape[1]))
        else:
            raise ValueError(
                f"image 格式不正确，期望 [B,H,W,C]，实际为 {tuple(target_image.shape)}"
            )
        if tuple(mask.shape[-2:]) != target_size:
            mask = F.interpolate(
                mask.unsqueeze(1),
                size=target_size,
                mode="bilinear",
                align_corners=False,
            ).squeeze(1)
    mask = (mask > 0.05).float()
    return mask.unsqueeze(-1).repeat(1, 1, 1, 3)


def _connected_white_region(candidate, strict_white):
    """Select near-white components that contain a strict-white canvas-edge seed."""
    try:
        import cv2

        _, labels = cv2.connectedComponents(candidate.astype(np.uint8), connectivity=4)
        border_labels = np.unique(
            np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]))
        )
        strict_labels = np.unique(labels[strict_white])
        selected_labels = np.intersect1d(border_labels, strict_labels)
        selected_labels = selected_labels[selected_labels != 0]
        return np.isin(labels, selected_labels)
    except ImportError:
        from collections import deque

        height, width = candidate.shape
        selected = np.zeros_like(candidate, dtype=bool)
        queue = deque()
        edge_points = (
            [(0, x) for x in range(width)]
            + [(height - 1, x) for x in range(width)]
            + [(y, 0) for y in range(1, height - 1)]
            + [(y, width - 1) for y in range(1, height - 1)]
        )
        for y, x in edge_points:
            if strict_white[y, x] and candidate[y, x] and not selected[y, x]:
                selected[y, x] = True
                queue.append((y, x))
        while queue:
            y, x = queue.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < height and 0 <= nx < width:
                    if candidate[ny, nx] and not selected[ny, nx]:
                        selected[ny, nx] = True
                        queue.append((ny, nx))
        return selected


def _make_boundary_white_mask(image):
    """Detect only pure-white expansion canvas connected to the outside boundary."""
    image = _unpack(image)
    if image is None:
        return None
    if image.ndim == 3:
        image = image.unsqueeze(0)
    if image.ndim != 4 or image.shape[-1] < 3:
        raise ValueError(f"image 格式不正确，期望 [B,H,W,C]，实际为 {tuple(image.shape)}")

    source = image.detach().float().clamp(0.0, 1.0)
    masks = []
    coverages = []
    for batch_index in range(int(source.shape[0])):
        rgb = source[batch_index, ..., :3].cpu().numpy()
        channel_min = rgb.min(axis=2)
        channel_range = rgb.max(axis=2) - channel_min
        candidate = (channel_min >= 0.975) & (channel_range <= 0.025)
        strict_white = (channel_min >= 0.995) & (channel_range <= 0.008)
        selected = _connected_white_region(candidate, strict_white)
        coverage = float(selected.mean())
        if coverage < 0.002:
            raise ValueError(
                "“扩图”没有检测到与画布边缘相连的 #ffffff 纯白区域。"
                "请先把需要扩充的边界填充为纯白色。"
            )
        if coverage > 0.95:
            raise ValueError("“扩图”检测到的白色区域超过画面 95%，请检查输入图是否正确。")
        masks.append(selected.astype(np.float32))
        coverages.append(coverage)

    mask = source.new_tensor(np.stack(masks, axis=0))
    guide = mask.unsqueeze(-1).repeat(1, 1, 1, 3)
    return guide, sum(coverages) / len(coverages)


def _make_removal_overlay(image, mask_guide):
    """Mark the selected area directly on the source with a vivid magenta overlay."""
    image = _unpack(image)
    if image.ndim == 3:
        image = image.unsqueeze(0)
    if image.ndim != 4 or image.shape[-1] != 3:
        raise ValueError(f"image 格式不正确，期望 [B,H,W,3]，实际为 {tuple(image.shape)}")

    source = image.detach().float().clamp(0.0, 1.0)
    mask = mask_guide[..., :1].to(device=source.device, dtype=source.dtype)
    if mask.shape[0] == 1 and source.shape[0] > 1:
        mask = mask.expand(source.shape[0], -1, -1, -1)
    elif mask.shape[0] != source.shape[0]:
        raise ValueError(
            f"image 与 mask 批次数量不一致：image={source.shape[0]} mask={mask.shape[0]}"
        )

    magenta = source.new_tensor((1.0, 0.0, 0.85)).view(1, 1, 1, 3)
    alpha = mask * 0.82
    return source * (1.0 - alpha) + magenta * alpha


def _closest_supported_aspect_ratio(image):
    """Return the supported ratio nearest to a ComfyUI IMAGE tensor."""
    image = _unpack(image)
    if image is None or image.ndim not in (3, 4):
        return "1:1"
    if image.ndim == 4:
        height, width = int(image.shape[1]), int(image.shape[2])
    else:
        height, width = int(image.shape[0]), int(image.shape[1])
    if height <= 0 or width <= 0:
        return "1:1"

    source_ratio = width / height
    candidates = [ratio for ratio in _RATIO_TO_SIZE_1K if ratio != "auto"]
    return min(
        candidates,
        key=lambda ratio: abs(
            math.log((int(ratio.split(":")[0]) / int(ratio.split(":")[1])) / source_ratio)
        ),
    )


class SynVowGptImage2ProductStudio:
    """One-node access to six focused GPT-Image-2 product editing workflows."""

    FUNCTION = "generate"
    CATEGORY = CATEGORY
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mode": (MODES, {"default": MODE_PRODUCT_REFINE}),
                "model_type": (
                    _MODEL_TYPE_OPTIONS,
                    {"default": "gpt-image-2-稳定"},
                ),
                "quality": (["auto", "low", "medium", "high"], {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (list(_RATIO_TO_SIZE_1K.keys()), {"default": "auto"}),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 2147483647,
                        "control_after_generate": True,
                    },
                ),
                "llm_model": _llm_model_input(),
            },
            "optional": {
                "reference_image": ("IMAGE",),
                "mask": ("MASK",),
                "extra_instructions": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "可选：描述摆放位置、移除目标、光效偏好、扩图环境或其他补充要求",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("images", "final_prompt", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def generate(
        self,
        image,
        mode=None,
        model_type=None,
        quality=None,
        resolution=None,
        aspect_ratio=None,
        seed=None,
        llm_model=None,
        reference_image=None,
        mask=None,
        extra_instructions=None,
    ):
        image = _unpack(image)
        if image is None:
            raise ValueError("请连接主输入图片 image。")

        mode = _normalize_mode(_unpack(mode) or MODE_PRODUCT_REFINE)
        model_type = _unpack(model_type) or "gpt-image-2-稳定"
        quality = _unpack(quality) or "auto"
        resolution = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio) or "auto"
        if mode in (MODE_CLARITY_RESTORE, MODE_OUTPAINT) and aspect_ratio == "auto":
            aspect_ratio = _closest_supported_aspect_ratio(image)
        seed = int(_unpack(seed) or 0)
        llm_model = _unpack(llm_model) or _DEFAULT_LLM_MODEL
        if llm_model == _LEGACY_LLM_AUTO:
            llm_model = _DEFAULT_LLM_MODEL
        reference_image = _unpack(reference_image)
        outpaint_coverage = None
        if mode == MODE_OUTPAINT:
            mask_guide, outpaint_coverage = _make_boundary_white_mask(image)
        elif mode in (MODE_OBJECT_REMOVE, MODE_ADD_LIGHT_EFFECT):
            mask_guide = _mask_to_guide_image(mask, image)
        else:
            mask_guide = None
        extra_instructions = _unpack(extra_instructions) or ""

        base_prompt = build_product_studio_prompt(
            mode,
            extra_instructions,
            has_reference=reference_image is not None,
            has_mask=mask_guide is not None,
        )

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)
        final_prompt = base_prompt
        llm_status = "off"
        if llm_model != _LLM_OFF:
            try:
                final_prompt = _enhance_prompt_with_llm(
                    api_key,
                    llm_model,
                    mode,
                    base_prompt,
                    extra_instructions,
                    image,
                    mask_guide=mask_guide,
                    reference_image=reference_image,
                    seed=seed,
                )
                llm_status = llm_model
            except Exception as exc:
                llm_status = f"fallback({llm_model})"
                print(f"[ProductStudio] LLM 增强失败，回退本地模板：{exc}")
        effective_resolution, size = _resolve_size_params(
            model_type,
            aspect_ratio,
            resolution,
        )

        if mode == MODE_OBJECT_REMOVE and mask_guide is not None:
            images = [_make_removal_overlay(image, mask_guide), mask_guide]
        else:
            images = [image]
            if mask_guide is not None:
                images.append(mask_guide)
        if reference_image is not None and mode != MODE_OBJECT_REMOVE:
            images.append(reference_image)

        image_urls = _run_tasks(
            [(final_prompt, images)],
            model_type,
            size,
            quality,
            effective_resolution,
            True,
            api_key,
            headers,
            _API_URL,
            _POLL_URL,
        )
        successful = sum(1 for url in image_urls if url)
        mask_status = "yes" if mask_guide is not None else "no"
        coverage_status = (
            f" white_area={outpaint_coverage:.1%}" if outpaint_coverage is not None else ""
        )
        if successful:
            status = (
                f"已完成 mode={mode} model={model_type} "
                f"ratio={aspect_ratio} size={size} quality={quality} "
                f"seed={seed} mask={mask_status} llm={llm_status}{coverage_status}"
            )
        else:
            status = (
                f"[ERROR] 生成失败 mode={mode} model={model_type} "
                f"ratio={aspect_ratio} size={size} quality={quality} "
                f"seed={seed} mask={mask_status} llm={llm_status}{coverage_status}"
            )

        output = _collect_image_tensors(image_urls)
        synvow_auth.refresh_balance()
        return output, final_prompt, status


NODE_CLASS_MAPPINGS = {
    "SynVowGptImage2ProductStudio": SynVowGptImage2ProductStudio,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGptImage2ProductStudio": "SynVow GPT-Image-2 产品六合一",
}
