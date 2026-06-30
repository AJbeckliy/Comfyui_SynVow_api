"""
NanoBanana SynVow API nodes - 图像生成 / 批量生成
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
from .media_common import upload_image as _upload_image

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_MODEL_OPTIONS = [
    "nano-banana-2-低价",
    "nano-banana-2-2605",
    "nano-banana-2-稳定",
    "nano-banana-2-官方",
    "nano-banana-pro-低价",
    "nano-banana-pro-2605",
    "nano-banana-pro-稳定",
    "nano-banana-pro-官方",
]


def _tensor_to_pil(image_tensor):
    if len(image_tensor.shape) > 3:
        image_tensor = image_tensor[0]
    i = 255. * image_tensor.cpu().numpy()
    return Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))


_ASPECT_RATIOS = [
    "auto", "1:1", "16:9", "9:16", "4:3", "3:4", "4:5", "5:4",
    "2:3", "3:2", "21:9", "1:4", "4:1", "1:8", "8:1",
]


def _find_closest_aspect_ratio(width, height):
    _ratios = {
        "1:1": (1,1), "16:9": (16,9), "9:16": (9,16), "4:3": (4,3), "3:4": (3,4),
        "4:5": (4,5), "5:4": (5,4), "2:3": (2,3), "3:2": (3,2), "21:9": (21,9),
        "1:4": (1,4), "4:1": (4,1), "1:8": (1,8), "8:1": (8,1),
    }
    input_ratio = width / height
    best_match = "1:1"
    min_diff = float("inf")
    for name, (w, h) in _ratios.items():
        diff = abs(input_ratio - w / h)
        if diff < min_diff:
            min_diff = diff
            best_match = name
    return best_match


def _blank_image(h=1024, w=1024):
    return torch.zeros((1, h, w, 3), dtype=torch.float32)


def _extract_urls(r):
    urls = []
    if not isinstance(r, dict):
        return urls
    # 路径1: 旧模型 r["results"][{"url": str}]
    for item in r.get("results", []):
        if isinstance(item, dict) and item.get("url"):
            urls.append(item["url"])
    if urls:
        return urls
    # 路径2: 新模型 r["data"]["result"]["images"][{"url": str|list}]
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
    # 路径3: 低价模型 r["result"]["url"] (单个字符串)
    result = r.get("result")
    if isinstance(result, dict):
        url = result.get("url")
        if isinstance(url, str) and url:
            urls.append(url)
        elif isinstance(url, list):
            urls.extend(u for u in url if u)
    return urls


_NEW_MODELS = {
    "nano-banana-2-稳定", "nano-banana-2-官方",
    "nano-banana-pro-稳定", "nano-banana-pro-官方",
}

_LOWPRICE_MODELS = {
    "nano-banana-2-低价", "nano-banana-pro-低价",
}


_API_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/image/edit"
_POLL_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/tasks"


def _build_payload(model, prompt, aspect_ratio, image_size, is_img2img, img_tensors, api_key=None):
    payload = {"model": model, "prompt": prompt}
    if model in _LOWPRICE_MODELS:
        if aspect_ratio and aspect_ratio != "auto":
            payload["ratio"] = aspect_ratio
        if image_size:
            payload["resolution"] = image_size
        if is_img2img and img_tensors and api_key:
            payload["files"] = [{"url": _upload_image(api_key, t), "type": "image"} for t in img_tensors]
    elif model in _NEW_MODELS:
        if aspect_ratio and aspect_ratio != "auto":
            payload["size"] = aspect_ratio
        if image_size:
            payload["resolution"] = image_size
        if is_img2img and img_tensors and api_key:
            payload["image_urls"] = [_upload_image(api_key, t) for t in img_tensors]
    else:
        payload["replyType"] = "async"
        if aspect_ratio and aspect_ratio != "auto":
            payload["aspectRatio"] = aspect_ratio
        if image_size:
            payload["imageSize"] = image_size
        if is_img2img and img_tensors and api_key:
            payload["images"] = [_upload_image(api_key, t) for t in img_tensors]
    return payload


def _submit_task(payload, headers, api_url):
    model = payload.get('model')
    img_count = len(payload.get("image_urls") or payload.get("files") or payload.get("images") or [])
    print(f"[NanoBanana] 提交: model={model} images={img_count}")
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
    print(f"[NanoBanana] task_id=...{task_id[-8:]}")
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
            print(f"[NanoBanana] 超时: ...{task_id[-8:]} ({elapsed}s)")
            return None
        try:
            poll_res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30, verify=False)
            poll_res.raise_for_status()
            poll_json = poll_res.json()
            data_field = poll_json.get("data", poll_json) if isinstance(poll_json, dict) else poll_json
            status = data_field.get("status", "") if isinstance(data_field, dict) else ""
            print(f"[NanoBanana] ...{task_id[-8:]} status={status} ({elapsed}s)")
            if status in ("SUCCESS", "success", "succeeded", "completed", "done", "finished"):
                return poll_json
            elif status in ("FAILURE", "failed", "error", "EXCEPTION"):
                msg = data_field.get("fail_reason", "任务失败")
                print(f"[NanoBanana] 失败: ...{task_id[-8:]} {msg}")
                return None
        except Exception as e:
            print(f"[NanoBanana] 轮询异常: ...{task_id[-8:]} {e}，跳过")
            return None


def _download_image(img_url):
    short = f"...{img_url[-24:]}" if len(img_url) > 24 else img_url
    print(f"[NanoBanana] 开始下载: {short}")
    for attempt in range(3):
        try:
            r = requests.get(img_url, timeout=120, verify=False)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0
            print(f"[NanoBanana] 下载成功 ({attempt+1}/3): {short} 尺寸={img.width}x{img.height}")
            return torch.from_numpy(arr).unsqueeze(0)
        except Exception as e:
            print(f"[NanoBanana] 下载失败 ({attempt+1}/3): {short} 错误={e}")
            if attempt < 2:
                wait = 3 * (attempt + 1)
                print(f"[NanoBanana] {wait}s 后重试...")
                time.sleep(wait)
    print(f"[NanoBanana] 3次重试均失败，使用黑图占位: {short}")
    return _blank_image()


def _download_with_placeholder(image_urls):
    """并发下载所有 URL，失败/缺失位置用黑图占位，返回 tensor 列表（顺序对齐）。"""
    valid = [(i, u) for i, u in enumerate(image_urls) if u]
    print(f"[NanoBanana] 并发下载 {len(valid)}/{len(image_urls)} 张图片...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(image_urls), 1)) as ex:
        futures = {i: ex.submit(_download_image, u) for i, u in valid}
    downloaded = {i: f.result() for i, f in futures.items()}
    print(f"[NanoBanana] 下载完成 {len(downloaded)}/{len(image_urls)} 张")
    ref_h, ref_w = next(((t.shape[1], t.shape[2]) for t in downloaded.values()), (1024, 1024))
    return [downloaded.get(i, _blank_image(ref_h, ref_w)) for i in range(len(image_urls))]



def _collect_tensors(image_urls):
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


def _unpack(v):
    return v[0] if isinstance(v, list) else v


def _run_tasks(tasks, model, aspect_ratio, image_size, is_img2img, api_key, headers, api_url, poll_url):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)

    submitted = []
    for i, (p, imgs) in enumerate(tasks):
        payload = _build_payload(model, p, aspect_ratio, image_size, is_img2img, imgs, api_key=api_key)
        try:
            task_id, consumption_id = _submit_task(payload, headers, api_url)
            submitted.append((task_id, consumption_id))
            print(f"[NanoBanana] [{i+1}/{total}] 提交成功 task_id=...{task_id[-8:]}")
        except Exception as e:
            print(f"[NanoBanana] [{i+1}/{total}] 提交失败: {e}")
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
            image_urls.extend(urls)
        else:
            print(f"[NanoBanana] task[{i}] 失败，黑图占位")
            image_urls.append(None)
    return image_urls


def _is_changed(**kwargs):
    import hashlib, json
    key = json.dumps({k: str(v) for k, v in kwargs.items()}, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(key.encode()).hexdigest()


class SynVowNanoBanana:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_OPTIONS, {"default": "nano-banana-2-2605"}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",), "image6": ("IMAGE",),
                "image7": ("IMAGE",), "image8": ("IMAGE",), "image9": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def generate(self, model_type=None, aspect_ratio=None, image_size=None, seed=None,
                 prompt=None, image1=None, image2=None, image3=None, image4=None,
                 image5=None, image6=None, image7=None, image8=None, image9=None):
        model_type   = _unpack(model_type) or "nano-banana-2-2605"
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        seed         = _unpack(seed)
        prompt       = _unpack(prompt)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)
        image9 = _unpack(image9)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8, image9] if t is not None]
        if aspect_ratio == "auto" and imgs:
            pil0 = _tensor_to_pil(imgs[0])
            aspect_ratio = _find_closest_aspect_ratio(pil0.width, pil0.height)
        elif aspect_ratio == "auto":
            aspect_ratio = "1:1"
        is_img2img = len(imgs) > 0

        p = str(prompt).strip() if prompt else ""
        tasks = [(p, imgs)]

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, is_img2img, api_key, headers, _API_URL, _POLL_URL)
        successful = sum(1 for u in image_urls if u)
        if successful:
            status_str = f"已完成 model={model_type} aspectRatio={aspect_ratio} size={image_size}"
        else:
            status_str = f"[ERROR] 生成失败 model={model_type} aspectRatio={aspect_ratio}"

        out_tensor = _collect_tensors(image_urls)
        synvow_auth.refresh_balance()
        return (out_tensor, status_str)



class SynVowNanoBanana_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_OPTIONS, {"default": "nano-banana-2-2605"}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image1": ("IMAGE",), "image2": ("IMAGE",), "image3": ("IMAGE",),
                "image4": ("IMAGE",), "image5": ("IMAGE",), "image6": ("IMAGE",),
                "image7": ("IMAGE",), "image8": ("IMAGE",), "image9": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "status")

    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, model_type=None, aspect_ratio=None, image_size=None, seed=None,
                      prompts_list=None, image1=None, image2=None, image3=None, image4=None,
                      image5=None, image6=None, image7=None, image8=None, image9=None):
        model_type   = _unpack(model_type) or "nano-banana-2-2605"
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        seed         = _unpack(seed)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)
        image9 = _unpack(image9)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8, image9] if t is not None]
        if aspect_ratio == "auto" and imgs:
            pil0 = _tensor_to_pil(imgs[0])
            aspect_ratio = _find_closest_aspect_ratio(pil0.width, pil0.height)
        elif aspect_ratio == "auto":
            aspect_ratio = "1:1"
        is_img2img = len(imgs) > 0

        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [p for p in prompts if p is not None]
        tasks = [(p, imgs) for p in prompts]
        total = len(tasks)
        print(f"[NanoBanana TBatch] {total} 条 prompt, model={model_type}")

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, is_img2img, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{total} model={model_type} aspectRatio={aspect_ratio} size={image_size}" if successful else f"[ERROR] 所有任务失败 model={model_type} total={total}"
        print(f"[NanoBanana TBatch] 完成: {successful}/{total}")
        synvow_auth.refresh_balance()
        return (image_list, status_str)



class SynVowNanoBanana_IBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_OPTIONS, {"default": "nano-banana-2-2605"}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
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

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, image_size=None,
                      prompt=None, seed=None,
                      images_list2=None, images_list3=None, images_list4=None, images_list5=None):
        model_type   = _unpack(model_type) or "nano-banana-2-2605"
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        prompt       = _unpack(prompt)
        seed         = _unpack(seed)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        p = str(prompt).strip() if prompt else ""
        all_lists = [images_list1,
                     images_list2 if images_list2 is not None else [],
                     images_list3 if images_list3 is not None else [],
                     images_list4 if images_list4 is not None else [],
                     images_list5 if images_list5 is not None else []]
        batch_size = max(len(lst) for lst in all_lists)

        if aspect_ratio == "auto":
            first_nonempty = next((lst for lst in all_lists if lst), None)
            if first_nonempty:
                pil0 = _tensor_to_pil(first_nonempty[0])
                aspect_ratio = _find_closest_aspect_ratio(pil0.width, pil0.height)
            else:
                aspect_ratio = "1:1"

        print(f"[NanoBanana IBatch] {batch_size} 组图, model={model_type}")

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

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, True, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model_type} aspectRatio={aspect_ratio} size={image_size}" if successful else f"[ERROR] 所有任务失败 model={model_type} total={batch_size}"
        print(f"[NanoBanana IBatch] 完成: {successful}/{batch_size}")
        synvow_auth.refresh_balance()
        return (image_list, status_str)



class SynVowNanoBanana_TIBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True, False)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images_list1": ("IMAGE",),
                "model_type": (_MODEL_OPTIONS, {"default": "nano-banana-2-2605"}),
                "aspect_ratio": (_ASPECT_RATIOS, {"default": "1:1"}),
                "image_size": (["1K", "2K", "4K"], {"default": "2K"}),
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
    RETURN_NAMES = ("images", "image_urls")

    IS_CHANGED = staticmethod(_is_changed)

    def process_batch(self, images_list1, model_type=None, aspect_ratio=None, image_size=None,
                      prompt_order=None, seed=None,
                      prompts_list=None, images_list2=None, images_list3=None,
                      images_list4=None, images_list5=None):
        model_type   = _unpack(model_type) or "nano-banana-2-2605"
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        prompt_order = _unpack(prompt_order) or "sequential"
        seed         = _unpack(seed)

        api_key = synvow_auth.read_api_key()
        headers = synvow_auth.make_api_headers(api_key)

        all_lists = [images_list1,
                     images_list2 if images_list2 is not None else [],
                     images_list3 if images_list3 is not None else [],
                     images_list4 if images_list4 is not None else [],
                     images_list5 if images_list5 is not None else []]
        batch_size = max(len(lst) for lst in all_lists)

        if aspect_ratio == "auto":
            first_nonempty = next((lst for lst in all_lists if lst), None)
            if first_nonempty:
                pil0 = _tensor_to_pil(first_nonempty[0])
                aspect_ratio = _find_closest_aspect_ratio(pil0.width, pil0.height)
            else:
                aspect_ratio = "1:1"

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

        print(f"[NanoBanana TIBatch] {batch_size} 组图, {prompts_count} 条 prompt, order={prompt_order}, model={model_type}")

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

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, True, api_key, headers, _API_URL, _POLL_URL)
        image_list = _download_with_placeholder(image_urls)

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model_type} aspectRatio={aspect_ratio} size={image_size}" if successful else f"[ERROR] 所有任务失败 model={model_type} total={batch_size}"
        print(f"[NanoBanana TIBatch] 完成: {successful}/{batch_size}")
        synvow_auth.refresh_balance()
        return (image_list, status_str)


NODE_CLASS_MAPPINGS = {
    "SynVowNanoBanana": SynVowNanoBanana,
    "SynVowNanoBanana_TBatch": SynVowNanoBanana_TBatch,
    "SynVowNanoBanana_IBatch": SynVowNanoBanana_IBatch,
    "SynVowNanoBanana_TIBatch": SynVowNanoBanana_TIBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowNanoBanana": "SynVow NanoBanana",
    "SynVowNanoBanana_TBatch": "SynVow NanoBanana (T_batch)",
    "SynVowNanoBanana_IBatch": "SynVow NanoBanana (I_batch)",
    "SynVowNanoBanana_TIBatch": "SynVow NanoBanana (T_I_batch)",
}
