"""
SynVow GPT API node - Chat
"""

import concurrent.futures
import requests as _requests

from . import synvow_auth
from .media_common import upload_image as _upload_image, DIRECT_API_BASE
from .model_display import combo_models, resolve_model

GPT_API_MODELS = [
    "gpt-5.5-稳定",
    "gpt-5.6-sol-稳定",
    "gpt-5.4-qy",
    "gpt-5.5-qy",
    "gpt-5.6-sol-qy",
    "gpt-5.5-2606",
    "gpt-5.4-2606",
]
GPT_MODEL_OPTIONS = combo_models(GPT_API_MODELS)
DEFAULT_GPT_MODEL = GPT_MODEL_OPTIONS[0]


class SynVowGPTAPI:
    FUNCTION = "generate"
    CATEGORY = "💫SynVow_api/api/文本"
    OUTPUT_IS_LIST = (True,)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (GPT_MODEL_OPTIONS, {"default": DEFAULT_GPT_MODEL}),
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
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output",)

    @classmethod
    def IS_CHANGED(cls, 模型, user_prompt, seed, **kwargs):
        import hashlib
        key = f"{模型}|{user_prompt}|{seed}"
        return hashlib.md5(key.encode()).hexdigest()

    def _request_single(self, img_tensors, model_name, user_prompt, seed, api_key):
        if not isinstance(img_tensors, (list, tuple)):
            img_tensors = [img_tensors]

        if img_tensors:
            user_content = [{"type": "text", "text": user_prompt}]
            for t in img_tensors:
                url = _upload_image(api_key, t)
                user_content.append({"type": "image_url", "image_url": {"url": url}})
        else:
            user_content = user_prompt

        request_body = {
            "model": model_name,
            "stream": False,
            "messages": [{"role": "user", "content": user_content}],
        }
        headers = synvow_auth.make_api_headers(api_key)
        url = f"{DIRECT_API_BASE}/api/models/completions"
        print(f"[GPT] {model_name} 模型正在生成...")
        res = _requests.post(url, headers=headers, json=request_body, timeout=600, verify=False)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code}: {res.text[:200]}")
        response_data = res.json()
        print(f"[GPT] {model_name} 模型生成完毕。")
        text = synvow_auth.parse_chat_response(response_data)
        if not text:
            raise RuntimeError("模型未返回有效内容")
        return text

    def generate(self, 模型, user_prompt, seed,
                 image_1=None, image_2=None, image_3=None, image_4=None,
                 image_5=None, image_6=None, image_7=None, image_8=None,
                 image_9=None, image_10=None):
        api_key = synvow_auth.read_api_key()
        model_name = resolve_model(模型, GPT_API_MODELS[0])

        single_imgs = [img for img in [image_1, image_2, image_3, image_4, image_5,
                                       image_6, image_7, image_8, image_9, image_10]
                       if img is not None]
        task_inputs = [single_imgs] if single_imgs else [[]]

        outputs = [None] * len(task_inputs)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(task_inputs), 1)) as executor:
                future_map = {
                    executor.submit(self._request_single, imgs, model_name, user_prompt, seed, api_key): i
                    for i, imgs in enumerate(task_inputs)
                }
                for future in concurrent.futures.as_completed(future_map):
                    outputs[future_map[future]] = future.result()
            return (outputs,)
        finally:
            synvow_auth.refresh_balance()


class SynVowGPTAPI_TBatch:
    FUNCTION = "process_batch"
    CATEGORY = "💫SynVow_api/api/文本"
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    DESCRIPTION = "SynVow GPT 提示词生成 批量"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (GPT_MODEL_OPTIONS, {"default": DEFAULT_GPT_MODEL}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "prompts_list": ("STRING", {"forceInput": True}),
                "image_1": ("IMAGE",), "image_2": ("IMAGE",), "image_3": ("IMAGE",),
                "image_4": ("IMAGE",), "image_5": ("IMAGE",), "image_6": ("IMAGE",),
                "image_7": ("IMAGE",), "image_8": ("IMAGE",), "image_9": ("IMAGE",),
                "image_10": ("IMAGE",),
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
                      image_9=None, image_10=None):
        def _u(v, d=None):
            return v[0] if isinstance(v, list) and v else (v if v is not None else d)

        model_name = resolve_model(_u(模型), GPT_API_MODELS[0])
        seed_val = _u(seed, 0)
        api_key = synvow_auth.read_api_key()
        imgs = [_u(t) for t in [image_1, image_2, image_3, image_4, image_5,
                                image_6, image_7, image_8, image_9, image_10]
                if _u(t) is not None]
        raw = prompts_list if isinstance(prompts_list, list) else ([prompts_list] if prompts_list else [""])
        prompts = [str(p).strip() for p in raw if p is not None and str(p).strip()]
        if not prompts:
            prompts = [""]
        print(f"[GPT TBatch] {len(prompts)} 条 prompt, model={model_name}")
        outputs = [None] * len(prompts)
        single = SynVowGPTAPI()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(prompts), 1)) as executor:
                future_map = {
                    executor.submit(single._request_single, imgs, model_name, p, seed_val, api_key): i
                    for i, p in enumerate(prompts)
                }
                for future in concurrent.futures.as_completed(future_map):
                    outputs[future_map[future]] = future.result()
            return (outputs,)
        finally:
            synvow_auth.refresh_balance()


NODE_CLASS_MAPPINGS = {
    "SynVowGPTAPI": SynVowGPTAPI,
    "SynVowGPTAPI_TBatch": SynVowGPTAPI_TBatch,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGPTAPI": "SynVow GPT 提示词生成",
    "SynVowGPTAPI_TBatch": "SynVow GPT 提示词生成 (T_batch)",
}
