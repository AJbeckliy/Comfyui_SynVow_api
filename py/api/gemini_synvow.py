"""
SynVow Gemini API node - Chat/Vision via local proxy
Uses Proxy_Router + X-API-Key auth (same pattern as NanoBanana)
"""

import json
import io
import numpy as np
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


class SynVowGeminiAPI:
    FUNCTION = "generate"
    CATEGORY = "\U0001f4abSynVow_api"
    DESCRIPTION = "通过 SynVow 代理调用 Gemini 模型，支持多图输入"

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
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _tensor_to_base64(self, tensor):
        """将图片 tensor 转成 base64 字符串"""
        import base64
        i = 255.0 * tensor[0].cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _upload_image(self, tensor, api_key):
        """上传图片到 SynVow，返回公开 URL（供 GPT 类模型使用）"""
        import requests as _requests
        i = 255.0 * tensor[0].cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        res = _requests.post(
            "https://service.synvow.com/api/v1/api/upload/images",
            headers={"X-API-Key": api_key},
            files={"files": ("image.jpg", buf, "image/jpeg")},
            timeout=30, verify=False,
        )
        if res.status_code != 200:
            raise RuntimeError(f"图片上传失败: {res.status_code} {res.text[:100]}")
        data = res.json()
        urls = data.get("data", {}).get("urls", []) if isinstance(data.get("data"), dict) else data.get("data", [])
        if not urls:
            raise RuntimeError(f"图片上传响应无URL: {res.text[:100]}")
        url = urls[0]
        # 确保是 https
        return url.replace("http://", "https://")

    def generate(self, 模型, 模式, system_prompt, user_prompt, seed=0, **kwargs):
        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            return (str(e), json.dumps({"error": str(e)}, ensure_ascii=False), json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))

        model_name = GEMINI_MODEL_MAP.get((模型, 模式), "gemini-3.1-flash-默认")

        # 图片转 base64，用 content 数组格式（OpenAI 多模态标准）
        user_content = []
        image_count = 0
        for i in range(1, 11):
            img = kwargs.get(f"image_{i}")
            if img is not None:
                try:
                    b64 = self._tensor_to_base64(img)
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
                    image_count += 1
                except Exception as e:
                    print(f"[SynVow Gemini] 图片{i}处理失败: {e}")

        if user_prompt:
            user_content.append({"type": "text", "text": user_prompt})

        # 无图时 content 直接用字符串，有图用数组
        final_content = user_content if image_count > 0 else user_prompt

        request_body = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": final_content},
            ],
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
        consumption_id = response_data.get("consumption_id", "") if isinstance(response_data, dict) else ""
        debug = json.dumps({"model": model_name, "images": image_count, "raw": raw_text[:500]}, ensure_ascii=False)
        task_info = json.dumps({"status": "SUCCESS", "consumption_id": consumption_id, "model": model_name}, ensure_ascii=False)
        return (raw_text, debug, task_info)


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
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

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
        consumption_id = response_data.get("consumption_id", "") if isinstance(response_data, dict) else ""
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
