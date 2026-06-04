"""
SynVow GPT-Image-2 节点
"""

import concurrent.futures
import io
import random as _random
import time

import comfy.utils

import numpy as np
import requests
import torch
import urllib3
from PIL import Image

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


_RATIO_TO_SIZE_1K = {
    "auto":  "auto",
    "1:1":   "1024x1024",
    "16:9":  "1536x1024",
    "9:16":  "1024x1536",
    "4:3":   "1360x1024",
    "3:4":   "1024x1360",
    "5:4":   "1280x1024",
    "4:5":   "1024x1280",
    "3:2":   "1152x768",
    "2:3":   "768x1152",
    "3:1":   "1536x512",
    "1:3":   "512x1536",
    "2:1":   "1280x640",
    "1:2":   "640x1280",
    "21:9":  "1792x768",
    "9:21":  "768x1792",
}

_RATIO_TO_SIZE_2K = {
    "auto":  "auto",
    "1:1":   "2048x2048",
    "16:9":  "2048x1152",
    "9:16":  "1152x2048",
    "4:3":   "2048x1536",
    "3:4":   "1536x2048",
    "5:4":   "2048x1632",
    "4:5":   "1632x2048",
    "3:2":   "2048x1360",
    "2:3":   "1360x2048",
    "3:1":   "2048x688",
    "1:3":   "688x2048",
    "2:1":   "2048x1024",
    "1:2":   "1024x2048",
    "21:9":  "2560x1104",
    "9:21":  "1104x2560",
}

_RATIO_TO_SIZE_4K = {
    "auto":  "auto",
    "1:1":   "2880x2880",
    "16:9":  "3840x2160",
    "9:16":  "2160x3840",
    "4:3":   "3312x2480",
    "3:4":   "2480x3312",
    "5:4":   "3200x2560",
    "4:5":   "2560x3200",
    "3:2":   "3520x2352",
    "2:3":   "2352x3520",
    "3:1":   "3840x1280",
    "1:3":   "1280x3840",
    "2:1":   "3840x1920",
    "1:2":   "1920x3840",
    "21:9":  "3840x1648",
    "9:21":  "1648x3840",
}

_RATIO_MAPS = {"1K": _RATIO_TO_SIZE_1K, "2K": _RATIO_TO_SIZE_2K, "4K": _RATIO_TO_SIZE_4K}

_MODEL_TYPE_OPTIONS = [
    "gpt-image-2-1k-2605",
    "gpt-image-2-4k-2605",
    "gpt-image-2-稳定",
]

_NEW_MODELS = {"gpt-image-2-稳定"}


def _upload_image_for_backup(api_key, img_tensor):
    arr = (img_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).convert("RGB").save(buf, format="JPEG", quality=90)
    buf.seek(0)
    upload_url = f"{synvow_auth.DIRECT_API_BASE}/api/upload/images"
    res = requests.post(
        upload_url,
        headers={"X-API-Key": api_key},
        files=[("files", ("image.jpg", buf, "image/jpeg"))],
        verify=False, timeout=60,
    )
    data = res.json()
    if res.status_code != 200 or data.get("code") != 200:
        raise RuntimeError(f"Image upload failed: {data}")
    urls = data.get("data", {}).get("urls", [])
    if not urls:
        raise RuntimeError(f"Image upload returned no URL: {data}")
    return urls[0]


def _blank_image(h=1024, w=1024):
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


def _append_url(urls, value):
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        if value not in urls:
            urls.append(value)
    elif isinstance(value, list):
        for item in value:
            _append_url(urls, item)


def _collect_urls_recursive(value, urls):
    if isinstance(value, dict):
        for key in ("url", "image_url", "imageUrl", "output_url", "outputUrl"):
            _append_url(urls, value.get(key))
        for key in ("images", "results", "result", "output", "outputs", "data", "sourceData"):
            if key in value:
                _collect_urls_recursive(value.get(key), urls)
    elif isinstance(value, list):
        for item in value:
            _collect_urls_recursive(item, urls)


