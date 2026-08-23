"""
SynVow Qwen API node - Chat
"""

import concurrent.futures
import requests as _requests

from . import synvow_auth
from .media_common import DIRECT_API_BASE, upload_image as _upload_image, upload_media_file
from .model_display import combo_models, resolve_model

QWEN_API_MODELS = [
    "qwen3.6-flash-wd",
    "qwen3.6-plus-wd",
    "qwen3.7-plus-wd",
    "qwen3.7-max-wd",
    "qwen3.8-max-wd",
]
QWEN_MODEL_OPTIONS = combo_models(QWEN_API_MODELS)
DEFAULT_QWEN_MODEL = QWEN_MODEL_OPTIONS[0]


def _request_qwen(img_tensors, model_name, user_prompt, api_key, video_path=""):
    if not isinstance(img_tensors, (list, tuple)):
        img_tensors = [img_tensors]
    img_tensors = [t for t in img_tensors if t is not None]
    video_url = upload_media_file(api_key, video_path, "video") if video_path else ""

    if img_tensors or video_url:
        user_content = [{"type": "text", "text": user_prompt}]
        for t in img_tensors:
            url = _upload_image(api_key, t)
            user_content.append({"type": "image_url", "image_url": {"url": url}})
        if video_url:
            user_content.append({"type": "video_url", "video_url": {"url": video_url}})
    else:
        user_content = user_prompt

    request_body = {
        "model": model_name,
        "stream": False,
        "messages": [{"role": "user", "content": user_content}],
    }
    headers = synvow_auth.make_api_headers(api_key)
    url = f"{DIRECT_API_BASE}/api/models/completions"
    print(f"[Qwen] {model_name} 模型正在生成...")
    res = _requests.post(url, headers=headers, json=request_body, timeout=600, verify=False)
    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:200]}")
    print(f"[Qwen] {model_name} 模型生成完毕。")
    text = synvow_auth.parse_chat_response(res.json())
    if not text:
        raise RuntimeError("模型未返回有效内容")
    return text


class SynVowQwenAPI:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/文本"
    OUTPUT_IS_LIST = (True,)
    DESCRIPTION = "SynVow LLM-Qwen"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (QWEN_MODEL_OPTIONS, {"default": DEFAULT_QWEN_MODEL}),
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "image_5": ("IMAGE",),
                "image_6": ("IMAGE",),
                "image_7": ("IMAGE",),
                "image_8": ("IMAGE",),
                "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
                "video_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)

    @classmethod
    def IS_CHANGED(cls, 模型, user_prompt, seed, **kwargs):
        import hashlib
        key = f"{模型}|{user_prompt}|{seed}|{kwargs.get('video_path', '')}"
        return hashlib.md5(key.encode()).hexdigest()

    def generate(self, 模型, user_prompt, seed,
                 image_1=None, image_2=None, image_3=None, image_4=None,
                 image_5=None, image_6=None, image_7=None, image_8=None,
                 image_9=None, image_10=None, video_path=""):
        del seed
        api_key = synvow_auth.read_api_key()
        model_name = resolve_model(模型, QWEN_API_MODELS[0])
        imgs = [img for img in [image_1, image_2, image_3, image_4, image_5,
                                image_6, image_7, image_8, image_9, image_10]
                if img is not None]
        try:
            text = _request_qwen(imgs, model_name, user_prompt, api_key, video_path or "")
            return ([text],)
        finally:
            synvow_auth.refresh_balance()


class SynVowQwenAPI_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/文本"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    DESCRIPTION = "SynVow LLM-Qwen 提示词批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (QWEN_MODEL_OPTIONS, {"default": DEFAULT_QWEN_MODEL}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
                "video_path": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("outputs",)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import hashlib
        import json
        return hashlib.md5(json.dumps(kwargs, default=str).encode()).hexdigest()

    def process_batch(self, 模型=None, seed=None, prompts_list=None,
                      image_1=None, image_2=None, image_3=None, image_4=None,
                      image_5=None, image_6=None, image_7=None, image_8=None,
                      image_9=None, image_10=None, video_path=None):
        del seed

        def _u(v, d=None):
            return v[0] if isinstance(v, list) and v else (v if v is not None else d)

        model_name = resolve_model(_u(模型), QWEN_API_MODELS[0])
        video = _u(video_path, "") or ""
        api_key = synvow_auth.read_api_key()
        imgs = [_u(t) for t in [image_1, image_2, image_3, image_4, image_5,
                                image_6, image_7, image_8, image_9, image_10]
                if _u(t) is not None]
        raw = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [str(p).strip() for p in raw if p is not None and str(p).strip()]
        if not prompts:
            prompts = [""]
        print(f"[Qwen TBatch] {len(prompts)} 条 prompt, model={model_name}")
        outputs = [None] * len(prompts)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(prompts), 1)) as executor:
                future_map = {
                    executor.submit(_request_qwen, imgs, model_name, p, api_key, video): i
                    for i, p in enumerate(prompts)
                }
                for future in concurrent.futures.as_completed(future_map):
                    outputs[future_map[future]] = future.result()
            return (outputs,)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowQwenAPI": SynVowQwenAPI,
    "SynVowQwenAPI_TBatch": SynVowQwenAPI_TBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowQwenAPI": "SynVow LLM-Qwen",
    "SynVowQwenAPI_TBatch": "SynVow LLM-Qwen (T_batch)",
}
