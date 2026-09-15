# -*- coding: utf-8 -*-
"""
Alpha-aware SynVow GPT-Image-2 batch node.

Returns original image URLs so transparent PNGs can be saved directly with
their alpha channel.
"""

import concurrent.futures
import math
import re
import threading
import time

import comfy.utils
import requests

from . import synvow_auth
from .gpt_image_2_synvow import (
    _ASPECTS,
    _DEFAULT_GPT_IMAGE_COMBO,
    _MODEL_TYPE_OPTIONS,
    _NEW_MODELS,
    _QUALITIES_EXT,
    _STYLES,
    _build_payload,
    _is_changed,
    _prep_model,
    _unpack,
)
from .media_common import EDIT_POLL_URL, EDIT_SUBMIT_URL, extract_result_urls


CATEGORY = "💫SynVow_api/api/图像"
SUBMIT_RETRY_ATTEMPTS = 3
POLL_WORKER_LIMIT = 4
BLACK_PLACEHOLDER_TOKEN = "__SYNVOW_BLACK_PLACEHOLDER__"
SPLIT_ROUTING_OPTIONS = ("质量优先自动路由", "统一使用所选模型")
_ALPHA_CANCEL_EVENT = threading.Event()


class AlphaPollingCancelled(RuntimeError):
    pass


def request_alpha_cancel():
    _ALPHA_CANCEL_EVENT.set()


def _raise_if_alpha_cancelled():
    if _ALPHA_CANCEL_EVENT.is_set():
        raise AlphaPollingCancelled("已取消 GPT-Image-2 Alpha 轮询。")
    try:
        import comfy.model_management as mm
        mm.throw_exception_if_processing_interrupted()
    except AlphaPollingCancelled:
        raise


def _sleep_interruptible(seconds):
    end_time = time.time() + seconds
    while time.time() < end_time:
        _raise_if_alpha_cancelled()
        time.sleep(min(0.5, max(0, end_time - time.time())))
    _raise_if_alpha_cancelled()


def _poll_alpha_task(task_id, consumption_id, headers, poll_url, model):
    poll_body = {"task_id": task_id, "model": model}
    if consumption_id is not None:
        poll_body["consumption_id"] = consumption_id
    timeout_total = 1800
    interval = 5
    start_time = time.time()
    consecutive_errors = 0
    while True:
        _sleep_interruptible(interval)
        elapsed = int(time.time() - start_time)
        if elapsed >= timeout_total:
            print(f"[GPT-Image-2 Alpha] 超时: ...{task_id[-8:]} ({elapsed}s)")
            return None
        try:
            _raise_if_alpha_cancelled()
            poll_res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30, verify=False)
            _raise_if_alpha_cancelled()
            poll_res.raise_for_status()
            poll_json = poll_res.json()
            consecutive_errors = 0
            data_field = poll_json.get("data", poll_json) if isinstance(poll_json, dict) else poll_json
            # 2607 用 state，其余模型用 status
            status = ""
            if isinstance(data_field, dict):
                status = data_field.get("state") or data_field.get("status") or ""
            print(f"[GPT-Image-2 Alpha] ...{task_id[-8:]} status={status} ({elapsed}s)")
            if status in ("SUCCESS", "success", "succeeded", "completed", "done", "finished"):
                return poll_json
            if status in ("FAILURE", "failed", "error", "EXCEPTION"):
                msg = "任务失败"
                if isinstance(data_field, dict):
                    msg = data_field.get("error") or data_field.get("fail_reason", "任务失败")
                print(f"[GPT-Image-2 Alpha] 失败: ...{task_id[-8:]} {msg}")
                return None
        except AlphaPollingCancelled:
            raise
        except Exception as exc:
            consecutive_errors += 1
            print(f"[GPT-Image-2 Alpha] 轮询异常({consecutive_errors}/12): ...{task_id[-8:]} {exc}")
            if consecutive_errors >= 12:
                print(f"[GPT-Image-2 Alpha] 连续轮询异常过多，放弃: ...{task_id[-8:]}")
                return None


def _is_retryable_submit_error(exc):
    text = str(exc or "").lower()
    retry_markers = (
        "excessive system load",
        "too many requests",
        "rate limit",
        "timeout",
        "temporarily",
        "http 429",
        "http 500",
        "http 502",
        "http 503",
        "http 504",
    )
    return any(marker in text for marker in retry_markers)


def _response_error_text(response, limit=800):
    try:
        text = response.text or ""
    except Exception:
        text = ""
    text = text.replace("\n", " ").replace("\r", " ").strip()
    return text[:limit]


def _post_generation_payload(api_url, headers, payload):
    return requests.post(
        api_url,
        headers=headers,
        json=payload,
        params={"async": "true"},
        timeout=120,
        verify=False,
    )