def _extract_urls(r):
    urls = []
    if not isinstance(r, dict):
        return urls
    # 路径1: 旧模型(2605) r["results"][{"url": str}]
    for item in r.get("results", []):
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    if urls:
        return urls
    # 路径2: 新模型(稳定) r["data"]["result"]["images"][{"url": str|list}]
    try:
        images = r["data"]["result"]["images"]
        for item in images:
            url = item.get("url")
            if isinstance(url, list):
                urls.extend(u for u in url if u)
            elif url:
                urls.append(url)
    except (KeyError, TypeError):
        pass
    if urls:
        return urls
    _collect_urls_recursive(r, urls)
    return urls


def _build_payload(model, prompt, size, quality, resolution, is_img2img, img_tensors, api_key=None):
    payload = {"model": model, "prompt": prompt}
    if model in _NEW_MODELS:
        if size and size != "auto":
            payload["size"] = size
        if resolution:
            payload["resolution"] = resolution
        if is_img2img and img_tensors and api_key:
            payload["image_urls"] = [_upload_image_for_backup(api_key, t) for t in img_tensors]
    else:
        payload["replyType"] = "async"
        if size and size != "auto":
            payload["aspectRatio"] = size
        if quality and quality != "auto":
            payload["quality"] = quality
        if is_img2img and img_tensors and api_key:
            payload["images"] = [_upload_image_for_backup(api_key, t) for t in img_tensors]
    return payload


def _submit_task(payload, headers, api_url):
    model = payload.get('model')
    img_key = "image_urls" if "image_urls" in payload else "images"
    img_count = len(payload.get(img_key, []))
    print(f"[GPT-Image-2] 提交: model={model} images={img_count}")
    res = requests.post(api_url, headers=headers, json=payload,
                        params={"async": "true"}, timeout=120, verify=False)
    res.raise_for_status()
    _d = res.json() if isinstance(res.json(), dict) else {}
    _data = _d.get("data")
    _data_item = (_data[0] if isinstance(_data, list) and _data else None) or (_data if isinstance(_data, dict) else {})
    _source_data = _data_item.get("sourceData") or {}
    _source_inner = _source_data.get("data")
    _source_item = (_source_inner[0] if isinstance(_source_inner, list) and _source_inner else {})
    task_id = (
        _d.get("task_id")
        or _data_item.get("task_id")
        or _source_item.get("task_id")
        or _source_data.get("task_id")
    )
    consumption_id = _d.get("consumption_id") or _data_item.get("consumption_id")
    if not task_id:
        raise RuntimeError(f"提交失败，无 task_id: {str(_d)[:200]}")
    print(f"[GPT-Image-2] task_id=...{task_id[-8:]}")
    return task_id, consumption_id


def _poll_task(task_id, consumption_id, headers, poll_url, model):
    import comfy.model_management as mm
    poll_body = {"task_id": task_id, "model": model}
    if consumption_id is not None:
        poll_body["consumption_id"] = consumption_id
    timeout_total = 1800
    interval = 5
    start_time = time.time()
    while True:
        mm.throw_exception_if_processing_interrupted()
        time.sleep(interval)
        mm.throw_exception_if_processing_interrupted()
        elapsed = int(time.time() - start_time)
        if elapsed >= timeout_total:
            print(f"[GPT-Image-2] 超时: ...{task_id[-8:]} ({elapsed}s)")
            return None
        try:
            poll_res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30, verify=False)
            poll_res.raise_for_status()
            poll_json = poll_res.json()
            data_field = poll_json.get("data", poll_json) if isinstance(poll_json, dict) else poll_json
            status = data_field.get("status", "") if isinstance(data_field, dict) else ""
            print(f"[GPT-Image-2] ...{task_id[-8:]} status={status} ({elapsed}s)")
            if status in ("SUCCESS", "success", "succeeded", "completed", "done", "finished"):
                return poll_json
            elif status in ("FAILURE", "failed", "error", "EXCEPTION"):
                msg = data_field.get("fail_reason", "任务失败")
                print(f"[GPT-Image-2] 失败: ...{task_id[-8:]} {msg}")
                return None
        except Exception as e:
            print(f"[GPT-Image-2] 轮询异常: ...{task_id[-8:]} {e}，跳过")
            return None


