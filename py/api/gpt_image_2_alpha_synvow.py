# -*- coding: utf-8 -*-
"""
Alpha-aware SynVow GPT-Image-2 batch node.

This file only adds new nodes. It reuses the existing GPT-Image-2 request,
auth, submit, poll, and URL parsing helpers, and returns original image URLs
so transparent PNGs can be saved directly with their alpha channel.
"""

import concurrent.futures
import threading
import time

import comfy.utils
import requests

from . import synvow_auth
from .gpt_image_2_synvow import (
    _API_URL,
    _MODEL_TYPE_OPTIONS,
    _NEW_MODELS,
    _POLL_URL,
    _RATIO_TO_SIZE_1K,
    _build_payload,
    _extract_urls,
    _is_changed,
    _resolve_size_params,
    _unpack,
)


CATEGORY = "💫SynVow_api/api/图像"
TRANSPARENT_BACKGROUND_MODE = "固定透明(background=transparent)"
SUBMIT_RETRY_ATTEMPTS = 3
POLL_WORKER_LIMIT = 4
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
            status = data_field.get("status", "") if isinstance(data_field, dict) else ""
            print(f"[GPT-Image-2 Alpha] ...{task_id[-8:]} status={status} ({elapsed}s)")
            if status in ("SUCCESS", "success", "succeeded", "completed", "done", "finished"):
                return poll_json
            if status in ("FAILURE", "failed", "error", "EXCEPTION"):
                msg = data_field.get("fail_reason", "任务失败") if isinstance(data_field, dict) else "任务失败"
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


def _is_balance_or_auth_error(value):
    text = str(value or "").lower()
    markers = (
        "账户余额不足",
        "余额最少",
        "insufficient balance",
        "insufficient funds",
        "quota",
        "unauthorized",
        "forbidden",
        "invalid api key",
        "api key",
    )
    return any(marker in text for marker in markers)


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


def _official_image_payload_fallbacks(payload):
    image_urls = payload.get("image_urls")
    if payload.get("model") != "gpt-image-2-官方" or not image_urls:
        return []

    base = {key: value for key, value in payload.items() if key != "image_urls"}
    return [
        ("images", {**base, "images": image_urls}),
        ("files", {**base, "files": [{"url": url, "type": "image"} for url in image_urls]}),
    ]


def _submit_alpha_task(payload, headers, api_url):
    model = payload.get("model")
    img_key = "image_urls" if "image_urls" in payload else "images"
    img_count = len(payload.get(img_key, []))
    print(f"[GPT-Image-2 Alpha] 提交: model={model} images={img_count}")
    response = _post_generation_payload(api_url, headers, payload)
    if response.status_code >= 400:
        first_error = _response_error_text(response)
        fallback_success = False
        if not _is_balance_or_auth_error(first_error):
            for field_name, fallback_payload in _official_image_payload_fallbacks(payload):
                print(
                    f"[GPT-Image-2 Alpha] 官方模型参考图提交失败，尝试兼容字段 {field_name}: "
                    f"HTTP {response.status_code} {first_error}"
                )
                response = _post_generation_payload(api_url, headers, fallback_payload)
                if response.status_code < 400:
                    fallback_success = True
                    print(f"[GPT-Image-2 Alpha] 官方模型参考图兼容字段 {field_name} 提交成功")
                    break
                print(
                    f"[GPT-Image-2 Alpha] 官方模型参考图兼容字段 {field_name} 仍失败: "
                    f"HTTP {response.status_code} {_response_error_text(response)}"
                )
        if not fallback_success:
            raise RuntimeError(f"提交失败 HTTP {response.status_code}: {_response_error_text(response) or first_error}")

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


def _normalize_model_type(model_type):
    aliases = {"gpt-image-2-official": "gpt-image-2-官方"}
    return aliases.get(str(model_type), model_type)


