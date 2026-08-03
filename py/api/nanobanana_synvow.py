"""NanoBanana SynVow 图像生成 / 批量生成"""

import concurrent.futures
import random as _random
import time

import comfy.utils
import numpy as np
import urllib3
from PIL import Image

from . import synvow_auth
from .media_common import (
    download_image_tensors,
    extract_result_urls,
    is_changed_by_inputs as _is_changed,
    poll_edit_task,
    stack_image_tensors,
    submit_edit_async,
    unpack_list_input as _unpack,
    upload_image as _upload_image,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_MODEL_OPTIONS = [
    "nano-banana-2-2605",
    "nano-banana-2-lite-2607",
    "nano-banana-2-稳定",
    "nano-banana-2-官方",
    "nanobanana2-qy",
    "nano-banana-pro-2605",
    "nano-banana-pro-稳定",
    "nano-banana-pro-官方",
    "nanobananapro-qy",
]

_DEFAULT_NANO_BANANA_MODEL = "nano-banana-2-稳定"


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


_MODERN_MODELS = {
    "nano-banana-2-稳定", "nano-banana-2-官方",
    "nano-banana-pro-稳定", "nano-banana-pro-官方",
}
_QY_MODELS = {"nanobanana2-qy", "nanobananapro-qy"}


def _build_payload(model, prompt, aspect_ratio, image_size, is_img2img, img_tensors, api_key=None):
    image_urls = []
    if is_img2img and img_tensors and api_key:
        image_urls = [_upload_image(api_key, t) for t in img_tensors]

    if model in _QY_MODELS:
        parts = [{"text": prompt or ""}]
        for url in image_urls:
            parts.append({"fileData": {"fileUri": url}})
        image_config = {}
        if aspect_ratio and aspect_ratio != "auto":
            image_config["aspectRatio"] = aspect_ratio
        if image_size:
            image_config["imageSize"] = image_size
        generation_config = {"responseModalities": ["IMAGE"]}
        if image_config:
            generation_config["imageConfig"] = image_config
        return {
            "model": model,
            "response_format": "url",
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
        }

    if model in _MODERN_MODELS:
        payload = {"model": model, "prompt": prompt}
        if aspect_ratio and aspect_ratio != "auto":
            payload["size"] = aspect_ratio
        if image_size:
            payload["resolution"] = image_size
        if image_urls:
            payload["image_urls"] = image_urls
        return payload

    payload = {"model": model, "prompt": prompt, "replyType": "async"}
    if aspect_ratio and aspect_ratio != "auto":
        payload["aspectRatio"] = aspect_ratio
    if image_size:
        payload["imageSize"] = image_size
    if image_urls:
        payload["images"] = image_urls
    return payload


def _poll_urls(api_key, task_id, model, consumption_id=""):
    def pick(inner, data):
        found = extract_result_urls(inner) or extract_result_urls(data)
        return found or None

    result = poll_edit_task(
        api_key, task_id, model, "NanoBanana",
        consumption_id=consumption_id or "", fail_soft=True, pick_url=pick,
    )
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _run_tasks(tasks, model, aspect_ratio, image_size, is_img2img, api_key):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)

    submitted = []
    for i, (p, imgs) in enumerate(tasks):
        payload = _build_payload(model, p, aspect_ratio, image_size, is_img2img, imgs, api_key=api_key)
        try:
            task_id, consumption_id = submit_edit_async(api_key, payload, "NanoBanana")
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
        urls = _poll_urls(api_key, task_id, model, consumption_id)
        pbar.update(1)
        return urls

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        poll_results = list(executor.map(_poll_one, submitted))

    image_urls = []
    for i, urls in enumerate(poll_results):
        if urls:
            image_urls.extend(urls)
        else:
            print(f"[NanoBanana] task[{i}] 失败，黑图占位")
            image_urls.append(None)
    return image_urls


class SynVowNanoBanana:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/图像"
    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_NANO_BANANA_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_NANO_BANANA_MODEL
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        prompt       = _unpack(prompt)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)
        image9 = _unpack(image9)

        api_key = synvow_auth.read_api_key()

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8, image9] if t is not None]
        if aspect_ratio == "auto" and imgs:
            pil0 = _tensor_to_pil(imgs[0])
            aspect_ratio = _find_closest_aspect_ratio(pil0.width, pil0.height)
        elif aspect_ratio == "auto":
            aspect_ratio = "1:1"
        is_img2img = len(imgs) > 0

        p = str(prompt).strip() if prompt else ""
        tasks = [(p, imgs)]

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, is_img2img, api_key)
        successful = sum(1 for u in image_urls if u)
        if successful:
            status_str = f"已完成 model={model_type} aspectRatio={aspect_ratio} size={image_size}"
        else:
            status_str = f"[ERROR] 生成失败 model={model_type} aspectRatio={aspect_ratio}"

        out_tensor = stack_image_tensors(image_urls, tag="NanoBanana")
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
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_NANO_BANANA_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_NANO_BANANA_MODEL
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)
        image9 = _unpack(image9)

        api_key = synvow_auth.read_api_key()

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

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, is_img2img, api_key)
        image_list = download_image_tensors(image_urls, tag="NanoBanana")

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
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_NANO_BANANA_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_NANO_BANANA_MODEL
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        prompt       = _unpack(prompt)

        api_key = synvow_auth.read_api_key()

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

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, True, api_key)
        image_list = download_image_tensors(image_urls, tag="NanoBanana")

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
                "model_type": (_MODEL_OPTIONS, {"default": _DEFAULT_NANO_BANANA_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_NANO_BANANA_MODEL
        aspect_ratio = _unpack(aspect_ratio) or "1:1"
        image_size   = _unpack(image_size) or "2K"
        prompt_order = _unpack(prompt_order) or "sequential"

        api_key = synvow_auth.read_api_key()

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

        image_urls = _run_tasks(tasks, model_type, aspect_ratio, image_size, True, api_key)
        image_list = download_image_tensors(image_urls, tag="NanoBanana")

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