def _download_image(img_url):
    short = f"...{img_url[-24:]}" if len(img_url) > 24 else img_url
    print(f"[GPT-Image-2] 开始下载: {short}")
    for attempt in range(3):
        try:
            with requests.Session() as _s:
                r = _s.get(img_url, timeout=120, verify=False)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            print(f"[GPT-Image-2] 下载成功 ({attempt+1}/3): {short} 尺寸={img.width}x{img.height}")
            return torch.from_numpy(arr).unsqueeze(0)
        except Exception as e:
            print(f"[GPT-Image-2] 下载失败 ({attempt+1}/3): {short} 错误={e}")
            if attempt < 2:
                wait = 3 * (attempt + 1)
                print(f"[GPT-Image-2] {wait}s 后重试...")
                time.sleep(wait)
    print(f"[GPT-Image-2] 3次重试均失败，使用黑图占位: {short}")
    return _blank_image()


def _download_with_placeholder(image_urls):
    """并发下载所有 URL，失败/缺失位置用黑图占位，返回 tensor 列表（顺序对齐）。"""
    valid = [(i, u) for i, u in enumerate(image_urls) if u]
    print(f"[GPT-Image-2] 并发下载 {len(valid)}/{len(image_urls)} 张图片...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(image_urls), 1)) as ex:
        futures = {i: ex.submit(_download_image, u) for i, u in valid}
    downloaded = {i: f.result() for i, f in futures.items()}
    print(f"[GPT-Image-2] 下载完成 {len(downloaded)}/{len(image_urls)} 张")
    ref_h, ref_w = next(((t.shape[1], t.shape[2]) for t in downloaded.values()), (1024, 1024))
    return [downloaded.get(i, _blank_image(ref_h, ref_w)) for i in range(len(image_urls))]


def _download_urls_with_placeholder(image_urls):
    return _download_with_placeholder(image_urls)


def _collect_image_tensors(image_urls):
    tensors = _download_with_placeholder(image_urls)
    if not tensors:
        return _blank_image()
    h, w = tensors[0].shape[1], tensors[0].shape[2]
    resized = []
    for t in tensors:
        if t.shape[1] != h or t.shape[2] != w:
            pil = Image.fromarray((t[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8))
            pil = pil.resize((w, h), Image.LANCZOS)
            t = torch.from_numpy(np.array(pil).astype(np.float32) / 255.0).unsqueeze(0)
        resized.append(t)
    return torch.cat(resized, dim=0)


_API_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/image/edit"
_POLL_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/tasks"


def _is_changed(**kwargs):
    import hashlib, json
    key = json.dumps({k: str(v) for k, v in kwargs.items()}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key.encode()).hexdigest()


def _send_refresh():
    try:
        import server
        server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
    except Exception:
        pass


def _unpack(v):
    return v[0] if isinstance(v, list) else v


def _run_tasks(tasks, model, size, quality, resolution, is_img2img, api_key, headers, api_url, poll_url):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)

    submitted = []
    for i, (p, imgs) in enumerate(tasks):
        payload = _build_payload(model, p, size, quality, resolution, is_img2img, imgs, api_key=api_key)
        try:
            task_id, consumption_id = _submit_task(payload, headers, api_url)
            submitted.append((task_id, consumption_id))
            print(f"[GPT-Image-2] [{i+1}/{total}] 提交成功 task_id=...{task_id[-8:]}")
        except Exception as e:
            print(f"[GPT-Image-2] [{i+1}/{total}] 提交失败: {e}")
            submitted.append(None)
        if i < total - 1:
            time.sleep(1)

    def _poll_one(item):
        if item is None:
            pbar.update(1)
            return None
        task_id, consumption_id = item
        result = _poll_task(task_id, consumption_id, headers, poll_url, model)
        pbar.update(1)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=total) as executor:
        poll_results = list(executor.map(_poll_one, submitted))

    image_urls = []
    for i, r in enumerate(poll_results):
        if r is not None:
            urls = _extract_urls(r)
            if urls:
                image_urls.extend(urls)
            else:
                print(f"[GPT-Image-2] [{i+1}/{total}] 任务完成但未解析到图片URL: {str(r)[:500]}")
                image_urls.append(None)
        else:
            image_urls.append(None)
    return image_urls


