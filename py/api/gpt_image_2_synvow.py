"""
SynVow GPT-Image-2 节点 — 通过 SynVow /api/models/image/edit 接口生成/编辑图片
"""

import base64 as _b64
import io
import time

import numpy as np
import requests
import torch
import urllib3
from PIL import Image

from . import synvow_auth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SynVowGptImage2:
    """通过 SynVow 代理调用 GPT-Image-2，支持文生图和图生图（最多 4 张输入图）"""

    _conversation_history = []
    _last_image_urls = ""

    FUNCTION = "generate"
    CATEGORY = "\U0001f4abSynVow_api"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "model": (["gpt-image-2-文生图-默认", "gpt-image-2-图生图-默认"], {"default": "gpt-image-2-文生图-默认"}),
                "size": (["1024x1024", "1536x1024", "1024x1536"], {"default": "1024x1024"}),
                "clear_chats": ("BOOLEAN", {"default": True}),
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "response", "image_urls", "chats")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("NaN")

    def _format_history(self):
        if not SynVowGptImage2._conversation_history:
            return ""
        out = ""
        for entry in SynVowGptImage2._conversation_history:
            out += f"**User**: {entry['user']}\n\n**AI**: {entry['ai']}\n\n---\n\n"
        return out.strip()

    def _blank_image(self):
        return torch.zeros((1, 1024, 1024, 3), dtype=torch.float32)

    def generate(self, prompt, model="gpt-image-2-文生图-默认", size="1024x1024",
                 clear_chats=True,
                 image1=None, image2=None, image3=None, image4=None):

        try:
            api_key = synvow_auth.read_api_key()
        except RuntimeError as e:
            msg = str(e)
            print(f"[SynVow GPT-Image-2] {msg}")
            return (self._blank_image(), msg, "", self._format_history())

        if clear_chats:
            SynVowGptImage2._conversation_history = []
            SynVowGptImage2._last_image_urls = ""

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        DIRECT_API_BASE = "https://service.synvow.com/api/v1"
        LOCAL_BASE = synvow_auth.get_proxy_base()
        headers = synvow_auth.make_api_headers(api_key)

        is_img2img = "图生图" in model
        print(f"[SynVow GPT-Image-2] mode={'img2img' if is_img2img else 'text2img'}, model={model}")

        api_url = f"{LOCAL_BASE}/api/models/image/edit"
        resp_json = None

        try:
            payload = {"model": model, "prompt": prompt, "size": size}

            if is_img2img:
                image_list = []
                for img_tensor in [image1, image2, image3, image4]:
                    if img_tensor is not None:
                        arr = (img_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
                        buf = io.BytesIO()
                        Image.fromarray(arr).convert("RGB").save(buf, format="PNG")
                        image_list.append("data:image/png;base64," + _b64.b64encode(buf.getvalue()).decode())
                payload["image"] = image_list[0]
                if len(image_list) > 1:
                    payload["images"] = image_list[1:]
                print(f"[SynVow GPT-Image-2] img2img {len(image_list)} images")

            res = requests.post(api_url, headers=headers, json=payload,
                                params={"async": "true"}, timeout=60, verify=False)
            res.raise_for_status()
            submit_json = res.json()
        except Exception as e:
            msg = f"提交失败: {e}"
            print(f"[SynVow GPT-Image-2] {msg}")
            return (self._blank_image(), msg, "", self._format_history())

        _d = submit_json if isinstance(submit_json, dict) else {}
        task_id = (
            _d.get("task_id")
            or (_d.get("data") or {}).get("task_id")
            or ((_d.get("data") or {}).get("sourceData") or {}).get("task_id")
        )
        consumption_id = str(_d.get("consumption_id", "") or "")

        if not task_id:
            resp_json = submit_json
        else:
            print(f"[SynVow GPT-Image-2] task_id={task_id[:8]}... 轮询中")
            poll_url = f"{DIRECT_API_BASE}/api/models/tasks"
            poll_body = {"task_id": task_id, "model": model}
            if consumption_id:
                poll_body["consumption_id"] = consumption_id
            timeout_total = 600
            interval = 5
            elapsed = 0
            while elapsed < timeout_total:
                time.sleep(interval)
                elapsed += interval
                try:
                    poll_res = requests.post(poll_url, headers=headers, json=poll_body, timeout=30, verify=False)
                    poll_res.raise_for_status()
                    poll_json = poll_res.json()
                    data_field = poll_json.get("data", poll_json) if isinstance(poll_json, dict) else poll_json
                    status = data_field.get("status", "") if isinstance(data_field, dict) else ""
                    if status in ("SUCCESS", "success", "completed", "done", "finished"):
                        print(f"[SynVow GPT-Image-2] ✅ 完成 ({elapsed}s)")
                        resp_json = poll_json
                        break
                    elif status in ("FAILURE", "failed", "error"):
                        msg = data_field.get("fail_reason", "任务失败")
                        print(f"[SynVow GPT-Image-2] ❌ {msg}")
                        return (self._blank_image(), msg, "", self._format_history())
                except Exception as e:
                    print(f"[SynVow GPT-Image-2] 轮询异常: {e}")
            if resp_json is None:
                msg = f"轮询超时 ({timeout_total}s)"
                print(f"[SynVow GPT-Image-2] {msg}")
                return (self._blank_image(), msg, "", self._format_history())

        resp_code = resp_json.get("code", 200) if isinstance(resp_json, dict) else 200
        if isinstance(resp_code, int) and resp_code >= 400:
            msg = resp_json.get("message", str(resp_json))
            print(f"[SynVow GPT-Image-2] API error: {msg}")
            return (self._blank_image(), msg, "", self._format_history())

        # 结构: resp_json.data.data.data[].url
        def _extract_urls(d):
            if isinstance(d, list):
                return [item["url"] for item in d if isinstance(item, dict) and item.get("url")]
            if isinstance(d, dict):
                if "url" in d and d["url"]:
                    return [d["url"]]
                for key in ("data", "sourceData", "images"):
                    if key in d:
                        result = _extract_urls(d[key])
                        if result:
                            return result
            return []

        image_urls = _extract_urls(resp_json)

        image_urls_str = "\n".join(image_urls)
        if image_urls:
            SynVowGptImage2._last_image_urls = image_urls_str

        technical_response = (
            f"**Model**: {model}\n**Size**: {size}\n**Time**: {timestamp}"
        )
        SynVowGptImage2._conversation_history.append({"user": prompt, "ai": technical_response})
        chat_history = self._format_history()

        if image_urls:
            tensors = []
            for img_url in image_urls:
                try:
                    r = requests.get(img_url, timeout=120, verify=False)
                    r.raise_for_status()
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    arr = np.array(img).astype(np.float32) / 255.0
                    tensors.append(torch.from_numpy(arr).unsqueeze(0))
                except Exception as e:
                    print(f"[SynVow GPT-Image-2] 下载图片失败 {img_url}: {e}")
            if tensors:
                return (torch.cat(tensors, dim=0), technical_response, image_urls_str, chat_history)

        first_input = next((t for t in [image1, image2, image3, image4] if t is not None), None)
        if first_input is not None:
            return (first_input, technical_response, image_urls_str, chat_history)
        return (self._blank_image(), technical_response, image_urls_str, chat_history)


NODE_CLASS_MAPPINGS = {
    "SynVowGptImage2": SynVowGptImage2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowGptImage2": "SynVow GPT-Image-2",
}
