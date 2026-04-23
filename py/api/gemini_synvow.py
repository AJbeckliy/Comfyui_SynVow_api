"""
SynVow Gemini API node - Chat/Vision via local proxy
Uses Proxy_Router + X-API-Key auth (same pattern as NanoBanana)
"""

import base64
import concurrent.futures
import json
import io
import numpy as np
import requests as _requests
from PIL import Image

from . import synvow_auth

DEFAULT_SYSTEM_PROMPT = ""

GEMINI_MODEL_OPTIONS = ["gemini-3.1-flash", "gemini-3.1-pro"]
GEMINI_MODE_OPTIONS = ["默认", "优质"]
GEMINI_MODEL_MAP = {
    ("gemini-3.1-flash", "默认"): "gemini-3.1-flash-默认",
    ("gemini-3.1-flash", "优质"): "gemini-3.1-flash-优质",
    ("gemini-3.1-pro",   "默认"): "gemini-3.1-pro-默认",
    ("gemini-3.1-pro",   "优质"): "gemini-3.1-pro-优质",
}

DIRECT_API_BASE = "https://service.synvow.com/api/v1"


class SynVowGeminiAPI:
    FUNCTION = "generate"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "通过 SynVow 代理调用 Gemini 模型，图片列表并发请求，每张图输出一条提示词"
    OUTPUT_IS_LIST = (True, True, True)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (GEMINI_MODEL_OPTIONS, {"default": "gemini-3.1-flash"}),
                "模式": (GEMINI_MODE_OPTIONS, {"default": "默认"}),
                "system_prompt": ("STRING", {"multiline": True, "default": DEFAULT_SYSTEM_PROMPT}),
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
            "optional": {
                "images_list": ("IMAGE",),
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

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("output", "debug_info", "task_info")

    @classmethod
    def IS_CHANGED(cls, 模型, 模式, system_prompt, user_prompt, seed, **kwargs):
        import hashlib
        key = f"{模型}|{模式}|{system_prompt}|{user_prompt}|{seed}"
        return hashlib.md5(key.encode()).hexdigest()

    def _tensor_to_base64(self, tensor):
        i = 255.0 * tensor[0].cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _request_single(self, img_tensors, model_name, system_prompt, user_prompt, seed, api_key):
        """img_tensors: 单个 tensor 或 tensor 列表，多张图合并进一条消息"""
        try:
            if not isinstance(img_tensors, (list, tuple)):
                img_tensors = [img_tensors]
            user_content = []
            for t in img_tensors:
                b64 = self._tensor_to_base64(t)
                user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            if user_prompt:
                user_content.append({"type": "text", "text": user_prompt})
            request_body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 8192,
                "temperature": 0.7,
            }
            if seed > 0:
                request_body["seed"] = seed
            headers = synvow_auth.make_api_headers(api_key)
            url = f"{DIRECT_API_BASE}/api/models/chat/completions"
            res = _requests.post(url, headers=headers, json=request_body, timeout=300, verify=False)
            if res.status_code != 200:
                return f"HTTP {res.status_code}: {res.text[:200]}", "{}", "{}"
            response_data = res.json()
            raw_text = synvow_auth.parse_chat_response(response_data) or "Error: empty response"
            consumption_id = response_data.get("consumption_id") if isinstance(response_data, dict) else None
            debug = json.dumps({"model": model_name, "raw": raw_text[:500]}, ensure_ascii=False)
            task_info = json.dumps({"status": "SUCCESS", "consumption_id": consumption_id, "model": model_name}, ensure_ascii=False)
            return raw_text, debug, task_info
        except Exception as e:
            err = str(e)
            return err, json.dumps({"error": err}, ensure_ascii=False), json.dumps({"status": "error", "message": err}, ensure_ascii=False)

    def generate(self, 模型, 模式, system_prompt, user_prompt, seed,
                 images_list=None,
                 image_1=None, image_2=None, image_3=None, image_4=None,
                 image_5=None, image_6=None, image_7=None, image_8=None,
                 image_9=None, image_10=None):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            msg = str(e)
            return ([msg], [json.dumps({"error": msg}, ensure_ascii=False)], [json.dumps({"status": "error", "message": msg}, ensure_ascii=False)])

        model_name = GEMINI_MODEL_MAP.get((模型, 模式), "gemini-3.1-flash-默认")

        # images_list: 每张图独立一个并发任务
        # image_1~10: 合并为单次请求（多图一起发给 Gemini）
        if images_list is not None:
            if isinstance(images_list, (list, tuple)):
                task_inputs = list(images_list)
            else:
                task_inputs = [images_list[i:i+1] for i in range(images_list.shape[0])]
        else:
            single_imgs = [img for img in [image_1, image_2, image_3, image_4, image_5,
                                           image_6, image_7, image_8, image_9, image_10]
                           if img is not None]
            task_inputs = [single_imgs] if single_imgs else []

        if not task_inputs:
            return (["无图片输入"], ["{}"], ["{}"])

        print(f"[SynVow Gemini] 并发处理 {len(task_inputs)} 个任务")
        outputs = [None] * len(task_inputs)
        debugs = [None] * len(task_inputs)
        tasks = [None] * len(task_inputs)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(task_inputs)) as executor:
            future_map = {
                executor.submit(self._request_single, imgs, model_name, system_prompt, user_prompt, seed, api_key): i
                for i, imgs in enumerate(task_inputs)
            }
            for future in concurrent.futures.as_completed(future_map):
                idx = future_map[future]
                try:
                    outputs[idx], debugs[idx], tasks[idx] = future.result()
                except Exception as e:
                    err = str(e)
                    outputs[idx] = err
                    debugs[idx] = json.dumps({"error": err}, ensure_ascii=False)
                    tasks[idx] = json.dumps({"status": "error", "message": err}, ensure_ascii=False)

        return (outputs, debugs, tasks)