class SynVowGptImage2:

    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True

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
                "prompt": ("STRING", {"multiline": True, "default": ""}),
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

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, model_type=None, quality=None, resolution=None,
                 aspect_ratio=None, seed=None, prompt=None,
                 image1=None, image2=None, image3=None, image4=None,
                 image5=None, image6=None, image7=None, image8=None):
        model_type   = _unpack(model_type) or "gpt-image-2-1k-2605"
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        seed         = _unpack(seed)
        prompt       = _unpack(prompt)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)

        api_key = synvow_auth.read_api_key()

        headers = synvow_auth.make_api_headers(api_key)
        model = model_type or "gpt-image-2-1k-2605"
        eff_resolution = "1K" if model_type == "gpt-image-2-1k-2605" else resolution
        ratio_map = _RATIO_MAPS.get(eff_resolution, _RATIO_TO_SIZE_1K)
        size = ratio_map.get(aspect_ratio, "auto")

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None]
        is_img2img = len(imgs) > 0

        p = str(prompt).strip() if prompt else ""
        tasks = [(p, imgs)]

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, is_img2img, api_key, headers, _API_URL, _POLL_URL)
        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 model={model} size={size} quality={quality}" if successful else f"[ERROR] 生成失败 model={model} size={size}"

        out_tensor = _collect_image_tensors(image_urls)
        _send_refresh()
        return (out_tensor, status_str)


class SynVowGptImage2_TBatch:

    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

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

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, model_type=None, quality=None,
                      resolution=None, aspect_ratio=None, seed=None, prompts_list=None,
                      image1=None, image2=None, image3=None, image4=None,
                      image5=None, image6=None, image7=None, image8=None):
        model_type   = _unpack(model_type) or "gpt-image-2-1k-2605"
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        seed         = _unpack(seed)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)

        api_key = synvow_auth.read_api_key()

        headers = synvow_auth.make_api_headers(api_key)
        model = model_type or "gpt-image-2-1k-2605"
        eff_resolution = "1K" if model_type == "gpt-image-2-1k-2605" else resolution
        ratio_map = _RATIO_MAPS.get(eff_resolution, _RATIO_TO_SIZE_1K)
        size = ratio_map.get(aspect_ratio, "auto")

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None]
        is_img2img = len(imgs) > 0
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [p for p in prompts if p is not None]

        tasks = [(p, imgs) for p in prompts]
        total = len(tasks)
        print(f"[GPT-Image-2 TBatch] {total} 条 prompt, model={model}")

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, is_img2img, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_urls_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{total} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={total}"
        print(f"[GPT-Image-2 TBatch] 完成: {successful}/{total}")
        _send_refresh()
        return (image_list, status_str)


