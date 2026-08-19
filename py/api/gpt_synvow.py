"""
SynVow GPT API node - Chat
"""

import concurrent.futures
import requests as _requests

from . import synvow_auth
from .media_common import upload_image as _upload_image, DIRECT_API_BASE

GPT_MODEL_OPTIONS = [
    "PT5.5-稳定",
    "PT5.6-sol-稳定",
    "gpt-5.5-2606",
    "gpt-5.4-2606",
    "gpt-5.5-2605",
    "gpt-5.4-2605",
]
DEFAULT_GPT_MODEL = GPT_MODEL_OPTIONS[0]
_GPT_MODEL_ALIASES = {
    "gpt-5.5-2607": "gpt-5.5-稳定",
    "gpt-5.6-sol-2607": "gpt-5.6-sol-稳定",
    "PT5.5-稳定": "gpt-5.5-稳定",
    "PT5.6-sol-稳定": "gpt-5.6-sol-稳定",
}


def resolve_gpt_model(model_name):
    name = model_name or DEFAULT_GPT_MODEL
    return _GPT_MODEL_ALIASES.get(name, name)


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
        try:
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
                return f"HTTP {res.status_code}: {res.text[:200]}"
            response_data = res.json()
            print(f"[GPT] {model_name} 模型生成完毕。")
            return synvow_auth.parse_chat_response(response_data) or "Error: empty response"
        except Exception as e:
            return str(e)

    def generate(self, 模型, user_prompt, seed,
                 image_1=None, image_2=None, image_3=None, image_4=None,
                 image_5=None, image_6=None, image_7=None, image_8=None,
                 image_9=None, image_10=None):
        api_key = synvow_auth.read_api_key()
        model_name = resolve_gpt_model(模型)

        single_imgs = [img for img in [image_1, image_2, image_3, image_4, image_5,
                                       image_6, image_7, image_8, image_9, image_10]
                       if img is not None]
        task_inputs = [single_imgs] if single_imgs else [[]]

        outputs = [None] * len(task_inputs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(len(task_inputs), 1)) as executor:
            future_map = {
                executor.submit(self._request_single, imgs, model_name, user_prompt, seed, api_key): i
                for i, imgs in enumerate(task_inputs)
            }
            for future in concurrent.futures.as_completed(future_map):
                idx = future_map[future]
                try:
                    outputs[idx] = future.result()
                except Exception as e:
                    outputs[idx] = str(e)

            synvow_auth.refresh_balance()
        return (outputs,)


NODE_CLASS_MAPPINGS = {
    "SynVowGPTAPI": SynVowGPTAPI,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGPTAPI": "SynVow GPT 提示词生成",
}
