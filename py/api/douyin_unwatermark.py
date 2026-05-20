import os
import re
import requests

from . import synvow_auth
from .media_common import download_video

_SUBMIT_URL = f"{synvow_auth.DIRECT_API_BASE}/api/models/video/generate"
_MODEL_OPTIONS = ["抖音解析-qsy"]


def _extract_url(text):
    match = re.search(r"https?://\S+", text or "")
    return match.group(0) if match else ""


class SynVowVideoParser:
    FUNCTION = "parse"
    CATEGORY = "💫SynVow_api/api/视频"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": (_MODEL_OPTIONS, {"default": "抖音解析-qsy"}),
                "url_text": ("STRING", {"multiline": True, "default": "", "placeholder": "抖音链接，支持短链/分享文本"}),
                "save_path": ("STRING", {"multiline": False, "default": "", "placeholder": "留空则保存至 output 目录，填入路径则保存至指定目录"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_url", "video_path", "status")

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        import time
        return time.time()

    def parse(self, model, url_text, save_path):
        try:
            url = _extract_url(url_text)
            if not url:
                raise ValueError("未检测到有效链接，请输入抖音链接或包含链接的分享文本")

            api_key = synvow_auth.read_api_key()
            headers = synvow_auth.make_api_headers(api_key)
            print(f"[短视频解析] model={model} url={url[:60]}...")

            res = requests.post(
                _SUBMIT_URL,
                headers=headers,
                json={"model": model, "url": url},
                timeout=60,
                verify=False,
            )
            if res.status_code != 200:
                raise Exception(f"HTTP {res.status_code}: {res.text[:200]}")

            data = res.json()
            video_url = (data.get("data") or {}).get("work_url", "")
            if not video_url:
                raise Exception(f"响应中无视频 URL: {str(data)[:200]}")

            print(f"[短视频解析] 获取到视频链接: {video_url[:60]}...")

            import glob as _glob
            _out = save_path.strip() if save_path and save_path.strip() else ""
            if not _out:
                try:
                    import folder_paths as _fp
                    _out = _fp.get_output_directory()
                except Exception:
                    pass
            _existing = _glob.glob(os.path.join(_out, "douyin_*.mp4")) if _out else []
            _idx = len(_existing) + 1
            _fname = f"douyin_{_idx:05d}.mp4"
            video_path = download_video(video_url, "douyin", save_path, prefix="douyin", filename=_fname) or ""
            status = f"已完成 model={model}"

            try:
                import server
                server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
            except Exception:
                pass

            return (video_url, video_path, status)

        except Exception as e:
            print(f"[短视频解析] Error: {e}")
            try:
                import server
                server.PromptServer.instance.send_sync("synvow_refresh_balance", {})
            except Exception:
                pass
            return ("", "", f"[ERROR] {e}")


NODE_CLASS_MAPPINGS = {
    "SynVowVideoParser": SynVowVideoParser,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowVideoParser": "短视频解析",
}