def _submit_alpha_task(payload, headers, api_url):
    model = payload.get("model")
    img_key = "image_urls" if "image_urls" in payload else "images"
    img_count = len(payload.get(img_key, []))
    print(f"[GPT-Image-2 Alpha] 提交: model={model} images={img_count}")
    response = _post_generation_payload(api_url, headers, payload)
    if response.status_code >= 400:
        raise RuntimeError(f"提交失败 HTTP {response.status_code}: {_response_error_text(response)}")

    data = response.json() if isinstance(response.json(), dict) else {}
    data_field = data.get("data")
    data_item = (
        data_field[0] if isinstance(data_field, list) and data_field else None
    ) or (data_field if isinstance(data_field, dict) else {})
    source_data = data_item.get("sourceData") or {}
    source_inner = source_data.get("data")
    source_item = source_inner[0] if isinstance(source_inner, list) and source_inner else {}
    task_id = (
        data.get("task_id")
        or data_item.get("task_id")
        or source_item.get("task_id")
        or source_data.get("task_id")
    )
    consumption_id = data.get("consumption_id") or data_item.get("consumption_id")
    if not task_id:
        raise RuntimeError(f"提交失败，无 task_id: {str(data)[:200]}")
    print(f"[GPT-Image-2 Alpha] task_id=...{task_id[-8:]}")
    return task_id, consumption_id


def _submit_alpha_task_with_retry(payload, headers, api_url):
    last_exc = None
    for attempt in range(1, SUBMIT_RETRY_ATTEMPTS + 1):
        _raise_if_alpha_cancelled()
        try:
            return _submit_alpha_task(payload, headers, api_url)
        except Exception as exc:
            last_exc = exc
            if attempt >= SUBMIT_RETRY_ATTEMPTS or not _is_retryable_submit_error(exc):
                raise
            wait_seconds = 4 * attempt
            print(
                f"[GPT-Image-2 Alpha] 提交遇到临时负载/限流，{wait_seconds}s 后重试 "
                f"({attempt}/{SUBMIT_RETRY_ATTEMPTS}): {exc}"
            )
            _sleep_interruptible(wait_seconds)
    raise last_exc


def _apply_background_mode(payload, model, transparent):
    mode = "transparent" if transparent else "opaque"
    payload["background"] = mode
    payload["output_format"] = "png"
    if model not in _NEW_MODELS:
        payload["transparentBackground"] = bool(transparent)
    return mode


def _nearest_reference_aspect(image):
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 3:
        return "1:1"
    height = int(shape[-3])
    width = int(shape[-2])
    if height <= 0 or width <= 0:
        return "1:1"
    source_ratio = width / height
    candidates = [value for value in _ASPECTS if value != "auto" and ":" in value]
    return min(
        candidates,
        key=lambda value: abs(
            math.log(source_ratio / (float(value.split(":")[0]) / float(value.split(":")[1])))
        ),
    )


def _reference_custom_size(image, fallback_size):
    shape = getattr(image, "shape", None)
    match = re.fullmatch(r"(\d+)x(\d+)", str(fallback_size or ""))
    if shape is None or len(shape) < 3 or not match:
        return fallback_size
    source_height = int(shape[-3])
    source_width = int(shape[-2])
    if source_width <= 0 or source_height <= 0:
        return fallback_size
    fallback_width, fallback_height = (int(value) for value in match.groups())
    target_long_edge = max(fallback_width, fallback_height)
    if source_width >= source_height:
        target_width = target_long_edge
        target_height = max(16, round((target_long_edge * source_height / source_width) / 16) * 16)
    else:
        target_height = target_long_edge
        target_width = max(16, round((target_long_edge * source_width / source_height) / 16) * 16)
    return f"{target_width}x{target_height}"


def _is_background_layer_prompt(prompt):
    text = str(prompt or "")
    slot_marker = re.search(r"^\[Layer:\s*background\]", text, flags=re.IGNORECASE)
    legacy_marker = (
        "Reference image layer split request:" in text
        and re.search(r"Layer name:\s*[^\n]*背景", text, flags=re.IGNORECASE)
    )
    concise_marker = re.search(
        r"^Edit the input image\.\s*Return only (?:the )?complete background",
        text,
        flags=re.IGNORECASE,
    )
    return bool(slot_marker or legacy_marker or concise_marker)


def _layer_slot_id(prompt):
    match = re.search(r"^\[Layer:\s*([a-z_]+)\]", str(prompt or ""), flags=re.IGNORECASE)
    return match.group(1).lower() if match else ""