class SynVowGptImage2_IBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": "gpt-image-2-1k-2605"}),
                "quality": (["auto", "low", "medium", "high"], {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (list(_RATIO_TO_SIZE_1K.keys()), {"default": "1:1"}),
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",),
                "images_list5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None,
                      quality=None, resolution=None, aspect_ratio=None, prompt=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None):
        model_type   = _unpack(model_type) or "gpt-image-2-1k-2605"
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        prompt       = _unpack(prompt)
        seed         = _unpack(seed)

        api_key = synvow_auth.read_api_key()

        headers = synvow_auth.make_api_headers(api_key)
        model = model_type or "gpt-image-2-1k-2605"
        eff_resolution = "1K" if model_type == "gpt-image-2-1k-2605" else resolution
        ratio_map = _RATIO_MAPS.get(eff_resolution, _RATIO_TO_SIZE_1K)
        size = ratio_map.get(aspect_ratio, "auto")

        p = str(prompt).strip() if prompt else ""
        all_lists = [images_list1,
                     images_list2 if images_list2 is not None else [],
                     images_list3 if images_list3 is not None else [],
                     images_list4 if images_list4 is not None else [],
                     images_list5 if images_list5 is not None else []]
        batch_size = max(len(lst) for lst in all_lists)
        print(f"[GPT-Image-2 IBatch] {batch_size} 组图, model={model}")

        tasks = []
        for i in range(batch_size):
            imgs = []
            for lst in all_lists:
                if not lst:
                    continue
                if len(lst) == 1:
                    imgs.append(lst[0])
                elif i < len(lst):
                    imgs.append(lst[i])
            tasks.append((p, imgs))

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, True, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_urls_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
        print(f"[GPT-Image-2 IBatch] 完成: {successful}/{batch_size}")
        _send_refresh()
        return (image_list, status_str)


class SynVowGptImage2_TIBatch:

    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": "gpt-image-2-1k-2605"}),
                "quality": (["auto", "low", "medium", "high"], {"default": "auto"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (list(_RATIO_TO_SIZE_1K.keys()), {"default": "1:1"}),
                "prompt_order": (["sequential", "reverse", "random"], {"default": "sequential"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list2": ("IMAGE",),
                "images_list3": ("IMAGE",),
                "images_list4": ("IMAGE",),
                "images_list5": ("IMAGE",),
                "prompts_list": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, quality=None,
                      resolution=None, aspect_ratio=None, prompt_order=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None,
                      prompts_list=None):
        model_type   = _unpack(model_type) or "gpt-image-2-1k-2605"
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        prompt_order = _unpack(prompt_order) or "sequential"
        seed         = _unpack(seed)

        api_key = synvow_auth.read_api_key()

        headers = synvow_auth.make_api_headers(api_key)
        model = model_type or "gpt-image-2-1k-2605"
        eff_resolution = "1K" if model_type == "gpt-image-2-1k-2605" else resolution
        ratio_map = _RATIO_MAPS.get(eff_resolution, _RATIO_TO_SIZE_1K)
        size = ratio_map.get(aspect_ratio, "auto")

        all_lists = [images_list1,
                     images_list2 if images_list2 is not None else [],
                     images_list3 if images_list3 is not None else [],
                     images_list4 if images_list4 is not None else [],
                     images_list5 if images_list5 is not None else []]
        batch_size = max(len(lst) for lst in all_lists)

        prompts = [p for p in (prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [])) if p is not None]
        if not prompts:
            prompts = [""]
        prompts_count = len(prompts)
        if prompt_order == "reverse":
            prompts = prompts[::-1]
        assigned_prompts = [
            _random.choice(prompts) if prompt_order == "random" else prompts[i % prompts_count]
            for i in range(batch_size)
        ]

        print(f"[GPT-Image-2 TIBatch] {batch_size} 组图, {prompts_count} 条 prompt, order={prompt_order}, model={model}")

        tasks = []
        for i in range(batch_size):
            imgs = []
            for lst in all_lists:
                if not lst:
                    continue
                if len(lst) == 1:
                    imgs.append(lst[0])
                elif i < len(lst):
                    imgs.append(lst[i])
            tasks.append((assigned_prompts[i], imgs))

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, True, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_urls_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
        print(f"[GPT-Image-2 TIBatch] 完成: {successful}/{batch_size}")
        _send_refresh()
        return (image_list, status_str)


NODE_CLASS_MAPPINGS = {
    "SynVowGptImage2": SynVowGptImage2,
    "SynVowGptImage2_TBatch": SynVowGptImage2_TBatch,
    "SynVowGptImage2_IBatch": SynVowGptImage2_IBatch,
    "SynVowGptImage2_TIBatch": SynVowGptImage2_TIBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGptImage2": "SynVow GPT-Image-2",
    "SynVowGptImage2_TBatch": "SynVow GPT-Image-2 (T_batch)",
    "SynVowGptImage2_IBatch": "SynVow GPT-Image-2 (I_batch)",
    "SynVowGptImage2_TIBatch": "SynVow GPT-Image-2 (T_I_batch)",
}
