"""
SynVow GPT-Image-2 节点
"""

import concurrent.futures
import random as _random
import time

import comfy.utils
import urllib3

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
    "gpt-image-2-2607",
    "gpt-image-2-稳定",
    "gpt-image-2-官方",
    "gpt-image-2-1k-qy",
    "gpt-image-2-4k-qy",
]

_DEFAULT_GPT_IMAGE_MODEL = "gpt-image-2-稳定"
_NEW_MODELS = {"gpt-image-2-稳定"}
_RAW_RATIO_MODELS = {"gpt-image-2-官方"}
_NESTED_PARAM_MODELS = {"gpt-image-2-2607"}


def _is_qy_model(model):
    return str(model or "").endswith(("-qy", "-qy-t2v"))


def _locked_resolution(model):
    return "1K" if "-1k-" in str(model or "") else None


def _resolve_size_params(model, aspect_ratio, resolution):
    if model in _RAW_RATIO_MODELS:
        return resolution or "1K", aspect_ratio or "auto"
    locked = _locked_resolution(model)
    eff_resolution = locked or (resolution or "1K")
    ratio_map = _RATIO_MAPS.get(eff_resolution, _RATIO_TO_SIZE_1K)
    return eff_resolution, ratio_map.get(aspect_ratio, "auto")


def _build_payload(model, prompt, size, quality, resolution, is_img2img, img_tensors, api_key=None, aspect_ratio=None):
    payload = {"model": model, "prompt": prompt}
    image_urls = []
    if is_img2img and img_tensors and api_key:
        image_urls = [_upload_image(api_key, t) for t in img_tensors]

    if model in _NESTED_PARAM_MODELS:
        params = {
            "n": 1,
            "response_format": "url",
            "quality": (quality or "auto").lower(),
            "resolution": resolution,
            "size": size or "auto",
            "aspect_ratio": aspect_ratio or "auto",
        }
        if image_urls:
            params["images"] = image_urls
        payload["params"] = params
    elif model in _RAW_RATIO_MODELS:
        if size:
            payload["size"] = size
        if resolution:
            payload["resolution"] = resolution.lower()
        if quality:
            payload["quality"] = quality.lower()
        payload["n"] = 1
        if image_urls:
            payload["image_urls"] = image_urls
    elif _is_qy_model(model):
        if size:
            payload["size"] = size
        if quality:
            payload["quality"] = (quality or "auto").lower()
        if image_urls:
            payload["images"] = image_urls
    elif model in _NEW_MODELS:
        if size and size != "auto":
            payload["size"] = size
        if resolution:
            payload["resolution"] = resolution
        if image_urls:
            payload["image_urls"] = image_urls
    else:
        payload["replyType"] = "async"
        if size and size != "auto":
            payload["aspectRatio"] = size
        if quality and quality != "auto":
            payload["quality"] = quality
        if image_urls:
            payload["images"] = image_urls
    return payload