def _run_tasks_with_background(
    tasks,
    model,
    size,
    quality,
    resolution,
    is_img2img,
    api_key,
    headers,
    seed=None,
    gpt_style=None,
    transparent=True,
):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    _raise_if_alpha_cancelled()

    submitted = []
    for index, task in enumerate(tasks):
        prompt, images = task[:2]
        task_transparent = bool(task[2]) if len(task) > 2 else transparent
        task_options = task[3] if len(task) > 3 and isinstance(task[3], dict) else {}
        task_model = task_options.get("model", model)
        task_size = task_options.get("size", size)
        task_quality = task_options.get("quality", quality)
        task_resolution = task_options.get("resolution", resolution)
        task_style = task_options.get("gpt_style", gpt_style)
        _raise_if_alpha_cancelled()
        payload = _build_payload(
            task_model, prompt, task_size, task_quality, task_resolution, is_img2img, images,
            api_key=api_key, gpt_style=task_style, transparent=task_transparent,
        )
        try:
            seed_value = int(seed) if seed is not None else 0
        except Exception:
            seed_value = 0
        if seed_value > 0:
            payload["seed"] = seed_value
        background_mode = _apply_background_mode(payload, task_model, task_transparent)
        try:
            task_id, consumption_id = _submit_alpha_task_with_retry(payload, headers, EDIT_SUBMIT_URL)
            submitted.append((task_id, consumption_id, task_model))
            print(
                f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 提交成功 "
                f"model={task_model} quality={task_quality} background={background_mode} task_id=...{task_id[-8:]}"
            )
        except Exception as exc:
            print(f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 提交失败: {exc}")
            submitted.append(None)
        if index < total - 1:
            _sleep_interruptible(1)

    def _poll_one(item):
        _raise_if_alpha_cancelled()
        if item is None:
            pbar.update(1)
            return None
        task_id, consumption_id, task_model = item
        try:
            return _poll_alpha_task(task_id, consumption_id, headers, EDIT_POLL_URL, task_model)
        except AlphaPollingCancelled:
            raise
        except Exception as exc:
            print(f"[GPT-Image-2 Alpha] 轮询任务异常，使用黑图占位: ...{task_id[-8:]} {exc}")
            return None
        finally:
            pbar.update(1)

    worker_count = min(max(total, 1), POLL_WORKER_LIMIT)
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        poll_results = list(executor.map(_poll_one, submitted))

    image_urls = []
    for index, result in enumerate(poll_results):
        if result is not None:
            urls = extract_result_urls(result)
            if urls:
                image_urls.append(urls[0])
                if len(urls) > 1:
                    print(f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 返回多张图片，仅保留第一张以维持批次槽位")
            else:
                print(f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 任务完成但未解析到图片URL: {str(result)[:500]}")
                image_urls.append(None)
        else:
            image_urls.append(None)
    return image_urls


class SynVowGptImage2Alpha_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = CATEGORY
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (False, False)
    DESCRIPTION = "批量生成原始RGBA图片URL；单个任务失败时保留槽位并交由透明PNG保存节点生成黑图占位。"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": _DEFAULT_GPT_IMAGE_COMBO}),
                "gpt_style": (_STYLES, {"default": "sunburst"}),
                "quality": (_QUALITIES_EXT, {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (_ASPECTS, {"default": "1:1"}),
                "transparent": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "split_routing": (SPLIT_ROUTING_OPTIONS, {"default": "质量优先自动路由"}),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "image6": ("IMAGE",),
                "image7": ("IMAGE",),
                "image8": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("image_urls", "status")
    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(
        self,
        model_type=None,
        gpt_style=None,
        quality=None,
        resolution=None,
        aspect_ratio=None,
        transparent=True,
        seed=None,
        prompts_list=None,
        split_routing="质量优先自动路由",
        image1=None,
        image2=None,
        image3=None,
        image4=None,
        image5=None,
        image6=None,
        image7=None,
        image8=None,
    ):
        _ALPHA_CANCEL_EVENT.clear()
        transparent = _unpack(transparent)
        transparent = True if transparent is None else bool(transparent)
        seed = _unpack(seed)
        image1 = _unpack(image1)
        image2 = _unpack(image2)
        image3 = _unpack(image3)
        image4 = _unpack(image4)
        image5 = _unpack(image5)
        image6 = _unpack(image6)
        image7 = _unpack(image7)
        image8 = _unpack(image8)
        split_routing = _unpack(split_routing) or "质量优先自动路由"

        images = [item for item in [image1, image2, image3, image4, image5, image6, image7, image8] if item is not None]
        is_img2img = len(images) > 0
        requested_aspect = _unpack(aspect_ratio) or "auto"
        if requested_aspect == "auto" and images:
            requested_aspect = _nearest_reference_aspect(images[0])
        model, style, quality, eff_resolution, size = _prep_model(
            _unpack(model_type),
            _unpack(quality),
            _unpack(resolution) or "1K",
            requested_aspect,
            _unpack(gpt_style),
        )
        if images and str(model).startswith("gpt-image-2.5") and "-gf" not in str(model) and "-wd" not in str(model):
            size = _reference_custom_size(images[0], size)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [prompt for prompt in prompts if prompt is not None] or [""]
        background_layer_count = sum(_is_background_layer_prompt(prompt) for prompt in prompts)
        tasks = []
        routed_slots = []
        for prompt in prompts:
            task_transparent = False if transparent and _is_background_layer_prompt(prompt) else transparent
            options = {}
            slot_id = _layer_slot_id(prompt)
            if split_routing == "质量优先自动路由" and slot_id:
                if slot_id == "text_logo":
                    routed_model, routed_style, routed_quality, routed_resolution, routed_size = _prep_model(
                        "PT2.5-官方", "high", _unpack(resolution) or "1K", requested_aspect, "sunburst",
                    )
                    options = {
                        "model": routed_model,
                        "gpt_style": routed_style,
                        "quality": routed_quality,
                        "resolution": routed_resolution,
                        "size": routed_size,
                    }
                elif slot_id == "decorations":
                    routed_model, routed_style, routed_quality, routed_resolution, routed_size = _prep_model(
                        "PT2.5-2609", "medium", _unpack(resolution) or "1K", requested_aspect, "flare",
                    )
                    if images:
                        routed_size = _reference_custom_size(images[0], routed_size)
                    options = {
                        "model": routed_model,
                        "gpt_style": routed_style,
                        "quality": routed_quality,
                        "resolution": routed_resolution,
                        "size": routed_size,
                    }
                elif slot_id in ("background", "subject_product"):
                    routed_model, routed_style, routed_quality, routed_resolution, routed_size = _prep_model(
                        "PT2.5-2609", "medium", _unpack(resolution) or "1K", requested_aspect, "sunburst",
                    )
                    if images:
                        routed_size = _reference_custom_size(images[0], routed_size)
                    options = {
                        "model": routed_model,
                        "gpt_style": routed_style,
                        "quality": routed_quality,
                        "resolution": routed_resolution,
                        "size": routed_size,
                    }
                if options:
                    routed_slots.append(slot_id)
            tasks.append((prompt, images, task_transparent, options))

        background_mode = "transparent" if transparent else "opaque"
        print(f"[GPT-Image-2 Alpha TBatch] {len(tasks)} 条 prompt, model={model}, background={background_mode}")
        try:
            image_urls = _run_tasks_with_background(
                tasks,
                model,
                size,
                quality,
                eff_resolution,
                is_img2img,
                api_key,
                headers,
                seed=seed,
                gpt_style=style,
                transparent=transparent,
            )
        except AlphaPollingCancelled:
            raise
        except Exception as exc:
            print(f"[GPT-Image-2 Alpha TBatch] 批处理异常，全部槽位使用黑图占位: {exc}")
            image_urls = [None] * len(tasks)
        successful = sum(1 for url in image_urls if url)
        failed = max(0, len(tasks) - successful)

        status = (
            f"已完成 {successful}/{len(tasks)} model={model} size={size} quality={quality}；"
            f"输出URL {successful}/{len(image_urls)}；background={background_mode}；"
            f"分层背景自动不透明={background_layer_count}；"
            f"质量优先分槽路由={len(routed_slots)}/{len(tasks)}；"
            f"失败黑图占位={failed}/{len(tasks)}；"
            "透明模式可将 image_urls 连接到 SynVow 透明PNG保存预览。"
        )

        print(f"[GPT-Image-2 Alpha TBatch] 完成: {successful}/{len(tasks)} urls={successful}/{len(image_urls)}")
        synvow_auth.refresh_balance()
        output_slots = [
            url if url else f"{BLACK_PLACEHOLDER_TOKEN}:{index + 1}"
            for index, url in enumerate(image_urls)
        ]
        return ("\n".join(output_slots), status)


try:
    from aiohttp import web
    import server

    @server.PromptServer.instance.routes.post("/synvow/alpha/cancel")
    async def _synvow_alpha_cancel(request):
        request_alpha_cancel()
        return web.json_response({"ok": True, "message": "GPT-Image-2 Alpha polling cancel requested"})
except Exception as exc:
    print(f"[GPT-Image-2 Alpha] 取消轮询接口注册失败: {exc}")


NODE_CLASS_MAPPINGS = {
    "SynVowGptImage2Alpha_TBatch": SynVowGptImage2Alpha_TBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGptImage2Alpha_TBatch": "SynVow GPT-Image-2 Alpha (T_batch)",
}