def _send_alpha_refresh():
    try:
        synvow_auth.refresh_balance()
    except Exception:
        pass


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
):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    background = "transparent"
    _raise_if_alpha_cancelled()

    submitted = []
    for index, (prompt, images) in enumerate(tasks):
        _raise_if_alpha_cancelled()
        payload = _build_payload(model, prompt, size, quality, resolution, is_img2img, images, api_key=api_key)
        try:
            seed_value = int(seed) if seed is not None else 0
        except Exception:
            seed_value = 0
        if seed_value > 0:
            payload["seed"] = seed_value
        if background:
            payload["background"] = background
            if model not in _NEW_MODELS:
                payload["transparentBackground"] = background == "transparent"
        try:
            task_id, consumption_id = _submit_alpha_task_with_retry(payload, headers, _API_URL)
            submitted.append((task_id, consumption_id))
            print(f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 提交成功 task_id=...{task_id[-8:]}")
        except Exception as exc:
            print(f"[GPT-Image-2 Alpha] [{index + 1}/{total}] 提交失败: {exc}")
            if _is_balance_or_auth_error(exc):
                raise RuntimeError(
                    f"GPT-Image-2 Alpha 提交失败：model={model}，mode={'参考图/拆图' if is_img2img else '文生图'}，"
                    f"服务端返回：{exc}"
                )
            submitted.append(None)
        if index < total - 1:
            _sleep_interruptible(1)

    def _poll_one(item):
        _raise_if_alpha_cancelled()
        if item is None:
            pbar.update(1)
            return None
        task_id, consumption_id = item
        result = _poll_alpha_task(task_id, consumption_id, headers, _POLL_URL, model)
        pbar.update(1)
        return result

    worker_count = min(max(total, 1), POLL_WORKER_LIMIT)
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        poll_results = list(executor.map(_poll_one, submitted))

    image_urls = []
    for index, result in enumerate(poll_results):
        if result is not None:
            urls = _extract_urls(result)
            if urls:
                image_urls.extend(urls)
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

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": "gpt-image-2-1k-2605"}),
                "quality": (["auto", "low", "medium", "high"], {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (list(_RATIO_TO_SIZE_1K.keys()), {"default": "1:1"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
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
        quality=None,
        resolution=None,
        aspect_ratio=None,
        seed=None,
        prompts_list=None,
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
        model_type = _normalize_model_type(_unpack(model_type) or "gpt-image-2-1k-2605")
        quality = _unpack(quality)
        resolution = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        seed = _unpack(seed)
        image1 = _unpack(image1)
        image2 = _unpack(image2)
        image3 = _unpack(image3)
        image4 = _unpack(image4)
        image5 = _unpack(image5)
        image6 = _unpack(image6)
        image7 = _unpack(image7)
        image8 = _unpack(image8)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)
        model = model_type or "gpt-image-2-1k-2605"
        eff_resolution, size = _resolve_size_params(model, aspect_ratio, resolution)

        images = [item for item in [image1, image2, image3, image4, image5, image6, image7, image8] if item is not None]
        is_img2img = len(images) > 0
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [prompt for prompt in prompts if prompt is not None] or [""]
        tasks = [(prompt, images) for prompt in prompts]

        print(f"[GPT-Image-2 Alpha TBatch] {len(tasks)} 条 prompt, model={model}, background=transparent")
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
        )
        successful = sum(1 for url in image_urls if url)
        if successful == 0:
            raise RuntimeError(
                f"GPT-Image-2 Alpha 生成失败：model={model}，mode={'参考图/拆图' if is_img2img else '文生图'}，"
                f"total={len(tasks)}。请查看上方提交失败日志中的 HTTP 状态和服务端返回内容。"
            )

        status = (
            f"已完成 {successful}/{len(tasks)} model={model} size={size} quality={quality}；"
            f"输出URL {successful}/{len(image_urls)}；background={TRANSPARENT_BACKGROUND_MODE}；"
            "请连接 image_urls 到 SynVow 透明PNG保存预览。"
        )

        print(f"[GPT-Image-2 Alpha TBatch] 完成: {successful}/{len(tasks)} urls={successful}/{len(image_urls)}")
        _send_alpha_refresh()
        return ("\n".join([url for url in image_urls if url]), status)


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