class SynVowGeminiPromptGen:
    FUNCTION = "generate"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "通过 SynVow 代理调用 Gemini 模型生成提示词，纯文本输入，无图像"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "模型": (GEMINI_MODEL_OPTIONS, {"default": "gemini-3.1-flash"}),
                "模式": (GEMINI_MODE_OPTIONS, {"default": "默认"}),
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "user_prompt": ("STRING", {"multiline": True, "default": ""}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("output", "debug_info", "task_info")

    @classmethod
    def IS_CHANGED(cls, 模型, 模式, system_prompt, user_prompt, seed=0, **kwargs):
        import hashlib
        key = f"{模型}|{模式}|{system_prompt}|{user_prompt}|{seed}"
        return hashlib.md5(key.encode()).hexdigest()

    def generate(self, 模型, 模式, system_prompt, user_prompt, seed=0, **kwargs):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return (str(e), json.dumps({"error": str(e)}, ensure_ascii=False), json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        model_name = GEMINI_MODEL_MAP.get((模型, 模式), "gemini-3.1-flash-默认")

        # user_prompt 为空时用 system_prompt 内容顶替，避免 contents is required 报错
        effective_user = user_prompt.strip() if user_prompt and user_prompt.strip() else system_prompt.strip()
        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": effective_user})

        request_body = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 8192,
            "temperature": 0.7,
        }
        if seed > 0:
            request_body["seed"] = seed

        DIRECT_API_BASE = "https://service.synvow.com/api/v1"
        url = f"{DIRECT_API_BASE}/api/models/chat/completions"
        headers = synvow_auth.make_api_headers(api_key)

        try:
            import requests as _requests
            res = _requests.post(url, headers=headers, json=request_body, timeout=300, verify=False)
            if res.status_code != 200:
                msg = f"HTTP {res.status_code}: {res.text[:200]}"
                return (msg, json.dumps({"error": msg}, ensure_ascii=False), json.dumps({"status": "error", "message": msg}, ensure_ascii=False))
            response_data = res.json()
        except Exception as e:
            return (f"Request error: {e}", json.dumps({"error": str(e)}, ensure_ascii=False), json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        raw_text = synvow_auth.parse_chat_response(response_data) or "Error: empty response"
        consumption_id = response_data.get("consumption_id") if isinstance(response_data, dict) else None
        debug = json.dumps({"model": model_name, "raw": raw_text[:500]}, ensure_ascii=False)
        task_info = json.dumps({"status": "SUCCESS", "consumption_id": consumption_id, "model": model_name}, ensure_ascii=False)
        return (raw_text, debug, task_info)


NODE_CLASS_MAPPINGS = {
    "SynVowGeminiAPI": SynVowGeminiAPI,
    "SynVowGeminiPromptGen": SynVowGeminiPromptGen,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGeminiAPI": "SynVow Gemini API 图生文",
    "SynVowGeminiPromptGen": "SynVow Gemini 提示词生成",
}
