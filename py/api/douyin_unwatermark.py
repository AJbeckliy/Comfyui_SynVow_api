import base64
import glob
import os
import re
import requests

from . import synvow_auth
from .media_common import download_video

_SUBMIT_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/video/generate"

# 模型名（请求原样提交）
_MODEL_OPTIONS = [
    "抖音解析-qsy",
    "小红书",
    "视频号",
    "bilibili",
    "Youtube",
]
_DEFAULT_MODEL = "抖音解析-qsy"
_COOKIE_REQUIRED_MODELS = {"小红书"}
_CHANNEL_STYLE_MODELS = {"视频号", "bilibili"}

_FILE_PREFIX = {
    "抖音解析-qsy": "douyin",
    "小红书": "xhs",
    "视频号": "channels",
    "bilibili": "bilibili",
    "Youtube": "youtube",
}


def _extract_url(text):
    match = re.search(r"https?://\S+", text or "", re.I)
    if match:
        return match.group(0)
    t = (text or "").strip()
    return t if re.match(r"^https?://", t, re.I) else ""


def _encode_cookie_base64(cookie):
    trimmed = (cookie or "").strip()
    if not trimmed:
        return ""
    return base64.b64encode(trimmed.encode("utf-8")).decode("ascii")


def _extract_youtube_video_url(data):
    lists = data.get("video_lists") if isinstance(data, dict) else None
    if not isinstance(lists, list):
        return ""
    for item in lists:
        if isinstance(item, dict) and item.get("has_audio") and item.get("url"):
            return str(item["url"]).strip()
    if lists:
        last = lists[-1]
        if isinstance(last, dict) and last.get("url"):
            return str(last["url"]).strip()
    return ""


def _extract_remote_video_url(json_data, model):
    data = json_data.get("data") if isinstance(json_data, dict) else None
    if not isinstance(data, dict):
        data = {}

    if model == "Youtube":
        return _extract_youtube_video_url(data)

    if model == "小红书":
        return str(data.get("url") or "").strip()

    if model in _CHANNEL_STYLE_MODELS:
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        return str(data.get("video_url") or nested.get("video_url") or "").strip()

    # 抖音等：work_url
    return str(data.get("work_url") or "").strip()


class SynVowVideoParser:
    FUNCTION = "parse"
    CATEGORY = "💫SynVow_api/api/视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (_MODEL_OPTIONS, {"default": _DEFAULT_MODEL}),
                "url_text": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "视频链接，支持短链/分享文本（抖音/小红书/视频号/bilibili/Youtube）",
                    },
                ),
                "save_path": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "留空则保存至 output 目录，填入路径则保存至指定目录",
                    },
                ),
            },
            "optional": {
                "cookie": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "仅小红书需要：粘贴浏览器 Cookie（将自动 Base64）",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_url", "video_path", "status")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def parse(self, model, url_text, save_path, cookie=""):
        try:
            model = model or _DEFAULT_MODEL
            url = _extract_url(url_text)
            if not url:
                raise ValueError("未检测到有效链接，请输入视频链接或包含链接的分享文本")

            payload = {"model": model, "url": url}
            if model in _COOKIE_REQUIRED_MODELS:
                encoded = _encode_cookie_base64(cookie)
                if not encoded:
                    raise ValueError("小红书解析需要填写 cookie")
                payload["cookie"] = encoded

            api_key = synvow_auth.read_api_key()
            headers = synvow_auth.make_api_headers(api_key)
            print(f"[短视频解析] model={model} url={url[:60]}...")

            res = requests.post(
                _SUBMIT_URL,
                headers=headers,
                json=payload,
                timeout=60,
                verify=False,
            )
            if res.status_code != 200:
                body = {}
                try:
                    body = res.json()
                except Exception:
                    pass
                msg = body.get("message") or body.get("msg") or res.text[:200]
                raise Exception(f"HTTP {res.status_code}: {msg}")

            data = res.json()
            video_url = _extract_remote_video_url(data, model)
            if not video_url:
                raise Exception(f"响应中无视频 URL: {str(data)[:200]}")

            print(f"[短视频解析] 获取到视频链接: {video_url[:60]}...")

            prefix = _FILE_PREFIX.get(model, "video")
            out_dir = save_path.strip() if save_path and save_path.strip() else ""
            if not out_dir:
                try:
                    import folder_paths as _fp
                    out_dir = _fp.get_output_directory()
                except Exception:
                    pass
            existing = glob.glob(os.path.join(out_dir, f"{prefix}_*.mp4")) if out_dir else []
            idx = len(existing) + 1
            fname = f"{prefix}_{idx:05d}.mp4"
            video_path = download_video(video_url, prefix, save_path, prefix=prefix, filename=fname) or ""
            status = f"已完成 model={model}"

            synvow_auth.refresh_balance()
            return (video_url, video_path, status)

        except Exception as e:
            print(f"[短视频解析] Error: {e}")
            synvow_auth.refresh_balance()
            return ("", "", f"[ERROR] {e}")


NODE_CLASS_MAPPINGS = {
    "SynVowVideoParser": SynVowVideoParser,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVideoParser": "短视频解析",
}