def _poll_urls(api_key, task_id, model, consumption_id=""):
    def pick(inner, data):
        found = extract_result_urls(inner) or extract_result_urls(data)
        return found or None

    result = poll_edit_task(
        api_key, task_id, model, "GPT-Image-2",
        consumption_id=consumption_id or "", fail_soft=True, pick_url=pick,
    )
    if not result:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _run_tasks(tasks, model, size, quality, resolution, is_img2img, api_key, aspect_ratio=None):
    total = len(tasks)
    pbar = comfy.utils.ProgressBar(total)
    request_model = "gpt-image-2-4k-qy-t2v" if model == "gpt-image-2-4k-qy" and not is_img2img else model

    submitted = []
    for i, (p, imgs) in enumerate(tasks):
        payload = _build_payload(
            request_model, p, size, quality, resolution, is_img2img, imgs,
            api_key=api_key, aspect_ratio=aspect_ratio,
        )
        try:
            task_id, consumption_id = submit_edit_async(api_key, payload, "GPT-Image-2")
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
        urls = _poll_urls(api_key, task_id, request_model, consumption_id)
        pbar.update(1)
        return urls

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        poll_results = list(executor.map(_poll_one, submitted))

    image_urls = []
    for i, urls in enumerate(poll_results):
        if urls:
            image_urls.extend(urls)
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
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": _DEFAULT_GPT_IMAGE_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_GPT_IMAGE_MODEL
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        prompt       = _unpack(prompt)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)

        api_key = synvow_auth.read_api_key()

        model = model_type or _DEFAULT_GPT_IMAGE_MODEL
        eff_resolution, size = _resolve_size_params(model, aspect_ratio, resolution)

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None]
        is_img2img = len(imgs) > 0

        p = str(prompt).strip() if prompt else ""
        tasks = [(p, imgs)]

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, is_img2img, api_key, aspect_ratio=aspect_ratio)
        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 model={model} size={size} quality={quality}" if successful else f"[ERROR] 生成失败 model={model} size={size}"

        out_tensor = stack_image_tensors(image_urls, tag="GPT-Image-2")
        synvow_auth.refresh_balance()
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
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": _DEFAULT_GPT_IMAGE_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_GPT_IMAGE_MODEL
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        image1 = _unpack(image1); image2 = _unpack(image2)
        image3 = _unpack(image3); image4 = _unpack(image4)
        image5 = _unpack(image5); image6 = _unpack(image6)
        image7 = _unpack(image7); image8 = _unpack(image8)

        api_key = synvow_auth.read_api_key()

        model = model_type or _DEFAULT_GPT_IMAGE_MODEL
        eff_resolution, size = _resolve_size_params(model, aspect_ratio, resolution)

        imgs = [t for t in [image1, image2, image3, image4, image5, image6, image7, image8] if t is not None]
        is_img2img = len(imgs) > 0
        prompts = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [p for p in prompts if p is not None]

        tasks = [(p, imgs) for p in prompts]
        total = len(tasks)
        print(f"[GPT-Image-2 TBatch] {total} 条 prompt, model={model}")

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, is_img2img, api_key, aspect_ratio=aspect_ratio)
        image_list = download_image_tensors(image_urls, tag="GPT-Image-2")

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{total} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={total}"
        print(f"[GPT-Image-2 TBatch] 完成: {successful}/{total}")
        synvow_auth.refresh_balance()
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
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": _DEFAULT_GPT_IMAGE_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_GPT_IMAGE_MODEL
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        prompt       = _unpack(prompt)

        api_key = synvow_auth.read_api_key()

        model = model_type or _DEFAULT_GPT_IMAGE_MODEL
        eff_resolution, size = _resolve_size_params(model, aspect_ratio, resolution)

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

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, True, api_key, aspect_ratio=aspect_ratio)
        image_list = download_image_tensors(image_urls, tag="GPT-Image-2")

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
        print(f"[GPT-Image-2 IBatch] 完成: {successful}/{batch_size}")
        synvow_auth.refresh_balance()
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
                "model_type": (_MODEL_TYPE_OPTIONS, {"default": _DEFAULT_GPT_IMAGE_MODEL}),
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
        model_type   = _unpack(model_type) or _DEFAULT_GPT_IMAGE_MODEL
        quality      = _unpack(quality)
        resolution   = _unpack(resolution) or "1K"
        aspect_ratio = _unpack(aspect_ratio)
        prompt_order = _unpack(prompt_order) or "sequential"

        api_key = synvow_auth.read_api_key()

        model = model_type or _DEFAULT_GPT_IMAGE_MODEL
        eff_resolution, size = _resolve_size_params(model, aspect_ratio, resolution)

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

        image_urls = _run_tasks(tasks, model, size, quality, eff_resolution, True, api_key, aspect_ratio=aspect_ratio)
        image_list = download_image_tensors(image_urls, tag="GPT-Image-2")

        successful = sum(1 for u in image_urls if u)
        status_str = f"已完成 {successful}/{batch_size} model={model} size={size} quality={quality}" if successful else f"[ERROR] 所有任务失败 model={model} total={batch_size}"
        print(f"[GPT-Image-2 TIBatch] 完成: {successful}/{batch_size}")
        synvow_auth.refresh_balance()
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
